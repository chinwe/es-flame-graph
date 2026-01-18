"""
Test cases for Hot Threads parser
"""

import unittest
from pathlib import Path

from es_flame_graph.parser import HotThreadsParser, ThreadInfo


class TestHotThreadsParser(unittest.TestCase):
    """Test Hot Threads parser functionality"""

    def setUp(self):
        self.parser = HotThreadsParser()
        self.test_data_path = (
            Path(__file__).parent.parent / "examples" / "sample_hot_threads.txt"
        )

    def test_parse_file_exists(self):
        """Test parsing from existing file"""
        data = self.parser.parse_file(str(self.test_data_path))
        self.assertIsNotNone(data)
        self.assertGreater(len(data.threads), 0)

    def test_parse_text(self):
        """Test parsing from text"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

    1.0% (5.0ms out of 500ms) cpu usage by thread 'test-thread'
     10/10 snapshots sharing following 2 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
"""
        data = self.parser.parse_text(text)
        self.assertIsNotNone(data)
        self.assertEqual(len(data.threads), 1)

    def test_thread_info_structure(self):
        """Test thread info structure"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

    1.0% (5.0ms out of 500ms) cpu usage by thread 'test-thread'
     10/10 snapshots sharing following 2 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 1)

        thread = data.threads[0]
        self.assertEqual(thread.node_id, "abc123")
        self.assertEqual(thread.node_name, "node_name")
        self.assertEqual(thread.thread_name, "test-thread")
        self.assertEqual(thread.cpu_percent, 1.0)
        self.assertEqual(thread.cpu_time_ms, 5.0)
        self.assertEqual(thread.interval_ms, 500.0)
        self.assertEqual(thread.snapshots, "10/10")
        self.assertEqual(len(thread.stack_frames), 2)

    def test_cpu_info_extraction(self):
        """Test CPU info line parsing"""
        line = "1.0% (5.0ms out of 500ms) cpu usage by thread 'test-thread'"
        cpu_match = self.parser.cpu_usage_pattern.match(line.strip())

        self.assertIsNotNone(cpu_match)
        cpu_percent, cpu_time, unit, interval, thread_name = cpu_match.groups()
        self.assertEqual(float(cpu_percent), 1.0)
        self.assertEqual(float(cpu_time), 5.0)
        self.assertEqual(unit, "ms")
        self.assertEqual(float(interval), 500.0)
        self.assertEqual(thread_name, "test-thread")

    def test_cpu_info_extraction_micros(self):
        """Test CPU info line parsing with microseconds"""
        line = "0.0% (141.2micros out of 500ms) cpu usage by thread 'test-thread'"
        cpu_match = self.parser.cpu_usage_pattern.match(line.strip())

        self.assertIsNotNone(cpu_match)
        cpu_percent, cpu_time, unit, interval, thread_name = cpu_match.groups()
        self.assertEqual(float(cpu_percent), 0.0)
        self.assertEqual(float(cpu_time), 141.2)
        self.assertEqual(unit, "micros")
        self.assertEqual(float(interval), 500.0)
        self.assertEqual(thread_name, "test-thread")

    def test_stack_frame_reversal(self):
        """Test that stack frames are reversed (root first)"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

    1.0% (5.0ms out of 500ms) cpu usage by thread 'test-thread'
     10/10 snapshots sharing following 2 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
"""
        data = self.parser.parse_text(text)
        thread = data.threads[0]

        self.assertEqual(len(thread.stack_frames), 2)
        self.assertIn("Thread.run", thread.stack_frames[0])

    def test_total_cpu_time_calculation(self):
        """Test total CPU time calculation"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

    1.0% (5.0ms out of 500ms) cpu usage by thread 'test-thread-1'
     10/10 snapshots sharing following 1 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)

    2.0% (10.0ms out of 500ms) cpu usage by thread 'test-thread-2'
     10/10 snapshots sharing following 1 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
"""
        data = self.parser.parse_text(text)
        self.assertEqual(data.total_cpu_time, 15.0)

    def test_multiple_threads(self):
        """Test parsing multiple threads"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

    1.0% (5.0ms out of 500ms) cpu usage by thread 'thread-1'
     10/10 snapshots sharing following 1 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)

    1.5% (7.5ms out of 500ms) cpu usage by thread 'thread-2'
     10/10 snapshots sharing following 1 elements
       java.base@11.0.25/java.lang.Thread.run(Thread.java:829)
"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 2)

    def test_empty_data(self):
        """Test handling of empty data"""
        text = """
::: {abc123}{node_name}{hash123}{10.0.0.1}{10.0.0.1:9300}{dir}{attr=value}
   Hot threads at 2026-01-18T08:42:32.186Z, interval=500ms, busiestThreads=3, ignoreIdleThreads=true:

"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 0)
        self.assertEqual(data.total_cpu_time, 0.0)


if __name__ == "__main__":
    unittest.main()
