"""WCL 数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GearItem:
    slot: str
    name: str
    item_level: int = 0
    enchant: Optional[str] = None
    gems: List[str] = field(default_factory=list)


@dataclass
class CastEvent:
    ability_name: str
    timestamp_ms: int = 0
    time: str = ""
    target_name: str = ""
    ability_id: int = 0
    count: int = 0


@dataclass
class BuffEvent:
    buff_name: str
    source: str = ""
    uptime_seconds: float = 0.0


@dataclass
class PlayerRanking:
    name: str
    dps: float
    date: str
    duration: str
    report_code: str
    fight_id: int = 0
    source_id: int = 0
    _combatant_info: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class BossRanking:
    boss_name: str
    boss_name_cn: str
    encounter_id: int
    rankings: List[PlayerRanking] = field(default_factory=list)


@dataclass
class PlayerDetail:
    name: str
    gear: List[GearItem] = field(default_factory=list)
    casts: List[CastEvent] = field(default_factory=list)
    buffs: List[BuffEvent] = field(default_factory=list)
