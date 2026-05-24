"""输出格式化：Markdown 表格 + HTML + 控制台"""

from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Dict, List

from config import OUTPUT_DIR, OUTPUT_FILENAME
from models import BossRanking, PlayerDetail, TimelineEvent, TimelineWindow
from translations import translator


TIMELINE_KIND_LABELS = {
    "cast": "释放技能",
    "buff_apply": "获得 Buff",
    "buff_remove": "移除 Buff",
    "buff_refresh": "刷新 Buff",
    "debuff_apply": "获得 Debuff",
    "debuff_remove": "移除 Debuff",
    "debuff_refresh": "刷新 Debuff",
}


def _translate_timeline_name(event_or_window: TimelineEvent | TimelineWindow) -> str:
    if event_or_window.kind == "cast":
        return translator.translate_ability(event_or_window.ability_id, event_or_window.name)
    return translator.translate_buff(event_or_window.ability_id, event_or_window.name)


def _translate_timeline_actor(name: str) -> str:
    return translator.translate_actor(name) if name else "-"


def _timeline_position(timestamp_ms: int, duration_ms: int) -> float:
    if not duration_ms:
        return 0.0
    return max(0.0, min(100.0, timestamp_ms / duration_ms * 100.0))


def format_rankings_table(boss_rankings: List[BossRanking]) -> str:
    """将所有 Boss 的排名格式化为 Markdown 表格"""
    lines: List[str] = []

    lines.append("# WCL 时光服武器战士 DPS 榜单")
    lines.append("生成时间: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    lines.append("职业: 武器战士 (Arms Warrior)")
    lines.append("副本: 纳克萨玛斯 (Naxxramas) P3")
    lines.append("")

    total_players = sum(len(b.rankings) for b in boss_rankings)
    lines.append("共 {} 个 Boss，{} 条排名数据".format(len(boss_rankings), total_players))
    lines.append("")

    for boss in boss_rankings:
        lines.append("## {} ({})".format(boss.boss_name_cn, boss.boss_name))
        lines.append("")

        if not boss.rankings:
            lines.append("> 该 Boss 暂无武器战士数据")
            lines.append("")
            continue

        lines.append("| 排名 | 名字（游戏ID） | 秒伤 | 日期 | 用时 |")
        lines.append("|------|---------------|------|------|------|")

        for i, player in enumerate(boss.rankings, 1):
            date_display = player.date if player.date else "-"
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    i, player.name, int(player.dps), date_display, player.duration
                )
            )

        lines.append("")

    return "\n".join(lines)


def format_player_detail(
    boss_name_cn: str, player_name: str, detail: PlayerDetail
) -> str:
    """格式化单个角色的详情"""
    lines: List[str] = []

    lines.append("### {} - {}".format(boss_name_cn, player_name))
    lines.append("")

    # 装备
    lines.append("#### 装备")
    lines.append("")
    if detail.gear:
        lines.append("| 部位 | 名称 | 物品等级 | 附魔 | 宝石 |")
        lines.append("|------|------|---------|------|------|")
        for g in detail.gear:
            item_name = translator.translate_item(g.item_id, g.name)
            gems_str = ", ".join(g.gems) if g.gems else "-"
            enchant_str = translator.translate_enchant(g.enchant) if g.enchant else "-"
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    g.slot, item_name, g.item_level, enchant_str, gems_str
                )
            )
    else:
        lines.append("> 未获取到装备数据")
    lines.append("")

    # 技能释放
    lines.append("#### 技能释放")
    lines.append("")
    if detail.casts:
        lines.append("| 时间 | 技能 | 目标 |")
        lines.append("|------|------|------|")
        for c in detail.casts:
            ability_name = translator.translate_ability(c.ability_id, c.ability_name)
            target = translator.translate_actor(c.target_name) if c.target_name else "-"
            lines.append("| {} | {} | {} |".format(c.time, ability_name, target))
    else:
        lines.append("> 未获取到技能数据")
    lines.append("")

    # Timeline
    lines.append("#### 爆发时间轴")
    lines.append("")
    if detail.timeline_events:
        lines.append("| 时间 | 类型 | 名称 | 来源 | 目标 |")
        lines.append("|------|------|------|------|------|")
        for event in detail.timeline_events:
            name = _translate_timeline_name(event)
            kind = TIMELINE_KIND_LABELS.get(event.kind, event.kind)
            source = _translate_timeline_actor(event.source)
            target = _translate_timeline_actor(event.target)
            lines.append("| {} | {} | {} | {} | {} |".format(
                event.time, kind, name, source, target
            ))
    else:
        lines.append("> 未获取到关键 Buff/Debuff 时间轴数据")
    lines.append("")

    return "\n".join(lines)


def format_all_details(
    boss_rankings: List[BossRanking],
    player_details: Dict[str, PlayerDetail],
) -> str:
    """格式化所有角色详情"""
    lines: List[str] = []
    lines.append("# 武器战士角色详情")
    lines.append("")
    lines.append("---")
    lines.append("")

    for boss in boss_rankings:
        for player in boss.rankings:
            key = "{}/{}".format(boss.boss_name_cn, player.name)
            detail = player_details.get(key)
            if detail:
                lines.append(
                    format_player_detail(boss.boss_name_cn, player.name, detail)
                )
            else:
                lines.append("### {} - {}".format(boss.boss_name_cn, player.name))
                lines.append("")
                lines.append("> 未获取到角色详情")
                lines.append("")

    return "\n".join(lines)


def format_rankings_html(boss_rankings: List[BossRanking]) -> str:
    """将排名数据格式化为精美的 HTML 页面"""
    total_players = sum(len(b.rankings) for b in boss_rankings)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 计算全局最大 DPS（用于进度条比例）
    max_dps = max(
        (p.dps for b in boss_rankings for p in b.rankings), default=1
    )

    boss_cards = ""
    for boss in boss_rankings:
        safe_cn = html.escape(boss.boss_name_cn)
        safe_en = html.escape(boss.boss_name)

        if not boss.rankings:
            boss_cards += f"""
        <div class="boss-card">
          <div class="boss-header">
            <span class="boss-name">{safe_cn}</span>
            <span class="boss-name-en">{safe_en}</span>
          </div>
          <div class="no-data">暂无武器战士数据</div>
        </div>"""
            continue

        rows = ""
        for i, p in enumerate(boss.rankings, 1):
            medal_class = ["gold", "silver", "bronze"][i - 1] if i <= 3 else ""
            medal_icon = ["&#x1F947;", "&#x1F948;", "&#x1F949;"][i - 1] if i <= 3 else str(i)
            bar_pct = int(p.dps / max_dps * 100)
            safe_name = html.escape(p.name)
            date_display = p.date if p.date else "-"
            rows += f"""
              <div class="player-row {medal_class}">
                <div class="rank-cell">{medal_icon}</div>
                <div class="name-cell">{safe_name}</div>
                <div class="dps-cell">
                  <div class="dps-bar-container">
                    <div class="dps-bar" style="width:{bar_pct}%"></div>
                  </div>
                  <span class="dps-value">{int(p.dps):,}</span>
                </div>
                <div class="date-cell">{date_display}</div>
                <div class="duration-cell">{p.duration}</div>
              </div>"""

        boss_cards += f"""
        <div class="boss-card">
          <div class="boss-header">
            <span class="boss-name">{safe_cn}</span>
            <span class="boss-name-en">{safe_en}</span>
          </div>
          <div class="table-header">
            <div class="rank-cell">排名</div>
            <div class="name-cell">名字</div>
            <div class="dps-cell">秒伤</div>
            <div class="date-cell">日期</div>
            <div class="duration-cell">用时</div>
          </div>
          <div class="player-rows">{rows}
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WCL 时光服武器战士 DPS 榜单</title>
<style>
  :root {{
    --bg-primary: #0a0e17;
    --bg-card: #141a2a;
    --bg-row: #1a2236;
    --bg-row-hover: #222d45;
    --border-color: #2a3550;
    --text-primary: #e8eaf0;
    --text-secondary: #8892a8;
    --text-muted: #5a6478;
    --gold: #ffd700;
    --gold-bg: rgba(255,215,0,0.08);
    --silver: #c0c0c0;
    --silver-bg: rgba(192,192,192,0.06);
    --bronze: #cd7f32;
    --bronze-bg: rgba(205,127,50,0.06);
    --bar-gold: linear-gradient(90deg, #ffd700, #ffaa00);
    --bar-silver: linear-gradient(90deg, #c0c0c0, #a0a0c0);
    --bar-bronze: linear-gradient(90deg, #cd7f32, #b06820);
    --bar-normal: linear-gradient(90deg, #4a7cff, #3a5fd9);
    --accent: #4a7cff;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
  }}

  .container {{
    max-width: 960px;
    margin: 0 auto;
  }}

  /* Header */
  .page-header {{
    text-align: center;
    padding: 40px 20px 30px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 30px;
  }}
  .page-header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }}
  .page-header h1 span {{
    color: var(--accent);
  }}
  .page-header .subtitle {{
    color: var(--text-secondary);
    font-size: 14px;
  }}
  .meta-bar {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
    flex-wrap: wrap;
  }}
  .meta-item {{
    font-size: 13px;
    color: var(--text-muted);
  }}
  .meta-item strong {{
    color: var(--text-secondary);
  }}

  /* Boss Card */
  .boss-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    margin-bottom: 20px;
    overflow: hidden;
  }}
  .boss-header {{
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 14px 20px;
    background: rgba(74,124,255,0.06);
    border-bottom: 1px solid var(--border-color);
  }}
  .boss-name {{
    font-size: 17px;
    font-weight: 600;
  }}
  .boss-name-en {{
    font-size: 12px;
    color: var(--text-muted);
  }}
  .no-data {{
    padding: 24px 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 14px;
  }}

  /* Table Layout */
  .table-header {{
    display: flex;
    align-items: center;
    padding: 8px 20px;
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border-color);
  }}
  .player-row {{
    display: flex;
    align-items: center;
    padding: 10px 20px;
    border-bottom: 1px solid rgba(42,53,80,0.5);
    transition: background 0.15s;
  }}
  .player-row:last-child {{ border-bottom: none; }}
  .player-row:hover {{ background: var(--bg-row-hover); }}

  .player-row.gold {{ background: var(--gold-bg); }}
  .player-row.gold:hover {{ background: rgba(255,215,0,0.14); }}
  .player-row.silver {{ background: var(--silver-bg); }}
  .player-row.silver:hover {{ background: rgba(192,192,192,0.1); }}
  .player-row.bronze {{ background: var(--bronze-bg); }}
  .player-row.bronze:hover {{ background: rgba(205,127,50,0.1); }}

  .rank-cell {{ width: 50px; text-align: center; flex-shrink: 0; }}
  .name-cell {{ width: 140px; flex-shrink: 0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .dps-cell {{ flex: 1; display: flex; align-items: center; gap: 10px; min-width: 0; }}
  .date-cell {{ width: 100px; text-align: center; flex-shrink: 0; font-size: 13px; color: var(--text-secondary); }}
  .duration-cell {{ width: 60px; text-align: center; flex-shrink: 0; font-size: 13px; color: var(--text-secondary); }}

  .gold .rank-cell {{ font-size: 18px; }}
  .silver .rank-cell {{ font-size: 18px; }}
  .bronze .rank-cell {{ font-size: 18px; }}

  /* DPS Bar */
  .dps-bar-container {{
    flex: 1;
    height: 8px;
    background: rgba(255,255,255,0.05);
    border-radius: 4px;
    overflow: hidden;
  }}
  .dps-bar {{
    height: 100%;
    border-radius: 4px;
    background: var(--bar-normal);
    transition: width 0.3s;
  }}
  .gold .dps-bar {{ background: var(--bar-gold); }}
  .silver .dps-bar {{ background: var(--bar-silver); }}
  .bronze .dps-bar {{ background: var(--bar-bronze); }}

  .dps-value {{
    font-weight: 600;
    font-size: 14px;
    white-space: nowrap;
    min-width: 60px;
    text-align: right;
  }}

  /* Footer */
  .page-footer {{
    text-align: center;
    padding: 24px 0 10px;
    font-size: 12px;
    color: var(--text-muted);
  }}
  .page-footer a {{
    color: var(--accent);
    text-decoration: none;
  }}
  .page-footer a:hover {{ text-decoration: underline; }}

  @media (max-width: 640px) {{
    body {{ padding: 10px; }}
    .page-header h1 {{ font-size: 22px; }}
    .boss-header {{ padding: 12px 14px; }}
    .player-row {{ padding: 8px 14px; }}
    .name-cell {{ width: 100px; font-size: 13px; }}
    .date-cell {{ width: 80px; font-size: 12px; }}
    .duration-cell {{ width: 50px; font-size: 12px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header class="page-header">
    <h1>WCL 时光服<span>武器战士</span>DPS 榜单</h1>
    <div class="subtitle">纳克萨玛斯 (Naxxramas) Phase 3</div>
    <div class="meta-bar">
      <span class="meta-item">共 <strong>{len(boss_rankings)}</strong> 个 Boss</span>
      <span class="meta-item"><strong>{total_players}</strong> 条排名数据</span>
      <span class="meta-item">生成于 <strong>{gen_time}</strong></span>
    </div>
  </header>

  <main class="boss-list">
{boss_cards}
  </main>

  <footer class="page-footer">
    数据来源 <a href="https://cn.titan.warcraftlogs.com" target="_blank">Warcraft Logs</a>
  </footer>
</div>
</body>
</html>"""


def _format_timeline_html(detail: PlayerDetail) -> str:
    if not detail.timeline_events and not detail.timeline_windows:
        return '<div class="no-data">未获取到关键 Buff/Debuff 时间轴数据</div>'

    duration_ms = detail.fight_duration_ms or max(
        [e.timestamp_ms for e in detail.timeline_events] +
        [w.end_ms for w in detail.timeline_windows] +
        [1]
    )

    lane_rows = ""
    for window in detail.timeline_windows:
        start_pct = _timeline_position(window.start_ms, duration_ms)
        end_pct = _timeline_position(window.end_ms, duration_ms)
        width_pct = max(end_pct - start_pct, 0.6)
        name = _translate_timeline_name(window)
        source = _translate_timeline_actor(window.source)
        target = _translate_timeline_actor(window.target)
        lane_class = "debuff-lane" if window.kind == "debuff" else "buff-lane"
        lane_rows += """
                <div class="timeline-lane {lane_class}">
                  <div class="lane-label" title="{title}">{name}</div>
                  <div class="lane-track">
                    <div class="window-segment {kind}" style="left:{left:.3f}%;width:{width:.3f}%;" title="{title}: {start} - {end}"></div>
                  </div>
                  <div class="lane-meta">{start} - {end}</div>
                </div>""".format(
            lane_class=lane_class,
            kind=html.escape(window.kind),
            left=start_pct,
            width=width_pct,
            name=html.escape(name),
            title=html.escape("{} / {} -> {}".format(name, source, target)),
            start=html.escape(window.start_time),
            end=html.escape(window.end_time),
        )

    cast_markers = ""
    for event in detail.timeline_events:
        if event.kind != "cast":
            continue
        left_pct = _timeline_position(event.timestamp_ms, duration_ms)
        name = _translate_timeline_name(event)
        cast_markers += """
                  <span class="cast-marker" style="left:{left:.3f}%;" title="{time} {name}"></span>""".format(
            left=left_pct,
            time=html.escape(event.time),
            name=html.escape(name),
        )

    event_rows = ""
    for event in detail.timeline_events:
        name = _translate_timeline_name(event)
        kind = TIMELINE_KIND_LABELS.get(event.kind, event.kind)
        source = _translate_timeline_actor(event.source)
        target = _translate_timeline_actor(event.target)
        row_class = event.kind.replace("_", "-")
        event_rows += """
                  <tr class="{row_class}">
                    <td class="time-cell">{time}</td>
                    <td><span class="event-pill {row_class}">{kind}</span></td>
                    <td class="ability-cell">{name}</td>
                    <td>{source}</td>
                    <td>{target}</td>
                    <td class="ability-id-cell">{ability_id}</td>
                  </tr>""".format(
            row_class=html.escape(row_class),
            time=html.escape(event.time),
            kind=html.escape(kind),
            name=html.escape(name),
            source=html.escape(source),
            target=html.escape(target),
            ability_id=event.ability_id or "-",
        )

    if not lane_rows:
        lane_rows = '<div class="no-data compact">未发现关键 Buff/Debuff 覆盖区间</div>'
    if not cast_markers:
        cast_markers = '<span class="timeline-empty-note">未发现关键技能释放点</span>'

    return """
            <div class="burst-timeline">
              <div class="timeline-summary">
                <span>关键覆盖 {window_count}</span>
                <span>关键事件 {event_count}</span>
                <span>战斗时长 {duration}</span>
              </div>
              <div class="timeline-board">
                <div class="cast-track">
                  <div class="lane-label">关键技能</div>
                  <div class="lane-track marker-track">{markers}</div>
                  <div class="lane-meta"></div>
                </div>
                {lanes}
              </div>
              <div class="event-table-wrap timeline-events">
                <table class="data-table event-table">
                  <thead><tr><th>时间</th><th>类型</th><th>名称</th><th>来源</th><th>目标</th><th>ID</th></tr></thead>
                  <tbody>{rows}</tbody>
                </table>
              </div>
            </div>""".format(
        window_count=len(detail.timeline_windows),
        event_count=len(detail.timeline_events),
        duration=_format_timeline_duration(duration_ms),
        markers=cast_markers,
        lanes=lane_rows,
        rows=event_rows,
    )


def _format_timeline_duration(duration_ms: int) -> str:
    total_seconds = max(int(duration_ms), 0) / 1000.0
    return "{:.1f}s".format(total_seconds)


def format_player_details_html(
    boss_rankings: List[BossRanking],
    player_details: Dict[str, PlayerDetail],
) -> str:
    """将角色详情格式化为精美的 HTML 页面"""
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_players = sum(len(b.rankings) for b in boss_rankings)

    boss_sections = ""
    for boss in boss_rankings:
        safe_boss_cn = html.escape(boss.boss_name_cn)
        safe_boss_en = html.escape(boss.boss_name)

        player_cards = ""
        for player in boss.rankings:
            key = "{}/{}".format(boss.boss_name_cn, player.name)
            detail = player_details.get(key)
            safe_name = html.escape(player.name)

            if not detail or (
                not detail.gear
                and not detail.casts
                and not detail.timeline_events
                and not detail.timeline_windows
            ):
                player_cards += """
            <div class="player-card">
              <div class="player-header">
                <span class="player-name">{name}</span>
                <span class="player-dps">{dps:,} DPS</span>
              </div>
              <div class="no-data">暂无详情数据</div>
            </div>""".format(name=safe_name, dps=int(player.dps))
                continue

            # Gear table
            gear_html = '<div class="no-data">未获取到装备数据</div>'
            if detail.gear:
                gear_rows = ""
                for g in detail.gear:
                    item_name = translator.translate_item(g.item_id, g.name)
                    enchant = translator.translate_enchant(g.enchant) if g.enchant else "-"
                    enchant_str = html.escape(enchant) if enchant else "-"
                    gems_str = ", ".join(html.escape(str(gem)) for gem in g.gems) if g.gems else "-"
                    gear_rows += """
                  <tr>
                    <td class="slot-cell">{slot}</td>
                    <td class="item-cell">{name}</td>
                    <td class="ilvl-cell">{ilvl}</td>
                    <td>{enchant}</td>
                    <td>{gems}</td>
                  </tr>""".format(
                        slot=html.escape(g.slot),
                        name=html.escape(item_name),
                        ilvl=g.item_level,
                        enchant=enchant_str,
                        gems=gems_str,
                    )
                gear_html = """
            <table class="data-table gear-table">
              <thead><tr><th>部位</th><th>名称</th><th>物等</th><th>附魔</th><th>宝石</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>""".format(rows=gear_rows)

            # Casts table
            casts_html = '<div class="no-data">未获取到技能数据</div>'
            if detail.casts:
                cast_rows = ""
                for c in detail.casts:
                    ability_name = translator.translate_ability(c.ability_id, c.ability_name)
                    target_name = translator.translate_actor(c.target_name) if c.target_name else ""
                    target = html.escape(target_name) if target_name else "-"
                    ability_id = str(c.ability_id) if c.ability_id else "-"
                    cast_rows += """
                  <tr>
                    <td class="time-cell">{time}</td>
                    <td class="ability-cell">{name}</td>
                    <td>{target}</td>
                    <td class="ability-id-cell">{ability_id}</td>
                  </tr>""".format(
                        time=html.escape(c.time),
                        name=html.escape(ability_name),
                        target=target,
                        ability_id=ability_id,
                    )
                casts_html = """
            <div class="event-table-wrap">
              <table class="data-table event-table">
                <thead><tr><th>时间</th><th>技能</th><th>目标</th><th>ID</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>""".format(rows=cast_rows)

            timeline_html = _format_timeline_html(detail)

            player_cards += """
            <div class="player-card">
              <div class="player-header">
                <span class="player-name">{name}</span>
                <span class="player-dps">{dps:,} DPS</span>
              </div>
              <div class="detail-sections">
                <details open>
                  <summary><span class="section-icon">&#x2694;</span> 装备</summary>
                  {gear}
                </details>
                <details>
                  <summary><span class="section-icon">&#x2728;</span> 技能释放</summary>
                  {casts}
                </details>
                <details>
                  <summary><span class="section-icon">&#x23F1;</span> 爆发时间轴</summary>
                  {timeline}
                </details>
              </div>
            </div>""".format(
                name=safe_name,
                dps=int(player.dps),
                gear=gear_html,
                casts=casts_html,
                timeline=timeline_html,
            )

        if not boss.rankings:
            boss_sections += """
        <div class="boss-section">
          <div class="boss-header">
            <span class="boss-name">{cn}</span>
            <span class="boss-name-en">{en}</span>
          </div>
          <div class="no-data">暂无武器战士数据</div>
        </div>""".format(cn=safe_boss_cn, en=safe_boss_en)
        else:
            boss_sections += """
        <div class="boss-section">
          <div class="boss-header">
            <span class="boss-name">{cn}</span>
            <span class="boss-name-en">{en}</span>
            <span class="boss-count">{cnt} 名玩家</span>
          </div>
          <div class="player-grid">
            {cards}
          </div>
        </div>""".format(
                cn=safe_boss_cn,
                en=safe_boss_en,
                cnt=len(boss.rankings),
                cards=player_cards,
            )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>武器战士角色详情 - WCL 时光服</title>
<style>
  :root {{
    --bg-primary: #0a0e17;
    --bg-card: #141a2a;
    --bg-card-alt: #111724;
    --bg-row-hover: #1e2840;
    --bg-row-even: #161d30;
    --border-color: #2a3550;
    --border-light: rgba(42,53,80,0.5);
    --text-primary: #e8eaf0;
    --text-secondary: #8892a8;
    --text-muted: #5a6478;
    --accent: #4a7cff;
    --accent-dim: rgba(74,124,255,0.1);
    --cast-bar: linear-gradient(90deg, #4a7cff, #6c5ce7);
    --buff-bar: linear-gradient(90deg, #00b894, #55efc4);
    --ilvl-epic: #a335ee;
    --ilvl-legendary: #ff8000;
    --ilvl-rare: #0070dd;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 20px;
    min-height: 100vh;
  }}

  .container {{ max-width: 1400px; margin: 0 auto; }}

  /* Page header */
  .page-header {{
    text-align: center;
    padding: 40px 20px 30px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 30px;
  }}
  .page-header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }}
  .page-header h1 span {{ color: var(--accent); }}
  .page-header .subtitle {{
    color: var(--text-secondary);
    font-size: 14px;
  }}
  .meta-bar {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
    flex-wrap: wrap;
  }}
  .meta-item {{
    font-size: 13px;
    color: var(--text-muted);
  }}
  .meta-item strong {{ color: var(--text-secondary); }}

  /* Boss section */
  .boss-section {{
    margin-bottom: 32px;
  }}
  .boss-section > .boss-header {{
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 12px 20px;
    background: var(--accent-dim);
    border: 1px solid var(--border-color);
    border-radius: 10px 10px 0 0;
    border-bottom: 2px solid var(--accent);
  }}
  .boss-section .boss-name {{
    font-size: 18px;
    font-weight: 700;
  }}
  .boss-section .boss-name-en {{
    font-size: 12px;
    color: var(--text-muted);
  }}
  .boss-section .boss-count {{
    margin-left: auto;
    font-size: 12px;
    color: var(--text-muted);
    background: rgba(255,255,255,0.05);
    padding: 2px 10px;
    border-radius: 12px;
  }}

  /* Player grid */
  .player-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 16px;
    padding: 16px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-top: none;
    border-radius: 0 0 10px 10px;
  }}

  /* Player card */
  .player-card {{
    background: var(--bg-card-alt);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    overflow: hidden;
  }}
  .player-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-light);
  }}
  .player-name {{
    font-size: 15px;
    font-weight: 600;
  }}
  .player-dps {{
    font-size: 13px;
    font-weight: 700;
    color: var(--accent);
    background: var(--accent-dim);
    padding: 2px 10px;
    border-radius: 12px;
  }}

  /* Detail sections (collapsible) */
  .detail-sections details {{
    border-bottom: 1px solid var(--border-light);
  }}
  .detail-sections details:last-child {{
    border-bottom: none;
  }}
  .detail-sections summary {{
    padding: 10px 16px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
    list-style: none;
    display: flex;
    align-items: center;
    gap: 6px;
    user-select: none;
    transition: background 0.15s, color 0.15s;
  }}
  .detail-sections summary:hover {{
    background: var(--bg-row-hover);
    color: var(--text-primary);
  }}
  .detail-sections summary::before {{
    content: "\\25B6";
    font-size: 9px;
    transition: transform 0.2s;
    display: inline-block;
    width: 14px;
    text-align: center;
  }}
  .detail-sections details[open] > summary::before {{
    transform: rotate(90deg);
  }}
  .section-icon {{
    font-size: 14px;
  }}
  .detail-sections .no-data {{
    padding: 12px 16px;
    color: var(--text-muted);
    font-size: 13px;
  }}

  /* Data table */
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }}
  .data-table th {{
    text-align: left;
    padding: 6px 10px;
    font-weight: 600;
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: rgba(0,0,0,0.2);
    position: sticky;
    top: 0;
  }}
  .data-table td {{
    padding: 5px 10px;
    border-top: 1px solid rgba(42,53,80,0.3);
    color: var(--text-secondary);
    white-space: nowrap;
  }}
  .data-table tbody tr:hover {{
    background: var(--bg-row-hover);
  }}
  .data-table tbody tr:nth-child(even) {{
    background: var(--bg-row-even);
  }}
  .slot-cell {{
    color: var(--text-muted);
    width: 52px;
    font-size: 11px;
  }}
  .item-cell {{
    color: var(--text-primary);
    font-weight: 500;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .ilvl-cell {{
    color: var(--ilvl-epic);
    font-weight: 600;
    width: 36px;
    text-align: center;
  }}
  .event-table-wrap {{
    max-height: 360px;
    overflow: auto;
  }}
  .event-table .time-cell {{
    width: 74px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }}
  .event-table .ability-cell {{
    color: var(--text-primary);
    font-weight: 500;
  }}
  .event-table .ability-id-cell {{
    width: 58px;
    color: var(--text-muted);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}

  /* Burst timeline */
  .burst-timeline {{
    padding: 10px 12px 12px;
  }}
  .timeline-summary {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }}
  .timeline-summary span {{
    font-size: 11px;
    color: var(--text-secondary);
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(42,53,80,0.5);
    border-radius: 999px;
    padding: 2px 8px;
  }}
  .timeline-board {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 12px;
  }}
  .timeline-lane,
  .cast-track {{
    display: grid;
    grid-template-columns: 142px minmax(120px, 1fr) 86px;
    align-items: center;
    gap: 8px;
    min-height: 24px;
  }}
  .lane-label {{
    color: var(--text-secondary);
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .lane-track {{
    position: relative;
    height: 10px;
    background: rgba(255,255,255,0.04);
    border-radius: 999px;
    overflow: hidden;
  }}
  .marker-track {{
    height: 24px;
    border-radius: 6px;
    overflow: visible;
  }}
  .lane-meta {{
    color: var(--text-muted);
    font-size: 10px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .window-segment {{
    position: absolute;
    top: 0;
    height: 100%;
    border-radius: 999px;
  }}
  .window-segment.buff {{
    background: linear-gradient(90deg, #00b894, #55efc4);
  }}
  .window-segment.debuff {{
    background: linear-gradient(90deg, #ff7675, #fdcb6e);
  }}
  .cast-marker {{
    position: absolute;
    top: 2px;
    width: 2px;
    height: 20px;
    background: #74b9ff;
    border-radius: 2px;
    box-shadow: 0 0 0 2px rgba(116,185,255,0.14);
  }}
  .timeline-empty-note {{
    display: inline-block;
    color: var(--text-muted);
    font-size: 11px;
    padding: 3px 8px;
  }}
  .timeline-events {{
    max-height: 300px;
  }}
  .event-pill {{
    display: inline-block;
    min-width: 64px;
    text-align: center;
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 10px;
    color: var(--text-primary);
    background: rgba(255,255,255,0.07);
  }}
  .event-pill.cast {{
    background: rgba(74,124,255,0.24);
  }}
  .event-pill.buff-apply {{
    background: rgba(0,184,148,0.24);
  }}
  .event-pill.buff-remove {{
    background: rgba(0,184,148,0.12);
  }}
  .event-pill.buff-refresh {{
    background: rgba(0,184,148,0.18);
  }}
  .event-pill.debuff-apply {{
    background: rgba(255,118,117,0.26);
  }}
  .event-pill.debuff-remove {{
    background: rgba(255,118,117,0.13);
  }}
  .event-pill.debuff-refresh {{
    background: rgba(255,118,117,0.19);
  }}
  .compact {{
    padding: 8px 0;
  }}

  /* Bar chart for casts / buffs */
  .bar-list {{
    padding: 8px 12px;
  }}
  .bar-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
  }}
  .bar-label {{
    width: 160px;
    font-size: 12px;
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 0;
  }}
  .bar-track {{
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.04);
    border-radius: 3px;
    overflow: hidden;
    min-width: 40px;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s;
  }}
  .cast-bar {{ background: var(--cast-bar); }}
  .buff-bar {{ background: var(--buff-bar); }}
  .bar-value {{
    width: 48px;
    text-align: right;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    flex-shrink: 0;
  }}

  .no-data {{
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 14px;
  }}

  /* Footer */
  .page-footer {{
    text-align: center;
    padding: 24px 0 10px;
    font-size: 12px;
    color: var(--text-muted);
  }}
  .page-footer a {{
    color: var(--accent);
    text-decoration: none;
  }}
  .page-footer a:hover {{ text-decoration: underline; }}

  @media (max-width: 920px) {{
    .player-grid {{
      grid-template-columns: 1fr;
      padding: 12px;
    }}
  }}
  @media (max-width: 640px) {{
    body {{ padding: 10px; }}
    .page-header h1 {{ font-size: 22px; }}
    .player-grid {{ padding: 8px; gap: 12px; }}
    .bar-label {{ width: 100px; font-size: 11px; }}
    .timeline-lane,
    .cast-track {{ grid-template-columns: 96px minmax(90px, 1fr) 64px; gap: 6px; }}
    .lane-meta {{ font-size: 9px; }}
    .data-table {{ font-size: 11px; }}
    .data-table th, .data-table td {{ padding: 4px 6px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header class="page-header">
    <h1>WCL 时光服<span>武器战士</span>角色详情</h1>
    <div class="subtitle">纳克萨玛斯 (Naxxramas) Phase 3</div>
    <div class="meta-bar">
      <span class="meta-item">共 <strong>{len(boss_rankings)}</strong> 个 Boss</span>
      <span class="meta-item"><strong>{total_players}</strong> 条排名数据</span>
      <span class="meta-item">生成于 <strong>{gen_time}</strong></span>
    </div>
  </header>

  <main class="boss-list">
{boss_sections}
  </main>

  <footer class="page-footer">
    数据来源 <a href="https://cn.titan.warcraftlogs.com" target="_blank">Warcraft Logs</a>
  </footer>
</div>
</body>
</html>"""


def save_to_file(content: str, filename: str = OUTPUT_FILENAME) -> str:
    """保存内容到 Markdown 文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def print_to_console(content: str) -> None:
    """打印到控制台"""
    print(content)
