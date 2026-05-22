# Tasks: WCL 时光服武器战士 DPS 榜单抓取工具

**Feature:** 001-wcl-arms-warrior-dps-ranking

---

## Phase 1: 项目基础设施

- [x] T001: 初始化 Python 项目 — 创建 `requirements.txt`，包含 `httpx`、`gql[httpx]`、`python-dotenv`、`tenacity` 依赖
- [x] T002: 创建 `.env.example` 文件 — 包含 `WCL_CLIENT_ID`、`WCL_CLIENT_SECRET` 模板
- [x] T003: 创建 `config.py` — 定义 WCL API 常量、Naxxramas Boss 列表（15个）、请求配置参数

## Phase 2: 数据模型

- [x] T004: 创建 `models.py` — 使用 dataclass 定义 `BossRanking`、`PlayerRanking`、`PlayerDetail`、`GearItem`、`CastEvent`、`BuffEvent` 数据模型

## Phase 3: WCL API 客户端

- [x] T005: 创建 `wcl_client.py` — 实现 `WCLClient` 类的 OAuth 认证（Client Credentials Flow）和 token 管理
- [x] T006: 在 `wcl_client.py` 中实现 GraphQL 查询执行方法，带重试机制和限流处理

## Phase 4: GraphQL 查询定义

- [x] T007: 创建 `queries.py` — 定义 `GET_PARTITIONS_QUERY`（查询 Naxxramas 分区）
- [x] T008: 在 `queries.py` 中定义 `GET_RANKINGS_QUERY`（查询 Boss 排名）
- [x] T009: 在 `queries.py` 中定义 `GET_PLAYER_DETAIL_QUERY`（查询角色装备详情）
- [x] T010: 在 `queries.py` 中定义 `GET_CASTS_QUERY` 和 `GET_BUFFS_QUERY`（查询技能释放和 Buff）

## Phase 5: 数据抓取编排

- [x] T011: 创建 `fetcher.py` — 实现 `WCLFetcher` 类，包含 `fetch_partitions()` 方法查询分区 ID
- [x] T012: 在 `fetcher.py` 中实现 `fetch_boss_rankings(encounter_id, partition_id)` 方法查询单个 Boss 排名
- [x] T013: 在 `fetcher.py` 中实现 `fetch_all_boss_rankings()` 方法遍历 15 个 Boss 查询排名
- [x] T014: 在 `fetcher.py` 中实现 `fetch_player_details()` 方法查询角色装备、技能、Buff
- [x] T015: 在 `fetcher.py` 中实现 `fetch_all()` 方法编排完整流程

## Phase 6: 输出格式化

- [x] T016: 创建 `formatter.py` — 实现 Markdown 表格格式化（Boss 排名表头：名字、秒伤、日期、用时）
- [x] T017: 在 `formatter.py` 中实现角色详情格式化（装备、技能、Buff）
- [x] T018: 在 `formatter.py` 中实现文件保存和双通道输出（控制台 + 文件）

## Phase 7: 入口与集成

- [x] T019: 创建 `main.py` — 加载配置、初始化客户端、调用 fetcher、格式化输出
- [ ] T020: 端到端测试 — 需要用户配置 WCL API 凭证后运行完整流程

---

## Task Dependencies

```
T001 → T005 → T006 → T011 → T012 → T013 → T015 → T019 → T020
T002 → T019
T003 → T005, T008
T004 → T012, T014, T016
T007 → T011
T009 → T014
T010 → T014
T016 → T017 → T018 → T019
```

## Parallelizable Tasks

- T001, T002, T003, T004 can run in parallel (no dependencies)
- T007, T008, T009, T010 can run in parallel after T001
