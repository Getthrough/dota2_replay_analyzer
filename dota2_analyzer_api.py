#!/usr/bin/env python3
"""
Dota2 战术复盘分析器 - 命令行原型
输入比赛ID，输出战术层面的复盘报告
支持多数据源：OpenDota + Stratz
"""

import sys
import json
import time
import subprocess
import requests
import os
from datetime import datetime
from pathlib import Path
from item_map import get_item_name

# ============ 配置 ============
OPENDOTA_API = "https://api.opendota.com/api"
STRATZ_API = "https://api.stratz.com/graphql"
CACHE_DIR = Path.home() / ".cache" / "dota2_analyzer"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 从环境变量读取 Stratz Token，或从配置文件读取
STRATZ_TOKEN = os.environ.get("STRATZ_TOKEN", "")
if not STRATZ_TOKEN:
    token_file = Path.home() / ".stratz_token"
    if token_file.exists():
        STRATZ_TOKEN = token_file.read_text().strip()

if STRATZ_TOKEN:
    print(f"[配置] Stratz Token 已加载 (长度: {len(STRATZ_TOKEN)})")
else:
    print("[配置] Stratz Token 未设置，仅使用 OpenDota 数据源")
    print("[提示] 设置方式: export STRATZ_TOKEN='your_token' 或写入 ~/.stratz_token")

# 分位置的核心指标权重（用于评估哪些数据最重要）
POSITION_METRICS = {
    1: ["gold_per_min", "last_hits", "hero_damage", "tower_damage", "kills", "deaths"],  # Carry
    2: ["gold_per_min", "xp_per_min", "hero_damage", "kills", "deaths", "last_hits"],   # Mid
    3: ["hero_damage", "tower_damage", "kills", "assists", "deaths", "gold_per_min"],    # Offlane
    4: ["assists", "hero_damage", "kills", "gold_per_min", "xp_per_min", "deaths"],      # Soft Support
    5: ["assists", "deaths", "hero_damage", "gold_per_min", "xp_per_min", "camps_stacked"], # Hard Support
}


def fetch_match_stratz(match_id: str) -> dict:
    """从Stratz获取比赛数据（GraphQL）"""
    if not STRATZ_TOKEN:
        return None
    
    cache_file = CACHE_DIR / f"match_stratz_{match_id}.json"
    
    if cache_file.exists():
        print(f"[缓存] 使用Stratz本地缓存: {cache_file}")
        return json.loads(cache_file.read_text())
    
    print(f"[获取] 从Stratz拉取比赛 {match_id}...")
    
    # GraphQL 查询 - 获取详细数据
    query = """
    query MatchQuery($matchId: Long!) {
      match(id: $matchId) {
        id
        didRadiantWin
        durationSeconds
        startDateTime
        gameMode
        regionId
        players {
          steamAccountId
          heroId
          isRadiant
          position
          kills
          deaths
          assists
          networth
          goldPerMinute
          experiencePerMinute
          numLastHits
          numDenies
          heroDamage
          towerDamage
          heroHealing
          isVictory
          level
          stats {
            itemPurchases {
              itemId
              time
            }
            deathEvents {
              time
              goldLost
            }
            killEvents {
              time
            }
          }
        }
      }
    }
    """
    
    variables = {"matchId": int(match_id)}
    
    try:
        resp = requests.post(
            STRATZ_API,
            json={"query": query, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {STRATZ_TOKEN}"
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        
        if "errors" in data:
            print(f"[错误] Stratz GraphQL 错误: {data['errors']}")
            return None
        
        match_data = data.get("data", {}).get("match")
        if match_data:
            cache_file.write_text(json.dumps(match_data, indent=2))
            print(f"[缓存] Stratz数据已保存: {cache_file}")
        return match_data
        
    except requests.exceptions.RequestException as e:
        print(f"[网络错误] Stratz请求失败: {e}")
        return None
    except Exception as e:
        print(f"[错误] Stratz处理失败: {e}")
        return None


def fetch_match_opendota(match_id: str) -> dict:
    """从OpenDota获取比赛数据（带缓存）"""
    cache_file = CACHE_DIR / f"match_opendota_{match_id}.json"
    
    if cache_file.exists():
        print(f"[缓存] 使用OpenDota本地缓存: {cache_file}")
        data = json.loads(cache_file.read_text())
    else:
        print(f"[获取] 从OpenDota拉取比赛 {match_id}...")
        url = f"{OPENDOTA_API}/matches/{match_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        cache_file.write_text(json.dumps(data, indent=2))
        print(f"[缓存] OpenDota数据已保存: {cache_file}")
    
    # 确保英雄名称被填充（OpenDota有时返回None）
    _fill_hero_names(data)
    return data


def _fill_hero_names(match_data: dict):
    """用本地英雄映射表填充英雄名称"""
    hero_map = _load_hero_map()
    for player in match_data.get("players", []):
        if not player.get("hero_name"):
            hero_id = player.get("hero_id")
            if hero_id and hero_id in hero_map:
                player["hero_name"] = hero_map[hero_id]
            else:
                player["hero_name"] = f"Hero_{hero_id}"


def _load_hero_map() -> dict:
    """加载英雄ID到名称的映射"""
    hero_cache = CACHE_DIR / "heroes.json"
    
    if hero_cache.exists():
        return {int(k): v for k, v in json.loads(hero_cache.read_text()).items()}
    
    # 从OpenDota获取
    try:
        resp = requests.get(f"{OPENDOTA_API}/heroes", timeout=30)
        resp.raise_for_status()
        heroes = resp.json()
        hero_map = {h["id"]: h["localized_name"] for h in heroes}
        hero_cache.write_text(json.dumps(hero_map, indent=2))
        return hero_map
    except Exception as e:
        print(f"[警告] 无法获取英雄列表: {e}")
        return {}


def merge_match_data(opendota_data: dict, stratz_data: dict) -> dict:
    """合并两个数据源的数据，Stratz数据补充到OpenDota数据中"""
    if not stratz_data:
        print("[合并] 仅使用OpenDota数据")
        return opendota_data
    
    if not opendota_data:
        print("[合并] 仅使用Stratz数据")
        return stratz_data
    
    print("[合并] 合并OpenDota + Stratz数据...")
    
    # 以OpenDota为基础结构
    merged = opendota_data.copy()
    
    # 将Stratz玩家数据按steamAccountId索引
    stratz_players = stratz_data.get("players", [])
    stratz_by_steam = {p.get("steamAccountId"): p for p in stratz_players if p.get("steamAccountId")}
    
    # 为每个OpenDota玩家补充Stratz数据
    for player in merged.get("players", []):
        steam_id = player.get("account_id")
        if steam_id and steam_id in stratz_by_steam:
            stratz_player = stratz_by_steam[steam_id]
            # 补充Stratz特有的详细数据
            stats = stratz_player.get("stats", {})
            if stats:
                player["_stratz_stats"] = stats
                player["_stratz_item_purchases"] = stats.get("itemPurchases", [])
                player["_stratz_death_events"] = stats.get("deathEvents", [])
                player["_stratz_kill_events"] = stats.get("killEvents", [])
            # 补充其他Stratz字段
            if "position" in stratz_player and stratz_player["position"] is not None:
                player["position"] = stratz_player["position"]
    
    # 标记数据来源
    merged["_data_sources"] = ["opendota", "stratz"]
    
    return merged


def _convert_stratz_players(stratz_players: list, match_data: dict) -> list:
    """将Stratz玩家数据格式转换为OpenDota兼容格式"""
    players = []
    for p in stratz_players:
        player = {
            "account_id": p.get("steamAccountId"),
            "hero_id": p.get("heroId"),
            "hero_name": _get_hero_name_from_id(p.get("heroId")),
            "player_slot": 0 if p.get("isRadiant") else 128,  # 简化处理
            "kills": p.get("kills"),
            "deaths": p.get("deaths"),
            "assists": p.get("assists"),
            "gold_per_min": p.get("goldPerMinute"),
            "xp_per_min": p.get("experiencePerMinute"),
            "last_hits": p.get("numLastHits"),
            "denies": p.get("numDenies"),
            "hero_damage": p.get("heroDamage"),
            "tower_damage": p.get("towerDamage"),
            "hero_healing": p.get("heroHealing"),
            "isRadiant": p.get("isRadiant"),
            "win": p.get("isVictory"),
            "net_worth": p.get("networth"),
            "level": p.get("level"),
            # Stratz特有数据
            "_stratz_stats": p.get("stats", {}),
            "_stratz_abilities": p.get("abilities", []),
            "_stratz_items": p.get("items", []),
        }
        players.append(player)
    
    return players


def _get_hero_name_from_id(hero_id: int) -> str:
    """从英雄ID获取名称"""
    hero_map = _load_hero_map()
    return hero_map.get(hero_id, f"Hero_{hero_id}")


def extract_player_data(match_data: dict, target_player_id: str = None) -> dict:
    """
    提取目标玩家的关键数据
    如果指定了target_player_id（Steam32位ID），查找对应玩家
    否则默认分析天辉第一位玩家（简化版）
    """
    players = match_data.get("players", [])
    if not players:
        raise ValueError("比赛数据中没有玩家信息")
    
    target = None
    if target_player_id:
        # 尝试匹配account_id
        pid = int(target_player_id)
        for p in players:
            if p.get("account_id") == pid:
                target = p
                print(f"[匹配] 找到目标玩家 (Steam ID: {pid})")
                break
        if not target:
            print(f"[警告] 未找到Steam ID {target_player_id} 的玩家，使用默认玩家")
    
    if not target:
        # 默认取天辉第一位玩家（player_slot < 128）
        for p in players:
            if p.get("player_slot", 0) < 128:
                target = p
                break
        if not target:
            target = players[0]
    
    # 提取关键战术数据（区分"数据为0"和"数据缺失"）
    def _get_val(field, default=0, missing_label=None):
        val = target.get(field)
        if val is None:
            return missing_label if missing_label is not None else default
        return val
    
    # 检查是否有Stratz详细数据
    stratz_stats = target.get("_stratz_stats", {})
    has_stratz = bool(stratz_stats)
    
    # 从Stratz数据提取更详细的指标
    obs_placed = _get_val("obs_placed", missing_label="N/A")
    sen_placed = _get_val("sen_placed", missing_label="N/A")
    camps_stacked = _get_val("camps_stacked", missing_label="N/A")
    rune_pickups = _get_val("rune_pickups", missing_label="N/A")
    stuns = _get_val("stuns", missing_label="N/A")
    teamfight_participation = _get_val("teamfight_participation", missing_label="N/A")
    damage_taken = _get_val("damage_taken", missing_label="N/A")
    lane_efficiency = _get_val("lane_efficiency", missing_label="N/A")
    
    # 如果有Stratz数据，优先使用Stratz的详细数据
    if has_stratz:
        stratz_stats = target.get("_stratz_stats", {})
        if stratz_stats:
            # 从Stratz deathEvents提取死亡时间线
            death_events = stratz_stats.get("deathEvents", [])
            if death_events and not target.get("deaths_log"):
                target["deaths_log"] = [{"time": d.get("time", 0)} for d in death_events]
            
            # 从Stratz itemPurchases提取购买记录（如果OpenDota没有）
            item_purchases = stratz_stats.get("itemPurchases", [])
            if item_purchases and not target.get("purchase_log"):
                target["purchase_log"] = [{"key": get_item_name(i.get("itemId", 0)), "time": i.get("time", 0)} for i in item_purchases]
    
    player_summary = {
        "player_slot": target.get("player_slot"),
        "hero_id": target.get("hero_id"),
        "hero_name": target.get("hero_name", "Unknown"),
        "position": _infer_position(target),
        "level": target.get("level"),
        "kills": target.get("kills"),
        "deaths": target.get("deaths"),
        "assists": target.get("assists"),
        "gold_per_min": target.get("gold_per_min"),
        "xp_per_min": target.get("xp_per_min"),
        "last_hits": target.get("last_hits"),
        "denies": target.get("denies"),
        "hero_damage": target.get("hero_damage"),
        "tower_damage": target.get("tower_damage"),
        "hero_healing": target.get("hero_healing"),
        "purchase_log": _extract_purchases(target),
        "ability_upgrades": target.get("ability_upgrades_arr", []),
        "permanent_buffs": target.get("permanent_buffs", []),
        "obs_placed": obs_placed,
        "sen_placed": sen_placed,
        "camps_stacked": camps_stacked,
        "rune_pickups": rune_pickups,
        "stuns": stuns,
        "teamfight_participation": teamfight_participation,
        "damage_taken": damage_taken,
        "damage_inflictor": _extract_damage_breakdown(target),
        "item_uses": _extract_item_uses(target),
        "kill_log": target.get("kills_log", []),
        "death_log": target.get("deaths_log", []),
        "lane_efficiency": lane_efficiency,
        "lane": target.get("lane"),
        "lane_role": target.get("lane_role"),
        "is_victory": _is_victory(target, match_data),
        "duration": match_data.get("duration"),
        "game_mode": match_data.get("game_mode"),
        "start_time": match_data.get("start_time"),
        "patch": match_data.get("patch"),
        "region": match_data.get("region"),
        "data_quality": "partial" if any(v == "N/A" for v in [obs_placed, teamfight_participation, stuns]) else "full",
        "has_stratz_data": has_stratz,
    }
    
    return player_summary


def _infer_position(player: dict) -> int:
    """
    根据lane_role + 英雄类型 + 经济数据综合推断位置
    """
    lane_role = player.get("lane_role")
    hero_name = player.get("hero_name", "").lower()
    gpm = player.get("gold_per_min", 0)
    obs = player.get("obs_placed", 0)
    camps = player.get("camps_stacked", 0)
    
    # 硬辅助英雄列表（几乎不可能打核心）
    hard_support_heroes = {
        "lion", "shadow shaman", "crystal maiden", "warlock", "dazzle", 
        "oracle", "winter wyvern", "witch doctor", "bane", "disruptor",
        "ancient apparition", "vengeful spirit", "skywrath mage", "grimstroke",
        "pugna", "undying", "treant protector", "omniknight", "abaddon"
    }
    
    # 纯核心英雄列表
    core_heroes = {
        "anti-mage", "spectre", "faceless void", "juggernaut", "phantom assassin",
        "slark", "sven", "terrorblade", "luna", "gyrocopter", "medusa", "morphling",
        "invoker", "storm spirit", "ember spirit", "void spirit", "templar assassin",
        "shadow fiend", "puck", "zeus", "queen of pain", "lina", "outworld destroyer",
        "beastmaster", "dark seer", "timbersaw", "mars", "primal beast", "underlord"
    }
    
    # 如果英雄明显是辅助，直接推断4/5
    if hero_name in hard_support_heroes:
        return 5 if obs > 2 or camps > 0 else 4
    
    # 如果英雄明显是核心，按分路推断
    if hero_name in core_heroes:
        if lane_role == 1:
            return 1
        elif lane_role == 2:
            return 2
        elif lane_role == 3:
            return 3
    
    # 通用推断逻辑
    if lane_role == 1:
        return 1
    elif lane_role == 2:
        return 2
    elif lane_role == 3:
        return 3
    elif lane_role == 4:
        # 4号位通常是辅助型但有一定资源
        return 4 if gpm < 400 else 3
    else:
        # 根据资源消耗和辅助指标推断
        if gpm > 500:
            return 1
        elif gpm > 400:
            return 2
        elif gpm > 320:
            return 3
        else:
            return 5 if obs > 2 or camps > 0 else 4


def _is_victory(player: dict, match: dict) -> bool:
    """判断玩家是否获胜"""
    player_slot = player.get("player_slot", 0)
    radiant_win = match.get("radiant_win", False)
    is_radiant = player_slot < 128
    return (is_radiant and radiant_win) or (not is_radiant and not radiant_win)


def _extract_purchases(player: dict) -> list:
    """提取物品购买时间线 - 尝试多种数据源"""
    key_items = []
    
    # 方法1: Stratz详细购买记录
    stratz_stats = player.get("_stratz_stats", {})
    if stratz_stats:
        purchases = stratz_stats.get("itemPurchases", [])
        for p in purchases:
            item_id = p.get("itemId")
            time_val = p.get("time", 0)
            if item_id:
                item_name = get_item_name(item_id)
                key_items.append({"item": item_name, "time": time_val})
    
    # 方法2: OpenDota purchase_log
    if not key_items:
        purchases = player.get("purchase_log", [])
        if purchases:
            for p in purchases:
                item = p.get("key", "")
                time_val = p.get("time", 0)
                if item and item not in ["tango", "clarity", "flask", "tpscroll", "ward_observer", "ward_sentry", "courier", "fly_courier", "enchanted_mango", "faerie_fire", "smoke_of_deceit", "dust", "tome_of_knowledge"]:
                    key_items.append({"item": item, "time": time_val})
    
    # 方法3: 如果purchase_log为空，从purchase字段提取
    if not key_items:
        purchase = player.get("purchase", {})
        for item, count in purchase.items():
            if count > 0 and item not in ["tango", "clarity", "flask", "tpscroll", "ward_observer", "ward_sentry"]:
                # purchase没有时间信息，用0占位
                key_items.append({"item": item, "time": 0})
    
    # 方法4: 从当前装备推断（最后的装备状态）
    if not key_items:
        for i in range(6):
            item_id = player.get(f"item_{i}")
            if item_id and item_id != 0:
                item_name = get_item_name(item_id)
                key_items.append({"item": item_name, "time": -1})  # -1表示最终装备
    
    return key_items[:20]


def _extract_damage_breakdown(player: dict) -> dict:
    """提取伤害来源 breakdown"""
    # 优先使用Stratz数据
    stratz_stats = player.get("_stratz_stats", {})
    if stratz_stats:
        hero_damage = stratz_stats.get("heroDamage", [])
        if hero_damage:
            return {d.get("damageType", "unknown"): d.get("count", 0) for d in hero_damage}
    
    damage = player.get("damage_inflictor", {})
    # 取前10个主要伤害来源
    sorted_damage = sorted(damage.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_damage[:10])


def _extract_item_uses(player: dict) -> dict:
    """提取物品使用次数"""
    # 优先使用Stratz数据
    stratz_stats = player.get("_stratz_stats", {})
    if stratz_stats:
        item_uses = stratz_stats.get("itemUses", [])
        if item_uses:
            return {get_item_name(i.get("itemId", 0)): i.get("count", 0) for i in item_uses if i.get("count", 0) > 0}
    
    item_uses = player.get("item_uses", {})
    # 过滤出主动物品
    active_items = {k: v for k, v in item_uses.items() if v > 0}
    return dict(sorted(active_items.items(), key=lambda x: x[1], reverse=True)[:15])


def build_analysis_prompt(player_data: dict) -> str:
    """构建给Claude的战术分析Prompt"""
    
    # 处理可能为N/A的值
    def fmt(val):
        if val == "N/A":
            return "数据缺失"
        if isinstance(val, float):
            return f"{val:.1f}"
        return str(val)
    
    prompt = f"""你是一位Dota2资深教练，擅长从比赛数据中提炼战术层面的复盘建议。

请分析以下这场Dota2比赛中玩家的表现，给出**战术层面**的深度复盘（不是统计数字罗列）。

**重要提示**：以下数据中标记为"数据缺失"的字段表示API没有返回该数据，不等于玩家没有执行该操作。请基于**有数据**的指标进行分析，不要对缺失数据做负面推断。

## 比赛基本信息
- 英雄: {player_data['hero_name']}
- 推断位置: {player_data['position']}号位 (1=Carry, 2=Mid, 3=Offlane, 4=Soft Support, 5=Hard Support)
- 比赛结果: {'胜利' if player_data['is_victory'] else '失败'}
- 比赛时长: {player_data['duration'] // 60}分{player_data['duration'] % 60}秒
- 版本Patch: {player_data['patch']}
- 分路: {player_data['lane']}路, 角色: {player_data['lane_role']}
- 数据完整性: {player_data['data_quality']}
- 是否有Stratz详细数据: {'是' if player_data['has_stratz_data'] else '否'}

## 核心数据
- KDA: {player_data['kills']}/{player_data['deaths']}/{player_data['assists']}
- GPM: {player_data['gold_per_min']}, XPM: {player_data['xp_per_min']}
- 补刀: {player_data['last_hits']}正补 / {player_data['denies']}反补
- 英雄伤害: {player_data['hero_damage']}, 建筑伤害: {player_data['tower_damage']}
- 治疗量: {player_data['hero_healing']}
- 控制时间: {fmt(player_data['stuns'])}
- 团战参与率: {fmt(player_data['teamfight_participation'])}
- 承受伤害: {fmt(player_data['damage_taken'])}
- 插眼数: {fmt(player_data['obs_placed'])}, 反眼数: {fmt(player_data['sen_placed'])}
- 堆野次数: {fmt(player_data['camps_stacked'])}
- 神符拾取: {fmt(player_data['rune_pickups'])}
- 对线效率: {fmt(player_data['lane_efficiency'])}

## 关键装备购买时间线（分钟:物品）
"""
    
    for item in player_data['purchase_log']:
        minutes = item['time'] // 60
        seconds = item['time'] % 60
        prompt += f"- {minutes:02d}:{seconds:02d} → {item['item']}\n"
    
    prompt += f"""
## 主要伤害来源
"""
    for source, dmg in list(player_data['damage_inflictor'].items())[:8]:
        prompt += f"- {source}: {dmg}\n"
    
    prompt += f"""
## 物品使用次数（主动物品）
"""
    for item, count in list(player_data['item_uses'].items())[:10]:
        prompt += f"- {item}: {count}次\n"

    prompt += f"""
## 死亡时间线（分钟）
"""
    for death in player_data['death_log'][:10]:
        t = death.get('time', 0)
        prompt += f"- {t // 60:02d}:{t % 60:02d}\n"

    prompt += """
---

请按以下结构输出复盘报告（用中文）：

## 1. 总体评价
- 这局在这5个维度分别打几分（1-10）：对线期、中期节奏、团战表现、资源利用、意识/视野
- 给出一个整体评价标签，如"稳健型Carry"、"激进但容易暴毙"、"团队型辅助"等

## 2. 做得好的地方（保持）
- 具体指出2-3个战术亮点，说明为什么好

## 3. 需要改进的地方（重点）
- 具体指出2-3个战术问题，说明：
  - 问题是什么
  - 理想情况下应该怎么处理
  - 给出一个可执行的训练建议（如下一局重点练习什么）

## 4. 关键决策复盘
- 分析装备购买时机是否合理（太早/太晚/选择是否正确）
- 分析死亡时间是否集中在某个阶段（如对线期频繁死亡 vs 后期带线被抓）
- 如果是辅助，分析眼位控制是否足够

## 5. 下一局行动清单
- 给出3个具体、可执行的改进点，下一场比赛刻意练习

注意：
- 不要罗列数据，要给出**战术判断**
- 基于""" + str(player_data['position']) + """号位的标准来评估（不同位置标准不同）
- 语气要直接、实用，像一位严厉的教练
- 对于标记为"数据缺失"的字段，不要假设玩家没做，只分析有数据的部分
"""
    return prompt


def call_claude(prompt: str) -> str:
    """通过claude -p无头模式调用"""
    print("[AI] 调用Claude进行战术分析...")
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            print(f"[错误] Claude调用失败: {result.stderr}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print("[错误] Claude调用超时")
        return None
    except FileNotFoundError:
        print("[错误] 找不到claude命令，请确保Claude Code CLI已安装")
        return None


def main():
    if len(sys.argv) < 2:
        print("用法: python dota2_analyzer.py <比赛ID> [Steam32位ID]")
        print("示例: python dota2_analyzer.py 7890123456")
        print("\n获取比赛ID:")
        print("1. 打开Dota2客户端 → 观战 → 最近比赛")
        print("2. 或访问 opendota.com 搜索自己的SteamID")
        sys.exit(1)
    
    match_id = sys.argv[1]
    target_player_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"=" * 60)
    print(f"Dota2 战术复盘分析器")
    print(f"比赛ID: {match_id}")
    print(f"=" * 60)
    
    try:
        # 1. 从两个数据源获取比赛数据
        opendota_data = fetch_match_opendota(match_id)
        stratz_data = fetch_match_stratz(match_id)
        
        # 2. 合并数据
        match_data = merge_match_data(opendota_data, stratz_data)
        
        # 3. 提取玩家数据
        player_data = extract_player_data(match_data, target_player_id)
        
        print(f"\n[信息] 分析英雄: {player_data['hero_name']}")
        print(f"[信息] 推断位置: {player_data['position']}号位")
        print(f"[信息] 比赛结果: {'胜利' if player_data['is_victory'] else '失败'}")
        print(f"[信息] 数据质量: {player_data['data_quality']}")
        if player_data['has_stratz_data']:
            print(f"[信息] Stratz详细数据: 可用")
        
        # 4. 构建Prompt
        prompt = build_analysis_prompt(player_data)
        
        # 可选：保存prompt用于调试
        debug_file = CACHE_DIR / f"prompt_{match_id}.txt"
        debug_file.write_text(prompt)
        print(f"[调试] Prompt已保存: {debug_file}")
        
        # 5. 调用Claude分析
        analysis = call_claude(prompt)
        
        if analysis:
            print("\n" + "=" * 60)
            print("战术复盘报告")
            print("=" * 60)
            print(analysis)
            
            # 保存报告
            report_file = CACHE_DIR / f"report_{match_id}.md"
            report_file.write_text(analysis)
            print(f"\n[保存] 报告已保存: {report_file}")
        else:
            print("[错误] 分析失败")
            
    except requests.exceptions.RequestException as e:
        print(f"[网络错误] 无法获取比赛数据: {e}")
    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
