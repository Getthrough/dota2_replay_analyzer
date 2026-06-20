#!/bin/bash
# Dota2 战术复盘分析器 - 便捷入口脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    echo "用法: ./analyze.sh <比赛ID> [Steam32位ID]"
    echo ""
    echo "示例:"
    echo "  ./analyze.sh 7890123456"
    echo "  ./analyze.sh 7890123456 123456789"
    echo ""
    echo "获取比赛ID的方法:"
    echo "  1. Dota2客户端 → 个人资料 → 比赛历史 → 右键复制比赛ID"
    echo "  2. 或访问 https://www.opendota.com 搜索自己的SteamID"
    exit 1
fi

python3 dota2_analyzer.py "$@"
