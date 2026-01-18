"""
Flame graph generator module

Generates interactive SVG flame graphs from parsed Hot Threads data.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re
import os

from .color import get_color


@dataclass
class FrameNode:
    """Represents a single frame in the flame graph"""

    name: str
    depth: int
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    value: float = 0.0
    samples_count: int = 0
    percentage: float = 0.0
    cpu_percent: float = 0.0
    color: str = "rgb(255,255,255)"
    start_time: float = 0.0
    end_time: float = 0.0
    parent: Optional["FrameNode"] = None
    children: List["FrameNode"] = field(default_factory=list)


class FlameGraphGenerator:
    """Generates interactive SVG flame graphs"""

    def __init__(
        self,
        width: int = 1920,
        height: int = 18,
        fontsize: int = 14,
        xpad: int = 10,
        ypad: int = 50,
        minwidth: str = "0.1",
        title: str = "Elasticsearch Hot Threads",
        color_theme: str = "hot",
        nametype: str = "Function:",
        countname: str = "samples",
        sort_by_cpu: bool = False,
        show_cpu_percent: bool = False,
    ):
        self.width = width
        self.height = height
        self.fontsize = fontsize
        self.fontwidth = 0.59
        self.xpad = xpad
        self.ypad = ypad
        self.minwidth = minwidth
        self.title = title
        self.color_theme = color_theme
        self.nametype = nametype
        self.countname = countname
        self.sort_by_cpu = sort_by_cpu
        self.show_cpu_percent = show_cpu_percent

        self.ypad1 = fontsize * 3
        self.ypad2 = fontsize * 2 + 10
        self.framepad = 1
        self.current_y = self.ypad1

        # Get JavaScript file path
        self.js_file = os.path.join(
            os.path.dirname(__file__), "..", "static", "interactions.js"
        )

    def generate(self, data) -> str:
        """
        Generate flame graph SVG from ParsedData

        Args:
            data: ParsedData object

        Returns:
            SVG string
        """
        merged = self._merge_threads(data.threads)
        root = self._build_tree(merged, data.total_cpu_time)
        self._assign_colors(root)
        self._calculate_layout(root, data.total_cpu_time)
        frames = self._collect_frames(root)
        frames = self._filter_by_minwidth(frames, data.total_cpu_time)
        return self._render_svg(frames, data.total_cpu_time)

    def _merge_threads(self, threads: List) -> dict:
        """
        Merge threads by node_id and thread_name, accumulate CPU time and samples.

        Args:
            threads: List of ThreadInfo objects

        Returns:
            Dict mapping node_id to list of (thread_name, cpu_time_ms, cpu_percent, samples_count) tuples
        """
        # First, group threads by node_id and thread_name
        # Store both cpu_time_ms and samples_count
        node_thread_groups = {}
        for thread in threads:
            node_key = thread.node_id
            if node_key not in node_thread_groups:
                node_thread_groups[node_key] = {}

            thread_name = thread.thread_name
            if thread_name in node_thread_groups[node_key]:
                # Accumulate both CPU time and samples count
                node_thread_groups[node_key][thread_name][0] += thread.cpu_time_ms
                node_thread_groups[node_key][thread_name][1] += thread.samples_count
            else:
                node_thread_groups[node_key][thread_name] = [
                    thread.cpu_time_ms,
                    thread.samples_count,
                ]

        # Calculate total CPU time for percentage
        total_cpu = sum(t.cpu_time_ms for t in threads)

        # Build result dict: node_id -> list of (thread_name, cpu_time, cpu_percent, samples_count)
        result = {}
        for node_id, thread_dict in node_thread_groups.items():
            node_total = sum(v[0] for v in thread_dict.values())
            node_samples = sum(v[1] for v in thread_dict.values())
            thread_list = []
            for thread_name, (cpu_time, samples_count) in thread_dict.items():
                cpu_percent = (cpu_time / node_total * 100) if node_total > 0 else 0
                thread_list.append((thread_name, cpu_time, cpu_percent, samples_count))

            # Sort by CPU time if enabled
            if self.sort_by_cpu:
                thread_list.sort(key=lambda x: x[1], reverse=True)

            result[node_id] = {
                "threads": thread_list,
                "node_cpu": node_total,
                "node_samples": node_samples,
                "node_percent": 100.0,
            }

        return result

    def _build_tree(self, merged: dict, total_time: float) -> FrameNode:
        """
        Build call tree with node hierarchy.

        Structure: all (root) -> node_id -> thread_name

        Args:
            merged: Dict mapping node_id to {'threads': [...], 'node_cpu': ..., 'node_samples': ..., 'node_percent': ...}
            total_time: Total CPU time

        Returns:
            Root FrameNode
        """
        root = FrameNode(
            name="all", depth=0, value=total_time, color="rgb(255,255,255)"
        )

        # Create node frames
        for node_id, node_data in merged.items():
            node_frame = FrameNode(
                name=node_id, depth=1, value=node_data["node_cpu"], parent=root
            )
            node_frame.cpu_percent = node_data["node_percent"]
            node_frame.percentage = node_data["node_percent"]
            node_frame.samples_count = node_data["node_samples"]
            root.children.append(node_frame)

            # Create thread frames under each node
            for thread_name, cpu_time, cpu_percent, samples_count in node_data[
                "threads"
            ]:
                thread_frame = FrameNode(
                    name=thread_name, depth=2, value=cpu_time, parent=node_frame
                )
                thread_frame.cpu_percent = cpu_percent
                thread_frame.samples_count = samples_count
                node_frame.children.append(thread_frame)

        return root

    def _assign_colors(self, node: FrameNode):
        """
        Assign colors to all nodes in tree

        Args:
            node: Root FrameNode
        """
        if node.name != "all":
            # Depth 1 = node level, use distinct color
            if node.depth == 1:
                # Node frames use a consistent blue-gray color
                node.color = "rgb(100, 120, 160)"
            # Depth 2 = thread level, use theme colors
            elif node.depth == 2:
                # Use cpu-based color theme if enabled
                if self.color_theme == "cpu":
                    node.color = self._get_cpu_color(node.cpu_percent)
                else:
                    node.color = get_color(node.name, self.color_theme)
            else:
                # Other depths use theme colors
                node.color = get_color(node.name, self.color_theme)

        for child in node.children:
            self._assign_colors(child)

    def _get_cpu_color(self, cpu_percent: float) -> str:
        """
        Generate color based on CPU usage percentage.
        Higher CPU = warmer colors (red/orange), lower CPU = cooler colors (blue/green).

        Args:
            cpu_percent: CPU percentage (0-100)

        Returns:
            RGB color string
        """
        # Normalize to 0-1 range
        ratio = min(cpu_percent / 100, 1.0)

        if ratio > 0.5:
            # High CPU: Orange to Red
            local_ratio = (ratio - 0.5) / 0.5
            r = 255
            g = int(165 * (1 - local_ratio))
            b = 0
        elif ratio > 0.2:
            # Medium CPU: Yellow to Orange
            local_ratio = (ratio - 0.2) / 0.3
            r = int(255 * (0.5 + 0.5 * local_ratio))
            g = int(255 * (1 - 0.4 * local_ratio))
            b = 0
        else:
            # Low CPU: Green to Yellow
            local_ratio = ratio / 0.2
            r = int(255 * local_ratio)
            g = 255
            b = int(100 * (1 - local_ratio))

        return f"rgb({r},{g},{b})"

    def _calculate_layout(self, root: FrameNode, total_time: float):
        """
        Calculate x, y, width for all frames

        New layout: Each node (depth=1) is displayed horizontally side-by-side.
        Threads (depth=2) are laid out horizontally within each node.

        Args:
            root: Root FrameNode
            total_time: Total CPU time
        """
        total_width = self.width - 2 * self.xpad

        def calc_percent(node: FrameNode, parent_value: float):
            # Each node's percentage is relative to its parent
            # Node level (depth=1) is always 100%
            if node.depth == 1:
                node.percentage = 100.0
            else:
                node.percentage = (
                    (node.value / parent_value) * 100 if parent_value > 0 else 0
                )
            for child in node.children:
                calc_percent(child, node.value)

        calc_percent(root, total_time)

        # Layout nodes (depth=1) - side by side horizontally at bottom
        # Layout threads (depth=2) - horizontal within each node, above nodes
        current_x = self.xpad

        for node in root.children:
            # Node width is proportional to its CPU time
            if total_time > 0:
                node.width = (node.value / total_time) * total_width
            else:
                node.width = 0
            node.x = current_x
            node.y = self.ypad1 + (self.height + self.framepad)

            current_x += node.width
            node.end_time = node.x + node.width

        # Layout threads above nodes
        current_x = self.xpad
        for node in root.children:
            if node.children:
                thread_x = node.x
                for thread in node.children:
                    thread.x = thread_x
                    # Thread width is proportional to its CPU time within the node
                    if node.value > 0:
                        thread.width = (thread.value / node.value) * node.width
                    else:
                        thread.width = 0
                    thread.y = self.ypad1
                    thread_x += thread.width

            current_x += node.width

        self.current_y = self.ypad1 + 2 * (self.height + self.framepad)

    def _calculate_time_ranges(self, node: FrameNode, current_time: float) -> float:
        """
        Recursively calculate start_time and end_time for each node

        Args:
            node: FrameNode
            current_time: Current time position

        Returns:
            Next time position
        """
        node.start_time = current_time

        for child in node.children:
            current_time = self._calculate_time_ranges(child, current_time)

        node.end_time = current_time
        return current_time

    def _convert_to_pixels(self, node: FrameNode, width_per_time: float):
        """
        Convert time ranges to pixel coordinates

        Args:
            node: FrameNode
            width_per_time: Pixels per millisecond
        """
        node.x = self.xpad + node.start_time * width_per_time
        node.width = (node.end_time - node.start_time) * width_per_time

        for child in node.children:
            self._convert_to_pixels(child, width_per_time)

    def _collect_frames(self, root: FrameNode) -> List[FrameNode]:
        """
        Collect all frames (excluding root) into a list

        Args:
            root: Root FrameNode

        Returns:
            List of FrameNode objects
        """
        frames = []

        def collect(node: FrameNode):
            if node.name != "all":
                frames.append(node)
            for child in node.children:
                collect(child)

        collect(root)
        return frames

    def _filter_by_minwidth(
        self, frames: List[FrameNode], total_time: float
    ) -> List[FrameNode]:
        """
        Filter frames by minimum width

        Args:
            frames: List of FrameNode objects
            total_time: Total CPU time

        Returns:
            Filtered list of FrameNode objects
        """
        if self.minwidth.endswith("%"):
            min_pct = float(self.minwidth.rstrip("%"))
            min_width = (self.width - 2 * self.xpad) * min_pct / 100
        else:
            min_width = float(self.minwidth)

        filtered = []
        for frame in frames:
            if frame.width >= min_width:
                filtered.append(frame)

        return filtered

    def _render_svg(self, frames: List[FrameNode], total_time: float) -> str:
        """
        Render flame graph as SVG

        Args:
            frames: List of FrameNode objects
            total_time: Total CPU time

        Returns:
            SVG string
        """
        # Calculate image height using actual layout position
        image_height = self.current_y + self.ypad2

        # SVG header
        svg_lines = [
            '<?xml version="1.0" standalone="no"?>',
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">',
            f'<svg version="1.1" width="{self.width}" height="{image_height}" '
            'onload="init(evt)" viewBox="0 0 '
            + str(self.width)
            + " "
            + str(image_height)
            + '" '
            'xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">',
        ]

        # Comments
        svg_lines.append(
            "<!-- Flame graph stack visualization. "
            "See https://github.com/brendangregg/FlameGraph -->"
        )

        svg_lines.append("<defs>")
        svg_lines.append(
            '  <linearGradient id="background" y1="0" y2="1" x1="0" x2="0">'
        )
        svg_lines.append('    <stop stop-color="#eeeeee" offset="5%" />')
        svg_lines.append('    <stop stop-color="#eeeeb0" offset="95%" />')
        svg_lines.append("  </linearGradient>")
        svg_lines.append("</defs>")

        svg_lines.append('<style type="text/css">')
        svg_lines.append(
            f"  text {{ font-family: Verdana; font-size: {self.fontsize}px; fill: black; }}"
        )
        svg_lines.append("  #search, #ignorecase { opacity: 0.1; cursor: pointer; }")
        svg_lines.append(
            "  #search:hover, #search.show, #ignorecase:hover, #ignorecase.show { opacity: 1; }"
        )
        svg_lines.append(
            "  #title { text-anchor: middle; font-size: "
            + str(self.fontsize + 5)
            + "px; }"
        )
        svg_lines.append("  #unzoom { cursor: pointer; }")
        svg_lines.append(
            "  #frames > *:hover { stroke: black; stroke-width: 0.5; cursor: pointer; }"
        )
        svg_lines.append("  .hide { display: none; }")
        svg_lines.append("  .parent { opacity: 0.5; }")
        svg_lines.append("</style>")

        svg_lines.append('<script type="text/ecmascript">')
        svg_lines.append(self._get_javascript())
        svg_lines.append("</script>")

        svg_lines.append(
            f'<rect x="0" y="0" width="{self.width}" height="{image_height}" '
            f'fill="url(#background)" />'
        )

        svg_lines.append(
            f'<text id="title" x="{self.width / 2}" y="{self.fontsize * 2}">'
            f"{self._escape_xml(self.title)}</text>"
        )

        svg_lines.append(
            f'<text id="unzoom" x="{self.xpad}" y="{self.fontsize * 2}" '
            'class="hide">Reset Zoom</text>'
        )
        svg_lines.append(
            f'<text id="search" x="{self.width - self.xpad - 100}" '
            f'y="{self.fontsize * 2}">Search</text>'
        )
        svg_lines.append(
            f'<text id="details" x="{self.xpad}" '
            f'y="{image_height - self.ypad2 / 2}"> </text>'
        )

        svg_lines.append('<g id="frames">')

        for frame in frames:
            y = frame.y

            node_id = ""
            if frame.depth == 1:
                node_id = frame.name
            elif frame.depth == 2 and hasattr(frame, "parent") and frame.parent:
                node_id = frame.parent.name

            svg_lines.append(f'  <g data-depth="{frame.depth}" data-node="{node_id}">')
            samples = (
                frame.samples_count if frame.samples_count > 0 else int(frame.value)
            )
            samples_str = "{:,}".format(samples)
            pct = f"{frame.percentage:.2f}"
            escaped_name = self._escape_xml(frame.name)

            info = f"{escaped_name} ({samples_str} {self.countname}, {pct}%)"
            svg_lines.append(f"    <title>{info}</title>")

            svg_lines.append(
                f'    <rect x="{frame.x:.1f}" y="{y:.1f}" '
                f'width="{frame.width:.1f}" height="{self.height - self.framepad}" '
                f'fill="{frame.color}" rx="2" ry="2" />'
            )

            chars = int(frame.width / (self.fontsize * self.fontwidth))
            if chars >= 3:
                # For thread level (depth=2), simplify the name
                display_name = frame.name
                if frame.depth == 2:
                    display_name = self._simplify_thread_name(frame.name)

                # Show CPU percent if enabled and frame is wide enough
                if self.show_cpu_percent and hasattr(frame, "cpu_percent"):
                    cpu_pct_text = f" {frame.cpu_percent:.1f}%"
                    remaining_chars = chars - len(cpu_pct_text)
                    if remaining_chars >= 3:
                        text = display_name[:remaining_chars]
                        if remaining_chars < len(display_name):
                            text = display_name[: remaining_chars - 2] + ".."
                        text = text + cpu_pct_text
                    else:
                        # Not enough space for both, show CPU % only
                        text = cpu_pct_text.strip()
                else:
                    text = display_name[:chars]
                    if chars < len(display_name):
                        text = display_name[: chars - 2] + ".."

                svg_lines.append(
                    f'    <text x="{frame.x + 3}" y="{y + self.fontsize}">'
                    f"{self._escape_xml(text)}</text>"
                )

            svg_lines.append("  </g>")

        svg_lines.append("</g>")
        svg_lines.append("</svg>")

        return "\n".join(svg_lines)

    def _escape_xml(self, text: str) -> str:
        """
        Escape special XML characters

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        return text

    def _simplify_thread_name(self, thread_name: str) -> str:
        """
        Simplify thread name by removing elasticsearch[node_id] prefix.

        Example:
        - elasticsearch[abc123][management][T#5] -> [management][T#5]
        - coral-orchestrator-170 -> coral-orchestrator-170 (no change)

        Args:
            thread_name: Original thread name

        Returns:
            Simplified thread name
        """
        # Match pattern: elasticsearch[node_id] followed by [...]
        import re

        # Match elasticsearch[...] followed by [...]
        pattern = r"^elasticsearch\[.+?\]\s*(\[.+\])"
        match = re.match(pattern, thread_name)
        if match:
            # Return the matched [...] part and everything after
            return thread_name[match.start(1) :]
        return thread_name

    def _get_javascript(self) -> str:
        """
        Read JavaScript interactions file

        Returns:
            JavaScript content as string
        """
        try:
            with open(self.js_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "// JavaScript file not found"
