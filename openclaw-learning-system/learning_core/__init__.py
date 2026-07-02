"""
OpenClaw Learning System Core

Downstream re-export package.
Canonical RL implementations live in openclaw-memory-system (memory_core/).
"""

# Re-export from memory-system (the canonical location)
from memory_core.q_learning_agent import QLearningAgent, ACTIONS, ACTION_MAP
from memory_core.rl_decision_helper import RLDecisionHelper

# Re-export config from memory-system
from memory_core.config import (
    get_workspace,
    get_memory_dir,
    get_cache_dir,
    get_hf_cache_dir,
    setup_hf_mirror,
)

# Re-export extended cognition modules
from memory_core.knowledge_graph import KnowledgeGraph
from memory_core.transfer_learner import TransferLearner
from memory_core.memory_consolidator import MemoryConsolidator
from memory_core.metacognition_monitor import MetacognitionMonitor

__all__ = [
    "QLearningAgent",
    "RLDecisionHelper",
    "ACTIONS",
    "ACTION_MAP",
    "KnowledgeGraph",
    "TransferLearner",
    "MemoryConsolidator",
    "MetacognitionMonitor",
    "get_workspace",
    "get_memory_dir",
    "get_cache_dir",
    "get_hf_cache_dir",
    "setup_hf_mirror",
]

__version__ = "2.0.0"  # Upverted after refactoring
