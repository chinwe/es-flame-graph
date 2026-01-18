# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Elasticsearch Hot Threads 火焰图生成器，用于将 Elasticsearch Hot Threads API 的输出可视化为交互式 SVG 火焰图。工具遵循 Brendan Gregg 的火焰图标准。

## 常用命令

### 安装依赖
```bash
pip install -e .
```

### 运行
```bash
# 基本用法
python main.py -i hot_threads.txt -o flamegraph.svg

# 使用安装后的命令行工具
es-flame-graph -i hot_threads.txt -o flamegraph.svg

# 高级选项
python main.py -i hot_threads.txt -o flamegraph.svg \
  --title "生产集群 A" \
  --width 1920 \
  --minwidth 0.5% \
  --color cpu \
  --sort-by-cpu \
  --show-cpu-percent

# 为每个节点生成单独的火焰图
python main.py -i hot_threads.txt --per-node
```

### 获取测试数据
```bash
# 从 Elasticsearch 获取 Hot Threads 数据
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt
curl -s http://localhost:9200/_nodes/hot_threads?threads=5 -H "Content-Type: application/json" > hot_threads.txt
```

## 架构说明

### 核心组件

1. **`es_flame_graph/parser.py`** - 数据解析器
   - `HotThreadsParser`: 解析 Elasticsearch Hot Threads 文本格式
   - `ThreadInfo`: 单个线程信息的数据类
   - `ParsedData`: 所有解析数据的容器
   - 使用正则表达式匹配节点头、CPU 使用、快照等模式

2. **`es_flame_graph/flamegraph.py`** - SVG 生成器
   - `FlameGraphGenerator`: 核心生成器类
   - `FrameNode`: 火焰图帧节点数据结构
   - 关键流程：
     - `_merge_threads()`: 合并相同节点的相同线程，累加 CPU 时间
     - `_build_tree()`: 构建层级树结构（all → node_id → thread_name）
     - `_assign_colors()`: 分配颜色
     - `_calculate_layout()`: 计算布局和百分比
     - `_render_svg()`: 渲染 SVG

3. **`es_flame_graph/color.py`** - 颜色系统
   - `get_color()`: 实现 Brendan Gregg 的颜色哈希算法
   - 确保相同函数名在不同火焰图中获得相同颜色
   - 支持 14 种颜色主题：hot、java、mem、io、wakeup、chain、red、green、blue、yellow、purple、aqua、orange、cpu

4. **`main.py`** - 命令行入口
   - 处理参数解析
   - 支持单节点和多节点模式（`--per-node`）
   - 默认启用 CPU 排序和百分比显示

5. **`static/interactions.js`** - JavaScript 交互功能
   - 嵌入到 SVG 中的交互代码
   - 功能：悬停提示、点击缩放、搜索、URL 状态保存

### 数据流

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

### 火焰图层级结构

```
all (根节点)
├── node_id (第一层：节点)
│   ├── thread-1 (第二层：线程)
│   └── thread-2 (第二层：线程)
└── another_node_id (第一层：节点)
    └── thread-3 (第二层：线程)
```

### 关键算法

**线程合并**：来自同一节点的相同线程会被合并，CPU 时间和样本数累加。这提供更清晰的可视化效果。

**颜色哈希**：使用确定性哈希算法，相同函数名总是获得相同颜色。

## 重要约定

- **样本计数显示**：显示实际样本数（`samples_count`）而非 CPU 时间（ms）
- **默认选项**：`--sort-by-cpu` 和 `--show-cpu-percent` 默认启用
- **最小宽度过滤**：使用 `--minwidth` 避免显示过窄的帧（支持像素或百分比）
- **SVG 输出文件**：已被 `.gitignore` 忽略

## 依赖

- Python 3.7+
- `svgwrite>=1.4.3`（唯一外部依赖）

## Git 忽略规则

- `*.svg`: 所有生成的 SVG 输出文件都被忽略
- `examples/`: 示例目录被忽略
- 标准 Python 忽略规则（`__pycache__/`、`*.pyc`、`venv/` 等）
