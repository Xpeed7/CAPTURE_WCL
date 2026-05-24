"""WCL V2 数据抓取编排"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import (
    CLASS_NAME,
    GEAR_SLOT_MAP,
    METRIC,
    NAXX_BOSSES,
    SERVER_REGION,
    SPEC_NAME,
)
from models import (
    BossRanking,
    BuffEvent,
    CastEvent,
    GearItem,
    PlayerDetail,
    PlayerRanking,
)
from queries import (
    GET_BUFFS_QUERY,
    GET_CASTS_QUERY,
    GET_FIGHTS_QUERY,
    GET_MASTER_DATA_QUERY,
    GET_PARTITIONS_QUERY,
    GET_PLAYER_DETAILS_QUERY,
    GET_RANKINGS_QUERY,
)
from wcl_client import WCLAPIError, WCLAuthError, WCLClient

logger = logging.getLogger(__name__)


class WCLFetcher:
    """WCL V2 数据抓取编排器"""

    def __init__(self, client: WCLClient):
        self.client = client
        self.naxx_zone_id: Optional[int] = None

    def find_naxx_zone_and_encounters(self) -> int:
        """通过 V2 API 直接查询 Naxxramas zone 获取 encounter IDs"""
        from config import NAXX_ZONE_ID
        logger.info("正在查询 Naxxramas zone (ID=%d)...", NAXX_ZONE_ID)

        query = """
        query ($zoneId: Int!) {
          worldData {
            zone(id: $zoneId) {
              id
              name
              encounters {
                id
                name
              }
            }
          }
        }
        """
        data = self.client.execute_query(query, {"zoneId": NAXX_ZONE_ID})
        zone = data.get("worldData", {}).get("zone", {})
        zone_id = zone.get("id", 0)
        zone_name = zone.get("name", "")
        encounters = zone.get("encounters", [])

        self.naxx_zone_id = zone_id
        logger.info("找到 Naxxramas: zone ID=%d, name=%s, encounters=%d", zone_id, zone_name, len(encounters))

        # 构建 encounter name -> id 映射
        encounter_map = {}
        for enc in encounters:
            encounter_map[enc["name"]] = enc["id"]

        # 匹配 boss 名称，更新 encounter_id
        matched = 0
        for boss in NAXX_BOSSES:
            eid = encounter_map.get(boss["name"])
            if eid:
                boss["encounter_id"] = eid
                logger.info("  %s -> encounter ID=%d", boss["name"], eid)
                matched += 1
            else:
                logger.warning("  未找到 encounter: %s", boss["name"])

        logger.info("匹配成功 %d/15 个 boss", matched)
        return zone_id

    def fetch_partitions(self) -> List[Dict[str, Any]]:
        """查询 Naxxramas 的分区列表"""
        if self.naxx_zone_id is None:
            raise WCLAPIError("Naxx zone ID 未设置")
        data = self.client.execute_query(
            GET_PARTITIONS_QUERY, {"zoneId": self.naxx_zone_id}
        )
        zone = data.get("worldData", {}).get("zone", {})
        partitions = zone.get("partitions", [])
        logger.info("分区数: %d", len(partitions))
        for p in partitions:
            logger.info("  partition: id=%s, name=%s, default=%s",
                        p.get("id"), p.get("name"), p.get("default"))
        return partitions

    def find_partition_id(self, partitions: List[Dict[str, Any]]) -> Optional[Any]:
        """找到合适的 partition ID"""
        # 优先使用 default partition
        for p in partitions:
            if p.get("default"):
                pid = p.get("id")
                logger.info("使用默认 partition: id=%s, name=%s", pid, p.get("name"))
                return pid
        if partitions:
            pid = partitions[0].get("id")
            logger.info("使用第一个 partition: id=%s", pid)
            return pid
        return None

    def fetch_boss_rankings(
        self, encounter_id: int, partition: Optional[Any] = None
    ) -> List[PlayerRanking]:
        """查询单个 Boss 的武器战士 DPS 排名"""
        variables: Dict[str, Any] = {
            "encounterId": int(encounter_id),
            "specName": SPEC_NAME,
            "className": CLASS_NAME,
            "metric": METRIC,
            "serverRegion": SERVER_REGION,
        }
        if partition is not None:
            variables["partition"] = int(partition)

        data = self.client.execute_query(GET_RANKINGS_QUERY, variables)
        encounter = data.get("worldData", {}).get("encounter", {})
        char_rankings = encounter.get("characterRankings")

        # characterRankings 返回 JSON 标量，可能是 dict 或 JSON 字符串
        import json as json_mod
        if isinstance(char_rankings, str):
            char_rankings = json_mod.loads(char_rankings)
        if not isinstance(char_rankings, dict):
            logger.warning("Boss ID=%d: characterRankings 返回格式异常: %s", encounter_id, type(char_rankings))
            return []

        raw_rankings = char_rankings.get("rankings", [])

        top3 = raw_rankings[:3]
        rankings = []
        for r in top3:
            start_time_ms = r.get("startTime", 0)
            date_str = ""
            if start_time_ms:
                date_str = datetime.fromtimestamp(
                    start_time_ms / 1000.0
                ).strftime("%Y-%m-%d")

            rankings.append(
                PlayerRanking(
                    name=r.get("name", ""),
                    dps=r.get("amount", 0),
                    date=date_str,
                    duration=self._format_duration(r.get("duration", 0)),
                    report_code=r.get("report", {}).get("code", ""),
                    fight_id=int(r.get("report", {}).get("fightID", 0)),
                    source_id=0,  # resolved later via masterData
                )
            )

        logger.info("Boss ID=%d: 获取到 %d 条排名（取前 3）", encounter_id, len(raw_rankings))
        return rankings

    def fetch_all_boss_rankings(self, partition: Optional[Any] = None) -> List[BossRanking]:
        """遍历 15 个 Boss，查询排名"""
        results = []
        for boss in NAXX_BOSSES:
            eid = boss["encounter_id"]
            if not eid:
                logger.warning("跳过 %s: 无 encounter ID", boss["name_cn"])
                results.append(BossRanking(
                    boss_name=boss["name"],
                    boss_name_cn=boss["name_cn"],
                    encounter_id=0,
                    rankings=[],
                ))
                continue
            try:
                rankings = self.fetch_boss_rankings(eid, partition)
                results.append(BossRanking(
                    boss_name=boss["name"],
                    boss_name_cn=boss["name_cn"],
                    encounter_id=eid,
                    rankings=rankings,
                ))
            except WCLAPIError as e:
                logger.error("Boss %s 查询失败: %s", boss["name_cn"], e)
                results.append(BossRanking(
                    boss_name=boss["name"],
                    boss_name_cn=boss["name_cn"],
                    encounter_id=eid,
                    rankings=[],
                ))
        return results

    def fetch_player_gear(
        self, report_code: str, fight_id: int, player_name: str
    ) -> List[GearItem]:
        """查询角色装备"""
        try:
            data = self.client.execute_query(
                GET_PLAYER_DETAILS_QUERY,
                {"code": report_code, "fightIds": [fight_id]},
            )
            player_details = (
                data.get("reportData", {})
                .get("report", {})
                .get("playerDetails")
            )

            if isinstance(player_details, str):
                import json as json_mod
                player_details = json_mod.loads(player_details)

            # 结构: {data: {playerDetails: {tanks: [...], healers: [...], dps: [...]}}}
            if isinstance(player_details, dict) and "data" in player_details:
                player_details = player_details["data"].get("playerDetails", {})

            # 遍历所有角色分类寻找目标
            for role_key in ("tanks", "healers", "dps"):
                players = player_details.get(role_key, []) if isinstance(player_details, dict) else []
                for pd in players:
                    if pd.get("name") == player_name:
                        combatant_info = pd.get("combatantInfo", {})
                        if combatant_info:
                            return self._parse_gear(combatant_info)
            return []
        except WCLAPIError as e:
            logger.error("获取装备失败 (report=%s): %s", report_code, e)
            return []

    def fetch_fights(self, report_code: str, fight_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """获取 report 中的 fights 列表"""
        variables: Dict[str, Any] = {"code": report_code}
        if fight_ids:
            variables["fightIds"] = fight_ids
        data = self.client.execute_query(GET_FIGHTS_QUERY, variables)
        fights = (
            data.get("reportData", {})
            .get("report", {})
            .get("fights", [])
        )
        return fights

    def lookup_source_id(self, report_code: str, player_name: str) -> int:
        """通过 masterData 查找角色的 sourceID"""
        data = self.client.execute_query(GET_MASTER_DATA_QUERY, {"code": report_code})
        actors = (
            data.get("reportData", {})
            .get("report", {})
            .get("masterData", {})
            .get("actors", [])
        )
        for actor in actors:
            if actor.get("name") == player_name:
                return actor.get("id", 0)
        return 0

    def fetch_player_casts(
        self, report_code: str, fight_id: int, source_id: int
    ) -> List[CastEvent]:
        """查询角色技能释放明细（events 端点，对应 WCL 分析-事件-施法）。"""
        try:
            import json as json_mod

            fight_start = 0
            fight_end = 0
            fights = self.fetch_fights(report_code, [fight_id])
            if fights:
                fight_start = int(fights[0].get("startTime", 0) or 0)
                fight_end = int(fights[0].get("endTime", 0) or 0)

            master_data = self.client.execute_query(
                GET_MASTER_DATA_QUERY, {"code": report_code}
            )
            report_master_data = (
                master_data.get("reportData", {})
                .get("report", {})
                .get("masterData", {})
            )
            ability_names = {
                int(a.get("gameID") or 0): a.get("name", "")
                for a in report_master_data.get("abilities", [])
                if isinstance(a, dict)
            }
            actor_names = {
                int(a.get("id") or 0): a.get("name", "")
                for a in report_master_data.get("actors", [])
                if isinstance(a, dict)
            }

            variables: Dict[str, Any] = {
                "code": report_code,
                "fightIds": [fight_id],
                "sourceId": source_id,
            }
            if fight_end:
                variables["endTime"] = float(fight_end)

            raw_events: List[Dict[str, Any]] = []
            while True:
                data = self.client.execute_query(GET_CASTS_QUERY, variables)
                events_page = (
                    data.get("reportData", {})
                    .get("report", {})
                    .get("events")
                )
                if isinstance(events_page, str):
                    events_page = json_mod.loads(events_page)

                if not isinstance(events_page, dict):
                    break

                page_data = events_page.get("data", [])
                if isinstance(page_data, str):
                    page_data = json_mod.loads(page_data)
                if isinstance(page_data, list):
                    raw_events.extend(e for e in page_data if isinstance(e, dict))

                next_page_timestamp = events_page.get("nextPageTimestamp")
                if not next_page_timestamp:
                    break
                if fight_end and int(next_page_timestamp) >= fight_end:
                    break
                if variables.get("startTime") == float(next_page_timestamp):
                    break
                variables["startTime"] = float(next_page_timestamp)

            casts: List[CastEvent] = []
            for event in sorted(raw_events, key=lambda e: e.get("timestamp", 0)):
                ability = event.get("ability", {})
                if not isinstance(ability, dict):
                    ability = {}
                target = event.get("target", {})
                if not isinstance(target, dict):
                    target = {}

                timestamp_ms = int(event.get("timestamp", 0) or 0)
                ability_id = int(
                    ability.get("guid")
                    or event.get("abilityGameID")
                    or event.get("abilityID")
                    or 0
                )
                target_id = int(event.get("targetID") or target.get("id") or 0)
                ability_name = (
                    ability.get("name")
                    or event.get("abilityName")
                    or ability_names.get(ability_id)
                    or "Unknown"
                )
                target_name = target.get("name") or actor_names.get(target_id, "")
                casts.append(
                    CastEvent(
                        ability_name=ability_name,
                        timestamp_ms=timestamp_ms,
                        time=self._format_relative_time(timestamp_ms - fight_start)
                        if fight_start
                        else str(timestamp_ms),
                        target_name=target_name,
                        ability_id=ability_id,
                    )
                )

            logger.info(
                "获取施法事件: report=%s fight=%d source=%d events=%d",
                report_code,
                fight_id,
                source_id,
                len(casts),
            )
            return casts
        except WCLAPIError as e:
            logger.error("获取技能失败: %s", e)
            return []

    def fetch_player_buffs(
        self, report_code: str, fight_id: int, source_id: int
    ) -> List[BuffEvent]:
        """查询角色获取的 Buff（table 端点）"""
        try:
            data = self.client.execute_query(
                GET_BUFFS_QUERY,
                {"code": report_code, "fightIds": [fight_id], "sourceId": source_id},
            )
            table = (
                data.get("reportData", {})
                .get("report", {})
                .get("table")
            )
            if isinstance(table, str):
                import json as json_mod
                table = json_mod.loads(table)

            entries = []
            if isinstance(table, dict):
                entries = table.get("data", {}).get("auras", [])

            return [
                BuffEvent(
                    buff_name=e.get("name", "Unknown"),
                    buff_id=int(e.get("id") or e.get("guid") or e.get("abilityGameID") or 0),
                    source="",
                    uptime_seconds=e.get("totalUptime", 0) / 1000.0,
                )
                for e in sorted(entries, key=lambda x: -x.get("totalUptime", 0))
            ]
        except WCLAPIError as e:
            logger.error("获取 Buff 失败: %s", e)
            return []

    def fetch_player_detail(self, player: PlayerRanking) -> PlayerDetail:
        """查询单个角色的完整详情"""
        gear = []
        casts = []
        buffs = []

        if not player.report_code or not player.fight_id:
            return PlayerDetail(name=player.name)

        # 1. 获取装备（通过 playerDetails，不需要 sourceID）
        gear = self.fetch_player_gear(
            player.report_code, player.fight_id, player.name
        )

        # 2. 通过 masterData 查找 sourceID（用于 casts/buffs 查询）
        source_id = 0
        try:
            source_id = self.lookup_source_id(player.report_code, player.name)
        except WCLAPIError as e:
            logger.error("查找 sourceID 失败: %s", e)

        # 3. 获取技能和 Buff
        if source_id:
            casts = self.fetch_player_casts(
                player.report_code, player.fight_id, source_id
            )
            buffs = self.fetch_player_buffs(
                player.report_code, player.fight_id, source_id
            )
        else:
            logger.warning("未找到 %s 在 report %s 中的 sourceID，跳过技能/Buff", player.name, player.report_code)

        return PlayerDetail(name=player.name, gear=gear, casts=casts, buffs=buffs)

    def fetch_all(self) -> tuple:
        """编排完整抓取流程"""
        # 1. 认证
        self.client.authenticate()

        # 2. 查找 Naxx zone 和 encounter IDs
        self.find_naxx_zone_and_encounters()

        # 3. 查询分区
        partitions = self.fetch_partitions()
        partition = self.find_partition_id(partitions)

        # 4. 查询所有 Boss 排名
        boss_rankings = self.fetch_all_boss_rankings(partition)

        # 5. 查询每个角色详情
        player_details: Dict[str, PlayerDetail] = {}
        for boss in boss_rankings:
            for player in boss.rankings:
                key = "{}/{}".format(boss.boss_name_cn, player.name)
                logger.info("正在获取角色详情: %s", key)
                detail = self.fetch_player_detail(player)
                player_details[key] = detail

        return boss_rankings, player_details

    @staticmethod
    def _parse_gear(combatant_info: Dict[str, Any]) -> List[GearItem]:
        """从 combatantInfo 解析装备"""
        gear = []
        gear_list = combatant_info.get("gear", [])
        for g in gear_list:
            slot_id = g.get("slot", -1)
            slot_name = GEAR_SLOT_MAP.get(slot_id, str(slot_id))
            enchant_raw = g.get("permanentEnchant", "")
            enchant_display = g.get("permanentEnchantName", "") or (str(enchant_raw) if enchant_raw else "")
            gems_raw = g.get("gems", [])
            gems_display = []
            for gem in gems_raw:
                if isinstance(gem, dict):
                    gems_display.append(gem.get("name", "gem#{}".format(gem.get("id", ""))))
                else:
                    gems_display.append(str(gem))
            gear.append(GearItem(
                slot=slot_name,
                name=g.get("name", ""),
                item_id=int(g.get("id") or 0),
                item_level=g.get("itemLevel", 0),
                enchant=enchant_display,
                gems=gems_display,
            ))
        return gear

    @staticmethod
    def _format_duration(milliseconds: float) -> str:
        """将毫秒格式化为 mm:ss"""
        if not milliseconds:
            return "00:00"
        total_seconds = int(milliseconds) // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return "{:02d}:{:02d}".format(minutes, seconds)

    @staticmethod
    def _format_relative_time(milliseconds: float) -> str:
        """将战斗内相对毫秒格式化为 m:ss.mmm。"""
        total_ms = max(int(milliseconds), 0)
        minutes = total_ms // 60000
        seconds = (total_ms % 60000) // 1000
        millis = total_ms % 1000
        return "{}:{:02d}.{:03d}".format(minutes, seconds, millis)
