# Feature Spec: WCL 时光服武器战士 DPS 榜单抓取工具

**Feature ID:** 001
**Feature Name:** wcl-arms-warrior-dps-ranking
**Status:** Clarified
**Created:** 2026-04-30

---

## Overview

从 Warcraft Logs (WCL) 抓取魔兽世界时光服（Time Traveler）P3 阶段纳克萨玛斯（Naxxramas）中武器战士（Arms Warrior）的 DPS 榜单数据，并以表格形式输出，同时进一步抓取排名靠前角色的装备、技能释放和 Buff 获取信息。

## User Stories

### US-1: 获取各 Boss 的武器战士 DPS 排名

**作为**魔兽世界时光服玩家，
**我希望**能看到纳克萨玛斯 P3 阶段每个 Boss 的武器战士 DPS 前三名数据，
**以便**了解当前版本的顶级 DPS 表现和参考学习。

**验收标准：**
- AC-1.1: 覆盖纳克萨玛斯全部 15 个 Boss（每个 Boss 单独统计）
- AC-1.2: 每个 Boss 只取秒伤（DPS）最高的前 3 名角色
- AC-1.3: 数据来源为 WCL GraphQL API（`worldData.encounter.characterRankings`）
- AC-1.4: 必须限定为时光服分区（partition），CN 区域
- AC-1.5: 限定职业为 Warrior，天赋为 Arms

### US-2: 以表格形式输出 DPS 榜单

**作为**用户，
**我希望**DPS 榜单以清晰的表格形式输出，
**以便**快速浏览和对比不同 Boss 的顶级表现。

**验收标准：**
- AC-2.1: 表头格式为：名字（游戏ID），秒伤，日期，用时
- AC-2.2: 每个 Boss 单独一个表格
- AC-2.3: 输出格式为 Markdown 表格
- AC-2.4: 秒伤数值保留整数
- AC-2.5: 日期格式为 YYYY-MM-DD
- AC-2.6: 用时格式为 mm:ss

### US-3: 抓取角色详细信息

**作为**玩家，
**我希望**能进一步查看排名角色的装备、技能释放和 Buff 信息，
**以便**学习顶级玩家的配装和打法。

**验收标准：**
- AC-3.1: 能通过 WCL API 获取角色的装备信息（`includeCombatantInfo: true`）
- AC-3.2: 能获取角色的技能释放列表（通过 `reportData.report.events` with `dataType: Casts`）
- AC-3.3: 能获取角色获取的 Buff 列表（通过 `reportData.report.events` with `dataType: Buffs`）
- AC-3.4: 每个角色详情以结构化格式输出

---

## Functional Requirements

### FR-1: API 认证
- 系统需要支持 OAuth 2.0 Client Credentials Flow 认证
- 用户需配置 `client_id` 和 `client_secret`
- Token 获取后应缓存，过期前自动刷新

### FR-2: Boss 列表定义
- 纳克萨玛斯 15 个 Boss 及其 Encounter ID：

| Boss | Encounter ID | 中文 |
|------|-------------|------|
| Anub'Rekhan | 1107 | 阿努布雷坎 |
| Grand Widow Faerlina | 1110 | 黑女巫法琳娜 |
| Maexxna | 1116 | 迈克斯纳 |
| Patchwerk | 1118 | 帕奇维克 |
| Grobbulus | 1111 | 格罗布鲁斯 |
| Gluth | 1108 | 格拉斯 |
| Thaddius | 1120 | 塔迪乌斯 |
| Noth the Plaguebringer | 1117 | 药剂师诺斯 |
| Heigan the Unclean | 1112 | 肮脏的希尔盖 |
| Loatheb | 1115 | 洛欧塞布 |
| Instructor Razuvious | 1113 | 教官拉苏维奥斯 |
| Gothik the Harvester | 1109 | 收割者戈提克 |
| The Four Horsemen | 1121 | 天启四骑士 |
| Sapphiron | 1119 | 萨菲隆 |
| Kel'Thuzad | 1114 | 克尔苏加德 |

### FR-3: 数据查询参数
- `metric: dps`
- `specName: "Arms"`, `className: "Warrior"`
- `difficulty: 3`（需验证时光服对应的 difficulty 值）
- `serverRegion: "CN"`
- `page: 1`（只需前 3 名，第一页即可）
- `partition: <P3 对应的 partition ID>`（需通过 API 查询确认）

### FR-4: 角色详情查询
- 使用排名数据中的 `reportID`（fight 的 report code）和 `fightID`、`sourceID`（角色 actor ID）
- 通过 `reportData.report.events` 查询 Casts 和 Buffs 数据

### FR-5: 输出格式
- 主输出：Markdown 文件，包含所有 Boss 的 DPS 排名表格
- 角色详情：单独的 Markdown 文件或追加到主输出中

---

## Non-Functional Requirements

### NFR-1: 性能
- 15 个 Boss 的查询应支持顺序执行，避免 API 限流
- 请求间隔不低于 1 秒

### NFR-2: 错误处理
- API 请求失败应重试最多 3 次
- 网络超时设置为 30 秒
- 对限流（429）响应应等待后重试

### NFR-3: 配置管理
- API 凭证通过 `.env` 文件或环境变量配置
- 不将凭证硬编码到源代码中

---

## Constraints & Assumptions

### 约束
- WCL API 需要 OAuth 2.0 认证，用户必须自行注册 WCL 应用获取凭证
- 时光服 P3 的 partition ID 需要通过 API 动态查询确认
- WCL API 可能存在限流，需要合理控制请求频率

### 假设
- WCL 的 `characterRankings` 接口可以返回时光服的数据
- `includeCombatantInfo: true` 参数可以获取装备信息
- 角色的 report 数据可以公开访问

---

## Clarifications

### Q1: WCL API 凭证
**回答：** 用户还没有注册 WCL 应用。
**处理方案：** 需要在工具中提供 WCL 应用注册指引，并支持通过 `.env` 文件配置凭证。同时提供一种无需 API 的备选方案（网页爬虫），以降低使用门槛。

### Q2: 时光服版本确认
**回答：** 时光服（Time Traveler）标准版本，P3 阶段对应 Naxxramas。
**处理方案：** 通过 WCL API 查询 `worldData.zone(id: 1006).partitions` 确认 P3 对应的 partition ID，确保数据精确。

### Q3: 角色详情范围
**回答：** 每个 Boss 前 3 名全部查看。
**处理方案：** 对每个 Boss 的 top 3 角色均调用 report API 获取装备、技能释放和 Buff 信息。

### Q4: 输出格式
**回答：** 控制台直接输出 + Markdown 文件保存。
**处理方案：** 默认在终端打印结果，同时将完整结果保存到 `output/` 目录下的 Markdown 文件。

---

## Out of Scope

- 构建 Web 服务或 GUI 界面
- 实时监控或自动刷新
- 支持其他职业或天赋
- 支持其他副本或阶段
- 历史数据归档或趋势分析
