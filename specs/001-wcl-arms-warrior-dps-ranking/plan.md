# Implementation Plan: WCL 时光服武器战士 DPS 榜单抓取工具

**Feature:** 001-wcl-arms-warrior-dps-ranking
**Created:** 2026-04-30

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | 简洁、丰富的 HTTP 和数据处理库生态 |
| HTTP Client | `httpx` | 支持 async、HTTP/2、重试机制 |
| GraphQL Client | `gql` + `httpx` | 类型安全的 GraphQL 查询构建 |
| Env Config | `python-dotenv` | `.env` 文件加载，凭证管理 |
| Output | 标准库 `markdown` + 文件 I/O | Markdown 表格生成 |
| Retry | `tenacity` | 优雅的重试机制 |
| Logging | 标准库 `logging` | 内置日志模块，零依赖 |

---

## Architecture

```
capture_wcl/
├── .env                          # API 凭证配置
├── .env.example                  # 凭证模板
├── main.py                       # 入口脚本
├── config.py                     # 常量和配置
├── wcl_client.py                 # WCL GraphQL API 客户端
├── models.py                     # 数据模型（dataclass）
├── queries.py                    # GraphQL 查询语句定义
├── fetcher.py                    # 数据抓取逻辑编排
├── formatter.py                  # 输出格式化（Markdown 表格）
└── output/                       # 输出目录
    └── ranking_results.md        # 生成的结果文件
```

---

## Module Design

### 1. `config.py` — 常量与配置

- WCL API endpoints（OAuth token URL、GraphQL endpoint）
- Naxxramas Boss 列表（name, encounter_id, chinese_name）
- API 参数常量（spec、class、metric、region）
- 请求配置（timeout、retry count、rate limit delay）

### 2. `models.py` — 数据模型

使用 Python dataclass 定义：

```python
@dataclass
class BossRanking:
    boss_name: str
    boss_name_cn: str
    encounter_id: int
    rankings: list[PlayerRanking]

@dataclass
class PlayerRanking:
    name: str            # 游戏ID
    dps: float           # 秒伤
    date: str            # 日期
    duration: str        # 用时
    report_code: str     # WCL report code（用于查详情）
    fight_id: int        # 战斗 ID
    source_id: int       # 角色 actor ID

@dataclass
class PlayerDetail:
    name: str
    gear: list[GearItem]
    casts: list[CastEvent]
    buffs: list[BuffEvent]

@dataclass
class GearItem:
    slot: str
    name: str
    item_level: int
    enchant: str | None
    gems: list[str]

@dataclass
class CastEvent:
    ability_name: str
    timestamp: int
    count: int

@dataclass
class BuffEvent:
    buff_name: str
    source: str
    uptime: float  # 秒
```

### 3. `wcl_client.py` — API 客户端

核心类 `WCLClient`：

- `authenticate()` — 使用 Client Credentials Flow 获取 access_token
- `execute_query(query, variables)` — 执行 GraphQL 查询，带重试和限流处理
- `_refresh_token()` — Token 过期时自动刷新
- `_handle_rate_limit()` — 429 响应时等待重试

### 4. `queries.py` — GraphQL 查询

定义三个核心查询：

1. **`GET_PARTITIONS_QUERY`** — 查询 Naxxramas zone 的分区列表，确认 P3 partition ID
2. **`GET_RANKINGS_QUERY`** — 查询指定 Boss 的武器战士 DPS 排名（top 3）
3. **`GET_PLAYER_DETAIL_QUERY`** — 查询指定 report 中某角色的装备、技能和 Buff

### 5. `fetcher.py` — 数据抓取编排

核心类 `WCLFetcher`：

- `fetch_all_boss_rankings()` — 遍历 15 个 Boss，逐个查询排名
- `fetch_player_details(report_code, fight_id, source_id)` — 查询单个角色的详情
- `fetch_all()` — 编排完整流程：认证 → 查分区 → 查排名 → 查详情

### 6. `formatter.py` — 输出格式化

- `format_rankings_table(boss_rankings)` — 生成 Markdown 表格
- `format_player_detail(player_detail)` — 生成角色详情的 Markdown
- `save_to_file(content, filepath)` — 保存到文件
- `print_to_console(content)` — 控制台输出

### 7. `main.py` — 入口

- 加载 `.env` 配置
- 初始化 `WCLClient` 和 `WCLFetcher`
- 调用 `fetch_all()` 获取数据
- 调用 formatter 生成输出
- 保存文件并打印到控制台

---

## API Interaction Flow

```
1. OAuth2 Client Credentials Flow
   POST https://www.warcraftlogs.com/oauth/token
   → 获得 access_token

2. 查询分区
   GraphQL → worldData.zone(id: 1006).partitions
   → 确认 P3 partition ID

3. 查询每个 Boss 排名 (×15)
   GraphQL → worldData.encounter(id: X).characterRankings(
     specName: "Arms", className: "Warrior",
     metric: dps, serverRegion: "CN",
     partition: P3_ID, page: 1
   )
   → 每个 Boss 的 top 3 武器战士

4. 查询每个角色详情 (×45, 最多)
   GraphQL → reportData.report(code: X).playerDetails(
     fightIDs: [Y], includeCombatantInfo: true
   )
   GraphQL → reportData.report(code: X).events(
     fightIDs: [Y], dataType: Casts, sourceID: Z
   )
   GraphQL → reportData.report(code: X).events(
     fightIDs: [Y], dataType: Buffs, sourceID: Z
   )
   → 装备、技能释放、Buff

5. 格式化输出
   → Markdown 表格 + 控制台打印
```

---

## Error Handling Strategy

| Scenario | Action |
|----------|--------|
| OAuth 认证失败 | 提示用户检查 client_id/client_secret，给出注册指引 |
| API 请求超时 | 重试最多 3 次，间隔 5s |
| 429 Rate Limit | 读取 Retry-After header，等待后重试 |
| 某个 Boss 查询失败 | 记录错误，跳过该 Boss，继续查询其余 |
| 某个角色详情查询失败 | 记录错误，跳过该角色，继续查询其余 |
| Partition ID 未找到 | 提示用户确认时光服是否处于 P3 阶段 |
| 无排名数据 | 输出"该 Boss 暂无武器战士数据" |

---

## Rate Limiting

- 请求间隔：每次 API 请求后等待 1 秒
- 批量查询时使用 asyncio 的 `asyncio.sleep(1)` 控制节奏
- 遇到 429 时，等待 `Retry-After` header 指定的时间（默认 60s）
