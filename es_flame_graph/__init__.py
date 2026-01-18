"""
Elasticsearch Hot Threads Flame Graph Generator

A tool to visualize Elasticsearch Hot Threads data as interactive flame graphs.
"""

__version__ = "0.1.0"
__author__ = "Sisyphus"

from .parser import HotThreadsParser, ThreadInfo, ParsedData
from .flamegraph import FlameGraphGenerator
from .color import get_color

__all__ = [
    "HotThreadsParser",
    "ThreadInfo",
    "ParsedData",
    "FlameGraphGenerator",
    "get_color",
]
