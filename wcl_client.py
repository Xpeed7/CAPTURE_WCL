"""WCL V2 GraphQL API 客户端"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import MAX_RETRIES, RATE_LIMIT_DELAY, REQUEST_TIMEOUT, WCL_GRAPHQL_URL, WCL_OAUTH_TOKEN_URL

logger = logging.getLogger(__name__)


class WCLAuthError(Exception):
    """WCL 认证失败"""


class WCLRateLimitError(Exception):
    """WCL API 限流"""


class WCLAPIError(Exception):
    """WCL API 请求失败"""


class WCLClient:
    """WCL V2 GraphQL API 客户端，支持 OAuth 认证"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = ""
        self._token_expires_at = 0.0
        self._http_client = httpx.Client(timeout=REQUEST_TIMEOUT)

    def authenticate(self) -> None:
        """使用 Client Credentials Flow 获取 access_token"""
        try:
            response = self._http_client.post(
                WCL_OAUTH_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
            logger.info("V2 认证成功，token 有效期 %s 秒", data.get("expires_in", 3600))
        except httpx.HTTPStatusError as e:
            raise WCLAuthError("认证失败: {} {}".format(e.response.status_code, e.response.text)) from e
        except httpx.RequestError as e:
            raise WCLAuthError("网络请求失败: {}".format(e)) from e

    def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._token_expires_at:
            logger.info("Token 过期或不存在，重新认证...")
            self.authenticate()

    @retry(
        retry=retry_if_exception_type((WCLRateLimitError, WCLAPIError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        reraise=True,
    )
    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行 GraphQL 查询"""
        self._ensure_token()
        try:
            response = self._http_client.post(
                WCL_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={"Authorization": "Bearer {}".format(self._access_token)},
            )
        except httpx.RequestError as e:
            raise WCLAPIError("网络请求失败: {}".format(e)) from e

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "30"))
            logger.warning("触发限流，等待 %d 秒后重试...", retry_after)
            raise WCLRateLimitError("Rate limited, retry after {}s".format(retry_after))

        if response.status_code != 200:
            raise WCLAPIError("API 返回错误: {} {}".format(response.status_code, response.text))

        result = response.json()
        if "errors" in result:
            error_msg = "; ".join(e.get("message", str(e)) for e in result["errors"])
            raise WCLAPIError("GraphQL 错误: {}".format(error_msg))

        time.sleep(RATE_LIMIT_DELAY)
        return result.get("data", {})

    def close(self) -> None:
        self._http_client.close()
