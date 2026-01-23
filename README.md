# Elasticsearch 火焰图生成器

将 Elasticsearch Hot Threads 和 Tasks API 数据可视化为交互式 SVG 火焰图。

## 特性

- **自动识别** - 智能识别混合的 Hot Threads 和 Tasks API 数据
- **双模式支持** - 同时支持 Hot Threads 和 Tasks API 格式
- **交互式火焰图** - 悬停提示、点击缩放、搜索功能
- **多种颜色主题** - hot、java、mem、cpu 等 14 种主题
- **零依赖** - 仅使用 Python 标准库

## 安装

```bash
git clone https://github.com/chinwe/es-flame-graph.git
cd es-flame-graph
```

## 使用方法

```bash
# 默认模式：自动识别并生成两个火焰图
python main.py -i examples/example.txt
# 输出: example_hot_threads.svg, example_tasks.svg

# 指定输出目录
python main.py -i examples/example.txt -o output/

# 单输入模式（禁用自动识别）
python main.py -i hot_threads.txt --no-auto -o output.svg
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-i, --input` | 输入文件路径 | 必需 |
| `-o, --output` | 输出目录 | `.` (当前目录) |
| `--auto` | 自动识别混合数据 | `True` |
| `--no-auto` | 禁用自动识别 | - |
| `--color` | 颜色主题 | `hot` |
| `--width` | SVG 宽度 | `1920` |
| `--per-node` | 每节点单独生成（仅 Hot Threads） | - |

## 获取数据

```bash
# Hot Threads
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt

# Tasks API
curl -s http://localhost:9200/_tasks > tasks.json

# 混合数据（自动识别）
cat > example.txt << EOF
::: {node_id}...
Hot threads at ...

tasks:marker
{"nodes": {...}}
EOF
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
- 无外部依赖

## 许可证

MIT License

## 参考资料

- [Brendan Gregg's Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [Elasticsearch Hot Threads API](https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-hot-threads.html)
