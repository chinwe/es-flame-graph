"""
Test cases for Tasks API parser
"""

import unittest
from es_flame_graph.tasks_parser import TasksParser, TaskInfo


class TestTasksParser(unittest.TestCase):
    """Test Tasks parser functionality"""

    def setUp(self):
        self.parser = TasksParser()

    def test_parse_text_with_valid_tasks(self):
        """Test parsing from JSON text with valid tasks"""
        text = """
{
  "nodes": {
    "abc123": {
      "name": "node1",
      "tasks": {
        "task1": {
          "action": "indices:data/read/search",
          "description": "search[logs-2026]",
          "running_time_in_nanos": 1500000000
        },
        "task2": {
          "action": "indices:data/write/bulk",
          "description": "bulk[logs-2026]",
          "running_time_in_nanos": 2500000000
        }
      }
    }
  }
}
"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 2)
        # Find each thread by action name (order may vary)
        search_thread = next(t for t in data.threads if "search" in t.thread_name)
        bulk_thread = next(t for t in data.threads if "bulk" in t.thread_name)
        self.assertAlmostEqual(search_thread.cpu_time_ms, 1500.0, places=1)
        self.assertAlmostEqual(bulk_thread.cpu_time_ms, 2500.0, places=1)

    def test_parse_text_with_same_action_aggregation(self):
        """Test that same actions are aggregated"""
        text = """
{
  "nodes": {
    "abc123": {
      "name": "node1",
      "tasks": {
        "task1": {
          "action": "search",
          "description": "test1",
          "running_time_in_nanos": 1000
        },
        "task2": {
          "action": "search",
          "description": "test2",
          "running_time_in_nanos": 2000
        }
      }
    }
  }
}
"""
        data = self.parser.parse_text(text)
        # Should be aggregated to one thread (both are root tasks with same action)
        self.assertEqual(len(data.threads), 1)
        self.assertEqual(data.threads[0].thread_name, "search")
        # 1000 + 2000 = 3000 nanos = 0.003 ms
        self.assertAlmostEqual(data.threads[0].cpu_time_ms, 0.003, places=3)
        # Task count should be 2
        self.assertEqual(data.threads[0].samples_count, 2)

    def test_parse_text_with_parent_child_hierarchy(self):
        """Test that child tasks are accumulated into parent"""
        text = """
{
  "nodes": {
    "node1": {
      "name": "test-node",
      "tasks": {
        "task1": {
          "action": "reindex",
          "description": "main reindex",
          "running_time_in_nanos": 10000000,
          "parent_task_id": "task2"
        },
        "task2": {
          "action": "reindex",
          "description": "",
          "running_time_in_nanos": 5000000
        },
        "task3": {
          "action": "bulk",
          "description": "bulk operation",
          "running_time_in_nanos": 2000,
          "parent_task_id": "task2"
        }
      }
    }
  }
}
"""
        data = self.parser.parse_text(text)
        # task1 and task3 are children of task2 (reindex)
        # Only reindex should be shown, with accumulated time
        # bulk is a child task, so it won't be shown separately
        self.assertEqual(len(data.threads), 1)
        reindex_thread = data.threads[0]
        self.assertEqual(reindex_thread.thread_name, "reindex")
        # reindex: 5000000 (task2) + 10000000 (task1) + 2000 (task3) = 15002000 ns = 15.002 ms
        self.assertAlmostEqual(reindex_thread.cpu_time_ms, 15.002, places=3)
        self.assertEqual(reindex_thread.samples_count, 3)  # 3 tasks total
        # Description should include all descriptions
        self.assertIn("main reindex", reindex_thread.stack_frames[0])
        self.assertIn("bulk operation", reindex_thread.stack_frames[0])

    def test_parse_text_with_multiple_nodes(self):
        """Test parsing with multiple nodes"""
        text = """
{
  "nodes": {
    "abc123": {
      "name": "node1",
      "tasks": {
        "task1": {
          "action": "search",
          "description": "test",
          "running_time_in_nanos": 1000
        }
      }
    },
    "def456": {
      "name": "node2",
      "tasks": {
        "task2": {
          "action": "index",
          "description": "test",
          "running_time_in_nanos": 2000
        }
      }
    }
  }
}
"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 2)
        self.assertEqual(data.node_count, 2)

    def test_parse_text_with_empty_tasks(self):
        """Test parsing with empty tasks"""
        text = """
{
  "nodes": {
    "abc123": {
      "name": "node1",
      "tasks": {}
    }
  }
}
"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 0)

    def test_parse_text_with_invalid_json(self):
        """Test handling of invalid JSON"""
        text = "not json"
        with self.assertRaises(ValueError):
            self.parser.parse_text(text)

    def test_extract_tasks(self):
        """Test _extract_tasks method"""
        text = """
{
  "nodes": {
    "abc123": {
      "name": "node1",
      "tasks": {
        "task1": {
          "action": "search",
          "description": "test",
          "running_time_in_nanos": 1000
        }
      }
    }
  }
}
"""
        import json
        data = json.loads(text)
        tasks = self.parser._extract_tasks(data)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["_node_id"], "abc123")
        self.assertEqual(tasks[0]["_node_name"], "node1")
        self.assertEqual(tasks[0]["_task_id"], "task1")

    def test_parse_task(self):
        """Test _parse_task method"""
        task_dict = {
            "_node_id": "abc123",
            "_node_name": "node1",
            "_task_id": "task1",
            "action": "search",
            "description": "test search",
            "running_time_in_nanos": 1500000000
        }
        task = self.parser._parse_task(task_dict)
        self.assertIsInstance(task, TaskInfo)
        self.assertEqual(task.node_id, "abc123")
        self.assertEqual(task.node_name, "node1")
        self.assertEqual(task.action, "search")
        self.assertEqual(task.description, "test search")
        self.assertEqual(task.running_time_nanos, 1500000000)

    def test_aggregate_tasks(self):
        """Test _aggregate_tasks method"""
        tasks = [
            TaskInfo(node_id="node1", node_name="Node 1", action="search", description="test1",
                     running_time_nanos=1000, task_id="task1"),
            TaskInfo(node_id="node1", node_name="Node 1", action="search", description="test2",
                     running_time_nanos=2000, task_id="task2"),
            TaskInfo(node_id="node1", node_name="Node 1", action="index", description="test3",
                     running_time_nanos=3000, task_id="task3"),
        ]
        aggregated = self.parser._aggregate_tasks(tasks)

        self.assertIn("node1", aggregated)
        self.assertIn("search", aggregated["node1"])
        self.assertIn("index", aggregated["node1"])

        # Check aggregation
        self.assertEqual(aggregated["node1"]["search"]["total_time"], 3000)  # 1000 + 2000
        self.assertEqual(aggregated["node1"]["search"]["task_count"], 2)
        self.assertEqual(aggregated["node1"]["index"]["total_time"], 3000)
        self.assertEqual(aggregated["node1"]["index"]["task_count"], 1)

    def test_to_thread_info_list(self):
        """Test _to_thread_info_list method"""
        aggregated = {
            "node1": {
                "search": {
                    "total_time": 3000000,
                    "task_count": 2,
                    "description": "test search"
                }
            }
        }
        threads = self.parser._to_thread_info_list(aggregated)

        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0].thread_name, "search")
        self.assertAlmostEqual(threads[0].cpu_time_ms, 3.0, places=1)
        self.assertEqual(threads[0].samples_count, 2)

    def test_parse_multiple_json_objects(self):
        """Test parsing multiple concatenated JSON objects"""
        text = """{"nodes":{"abc123":{"name":"node1","tasks":{"task1":{"action":"search","description":"test1","running_time_in_nanos":1000}}}}}
        {"nodes":{"def456":{"name":"node2","tasks":{"task2":{"action":"index","description":"test2","running_time_in_nanos":2000}}}}}"""
        data = self.parser.parse_text(text)
        # Should have 2 threads from 2 different JSON objects
        self.assertEqual(len(data.threads), 2)

    def test_parse_single_json_object_still_works(self):
        """Test that single JSON object still parses correctly"""
        text = """{"nodes":{"abc123":{"name":"node1","tasks":{"task1":{"action":"search","description":"test","running_time_in_nanos":1000}}}}}"""
        data = self.parser.parse_text(text)
        self.assertEqual(len(data.threads), 1)


if __name__ == "__main__":
    unittest.main()
