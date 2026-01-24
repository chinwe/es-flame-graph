# Elasticsearch 火焰图生成器

将 Elasticsearch Hot Threads 和 Tasks API 数据可视化为交互式 SVG 火焰图。

## 特性

- **自动识别** - 智能识别混合的 Hot Threads 和 Tasks API 数据
- **双模式支持** - 同时支持 Hot Threads 和 Tasks API 格式
- **交互式火焰图** - 悬停提示、点击缩放、搜索功能
- **多种颜色主题** - hot、java、mem、cpu 等 14 种主题
- **Treemap 布局** - 节点和线程以块状方式排列，更清晰的数据可视化
- **Python 包** - 可安装为命令行工具

## 安装

```bash
# 克隆仓库
git clone https://github.com/chinwe/es-flame-graph.git
cd es-flame-graph

# 安装依赖（包含 svgwrite）
pip install -e .

# 或者直接运行（仅需要 Python 3.7+）
python main.py -i input.txt
```

## 使用方法

```bash
# 默认模式：自动识别并生成两个火焰图
python main.py -i example.txt
# 输出: example_hot_threads.svg, example_tasks.svg

# 指定输出目录
python main.py -i example.txt -o output/

# 单输入模式（禁用自动识别）
python main.py -i hot_threads.txt --no-auto -o output.svg

# 高级选项
python main.py -i example.txt -o output/ \
  --title "生产集群 A" \
  --width 1920 \
  --height 18 \
  --minwidth 0.5% \
  --color cpu \
  --no-sort-by-cpu

# 为每个节点生成单独的火焰图（仅 Hot Threads）
python main.py -i hot_threads.txt --per-node -o output/
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入文件路径 | 必需 |
| `-o, --output` | 输出目录或文件路径 | `.` (当前目录) |
| `--auto` | 自动识别混合数据 | `True` |
| `--no-auto` | 禁用自动识别 | - |
| `--title` | 图表标题 | 自动检测 |
| `--color` | 颜色主题 | `hot` |
| `--width` | SVG 宽度（像素） | `1920` |
| `--height` | 帧高度（像素） | `18` |
| `--minwidth` | 最小帧宽度（像素或百分比） | `0.1` |
| `--sort-by-cpu` | 按 CPU 时间排序 | `True` |
| `--no-sort-by-cpu` | 禁用排序 | - |
| `--show-cpu-percent` | 显示 CPU 百分比 | `True` |
| `--no-show-cpu-percent` | 隐藏百分比 | - |
| `--per-node` | 每节点单独生成（仅 Hot Threads） | - |

## 获取数据

```bash
# Hot Threads
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt

# Tasks API
curl -s http://localhost:9200/_tasks > tasks.json

# 混合数据（自动识别，无需标记）
# 直接拼接两种数据即可
cat hot_threads.txt tasks.json > example.txt
```

## 输入格式

### Hot Threads 格式
```
::: {node_id}{node_name}...
   Hot threads at 2024-01-01T12:00:00Z, interval=500ms
    4.5% (22.5ms out of 500ms) cpu usage by thread 'thread-name'
     3/10 snapshots sharing following 25 elements
       java.base@11.0.25/jdk.internal.misc.Unsafe.park(Native Method)
       ...
```

### Tasks API 格式
```json
{
  "nodes": {
    "node_id": {
      "name": "node_name",
      "tasks": {
        "task_id": {
          "action": "indices:data/write/bulk",
          "running_time_in_nanos": 1234567
        }
      }
    }
  }
}
```

## 火焰图结构

```
all (根)
├── node_id (节点层)
│   ├── thread/action (线程或操作层)
│   └── thread/action
└── node_id
    └── thread/action
```

## 交互功能

- **悬停** - 查看详细信息
- **点击** - 缩放到特定函数
- **Ctrl+F** - 搜索函数
- **点击重置** - 返回完整视图

## 颜色主题

`hot` | `java` | `mem` | `io` | `cpu` | `wakeup` | `chain` | `red` | `green` | `blue` | `yellow` | `purple` | `aqua` | `orange`

## 要求

- Python 3.7+
- `svgwrite>=1.4.3`

## 许可证

MIT License

## 参考资料

- [Brendan Gregg's Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [Elasticsearch Hot Threads API](https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-hot-threads.html)
