#!/usr/bin/env python3
"""Dota2 DEM Analyzer - Parse DEM files and generate tactical reports via LLM."""

import json
import subprocess
import sys
import os
import argparse
from pathlib import Path

# Hero name mapping (English -> Chinese)
HERO_CN = {
    "Anti-Mage": "敌法师",
    "Axe": "斧王",
    "Bane": "祸乱之源",
    "Bloodseeker": "嗜血狂魔",
    "Crystal_Maiden": "水晶室女",
    "Drow_Ranger": "卓尔游侠",
    "Earthshaker": "撼地者",
    "Juggernaut": "主宰",
    "Mirana": "米拉娜",
    "Morphling": "变体精灵",
    "Shadow_Fiend": "影魔",
    "Phantom_Lancer": "幻影长矛手",
    "Puck": "帕克",
    "Pudge": "屠夫",
    "Razor": "剃刀",
    "Sand_King": "沙王",
    "Storm_Spirit": "风暴之灵",
    "Sven": "斯温",
    "Tiny": "小小",
    "Vengeful_Spirit": "复仇之魂",
    "Windrunner": "风行者",
    "Zeus": "宙斯",
    "Kunkka": "昆卡",
    "Lina": "莉娜",
    "Lion": "莱恩",
    "Shadow_Shaman": "暗影萨满",
    "Slardar": "斯拉达",
    "Tidehunter": "潮汐猎人",
    "Witch_Doctor": "巫医",
    "Lich": "巫妖",
    "Riki": "力丸",
    "Enigma": "谜团",
    "Tinker": "修补匠",
    "Sniper": "狙击手",
    "Necrolyte": "瘟疫法师",
    "Warlock": "术士",
    "Beastmaster": "兽王",
    "Queen_Of_Pain": "痛苦女王",
    "Venomancer": "剧毒术士",
    "Faceless_Void": "虚空假面",
    "Wraith_King": "冥魂大帝",
    "Death_Prophet": "死亡先知",
    "Phantom_Assassin": "幻影刺客",
    "Pugna": "帕格纳",
    "Templar_Assassin": "圣堂刺客",
    "Viper": "冥界亚龙",
    "Luna": "露娜",
    "Dragon_Knight": "龙骑士",
    "Dazzle": "戴泽",
    "Clockwerk": "发条技师",
    "Leshrac": "拉席克",
    "Natures_Prophet": "先知",
    "Lifestealer": "噬魂鬼",
    "Life_Stealer": "噬魂鬼",
    "Dark_Seer": "黑暗贤者",
    "Clinkz": "克林克兹",
    "Omniknight": "全能骑士",
    "Enchantress": "魅惑魔女",
    "Huskar": "哈斯卡",
    "Night_Stalker": "暗夜魔王",
    "Broodmother": "育母蜘蛛",
    "Bounty_Hunter": "赏金猎人",
    "Weaver": "编织者",
    "Jakiro": "杰奇洛",
    "Batrider": "蝙蝠骑士",
    "Chen": "陈",
    "Spectre": "幽鬼",
    "Ancient_Apparition": "远古冰魄",
    "Doom": "末日使者",
    "Ursa": "熊战士",
    "Spirit_Breaker": "裂魂人",
    "Gyrocopter": "矮人直升机",
    "Alchemist": "炼金术士",
    "Invoker": "祈求者",
    "Silencer": "沉默术士",
    "Outworld_Destroyer": "殁境神蚀者",
    "Lycan": "狼人",
    "Brewmaster": "酒仙",
    "Shadow_Demon": "暗影恶魔",
    "Lone_Druid": "德鲁伊",
    "Chaos_Knight": "混沌骑士",
    "Meepo": "米波",
    "Treant_Protector": "树精卫士",
    "Ogre_Magi": "食人魔魔法师",
    "Undying": "不朽尸王",
    "Rubick": "拉比克",
    "Disruptor": "干扰者",
    "Nyx_Assassin": "司夜刺客",
    "Naga_Siren": "娜迦海妖",
    "Keeper_Of_The_Light": "光之守卫",
    "Io": "艾欧",
    "Visage": "维萨吉",
    "Slark": "斯拉克",
    "Medusa": "美杜莎",
    "Troll_Warlord": "巨魔战将",
    "Centaur_Warrunner": "半人马战行者",
    "Magnus": "马格纳斯",
    "Timbersaw": "伐木机",
    "Bristleback": "钢背兽",
    "Tusk": "巨牙海民",
    "Skywrath_Mage": "天怒法师",
    "Abaddon": "亚巴顿",
    "Elder_Titan": "上古巨神",
    "Legion_Commander": "军团指挥官",
    "Techies": "工程师",
    "Ember_Spirit": "灰烬之灵",
    "Earth_Spirit": "大地之灵",
    "Underlord": "孽主",
    "Terrorblade": "恐怖利刃",
    "Phoenix": "凤凰",
    "Oracle": "神谕者",
    "Winter_Wyvern": "寒冬飞龙",
    "Arc_Warden": "天穹守望者",
    "Monkey_King": "齐天大圣",
    "Dark_Willow": "邪影芳灵",
    "Pangolier": "石鳞剑士",
    "Grimstroke": "天涯墨客",
    "Hoodwink": "森海飞霞",
    "Void_Spirit": "虚无之灵",
    "Snapfire": "电炎绝手",
    "Mars": "玛尔斯",
    "Dawnbreaker": "破晓辰星",
    "Marci": "玛西",
    "Primal_Beast": "獸",
    "Muerta": "琼英碧灵",
    "Largo": "凯",
    "Kez": "凯",
    "Ringmaster": "百戏大王",
}


def get_hero_cn(name: str) -> str:
    """Get Chinese hero name."""
    return HERO_CN.get(name, name)


def parse_dem_file(dem_file: str, steam_id: str = None) -> dict:
    """Parse DEM file using Java parser and return JSON data."""
    project_dir = Path(__file__).parent.resolve()
    java_parser_dir = project_dir / "java_parser"
    
    # Build classpath - use absolute paths
    clarity_jar = (project_dir / "clarity-src/build/libs/clarity-4.0.1.jar").resolve()
    m2_repo = Path.home() / ".m2/repository"
    
    cp_parts = [
        str((java_parser_dir / "target/classes").resolve()),
        str(clarity_jar),
        str(m2_repo / "org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar"),
        str(m2_repo / "com/skadistats/clarity-protobuf/6.1/clarity-protobuf-6.1.jar"),
        str(m2_repo / "it/unimi/dsi/fastutil-core/8.5.12/fastutil-core-8.5.12.jar"),
        str(m2_repo / "org/xerial/snappy/snappy-java/1.1.10.4/snappy-java-1.1.10.4.jar"),
        str(m2_repo / "com/google/code/gson/gson/2.10.1/gson-2.10.1.jar"),
    ]
    classpath = ":".join(cp_parts)
    
    # Ensure DEM file is absolute path
    dem_path = Path(dem_file).resolve()
    
    # Run Java parser
    output_json = f"/tmp/match_{Path(dem_file).stem}.json"
    cmd = [
        "java", "-cp", classpath,
        "com.dota2analyzer.DemParser",
        str(dem_path),
        steam_id or "",
        output_json
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error parsing DEM file: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    with open(output_json, 'r') as f:
        return json.load(f)


def generate_prompt(data: dict, target_steam_id: str = None, lanes: dict = None) -> str:
    """Generate tactical analysis prompt from parsed data."""
    
    radiant = []
    for h in data.get('radiant', []):
        hero_cn = get_hero_cn(h['heroName'])
        radiant.append(f"- {hero_cn} ({h['lane']}, {h['deaths']} deaths)")
    
    dire = []
    for h in data.get('dire', []):
        hero_cn = get_hero_cn(h['heroName'])
        dire.append(f"- {hero_cn} ({h['lane']}, {h['deaths']} deaths)")
    
    # Get final items for each hero
    items_info = []
    for team_name, team_data in [("天辉", data.get('radiant', [])), ("夜魇", data.get('dire', []))]:
        for h in team_data:
            hero_cn = get_hero_cn(h['heroName'])
            items = h.get('items', [])
            if items:
                key_items = [i for i in items if i not in ['回城卷轴', '树之祭祀', '魔法芒果', '仙灵之火', '侦查守卫', '岗哨守卫', '诡计之雾', '显影之尘']]
                items_str = ", ".join(key_items[:8]) if key_items else ", ".join(items[:5])
                items_info.append(f"{team_name} {hero_cn}: {items_str}")
    
    # Death summary
    death_summary = {}
    for d in data.get('deaths', []):
        hero = get_hero_cn(d['heroName'])
        death_summary[hero] = death_summary.get(hero, 0) + 1
    
    deaths_str = "\n".join([f"- {hero}: {count} 次" for hero, count in sorted(death_summary.items(), key=lambda x: -x[1])[:10]])
    
    # Lane matchup section
    lane_section = ""
    if lanes:
        lane_parts = []
        if 'top' in lanes:
            lane_parts.append(f"- 上路: {lanes['top']}")
        if 'mid' in lanes:
            lane_parts.append(f"- 中路: {lanes['mid']}")
        if 'bot' in lanes:
            lane_parts.append(f"- 下路: {lanes['bot']}")
        if lane_parts:
            lane_section = "\n## 对线信息（用户提供）\n" + "\n".join(lane_parts)
    
    prompt = f"""# Dota2 战术复盘分析

## 比赛概况
- 总时长: {data['totalTicks']} ticks

## 阵容
### 天辉 (Radiant)
{chr(10).join(radiant)}

### 夜魇 (Dire)
{chr(10).join(dire)}
{lane_section}

## 装备情况
{chr(10).join(items_info)}

## 死亡统计
{deaths_str}

## 分析要求
请基于以上数据提供战术复盘分析，包括：
1. **对线分析**: 各 lane 的对位关系，哪方优势
2. **装备路线**: 关键英雄的装备选择是否合理
3. **死亡分析**: 哪些英雄死亡过多，可能的原因
4. **团队配合**: 基于阵容的团战策略建议
5. **改进建议**: 针对劣势方的具体改进建议

请用中文回答，装备名称使用中文。"""
    
    return prompt


def analyze_with_llm(prompt: str) -> str:
    """Call LLM for tactical analysis."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"claude -p stderr: {result.stderr}", file=sys.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"claude -p not available: {e}", file=sys.stderr)
    
    return None


def prompt_for_lanes():
    """Interactive prompt for lane matchups when not provided via CLI."""
    print("\n=== 请输入各条线对线英雄信息 ===")
    print("格式: 英雄A vs 英雄B  (辅助用 + 连接)")
    print("例如: 幻影长矛手 vs 虚空假面")
    print("      复仇之魂+巫医 vs 斯温+暗影萨满")
    print("直接回车表示跳过该线路\n")
    
    lanes = {}
    lane_names = [
        ("top", "上路 (Top/优势路)"),
        ("mid", "中路 (Mid)"),
        ("bot", "下路 (Bot/劣势路)")
    ]
    
    for key, display in lane_names:
        user_input = input(f"{display}: ").strip()
        if user_input:
            lanes[key] = user_input
    
    return lanes if lanes else {}


def main():
    parser = argparse.ArgumentParser(description='Dota2 DEM Analyzer')
    parser.add_argument('dem_file', help='Path to DEM file')
    parser.add_argument('--steam-id', help='Target Steam32 ID', default=None)
    parser.add_argument('--output', '-o', help='Output report file', default=None)
    parser.add_argument('--lane-top', help='Top lane matchup, e.g. "CarryA vs OfflanerB"', default=None)
    parser.add_argument('--lane-mid', help='Mid lane matchup, e.g. "HeroA vs HeroB"', default=None)
    parser.add_argument('--lane-bot', help='Bot lane matchup, e.g. "CarryA+SupportB vs CarryC+SupportD"', default=None)
    parser.add_argument('--lanes', help='JSON string with lane matchups, e.g. \'{"top":"A vs B","mid":"C vs D","bot":"E+F vs G+H"}\'', default=None)
    args = parser.parse_args()
    
    if not os.path.exists(args.dem_file):
        print(f"Error: DEM file not found: {args.dem_file}", file=sys.stderr)
        sys.exit(1)
    
    # Collect lane info from CLI args
    lanes = {}
    if args.lane_top:
        lanes['top'] = args.lane_top
    if args.lane_mid:
        lanes['mid'] = args.lane_mid
    if args.lane_bot:
        lanes['bot'] = args.lane_bot
    
    # If --lanes JSON provided, parse it (overrides individual args)
    if args.lanes:
        try:
            lanes = json.loads(args.lanes)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid --lanes JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    # If no lane info provided at all, prompt interactively or show error
    if not lanes:
        if sys.stdin.isatty():
            lanes = prompt_for_lanes()
        else:
            print("\n错误: 未提供对线信息。", file=sys.stderr)
            print("请使用以下方式之一提供对线信息:\n", file=sys.stderr)
            print("  1. 命令行参数:", file=sys.stderr)
            print('     --lane-top "英雄A vs 英雄B" --lane-mid "英雄C vs 英雄D" --lane-bot "英雄E+辅助 vs 英雄F+辅助"', file=sys.stderr)
            print("  2. JSON 格式:", file=sys.stderr)
            print('     --lanes \'{"top":"A vs B","mid":"C vs D","bot":"E+F vs G+H"}\'', file=sys.stderr)
            print("  3. 在终端中直接运行，会提示交互式输入\n", file=sys.stderr)
            sys.exit(1)
    
    print(f"Parsing DEM file: {args.dem_file}")
    data = parse_dem_file(args.dem_file, args.steam_id)
    
    print("Generating tactical analysis prompt...")
    prompt = generate_prompt(data, args.steam_id, lanes)
    
    # Save prompt to file for LLM analysis
    prompt_file = f"/tmp/dota2_prompt_{Path(args.dem_file).stem}.txt"
    with open(prompt_file, 'w') as f:
        f.write(prompt)
    print(f"Prompt saved to: {prompt_file}")
    
    # Try LLM analysis
    print("Calling LLM for analysis...")
    analysis = analyze_with_llm(prompt)
    
    if analysis:
        if args.output:
            with open(args.output, 'w') as f:
                f.write(analysis)
            print(f"Report saved to: {args.output}")
        else:
            print("\n=== TACTICAL ANALYSIS ===\n")
            print(analysis)
    else:
        print("\nLLM analysis not available. Prompt saved for manual analysis.")
        print(f"You can run: cat {prompt_file} | claude -p")


if __name__ == '__main__':
    main()
