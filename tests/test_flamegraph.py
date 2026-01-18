"""
Test cases for flame graph generator
"""

import unittest
import os
from pathlib import Path

from es_flame_graph.parser import HotThreadsParser, ParsedData
from es_flame_graph.flamegraph import FlameGraphGenerator, FrameNode


class TestFlameGraphGenerator(unittest.TestCase):
    """Test flame graph generation"""

    def setUp(self):
        self.parser = HotThreadsParser()
        self.generator = FlameGraphGenerator(width=1920, height=18)

    def test_initialization(self):
        """Test FlameGraphGenerator initialization"""
        self.assertEqual(self.generator.width, 1920)
        self.assertEqual(self.generator.height, 18)
        self.assertEqual(self.generator.title, "Elasticsearch Hot Threads")
        self.assertEqual(self.generator.color_theme, "hot")

    def test_merge_threads_identical_stacks(self):
        """Test merging threads with identical stacks"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="abc123",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=5.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["A", "B", "C"],
            ),
            ThreadInfo(
                node_id="def456",
                node_name="node2",
                node_ip="10.0.0.2",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=2.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-2",
                snapshots="10/10",
                stack_frames=["A", "B", "C"],
            ),
        ]

        merged = self.generator._merge_threads(threads)

        # Now returns dict mapping node_id to thread data
        self.assertEqual(len(merged), 2)
        # Check node abc123
        self.assertIn("abc123", merged)
        self.assertEqual(merged["abc123"]["node_cpu"], 5.0)
        self.assertEqual(len(merged["abc123"]["threads"]), 1)
        self.assertEqual(merged["abc123"]["threads"][0][0], "thread-1")
        # Check node def456
        self.assertIn("def456", merged)
        self.assertEqual(merged["def456"]["node_cpu"], 10.0)
        self.assertEqual(len(merged["def456"]["threads"]), 1)
        self.assertEqual(merged["def456"]["threads"][0][0], "thread-2")

    def test_build_tree(self):
        """Test building tree from merged data"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="abc123",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["A", "B", "C"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        merged = self.generator._merge_threads(data.threads)
        root = self.generator._build_tree(merged, data.total_cpu_time)

        self.assertEqual(root.name, "all")
        self.assertEqual(root.value, 10.0)
        self.assertEqual(len(root.children), 1)
        # First level is node
        self.assertEqual(root.children[0].name, "abc123")
        self.assertEqual(root.children[0].depth, 1)
        self.assertEqual(root.children[0].value, 10.0)
        # Second level is thread
        self.assertEqual(len(root.children[0].children), 1)
        self.assertEqual(root.children[0].children[0].name, "thread-1")
        self.assertEqual(root.children[0].children[0].depth, 2)
        self.assertEqual(root.children[0].children[0].value, 10.0)

    def test_escape_xml(self):
        """Test XML character escaping"""
        self.assertEqual(
            self.generator._escape_xml('a<b>c&d"e'), "a&lt;b&gt;c&amp;d&quot;e"
        )

    def test_filter_by_minwidth_pixels(self):
        """Test filtering by minimum width in pixels"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="node1",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["LargeFunction"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        self.generator.minwidth = "0.5"
        merged = self.generator._merge_threads(data.threads)
        root = self.generator._build_tree(merged, data.total_cpu_time)
        self.generator._assign_colors(root)
        self.generator._calculate_layout(root, data.total_cpu_time)
        frames = self.generator._collect_frames(root)

        filtered = self.generator._filter_by_minwidth(frames, data.total_cpu_time)

        self.assertLessEqual(len(filtered), len(frames))

    def test_filter_by_minwidth_percent(self):
        """Test filtering by minimum width as percentage"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="node1",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=1.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["SmallFunction"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        self.generator.minwidth = "20%"
        merged = self.generator._merge_threads(data.threads)
        root = self.generator._build_tree(merged, data.total_cpu_time)
        self.generator._assign_colors(root)
        self.generator._calculate_layout(root, data.total_cpu_time)
        frames = self.generator._collect_frames(root)

        filtered = self.generator._filter_by_minwidth(frames, data.total_cpu_time)

        self.assertLessEqual(len(filtered), len(frames))

    def test_generate_svg(self):
        """Test SVG generation"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="node1",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["FunctionA", "FunctionB", "FunctionC"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        svg = self.generator.generate(data)

        self.assertIsNotNone(svg)
        self.assertIn("<?xml", svg)
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("function", svg.lower())

    def test_svg_includes_title(self):
        """Test that SVG includes title"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="node1",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["A"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        self.generator.title = "Test Title"
        svg = self.generator.generate(data)

        self.assertIn("Test Title", svg)

    def test_svg_includes_gradient(self):
        """Test that SVG includes gradient definition"""
        from es_flame_graph.parser import ThreadInfo

        threads = [
            ThreadInfo(
                node_id="node1",
                node_name="node1",
                node_ip="10.0.0.1",
                timestamp="2026-01-18T08:42:32Z",
                cpu_percent=1.0,
                cpu_time_ms=10.0,
                interval_ms=500.0,
                thread_name="thread-1",
                snapshots="10/10",
                stack_frames=["A"],
            )
        ]

        data = ParsedData(
            threads=threads, total_cpu_time=10.0, node_count=1, interval_ms=500.0
        )

        svg = self.generator.generate(data)

        self.assertIn("linearGradient", svg)
        self.assertIn("#eeeeee", svg)
        self.assertIn("#eeeeb0", svg)


if __name__ == "__main__":
    unittest.main()
