"""WCL 时光服武器战士 DPS 榜单抓取工具 - 入口"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

from fetcher import WCLFetcher
from formatter import format_all_details, format_player_details_html, format_rankings_html, format_rankings_table, print_to_console, save_to_file
from translations import save_missing_translations
from wcl_client import WCLAuthError, WCLAPIError, WCLClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    load_dotenv()

    client_id = os.getenv("WCL_CLIENT_ID", "")
    client_secret = os.getenv("WCL_CLIENT_SECRET", "")

    if not client_id or not client_secret or "here" in client_id:
        print("=" * 60)
        print("错误: 未配置 WCL V2 API 凭证")
        print()
        print("请在 .env 文件中填入以下内容：")
        print("  WCL_CLIENT_ID=你的client_id")
        print("  WCL_CLIENT_SECRET=你的client_secret")
        print()
        print("获取步骤：")
        print("1. 登录 https://www.warcraftlogs.com/")
        print("2. 前往 https://www.warcraftlogs.com/profile")
        print("3. 点击 API Clients -> Create Client")
        print("4. 填写应用名称和 Redirect URI")
        print("5. 获取 client_id 和 client_secret")
        print("=" * 60)
        return 1

    client = WCLClient(client_id, client_secret)
    fetcher = WCLFetcher(client)

    try:
        logger.info("开始抓取 WCL 时光服武器战士 DPS 榜单 (V2 API)...")
        boss_rankings, player_details = fetcher.fetch_all()

        # 格式化排名表格
        ranking_content = format_rankings_table(boss_rankings)
        print_to_console(ranking_content)

        # 保存排名到文件
        ranking_file = save_to_file(ranking_content)
        logger.info("排名数据已保存到: %s", ranking_file)

        # 生成 HTML 页面
        html_content = format_rankings_html(boss_rankings)
        html_file = save_to_file(html_content, "ranking_results.html")
        logger.info("HTML 页面已保存到: %s", html_file)

        # 格式化角色详情
        detail_content = format_all_details(boss_rankings, player_details)
        detail_file = save_to_file(detail_content, "player_details.md")
        logger.info("角色详情已保存到: %s", detail_file)

        # 生成角色详情 HTML 页面
        detail_html = format_player_details_html(boss_rankings, player_details)
        detail_html_file = save_to_file(detail_html, "player_details.html")
        logger.info("角色详情 HTML 已保存到: %s", detail_html_file)

        missing_file = save_missing_translations()
        logger.info("缺失翻译已保存到: %s", missing_file)

        logger.info("全部完成!")
        return 0

    except WCLAuthError as e:
        logger.error("认证失败: %s", e)
        return 1
    except WCLAPIError as e:
        logger.error("API 错误: %s", e)
        return 1
    except Exception:
        logger.exception("未知错误")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
