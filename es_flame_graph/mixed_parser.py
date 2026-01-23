"""
Mixed parser module

Parses input files containing both Hot Threads and Tasks API data,
automatically detecting and separating them.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class MixedData:
    """Container for separated Hot Threads and Tasks data"""

    hot_threads_text: Optional[str]
    tasks_text: Optional[str]
    hot_threads_count: int
    tasks_count: int


class MixedParser:
    """Parser for mixed Hot Threads and Tasks API input files"""

    def __init__(self):
        # Pattern for Hot Threads node header
        # Example: ::: {8d13c2252a3717d6039a93c52054b7db}{yzr8Xq-1TwytcvJ04S4YoQ}{...}
        self.hot_threads_pattern = re.compile(r"^:::\s+\{")

    def parse_file(self, filepath: str) -> MixedData:
        """Parse mixed data from a file"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_text(content)

    def parse_text(self, text: str) -> MixedData:
        """
        Parse and separate mixed Hot Threads and Tasks API data

        Args:
            text: Input text containing mixed Hot Threads and Tasks API data

        Returns:
            MixedData with separated texts
        """
        lines = text.split("\n")

        # Step 1: Find the tasks marker line (e.g., "tasks:dffs")
        tasks_marker_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"^tasks:", stripped):
                tasks_marker_idx = i
                break

        # Step 2: Collect Hot Threads data (before tasks marker, starting with :::)
        hot_threads_lines = []
        if tasks_marker_idx > 0:
            # Process lines before tasks marker
            for i in range(tasks_marker_idx):
                line = lines[i]
                if self.hot_threads_pattern.match(line):
                    # Found a Hot Threads section, collect until next section or tasks marker
                    while i < tasks_marker_idx:
                        hot_threads_lines.append(line)
                        i += 1
                        if i >= tasks_marker_idx:
                            break
                        line = lines[i]
                        # Stop if we hit another Hot Threads section
                        if self.hot_threads_pattern.match(line):
                            break
        else:
            # No tasks marker found, try to find any Hot Threads sections
            # and stop when we see a JSON object start
            i = 0
            while i < len(lines):
                line = lines[i]
                if self.hot_threads_pattern.match(line):
                    # Collect Hot Threads section
                    while i < len(lines):
                        hot_threads_lines.append(line)
                        i += 1
                        if i >= len(lines):
                            break
                        line = lines[i]
                        # Stop if we hit another Hot Threads section
                        if self.hot_threads_pattern.match(line):
                            break
                        # Stop if we hit a JSON object (likely Tasks API)
                        if line.strip().startswith("{"):
                            # Set this as the tasks marker for later use
                            tasks_marker_idx = i
                            break
                else:
                    i += 1

        # Step 3: Collect Tasks data
        tasks_lines = []
        if tasks_marker_idx >= 0:
            # Find the JSON object start (may be after "tasks:xxx" line)
            json_start_idx = tasks_marker_idx
            for i in range(tasks_marker_idx, len(lines)):
                if lines[i].strip().startswith("{"):
                    json_start_idx = i
                    break

            # Collect from JSON start to end of file
            for i in range(json_start_idx, len(lines)):
                tasks_lines.append(lines[i])

        hot_threads_text = "\n".join(hot_threads_lines) if hot_threads_lines else None
        tasks_text = "\n".join(tasks_lines) if tasks_lines else None

        # Count sections for summary
        ht_count = len(re.findall(r"Hot threads at", hot_threads_text or "")) if hot_threads_text else 0
        tasks_count = 1 if tasks_text else 0

        return MixedData(
            hot_threads_text=hot_threads_text,
            tasks_text=tasks_text,
            hot_threads_count=ht_count,
            tasks_count=tasks_count,
        )

    def generate_flamegraphs(
        self,
        mixed_data: MixedData,
        output_prefix: str,
        generator_kwargs: dict,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate flame graphs for both Hot Threads and Tasks data

        Args:
            mixed_data: Parsed mixed data
            output_prefix: Output file prefix (without extension)
            generator_kwargs: Arguments to pass to FlameGraphGenerator

        Returns:
            Tuple of (hot_threads_svg_path, tasks_svg_path)
        """
        from .parser import HotThreadsParser
        from .tasks_parser import TasksParser
        from .flamegraph import FlameGraphGenerator

        hot_threads_output = None
        tasks_output = None

        # Generate Hot Threads flame graph
        if mixed_data.hot_threads_text:
            ht_parser = HotThreadsParser()
            ht_data = ht_parser.parse_text(mixed_data.hot_threads_text)

            if ht_data.threads:
                ht_generator = FlameGraphGenerator(
                    title="Elasticsearch Hot Threads",
                    **generator_kwargs
                )
                ht_svg = ht_generator.generate(ht_data, is_tasks=False)

                hot_threads_output = f"{output_prefix}_hot_threads.svg"
                with open(hot_threads_output, "w", encoding="utf-8") as f:
                    f.write(ht_svg)

        # Generate Tasks flame graph
        if mixed_data.tasks_text:
            t_parser = TasksParser()
            t_data = t_parser.parse_text(mixed_data.tasks_text)

            if t_data.threads:
                t_generator = FlameGraphGenerator(
                    title="Elasticsearch Tasks",
                    **generator_kwargs
                )
                t_svg = t_generator.generate(t_data, is_tasks=True)

                tasks_output = f"{output_prefix}_tasks.svg"
                with open(tasks_output, "w", encoding="utf-8") as f:
                    f.write(t_svg)

        return hot_threads_output, tasks_output
