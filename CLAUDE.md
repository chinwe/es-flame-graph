# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Elasticsearch Hot Threads 和 Tasks API 火焰图生成器，用于将 Elasticsearch Hot Threads API 和 Tasks API 的输出可视化为交互式 SVG 火焰图。工具遵循 Brendan Gregg 的火焰图标准。

## 常用命令

### 安装依赖
```bash
pip install -e .
```

### 运行
```bash
# 默认模式（--auto）：自动识别混合的 Hot Threads 和 Tasks 数据
python main.py -i example.txt
# 生成: example_hot_threads.svg, example_tasks.svg

# 指定输出目录
python main.py -i example.txt -o output/

# 禁用自动模式，使用单输入模式
python main.py -i hot_threads.txt --no-auto -o output.svg

# 高级选项
python main.py -i example.txt -o output/ \
  --title "生产集群 A" \
  --width 1920 \
  --minwidth 0.5% \
  --color cpu \
  --sort-by-cpu \
  --show-cpu-percent

# 为每个节点生成单独的火焰图（仅 Hot Threads）
python main.py -i hot_threads.txt --per-node -o output/
```

### 获取测试数据
```bash
# 从 Elasticsearch 获取 Hot Threads 数据
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt
curl -s http://localhost:9200/_nodes/hot_threads?threads=5 -H "Content-Type: application/json" > hot_threads.txt

# 从 Elasticsearch 获取 Tasks 数据
curl -s http://localhost:9200/_tasks > tasks.json

# 混合数据（自动识别，无需特殊标记）
# 直接拼接两种数据即可
cat hot_threads.txt tasks.json > example.txt
```

## 架构说明

### 核心组件

1. **`es_flame_graph/parser.py`** - Hot Threads 数据解析器
   - `HotThreadsParser`: 解析 Elasticsearch Hot Threads 文本格式
   - `ThreadInfo`: 单个线程信息的数据类
   - `ParsedData`: 所有解析数据的容器
   - 使用正则表达式匹配节点头、CPU 使用、快照等模式

2. **`es_flame_graph/tasks_parser.py`** - Tasks API 数据解析器
   - `TasksParser`: 解析 Elasticsearch Tasks API JSON 格式
   - `TaskInfo`: 单个任务信息的数据类
   - 支持层级聚合（父任务-子任务关系）
   - 支持多个 JSON 对象的拼接解析

3. **`es_flame_graph/mixed_parser.py`** - 混合数据解析器
   - `MixedParser`: 自动识别并分离混合的 Hot Threads 和 Tasks 数据
   - 自动检测 Hot Threads（以 `:::` 开头）和 Tasks JSON（以 `{` 开头）
   - 无需特殊标记，直接拼接即可
   - 分别生成两个火焰图文件

4. **`es_flame_graph/flamegraph.py`** - SVG 生成器
   - `FlameGraphGenerator`: 核心生成器类
   - `FrameNode`: 火焰图帧节点数据结构
   - 关键流程：
     - `_merge_threads()`: 合并相同节点的相同线程，累加 CPU 时间
     - `_build_tree()`: 构建层级树结构（all → node_id → thread_name）
     - `_assign_colors()`: 分配颜色
     - `_calculate_layout()`: 计算布局和百分比
     - `_render_svg()`: 渲染 SVG

5. **`es_flame_graph/color.py`** - 颜色系统
   - `get_color()`: 实现 Brendan Gregg 的颜色哈希算法
   - 确保相同函数名在不同火焰图中获得相同颜色
   - 支持 14 种颜色主题：hot、java、mem、io、wakeup、chain、red、green、blue、yellow、purple、aqua、orange、cpu

6. **`main.py`** - 命令行入口
   - 默认启用 `--auto` 模式（自动识别混合数据）
   - 文件名自动生成（基于输入文件名）
   - `-o/--output` 指定输出目录
   - 支持单节点和多节点模式（`--per-node`）
   - 默认启用 CPU 排序和百分比显示

7. **`static/interactions.js`** - JavaScript 交互功能
   - 嵌入到 SVG 中的交互代码
   - 功能：悬停提示、点击缩放、搜索、URL 状态保存

### 数据流

#### Hot Threads 数据流
```
Elasticsearch Hot Threads 文本
    ↓
HotThreadsParser.parse_text()
    ↓
ParsedData (List[ThreadInfo])
    ↓
FlameGraphGenerator._merge_threads()
    ↓
FlameGraphGenerator._build_tree()
    ↓
FrameNode 树结构
    ↓
FlameGraphGenerator._calculate_layout()
    ↓
FlameGraphGenerator._render_svg()
    ↓
SVG 输出（包含嵌入式 JavaScript）
```

#### Tasks API 数据流
```
Elasticsearch Tasks API JSON
    ↓
TasksParser.parse_text()
    ↓
层级聚合（父任务-子任务）
    ↓
转换为 ThreadInfo 格式
    ↓
FlameGraphGenerator（同 Hot Threads）
    ↓
SVG 输出
```

#### 混合数据流
```
混合输入文件
    ↓
MixedParser.parse_text()
    ↓
自动检测 Hot Threads (:::) 和 Tasks JSON ({)
    ↓
分离为 Hot Threads 和 Tasks 两部分
    ↓
分别生成两个火焰图
    ↓
{basename}_hot_threads.svg
{basename}_tasks.svg
```

### 火焰图层级结构

#### Hot Threads 层级
```
all (根节点)
├── node_id (第一层：节点)
│   ├── thread-1 (第二层：线程)
│   └── thread-2 (第二层：线程)
└── another_node_id (第一层：节点)
    └── thread-3 (第二层：线程)
```

#### Tasks API 层级
```
all (根节点)
├── node_id (第一层：节点)
│   ├── action-1 (第二层：操作类型)
│   └── action-2 (第二层：操作类型)
└── another_node_id (第一层：节点)
    └── action-3 (第二层：操作类型)
```

### 关键算法

**线程合并**：来自同一节点的相同线程会被合并，CPU 时间和样本数累加。这提供更清晰的可视化效果。

**任务层级聚合**：子任务的运行时间会累加到父任务，相同 action 的任务会被合并显示。

**颜色哈希**：使用确定性哈希算法，相同函数名总是获得相同颜色。

## 重要约定

- **样本计数显示**：Hot Threads 显示实际样本数（`samples_count`），Tasks 显示运行时间
- **默认选项**：`--auto`、`--sort-by-cpu` 和 `--show-cpu-percent` 默认启用
- **最小宽度过滤**：使用 `--minwidth` 避免显示过窄的帧（支持像素或百分比）
- **文件名生成**：默认基于输入文件名自动生成（`example.txt` → `example_hot_threads.svg`, `example_tasks.svg`）
- **SVG 输出文件**：已被 `.gitignore` 忽略

## 依赖

- Python 3.7+
- `svgwrite>=1.4.3`（唯一外部依赖）

## Git 忽略规则

- `*.svg`: 所有生成的 SVG 输出文件都被忽略
- `examples/`: 示例目录被忽略
- 标准 Python 忽略规则（`__pycache__/`、`*.pyc`、`venv/` 等）
