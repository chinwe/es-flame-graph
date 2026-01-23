"""
Tasks API parser module

Parses Elasticsearch _tasks API JSON output into structured data.
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class TaskInfo:
    """Represents a single task's information from _tasks API"""

    node_id: str
    node_name: str
    action: str
    description: str
    running_time_nanos: int
    task_id: str


class TasksParser:
    """Parser for Elasticsearch _tasks API JSON output"""

    def parse_file(self, filepath: str):
        """Parse Tasks data from a JSON file"""
        from .parser import ParsedData

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_text(content)

    def parse_text(self, text: str):
        """
        Parse Tasks data from JSON text

        Supports both single JSON object and multiple concatenated JSON objects.

        Returns ParsedData compatible with FlameGraphGenerator:
        - threads: List[ThreadInfo] where thread_name = action
        - total_cpu_time: Sum of running_time_nanos (in milliseconds)
        - node_count: Number of unique nodes
        - interval_ms: 0 (not applicable for tasks)
        """
        from .parser import ThreadInfo, ParsedData

        text = text.strip()

        # Try to parse as single JSON object first
        try:
            data = json.loads(text)
            data_list = [data]
        except json.JSONDecodeError:
            # If single parse fails, try to parse as multiple concatenated JSON objects
            data_list = self._parse_multiple_json(text)

        if not data_list:
            raise ValueError("No valid JSON data found in input")

        # Extract tasks from all data objects
        all_tasks = []
        for data in data_list:
            tasks_data = self._extract_tasks(data)
            for task in tasks_data:
                task_info = self._parse_task(task)
                if task_info:
                    all_tasks.append(task_info)

        # Aggregate by node_id and action
        aggregated = self._aggregate_tasks(all_tasks)

        # Convert to ThreadInfo for FlameGraphGenerator compatibility
        threads = self._to_thread_info_list(aggregated)

        # Calculate total time (convert nanos to millis for compatibility)
        total_time_nanos = sum(t.running_time_nanos for t in all_tasks)
        total_time_ms = total_time_nanos / 1_000_000

        # Get unique node count
        node_ids = set(t.node_id for t in all_tasks)

        return ParsedData(
            threads=threads,
            total_cpu_time=total_time_ms,
            node_count=len(node_ids),
            interval_ms=0.0,
        )

    def _parse_multiple_json(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse multiple concatenated JSON objects.

        Handles format like: {"nodes":{...}}{"nodes":{...}}

        Args:
            text: Input text containing multiple concatenated JSON objects

        Returns:
            List of parsed JSON objects
        """
        result = []
        # Find all JSON objects by matching braces
        # This handles cases like: {...}{...} or {...} {...}
        brace_count = 0
        current = ""
        in_string = False
        escape_next = False

        for char in text:
            if escape_next:
                current += char
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                current += char
                continue

            if char == '"':
                in_string = not in_string
                current += char
                continue

            if not in_string:
                if char == '{':
                    if brace_count == 0 and current.strip():
                        # Skip whitespace between JSON objects
                        current = ""
                    brace_count += 1
                    current += char
                elif char == '}':
                    brace_count -= 1
                    current += char
                    if brace_count == 0:
                        # Complete JSON object
                        try:
                            obj = json.loads(current.strip())
                            result.append(obj)
                            current = ""
                        except json.JSONDecodeError:
                            # Skip invalid JSON and continue
                            current = ""
                else:
                    # Outside string, add all characters (including colons, commas, brackets, etc.)
                    current += char
            else:
                # Inside string, add all characters
                current += char

        return result

    def _extract_tasks(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tasks list from _tasks API response

        Handles both direct tasks list and nested node structure
        """
        tasks = []

        # Handle format: { "nodes": { "node_id": { "tasks": {...} } } }
        if "nodes" in data and isinstance(data["nodes"], dict):
            nodes_data = data["nodes"]
        else:
            # Direct format: { "node_id": { "tasks": {...} } }
            nodes_data = data

        # Extract tasks from each node
        for node_id, node_data in nodes_data.items():
            if isinstance(node_data, dict) and "tasks" in node_data:
                node_tasks = node_data["tasks"]
                for task_id, task in node_tasks.items():
                    task["_node_id"] = node_id
                    task["_node_name"] = node_data.get("name", node_id)
                    task["_task_id"] = task_id
                    tasks.append(task)

        return tasks

    def _parse_task(self, task: Dict[str, Any]) -> TaskInfo:
        """Parse a single task object"""
        node_id = task.get("_node_id", task.get("node_id", "unknown"))
        node_name = task.get("_node_name", node_id)
        task_id = task.get("_task_id", task.get("task_id", "unknown"))

        action = task.get("action", "unknown")
        description = task.get("description", "")
        running_time_nanos_raw = task.get("running_time_in_nanos", 0)
        try:
            running_time_nanos = int(running_time_nanos_raw)
        except (ValueError, TypeError):
            running_time_nanos = 0

        return TaskInfo(
            node_id=node_id,
            node_name=node_name,
            action=action,
            description=description,
            running_time_nanos=running_time_nanos,
            task_id=task_id,
        )

    def _aggregate_tasks(self, tasks: List[TaskInfo]) -> Dict[str, Dict[str, Dict]]:
        """
        Aggregate tasks by node_id and action

        Returns:
            Dict: {
                node_id: {
                    action: {
                        "total_time": float,
                        "task_count": int,
                        "description": str
                    }
                }
            }
        """
        result = {}

        for task in tasks:
            node_id = task.node_id
            action = task.action

            if node_id not in result:
                result[node_id] = {}

            if action not in result[node_id]:
                result[node_id][action] = {
                    "total_time": 0.0,
                    "task_count": 0,
                    "description": "",
                }

            result[node_id][action]["total_time"] += task.running_time_nanos
            result[node_id][action]["task_count"] += 1
            # Keep first description
            if task.description and not result[node_id][action]["description"]:
                result[node_id][action]["description"] = task.description

        return result

    def _to_thread_info_list(self, aggregated: Dict[str, Dict[str, Dict]]) -> List:
        """
        Convert aggregated tasks to ThreadInfo list

        Mapping:
        - action -> thread_name
        - running_time_nanos -> cpu_time_ms (converted)
        - task_count -> samples_count
        - description -> stored in stack_frames for tooltip
        """
        from .parser import ThreadInfo

        threads = []

        for node_id, actions in aggregated.items():
            for action, data in actions.items():
                # Use first task's node_name if available
                node_name = node_id

                thread_info = ThreadInfo(
                    node_id=node_id,
                    node_name=node_name,
                    node_ip="",
                    timestamp="",
                    cpu_percent=0.0,
                    cpu_time_ms=round(data["total_time"] / 1_000_000, 6),  # Convert to ms with precision
                    interval_ms=0.0,
                    thread_name=action,  # Use action as thread_name
                    snapshots="",
                    samples_count=data["task_count"],
                    stack_frames=[data["description"]] if data["description"] else [],
                )
                threads.append(thread_info)

        return threads
