# Dota2 战术复盘分析器 (DEM 版本)

基于 Java clarity 库解析 Dota2 DEM 录像文件，提取精确数据后调用 LLM 生成战术复盘报告。

## 特点

- **精确装备提取**: 直接从录像解析装备购买时间线，包括出门装
- **准确对线识别**: 通过前10分钟位置数据确定实际 lane 分配
- **死亡事件追踪**: 提取死亡时间、位置、死亡次数
- **中文装备名称**: 所有装备显示中文名称
- **LLM 战术分析**: 调用 Claude 生成详细战术复盘

## 使用方法

```bash
# 解析 DEM 文件并生成战术报告
python3 analyze_dem.py <dem_file> [--steam-id <steam_id>] [-o <output.md>]

# 示例
python3 analyze_dem.py 8851540899.dem --steam-id 123456789 -o report.md
```

## 项目结构

- `analyze_dem.py` - Python 主入口，调用 Java 解析器并生成 LLM Prompt
- `java_parser/` - Java DEM 解析器 (基于 clarity 4.0.1)
  - `src/main/java/com/dota2analyzer/DemParser.java` - 解析器主类
- `clarity-src/` - clarity 库源码（已编译）
- `*_api.*` - 旧 API 方案文件（已废弃）

## 依赖

- Java 17+
- Maven 3.6+
- Python 3.8+
- `claude` CLI (用于 LLM 分析)

## 构建

```bash
cd java_parser
mvn compile
```

## 技术方案对比

| 功能 | 旧 API 方案 | DEM 解析方案 |
|------|-----------|-------------|
| 装备识别 | ❌ 错误率高 | ✅ 精确提取 |
| 出门装 | ❌ 缺失 | ✅ 完整记录 |
| 对线识别 | ❌ 经常误判 | ✅ 位置分析 |
| 英雄名称 | 英文 | 中文 |
| 离线可用 | ❌ 需联网 | ✅ 本地解析 |
