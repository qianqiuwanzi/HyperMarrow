"""
openclaw-learning-system
Independent learning system for OpenClaw.

This package provides meta-learning capabilities WITHOUT depending on memory_core.
It maintains its own Q-table and experience buffer.
"""

from .independent_q_agent import IndependentQLearningAgent, ACTIONS, ACTION_MAP
from .config import get_learning_data_dir, setup_learning_config

__version__ = "2.0.0"
__all__ = [
    "IndependentQLearningAgent",
    "ACTIONS",
    "ACTION_MAP",
    "get_learning_data_dir",
    "setup_learning_config",
]
