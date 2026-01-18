"""
Elasticsearch Hot Threads Flame Graph Generator - CLI

Command-line interface for generating flame graphs from Hot Threads data.
"""

import argparse
import sys
from pathlib import Path

from es_flame_graph import HotThreadsParser, FlameGraphGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Elasticsearch Hot Threads Flame Graph Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i hot_threads.txt -o flamegraph.svg
  %(prog)s -i hot_threads.txt --title "Production Cluster"
  %(prog)s -i hot_threads.txt --width 1600 --minwidth 0.5%
        """,
    )

    parser.add_argument(
        "-i", "--input", required=True, help="Input file path (Hot Threads text output)"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="output.svg",
        help="Output SVG file path (default: output.svg)",
    )

    parser.add_argument(
        "--title",
        default="Elasticsearch Hot Threads",
        help="Graph title (default: 'Elasticsearch Hot Threads')",
    )

    parser.add_argument(
        "--width", type=int, default=1200, help="SVG width in pixels (default: 1200)"
    )

    parser.add_argument(
        "--height", type=int, default=16, help="Frame height in pixels (default: 16)"
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
        ],
        help="Color theme (default: hot)",
    )

    parser.add_argument(
        "--per-node",
        action="store_true",
        help="Generate separate flame graph for each node",
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

    parser = HotThreadsParser()
    try:
        data = parser.parse_text(text)
    except Exception as e:
        print(f"Error parsing Hot Threads data: {e}", file=sys.stderr)
        sys.exit(1)

    if not data.threads:
        print("Warning: No hot threads found in input data", file=sys.stderr)
        sys.exit(0)

    from collections import defaultdict

    output_path = Path(args.output)

    if args.per_node:
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
                title=f"{args.title} - {node_name}",
                color_theme=args.color,
            )

            try:
                svg = generator.generate(node_data)
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
        generator = FlameGraphGenerator(
            width=args.width,
            height=args.height,
            minwidth=args.minwidth,
            title=args.title,
            color_theme=args.color,
        )

        try:
            svg = generator.generate(data)
        except Exception as e:
            print(f"Error generating flame graph: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(svg)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"[OK] Flame graph generated: {args.output}")
        print(f"  Nodes: {data.node_count}")
        print(f"  Threads: {len(data.threads)}")
        print(f"  Total CPU time: {data.total_cpu_time:.2f}ms")


if __name__ == "__main__":
    main()
