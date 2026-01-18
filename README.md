# Elasticsearch Hot Threads 火焰图生成器

一个用于将 Elasticsearch Hot Threads 数据可视化为交互式火焰图的 Python 工具。

## 特性

- ✅ 解析 Elasticsearch Hot Threads API 输出
- ✅ 合并多个节点的线程数据
- ✅ 生成交互式 SVG 火焰图
- ✅ Brendan Gregg 经典火焰图风格
- ✅ 交互功能：悬停提示、点击缩放、搜索
- ✅ URL 状态保存（可分享链接）
- ✅ 多种颜色主题（hot、java、mem 等）
- ✅ Node 层级结构展示
- ✅ CPU 使用率颜色主题
- ✅ 按 CPU 排序和显示百分比

## 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/es-flame-graph.git
cd es-flame-graph

# 无需外部依赖（使用 Python 标准库）
```

## 使用方法

### 基本用法

```bash
python main.py -i hot_threads.txt -o flamegraph.svg
```

### 高级选项

```bash
# 自定义标题
python main.py -i hot_threads.txt -o flamegraph.svg --title "生产集群 A"

# 自定义宽度
python main.py -i hot_threads.txt -o flamegraph.svg --width 1920

# 设置最小帧宽度（像素或百分比）
python main.py -i hot_threads.txt -o flamegraph.svg --minwidth 0.5%

# 更改颜色主题
python main.py -i hot_threads.txt -o flamegraph.svg --color java

# 按 CPU 排序
python main.py -i hot_threads.txt -o flamegraph.svg --sort-by-cpu

# 显示 CPU 百分比
python main.py -i hot_threads.txt -o flamegraph.svg --show-cpu-percent

# 使用 CPU 颜色主题
python main.py -i hot_threads.txt -o flamegraph.svg --color cpu --sort-by-cpu --show-cpu-percent
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入文件路径（Hot Threads 文本输出） | 必需 |
| `-o, --output` | 输出 SVG 文件路径 | `output.svg` |
| `--title` | 图表标题 | `Elasticsearch Hot Threads` |
| `--width` | SVG 宽度（像素） | `1920` |
| `--height` | 帧高度（像素） | `18` |
| `--minwidth` | 最小帧宽度（像素或百分比） | `0.1` |
| `--color` | 颜色主题（hot、java、mem、cpu 等） | `hot` |
| `--sort-by-cpu` | 按 CPU 使用率排序（高到低） | `False` |
| `--show-cpu-percent` | 在标签中显示 CPU 百分比 | `False` |

### 获取 Hot Threads 数据

```bash
# 从 Elasticsearch API 获取
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt

# 或直接保存到文件
curl -s http://localhost:9200/_nodes/hot_threads?threads=5 \
  -H "Content-Type: application/json" > hot_threads.txt
```

## 火焰图结构

火焰图采用 Node 层级结构：

```
all (根节点)
├── node_id (第一层：节点)
│   ├── thread-1 (第二层：线程)
│   ├── thread-2 (第二层：线程)
│   └── thread-3 (第二层：线程)
└── another_node_id (第一层：节点)
    └── thread-4 (第二层：线程)
```

- **Node 层**：显示 node_id（如 `987b4adab17437a9187659f3e53487bb`）
- **Thread 层**：显示简化后的线程名（如 `[management][T#5]`）

## 交互功能

在浏览器中打开生成的 SVG 后，您可以：

- **悬停**：查看每个函数的详细信息（名称、CPU 时间、百分比）
- **点击**：缩放到特定的函数调用链
- **Ctrl+F / 点击搜索**：按名称搜索函数
- **Ctrl+I**：切换大小写敏感搜索
- **点击重置缩放**：返回完整视图

缩放和搜索状态保存在 URL 中，便于分享特定视图。

## 颜色主题

- `hot`：橙/红/黄色谱（默认）
- `cpu`：按 CPU 使用率着色（红色=高 CPU，绿色=低 CPU）
- `java`：Java 专用颜色（Java 为绿色，C++ 为黄色，系统为红色）
- `mem`：绿色谱，用于内存分析
- `io`：蓝色谱，用于 I/O 操作
- `wakeup`：青色，用于唤醒事件
- `chain`：Off-CPU 可视化
- `red`、`green`、`blue`、`yellow`、`purple`、`aqua`、`orange`：纯色

## 架构

工具包含以下几个组件：

1. **Parser** (`es_flame_graph/parser.py`)：解析 Hot Threads 文本格式
2. **Color** (`es_flame_graph/color.py`)：实现 Brendan Gregg 的颜色哈希算法
3. **FlameGraph** (`es_flame_graph/flamegraph.py`)：生成 SVG 火焰图
4. **JavaScript** (`static/interactions.js`)：嵌入式交互功能

## 算法详情

### 线程合并

来自同一节点的相同线程会被合并，CPU 时间累加。这样可以提供更清晰的可视化效果并减少噪音。

```
输入：
  节点 1，线程 A：3.6ms
  节点 2，线程 A：4.3ms
  节点 3，线程 B：5.8ms
  节点 3，线程 C：4.0ms

输出（按节点分组）：
  节点 1：[线程 A] (3.6ms, 16%)
  节点 2：[线程 A] (4.3ms, 19%)
  节点 3：[线程 B, 线程 C] (9.8ms, 65%)
```

### 颜色哈希

使用确定性哈希算法分配颜色，确保相同的函数名在不同的火焰图中获得相同的颜色。这是从 Brendan Gregg 的原始 Perl 实现移植而来的。

## 示例

查看 `examples/` 目录中的示例输入和输出文件。

## 要求

- Python 3.7+
- 无外部依赖（使用 Python 标准库）

## 许可证

MIT License

## 参考资料

- [Brendan Gregg's Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [FlameGraph Perl Script](https://github.com/brendangregg/FlameGraph)
- [Elasticsearch Hot Threads API](https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-hot-threads.html)
