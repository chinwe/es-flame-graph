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
    percentage: float = 0.0
    color: str = "rgb(255,255,255)"
    start_time: float = 0.0
    end_time: float = 0.0
    parent: Optional["FrameNode"] = None
    children: List["FrameNode"] = field(default_factory=list)


class FlameGraphGenerator:
    """Generates interactive SVG flame graphs"""

    def __init__(
        self,
        width: int = 1200,
        height: int = 16,
        fontsize: int = 12,
        xpad: int = 10,
        ypad: int = 50,
        minwidth: str = "0.1",
        title: str = "Elasticsearch Hot Threads",
        color_theme: str = "hot",
        nametype: str = "Function:",
        countname: str = "samples",
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

        self.ypad1 = fontsize * 3
        self.ypad2 = fontsize * 2 + 10
        self.framepad = 1

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

    def _merge_threads(self, threads: List) -> Dict[str, float]:
        """
        Merge threads with same stacks, accumulate CPU time

        For flame graph, we use thread name as the function name
        instead of the full call stack to keep the display simple.

        Args:
            threads: List of ThreadInfo objects

        Returns:
            Dict mapping thread_name to total_cpu_time
        """
        merged = {}
        for thread in threads:
            thread_name = thread.thread_name
            if thread_name in merged:
                merged[thread_name] += thread.cpu_time_ms
            else:
                merged[thread_name] = thread.cpu_time_ms
        return merged

    def _build_tree(self, merged: Dict[str, float], total_time: float) -> FrameNode:
        """
        Build call tree from merged thread data

        For per-node flame graphs, we create a flat list of threads.
        Each thread becomes a child of the root with its thread name and CPU time.

        Args:
            merged: Dict mapping thread_name to cpu_time
            total_time: Total CPU time

        Returns:
            Root FrameNode
        """
        root = FrameNode(
            name="all", depth=0, value=total_time, color="rgb(255,255,255)"
        )

        for thread_name, cpu_time in merged.items():
            child = FrameNode(name=thread_name, depth=1, value=cpu_time, parent=root)
            root.children.append(child)

        return root

    def _assign_colors(self, node: FrameNode):
        """
        Assign colors to all nodes in tree

        Args:
            node: Root FrameNode
        """
        if node.name != "all":
            node.color = get_color(node.name, self.color_theme)

        for child in node.children:
            self._assign_colors(child)

    def _calculate_layout(self, root: FrameNode, total_time: float):
        """
        Calculate x, y, width for all frames

        Args:
            root: Root FrameNode
            total_time: Total CPU time
        """
        width_per_time = (self.width - 2 * self.xpad) / total_time

        def calc_percent(node: FrameNode):
            node.percentage = (node.value / total_time) * 100
            for child in node.children:
                calc_percent(child)

        calc_percent(root)

        def set_time_ranges(node: FrameNode, start_time: float) -> float:
            node.start_time = start_time

            if not node.children:
                node.end_time = start_time + node.value
                return node.end_time

            max_child_end = start_time
            for child in node.children:
                child_end = set_time_ranges(child, start_time)
                if child_end > max_child_end:
                    max_child_end = child_end

            node.end_time = max_child_end
            return max_child_end

        set_time_ranges(root, 0)
        self._convert_to_pixels(root, width_per_time)

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
            min_time = total_time * min_pct / 100
        else:
            width_per_time = (self.width - 2 * self.xpad) / total_time
            min_time = float(self.minwidth) / width_per_time

        filtered = []
        for frame in frames:
            if (frame.end_time - frame.start_time) >= min_time:
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
        # Calculate image height
        max_depth = max((f.depth for f in frames), default=0)
        image_height = (max_depth + 1) * self.height + self.ypad1 + self.ypad2

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
            y = (
                image_height
                - self.ypad2
                - (frame.depth + 1) * self.height
                + self.framepad
            )

            svg_lines.append("  <g>")
            samples = int(frame.value)
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
                text = frame.name[:chars]
                if chars < len(frame.name):
                    text = frame.name[: chars - 2] + ".."

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
