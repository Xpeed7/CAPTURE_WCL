"""WCL V2 API 常量与配置"""

# WCL V2 GraphQL API Endpoints (Titan = Chinese Time Traveler servers)
WCL_OAUTH_TOKEN_URL = "https://titan.warcraftlogs.com/oauth/token"
WCL_GRAPHQL_URL = "https://titan.warcraftlogs.com/api/v2/client"

# Naxxramas Zone ID (时光服 WotLK: 纳克萨玛斯/黑曜圣所/永恒之眼)
NAXX_ZONE_ID = 1053

# 查询参数
SPEC_NAME = "Arms"
CLASS_NAME = "Warrior"
METRIC = "dps"
SERVER_REGION = "CN"

# 请求配置
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1.0

# Naxxramas Boss 列表 (V2 encounter IDs, 运行时通过 API 自动查询填充)
NAXX_BOSSES = [
    {"name": "Anub'Rekhan", "encounter_id": 0, "name_cn": "阿努布雷坎"},
    {"name": "Grand Widow Faerlina", "encounter_id": 0, "name_cn": "黑女巫法琳娜"},
    {"name": "Maexxna", "encounter_id": 0, "name_cn": "迈克斯纳"},
    {"name": "Patchwerk", "encounter_id": 0, "name_cn": "帕奇维克"},
    {"name": "Grobbulus", "encounter_id": 0, "name_cn": "格罗布鲁斯"},
    {"name": "Gluth", "encounter_id": 0, "name_cn": "格拉斯"},
    {"name": "Thaddius", "encounter_id": 0, "name_cn": "塔迪乌斯"},
    {"name": "Noth the Plaguebringer", "encounter_id": 0, "name_cn": "药剂师诺斯"},
    {"name": "Heigan the Unclean", "encounter_id": 0, "name_cn": "肮脏的希尔盖"},
    {"name": "Loatheb", "encounter_id": 0, "name_cn": "洛欧塞布"},
    {"name": "Instructor Razuvious", "encounter_id": 0, "name_cn": "教官拉苏维奥斯"},
    {"name": "Gothik the Harvester", "encounter_id": 0, "name_cn": "收割者戈提克"},
    {"name": "The Four Horsemen", "encounter_id": 0, "name_cn": "天启四骑士"},
    {"name": "Sapphiron", "encounter_id": 0, "name_cn": "萨菲隆"},
    {"name": "Kel'Thuzad", "encounter_id": 0, "name_cn": "克尔苏加德"},
]

# 装备槽位 ID -> 中文名称映射
GEAR_SLOT_MAP = {
    0: "头部",
    1: "颈部",
    2: "肩部",
    3: "背部",
    4: "胸部",
    5: "护腕",
    6: "手套",
    7: "腰带",
    8: "腿部",
    9: "脚部",
    10: "戒指1",
    11: "戒指2",
    12: "饰品1",
    13: "饰品2",
    14: "主手",
    15: "副手",
    16: "远程",
    17: "圣物",
    18: "战袍",
}

# 输出目录
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "ranking_results.md"
