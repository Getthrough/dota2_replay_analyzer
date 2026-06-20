# Dota2 战术复盘分析器 - 项目总结

## 项目概述
为 Dota2 菜鸟玩家构建的命令行战术复盘工具。输入比赛ID + Steam32位ID，自动拉取多源数据，通过 Claude 无头模式生成战术层面复盘报告。

## 当前状态
**已完成核心功能，Stratz 双源集成成功。**

---

## 技术架构

```
用户输入: ./analyze.sh <match_id> [steam32_id]
    ↓
数据层: OpenDota API (主) + Stratz GraphQL API (辅)
    ↓
合并层: 按 Steam ID 匹配，Stratz 数据补充到 OpenDota 结构
    ↓
提取层: 玩家定位、核心指标、装备时间线、死亡事件
    ↓
分析层: Claude CLI (claude -p) 无头模式
    ↓
输出: Markdown 报告 → ~/.cache/dota2_analyzer/report_<match_id>.md
```

---

## 文件结构

| 文件 | 说明 |
|------|------|
| `dota2_analyzer.py` | 主程序，双源数据获取/合并/分析 |
| `item_map.py` | 物品 ID 映射模块 |
| `items.json` | 基础物品映射（合成装备不完整） |
| `analyze.sh` | 便捷入口脚本 |
| `README.md` | 使用说明 |
| `~/.stratz_token` | Stratz API Token（已配置） |
| `~/.cache/dota2_analyzer/` | 缓存目录 |

---

## 已验证功能

### 1. 数据获取
- ✅ OpenDota API：免费，无 Key，有时网络超时
- ✅ Stratz GraphQL API：已配置 Token，数据更详细
- ✅ 本地缓存：避免重复请求

### 2. 数据合并
- ✅ 按 Steam Account ID 匹配双源玩家
- ✅ Stratz 特有数据补充到 OpenDota 结构（死亡事件、物品购买等）

### 3. 玩家提取
- ✅ 通过 Steam32位ID 定位目标玩家
- ✅ 位置推断：综合 lane_role + 英雄类型 + GPM
- ✅ 英雄名称映射（OpenDota heroes API）

### 4. 数据质量处理
- ✅ `None` → "N/A" 标记，避免 AI 过度推断
- ✅ 装备提取三降级：purchase_log → purchase dict → item_0~5
- ✅ 死亡时间线从 Stratz deathEvents 提取

### 5. AI 分析
- ✅ Claude CLI 无头模式调用
- ✅ 结构化 Prompt（5 维度评分 + 战术建议）
- ✅ 报告保存为 Markdown

---

## 已测试比赛

| 比赛ID | 英雄 | 结果 | 数据质量 | 分析亮点 |
|--------|------|------|----------|----------|
| 8851540899 | Windranger | 失败 | partial + Stratz | 死亡分布分析、装备里程碑判断 |

**用户 Steam ID**: 1187119470

---

## 已知问题

1. **物品映射不完整**：`items.json` 大量合成装备显示为 `recipe`，需要补充完整映射
2. **OpenDota 网络不稳定**：测试时多次超时（60s+），依赖本地缓存
3. **Stratz GraphQL 字段限制**：部分字段（wardPlacement、abilityUse 等）Schema 不匹配，已降级到可用字段集
4. **AI 输出偶尔被截断**：Claude 无头模式输出长度限制，需监控

---

## 待办事项

- [ ] 补充完整物品映射表（`items.json`）
- [ ] 测试更多比赛验证分析质量
- [ ] 添加版本元数据抓取（英雄胜率、热门出装）
- [ ] 考虑添加 Dotabuff 爬虫获取版本元数据
- [ ] 优化 Prompt 防止 AI 输出被截断

---

## 使用方式

```bash
cd ~/vibecoding/projects/dota2_replay_analyzer
./analyze.sh <match_id> [steam32_id]

# 示例
./analyze.sh 8851540899 1187119470
```

报告保存到：`~/.cache/dota2_analyzer/report_<match_id>.md`

---

## 关键配置

- **Stratz Token**: `~/.stratz_token`（已配置用户 Token）
- **缓存目录**: `~/.cache/dota2_analyzer/`
- **Python**: 3.14.2
- **依赖**: requests 2.32.5

---

## 技术决策记录

1. **双源架构**：Stratz 优先（数据更详细），OpenDota 兜底（免费无 Key）
2. **N/A 处理**：`None` 值必须标记为 "N/A" 而非 0，避免 AI 过度推断
3. **位置推断**：综合 lane_role + 英雄名称关键词（support/carry）+ GPM 阈值
4. **物品映射**：本地 `items.json` 优先，不依赖实时 API
5. **装备提取三降级**：purchase_log → purchase dict → item_0~5 当前装备
6. **Stratz GraphQL 字段**：通过实际测试确定可用字段集，避免 Schema 假设

---

## 用户偏好

- 目标用户暂时是自己，验证效果后再分享
- 需要战术层面分析，非统计层面
- 数据时效性要求低（当天出即可）
- 使用命令行工具 + LLM 分析原型
- 通过 `claude -p` 无头模式调用大模型

---

*总结时间: 2025年6月*
*项目路径: ~/vibecoding/projects/dota2_replay_analyzer/*
