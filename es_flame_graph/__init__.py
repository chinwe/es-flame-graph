"""
Elasticsearch Hot Threads Flame Graph Generator

A tool to visualize Elasticsearch Hot Threads data as interactive flame graphs.
Now supports both Hot Threads and Tasks API formats.
"""

__version__ = "0.2.0"
__author__ = "Sisyphus"

from .parser import HotThreadsParser, ThreadInfo, ParsedData
from .flamegraph import FlameGraphGenerator
from .color import get_color
from .tasks_parser import TasksParser

__all__ = [
    "HotThreadsParser",
    "ThreadInfo",
    "ParsedData",
    "FlameGraphGenerator",
    "get_color",
    "TasksParser",
]
