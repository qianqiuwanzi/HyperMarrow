"""
openclaw-learning-system — Canonical Learning System

This package contains ALL learning-related implementations:
  QLearningAgent, RLDecisionHelper, MetaLearner, TransferLearner, SkillExtractor

memory_core/ contains re-export shims for backward compatibility.
"""
from .q_learning_agent import QLearningAgent, ACTIONS, ACTION_MAP, _stable_hash
from .rl_decision_helper import RLDecisionHelper
from .meta_learner import MetaLearner, SkillExtractor
from .transfer_learner import TransferLearner
from .config import get_data_dir, get_learning_data_dir, setup_learning_config

__version__ = "2.0.0"
__all__ = [
    # Core RL
    "QLearningAgent",
    "ACTIONS",
    "ACTION_MAP",
    "_stable_hash",
    "RLDecisionHelper",
    # Meta-Learning
    "MetaLearner",
    "SkillExtractor",
    # Transfer
    "TransferLearner",
    # Config
    "get_data_dir",
    "get_learning_data_dir",
    "setup_learning_config",
]
