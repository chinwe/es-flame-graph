"""
Hot Threads parser module

Parses Elasticsearch Hot Threads API output into structured data.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ThreadInfo:
    """Represents a single hot thread's information"""

    node_id: str
    node_name: str
    node_ip: str
    timestamp: str
    cpu_percent: float
    cpu_time_ms: float
    interval_ms: float
    thread_name: str
    snapshots: str
    samples_count: int
    stack_frames: List[str]


@dataclass
class ParsedData:
    """Container for all parsed Hot Threads data"""

    threads: List[ThreadInfo]
    total_cpu_time: float
    node_count: int
    interval_ms: float


class HotThreadsParser:
    """Parser for Elasticsearch Hot Threads text output"""

    def __init__(self):
        # Pattern for node header line
        # Example: ::: {8d13c2252a3717d6039a93c52054b7db}{yzr8Xq-1TwytcvJ04S4YoQ}{...}
        self.node_header_pattern = re.compile(
            r"^:::\s+\{([a-f0-9]+)\}\{([^}]+)\}\{[^}]+\}\{([^}]+)\}"
        )

        # Pattern for hot threads header
        # Example: Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3
        self.hot_threads_header_pattern = re.compile(
            r"Hot threads at ([\dT:\.]+Z),\s+interval=(\d+)ms,"
        )

        # Pattern for CPU usage line
        # Example: 0.4% (2.2ms out of 500ms) cpu usage by thread 'thread-name'
        #          0.0% (141.2micros out of 500ms) cpu usage by thread 'thread-name'
        self.cpu_usage_pattern = re.compile(
            r"([\d.]+)%\s+\(([\d.]+)(micros|ms)\s+out of (\d+)ms\)\s+cpu usage by thread \'([^\']+)\'"
        )

        # Pattern for snapshots line
        # Example: 10/10 snapshots sharing following 6 elements
        self.snapshots_pattern = re.compile(
            r"(\d+)/(\d+) snapshots sharing following \d+ elements"
        )

    def parse_file(self, filepath: str) -> ParsedData:
        """Parse Hot Threads data from a file"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_text(content)

    def parse_text(self, text: str) -> ParsedData:
        """Parse Hot Threads data from text"""
        lines = text.split("\n")

        threads = []
        current_node = None
        current_timestamp = None
        current_interval = None
        current_thread_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for node header
            node_match = self.node_header_pattern.match(line)
            if node_match:
                node_id, node_name, node_ip = node_match.groups()
                current_node = {
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_ip": node_ip,
                }

            # Check for Hot threads header
            hot_threads_match = self.hot_threads_header_pattern.search(line)
            if hot_threads_match:
                current_timestamp, current_interval = hot_threads_match.groups()
                current_interval = float(current_interval)

            # Check for CPU usage line (start of a thread)
            cpu_match = self.cpu_usage_pattern.match(line.strip())
            if cpu_match:
                # Parse previous thread if exists
                if current_thread_lines and current_node:
                    thread = self._parse_thread_info(
                        current_thread_lines,
                        current_node,
                        current_timestamp,
                        current_interval,
                    )
                    if thread:
                        threads.append(thread)
                    current_thread_lines = []

                # Start new thread
                current_thread_lines = [line]

            # Collect thread lines (stack frames and snapshots)
            elif current_thread_lines and line.strip():
                current_thread_lines.append(line)

            # Empty line or node separator - end of current thread
            elif current_thread_lines and not line.strip():
                if current_node:
                    thread = self._parse_thread_info(
                        current_thread_lines,
                        current_node,
                        current_timestamp,
                        current_interval,
                    )
                    if thread:
                        threads.append(thread)
                    current_thread_lines = []

            i += 1

        # Don't forget the last thread
        if current_thread_lines and current_node:
            thread = self._parse_thread_info(
                current_thread_lines, current_node, current_timestamp, current_interval
            )
            if thread:
                threads.append(thread)

        # Calculate total CPU time
        total_cpu_time = sum(t.cpu_time_ms for t in threads)

        # Get unique node count
        node_ids = set(t.node_id for t in threads)

        return ParsedData(
            threads=threads,
            total_cpu_time=total_cpu_time,
            node_count=len(node_ids),
            interval_ms=current_interval or 500.0,
        )

    def _parse_thread_info(
        self,
        lines: List[str],
        node_info: dict,
        timestamp: Optional[str],
        interval: Optional[float],
    ) -> Optional[ThreadInfo]:
        """Parse thread information from collected lines"""
        if not lines:
            return None

        # First line: CPU usage
        cpu_line = lines[0].strip()
        cpu_match = self.cpu_usage_pattern.match(cpu_line)
        if not cpu_match:
            return None

        cpu_percent, cpu_time, unit, interval_ms, thread_name = cpu_match.groups()
        cpu_percent = float(cpu_percent)
        interval_ms = float(interval_ms)

        # Convert to milliseconds based on unit
        if unit == "micros":
            cpu_time_ms = float(cpu_time) / 1000
        else:  # unit == 'ms'
            cpu_time_ms = float(cpu_time)

        # Second line: snapshots
        snapshots = ""
        samples_count = 0
        if len(lines) > 1:
            snapshots_line = lines[1].strip()
            snapshots_match = self.snapshots_pattern.search(snapshots_line)
            if snapshots_match:
                snapshots = snapshots_match.group(1) + "/" + snapshots_match.group(2)
                samples_count = int(snapshots_match.group(1))

        # Remaining lines: stack frames
        stack_frames = []
        for line in lines[2:]:
            stripped = line.strip()
            if stripped and not stripped.startswith("["):
                # Remove Java module prefix if present
                # Example: java.base@11.0.25/jdk.internal.misc.Unsafe.park
                # Keep only: jdk.internal.misc.Unsafe.park
                frame = stripped
                if "@" in frame:
                    # Split on @ and take the part after /
                    parts = frame.split("@")
                    if len(parts) > 1 and "/" in parts[1]:
                        frame = parts[1].split("/")[-1]

                stack_frames.append(frame)

        # If no stack frames, skip this thread
        if not stack_frames:
            return None

        # Reverse stack frames to have root at the beginning
        # (Hot Threads shows leaf functions first)
        stack_frames = list(reversed(stack_frames))

        return ThreadInfo(
            node_id=node_info["node_id"],
            node_name=node_info["node_name"],
            node_ip=node_info["node_ip"],
            timestamp=timestamp or "",
            cpu_percent=cpu_percent,
            cpu_time_ms=cpu_time_ms,
            interval_ms=interval or interval_ms,
            thread_name=thread_name,
            snapshots=snapshots,
            samples_count=samples_count,
            stack_frames=stack_frames,
        )
