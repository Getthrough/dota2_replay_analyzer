#!/usr/bin/env python3
"""
物品ID映射模块 - 从OpenDota获取物品数据并映射
"""
import json
from pathlib import Path

# 项目目录下的物品映射文件
SCRIPT_DIR = Path(__file__).parent
ITEMS_FILE = SCRIPT_DIR / "items.json"


def load_item_map() -> dict:
    """加载物品ID到名称的映射"""
    if ITEMS_FILE.exists():
        try:
            data = json.loads(ITEMS_FILE.read_text())
            return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"[警告] 无法读取物品映射文件: {e}")
    
    # 极简回退映射
    return {
        1: "blink", 29: "boots of speed", 30: "gem of true sight",
        34: "magic stick", 35: "magic wand", 36: "ghost scepter",
        37: "clarity", 38: "healing salve", 39: "tango",
        40: "town portal scroll", 41: "dust of appearance",
        180: "stout shield", 11: "quelling blade", 12: "ring of protection",
        14: "gauntlets of strength", 15: "slippers of agility",
        16: "mantle of intelligence", 17: "iron branch", 18: "belt of strength",
        19: "band of elvenskin", 20: "robe of the magi", 21: "circlet",
        22: "ogre axe", 23: "blade of alacrity", 24: "staff of wizardry",
        25: "ultimate orb", 26: "gloves of haste", 27: "morbid mask",
        28: "ring of regen", 31: "cloak", 32: "talisman of evasion",
        33: "cheese", 6: "helm of iron will", 7: "javelin",
        8: "mithril hammer", 9: "platemail", 10: "quarterstaff",
        2: "blades of attack", 3: "broadsword", 4: "chainmail", 5: "claymore"
    }


def get_item_name(item_id: int) -> str:
    """获取物品名称"""
    item_map = load_item_map()
    return item_map.get(item_id, f"item_{item_id}")


if __name__ == "__main__":
    # 测试
    items = load_item_map()
    print(f"加载了 {len(items)} 个物品")
    # 常见物品ID测试
    test_ids = [1, 180, 77, 46, 29]  # blink, force staff, etc.
    for tid in test_ids:
        print(f"  {tid} -> {items.get(tid, 'unknown')}")
