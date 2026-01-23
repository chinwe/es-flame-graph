"""
Elasticsearch Hot Threads Flame Graph Generator - CLI

Command-line interface for generating flame graphs from Hot Threads data.
Now supports both Hot Threads and Tasks API formats.
"""

import argparse
import json
import sys
from pathlib import Path

from es_flame_graph import HotThreadsParser, TasksParser, FlameGraphGenerator


def detect_input_format(text: str) -> str:
    """
    Auto-detect input format: 'hot_threads' or 'tasks'

    Args:
        text: Input text content

    Returns:
        'hot_threads' or 'tasks'
    """
    text_stripped = text.strip()

    # Check for JSON (tasks API) - supports both single and multiple JSON objects
    if text_stripped.startswith("{"):
        try:
            data = json.loads(text_stripped)
            # Single JSON object - check for tasks API structure
            if "nodes" in data and isinstance(data.get("nodes"), dict):
                # Further validate: check for tasks field
                for node_data in data["nodes"].values():
                    if isinstance(node_data, dict) and "tasks" in node_data:
                        return "tasks"
        except json.JSONDecodeError:
            # Not a single JSON - might be multiple concatenated JSON objects
            # Try to parse using TasksParser's multiple JSON handler
            from es_flame_graph.tasks_parser import TasksParser
            parser = TasksParser()
            try:
                data_list = parser._parse_multiple_json(text_stripped)
                if data_list:
                    # Check if any of the parsed objects are tasks API responses
                    for data in data_list:
                        if "nodes" in data and isinstance(data.get("nodes"), dict):
                            for node_data in data["nodes"].values():
                                if isinstance(node_data, dict) and "tasks" in node_data:
                                    return "tasks"
            except Exception:
                pass

    # Check for Hot Threads patterns
    if "::: {" in text or "Hot threads at" in text:
        return "hot_threads"

    # Default to hot_threads
    return "hot_threads"


def format_time_nanos(nanos: float) -> str:
    """
    Format time in nanoseconds to the most appropriate unit

    Args:
        nanos: Time in nanoseconds

    Returns:
        Formatted time string
    """
    if nanos >= 1_000_000_000:
        return f"{nanos / 1_000_000_000:.2f}s"
    elif nanos >= 1_000_000:
        return f"{nanos / 1_000_000:.2f}ms"
    elif nanos >= 1_000:
        return f"{nanos / 1_000:.2f}μs"
    else:
        return f"{nanos:.0f}ns"


def main():
    parser = argparse.ArgumentParser(
        description="Elasticsearch Hot Threads Flame Graph Generator (supports Hot Threads & Tasks API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Hot Threads
  %(prog)s -i hot_threads.txt -o flamegraph.svg
  %(prog)s -i hot_threads.txt --title "Production Cluster"

  # Tasks API
  %(prog)s -i tasks.json -o tasks.svg
        """,
    )

    parser.add_argument(
        "-i", "--input", required=True, help="Input file path (Hot Threads text or Tasks API JSON)"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="output.svg",
        help="Output SVG file path (default: output.svg)",
    )

    parser.add_argument(
        "--title",
        default=None,  # None means auto-detect
        help="Graph title (default: auto-detected from input type)",
    )

    parser.add_argument(
        "--width", type=int, default=1920, help="SVG width in pixels (default: 1920)"
    )

    parser.add_argument(
        "--height", type=int, default=18, help="Frame height in pixels (default: 18)"
    )

    parser.add_argument(
        "--minwidth",
        default="0.1",
        help="Minimum frame width in pixels or percent "
        "(default: 0.1, e.g., '0.1' or '0.5%%')",
    )

    parser.add_argument(
        "--color",
        default="hot",
        choices=[
            "hot",
            "java",
            "mem",
            "io",
            "wakeup",
            "chain",
            "red",
            "green",
            "blue",
            "yellow",
            "purple",
            "aqua",
            "orange",
            "cpu",
        ],
        help="Color theme (default: hot). 'cpu' theme colors by CPU usage (red=high, green=low)",
    )

    parser.add_argument(
        "--sort-by-cpu",
        action="store_true",
        default=True,
        help="Sort threads/actions by value (highest first) (default: enabled)",
    )

    parser.add_argument(
        "--no-sort-by-cpu",
        action="store_false",
        dest="sort_by_cpu",
        help="Disable value-based sorting",
    )

    parser.add_argument(
        "--show-cpu-percent",
        action="store_true",
        default=True,
        help="Show percentage in flame graph labels (default: enabled)",
    )

    parser.add_argument(
        "--no-show-cpu-percent",
        action="store_false",
        dest="show_cpu_percent",
        help="Disable percentage display in labels",
    )

    parser.add_argument(
        "--per-node",
        action="store_true",
        help="[Hot Threads only] Generate separate flame graph for each node",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Detect input format
    input_format = detect_input_format(text)
    is_tasks = input_format == "tasks"

    # Parse based on format
    if is_tasks:
        parser = TasksParser()
    else:
        parser = HotThreadsParser()

    try:
        data = parser.parse_text(text)
    except Exception as e:
        print(f"Error parsing {input_format} data: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not data.threads:
        print("Warning: No data found in input", file=sys.stderr)
        sys.exit(0)

    # Determine title
    if args.title:
        title = args.title
    elif is_tasks:
        title = "Elasticsearch Tasks"
    else:
        title = "Elasticsearch Hot Threads"

    # --per-node is not supported for Tasks API
    if is_tasks and args.per_node:
        print("Warning: --per-node is not supported for Tasks API, ignoring...", file=sys.stderr)
        args.per_node = False

    output_path = Path(args.output)

    if args.per_node:
        # Per-node mode (Hot Threads only)
        from collections import defaultdict

        threads_by_node = defaultdict(list)
        for thread in data.threads:
            key = f"{thread.node_id}_{thread.node_name}"
            threads_by_node[key].append(thread)

        print(
            f"[OK] Generating {len(threads_by_node)} separate flame graphs (one per node)"
        )

        for node_key, node_threads in threads_by_node.items():
            if not node_threads:
                continue

            node_name = node_threads[0].node_name
            node_cpu = sum(t.cpu_time_ms for t in node_threads)

            node_data = type(
                "obj",
                (object,),
                {
                    "threads": node_threads,
                    "total_cpu_time": node_cpu,
                    "node_count": 1,
                    "interval_ms": node_threads[0].interval_ms,
                },
            )()

            if output_path.is_dir():
                svg_filename = str(output_path / f"{node_name}.svg")
            else:
                svg_filename = f"output_{node_name}.svg"

            generator = FlameGraphGenerator(
                width=args.width,
                height=args.height,
                minwidth=args.minwidth,
                title=f"{title} - {node_name}",
                color_theme=args.color,
                sort_by_cpu=args.sort_by_cpu,
                show_cpu_percent=args.show_cpu_percent,
            )

            try:
                svg = generator.generate(node_data, is_tasks=False)
            except Exception as e:
                print(
                    f"Error generating flame graph for {node_name}: {e}",
                    file=sys.stderr,
                )
                continue

            try:
                with open(svg_filename, "w", encoding="utf-8") as f:
                    f.write(svg)
                print(f"[OK] Generated: {svg_filename}")
            except Exception as e:
                print(f"Error writing {svg_filename}: {e}", file=sys.stderr)

    else:
        # Single graph mode
        generator = FlameGraphGenerator(
            width=args.width,
            height=args.height,
            minwidth=args.minwidth,
            title=title,
            color_theme=args.color,
            sort_by_cpu=args.sort_by_cpu,
            show_cpu_percent=args.show_cpu_percent,
        )

        try:
            svg = generator.generate(data, is_tasks=is_tasks)
        except Exception as e:
            print(f"Error generating flame graph: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(svg)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)

        # Print summary
        print(f"[OK] Flame graph generated: {args.output}")
        print(f"  Input format: {input_format}")
        print(f"  Nodes: {data.node_count}")
        if is_tasks:
            # For Tasks API, show total running time
            total_nanos = data.total_cpu_time * 1_000_000
            print(f"  Actions: {len(data.threads)}")
            print(f"  Total running time: {format_time_nanos(total_nanos)}")
        else:
            # For Hot Threads, show CPU time
            print(f"  Threads: {len(data.threads)}")
            print(f"  Total CPU time: {data.total_cpu_time:.2f}ms")


if __name__ == "__main__":
    main()
