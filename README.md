# Elasticsearch Hot Threads Flame Graph Generator

A Python tool to visualize Elasticsearch Hot Threads data as interactive flame graphs.

## Features

- ✅ Parse Elasticsearch Hot Threads API output
- ✅ Merge threads from multiple nodes
- ✅ Generate interactive SVG flame graphs
- ✅ Brendan Gregg's classic flame graph style
- ✅ Interactive features: hover tooltips, click-to-zoom, search
- ✅ URL state preservation (shareable links)
- ✅ Multiple color themes (hot, java, mem, etc.)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/es-flame-graph.git
cd es-flame-graph

# No external dependencies required (uses Python standard library)
```

## Usage

### Basic Usage

```bash
python main.py -i hot_threads.txt -o flamegraph.svg
```

### Advanced Options

```bash
# Custom title
python main.py -i hot_threads.txt -o flamegraph.svg --title "Production Cluster A"

# Custom width
python main.py -i hot_threads.txt -o flamegraph.svg --width 1600

# Set minimum frame width (pixels or percentage)
python main.py -i hot_threads.txt -o flamegraph.svg --minwidth 0.5%

# Change color theme
python main.py -i hot_threads.txt -o flamegraph.svg --color java

# Generate separate flame graph for each node
python main.py -i hot_threads.txt -o output_dir/ --per-node
```

### Per-Node Mode

When using `--per-node`, the tool generates a separate flame graph for each node in your Elasticsearch cluster. This is useful for comparing hot threads across different nodes.

```bash
# Generate one flame graph per node
python main.py -i hot_threads.txt -o node_graphs/ --per-node

# Output files:
# node_name_1.svg (flame graph for node 1)
# node_name_2.svg (flame graph for node 2)
# ...
```

Each flame graph will be named after the node and include all hot threads from that specific node.

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|----------|
| `-i, --input` | Input file path (Hot Threads text output) | Required |
| `-o, --output` | Output SVG file path | `output.svg` |
| `--title` | Graph title | `Elasticsearch Hot Threads` |
| `--width` | SVG width in pixels | `1200` |
| `--height` | Frame height in pixels | `16` |
| `--minwidth` | Minimum frame width (pixels or percent) | `0.1` |
| `--color` | Color theme (hot, java, mem, io, etc.) | `hot` |
| `--per-node` | Generate separate flame graph for each node | `False` |

### Getting Hot Threads Data

```bash
# From Elasticsearch API
curl -s http://localhost:9200/_nodes/hot_threads > hot_threads.txt

# Or save to file directly
curl -s http://localhost:9200/_nodes/hot_threads?threads=5 \
  -H "Content-Type: application/json" | python main.py -o flamegraph.svg
```

## Interactive Features

Once you open the generated SVG in a browser, you can:

- **Hover**: View detailed information about each function (name, CPU time, percentage)
- **Click**: Zoom into a specific function call chain
- **Ctrl+F / Click Search**: Search for functions by name
- **Ctrl-I**: Toggle case-sensitive search
- **Click Reset Zoom**: Return to the full view

The zoom and search states are preserved in the URL, making it easy to share specific views.

## Color Themes

- `hot`: Orange/red/yellow spectrum (default)
- `java`: Java-specific colors (green for Java, yellow for C++, red for system)
- `mem`: Green spectrum for memory profiling
- `io`: Blue spectrum for I/O operations
- `wakeup`: Aqua for wakeup events
- `chain`: Off-CPU visualization
- `red`, `green`, `blue`, `yellow`, `purple`, `aqua`, `orange`: Solid colors

## Architecture

The tool consists of several components:

1. **Parser** (`es_flame_graph/parser.py`): Parses Hot Threads text format
2. **Color** (`es_flame_graph/color.py`): Implements Brendan Gregg's color hashing
3. **FlameGraph** (`es_flame_graph/flamegraph.py`): Generates SVG flame graphs
4. **JavaScript** (`static/interactions.js`): Embedded interactivity

## Algorithm Details

### Thread Merging

Threads with identical call stacks are merged, and their CPU times are accumulated. This provides a cleaner visualization and reduces noise.

```
Input:
  Thread 1: A->B->C (2.0ms)
  Thread 2: A->B->C (1.5ms)
  Thread 3: X->Y (0.5ms)

Output (merged):
  A->B->C (3.5ms, 70%)
  X->Y (0.5ms, 10%)
```

### Color Hashing

Colors are assigned using a deterministic hash algorithm that ensures the same function name gets the same color across different flame graphs. This is ported from Brendan Gregg's original Perl implementation.

## Examples

See the `examples/` directory for sample input and output files.

## Requirements

- Python 3.7+
- No external dependencies (uses Python standard library)

## License

MIT License

## References

- [Brendan Gregg's Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- [FlameGraph Perl Script](https://github.com/brendangregg/FlameGraph)
- [Elasticsearch Hot Threads API](https://www.elastic.co/guide/en/elasticsearch/reference/current/cluster-nodes-hot-threads.html)
