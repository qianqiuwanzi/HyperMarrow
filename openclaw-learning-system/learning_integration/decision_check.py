"""
Decision Check Point — Learning System Integration

This module provides RL-enhanced decision support.
Inherits from memory_integration.decision_check and adds RL on top.
"""

import os
from pathlib import Path

# Set HF environment BEFORE any import
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'

# Import memory_core config
from memory_core.config import get_hf_cache_dir, get_workspace, setup_hf_mirror

# Set HF cache paths dynamically
_hf_cache = get_hf_cache_dir()
os.environ['HUGGINGFACE_HUB_CACHE'] = str(_hf_cache / 'hub')
os.environ['HF_HOME'] = str(_hf_cache)

# Import base class from memory system
from memory_integration.decision_check import DecisionCheckPoint as MemoryDecisionCheckPoint

# Import RL modules from learning system
from memory_core.q_learning_agent import QLearningAgent
from memory_core.rl_decision_helper import RLDecisionHelper


class LearningDecisionCheckPoint(MemoryDecisionCheckPoint):
    """
    Enhanced Decision Check Point with full RL integration.
    
    Extends MemoryDecisionCheckPoint by:
    - Loading trained Q-table from shared data directory
    - Providing RL-decision recommendations via RLDecisionHelper
    """

    # Action space (must match training data)
    ACTIONS = [
        "follow_rule_strictly",   # 0
        "use_existing_tool",       # 1
        "try_fix_three_times",    # 2
        "report_user",            # 3
        "switch_skill",           # 4
        "write_script",           # 5
        "skip_phase",             # 6
    ]

    def __init__(self, enable_vector_db=True, enable_rl=True):
        """
        Initialize Learning Decision Check Point.
        
        Args:
            enable_vector_db: Whether to enable vector memory database
            enable_rl: Whether to enable reinforcement learning
        """
        # Init base class WITHOUT RL (we handle RL ourselves)
        super().__init__(enable_vector_db=enable_vector_db, enable_rl=False)

        # Init RL helper with trained Q-table
        self.enable_rl = enable_rl
        self.rl_helper = None

        if enable_rl:
            self._init_rl_helper()

        print(f"[LearningDecisionCheckPoint] Initialized "
              f"(vector_db={self.vector_db is not None}, "
              f"rl_helper={self.rl_helper is not None})")

    def _init_rl_helper(self):
        """Initialize RLDecisionHelper with trained Q-table."""
        try:
            ws = get_workspace()
            data_dir = ws / "HyperMarrow" / "openclaw-memory-system" / "data"
            qtable_path = str(data_dir / "q_table.json")
            self.rl_helper = RLDecisionHelper(q_table_path=qtable_path)
            print(f"[LearningDecisionCheckPoint] RLDecisionHelper ready")
        except Exception as e:
            print(f"[LearningDecisionCheckPoint] RLDecisionHelper init failed: {e}")
            self.rl_helper = None

    def check(self, action, context=None):
        """
        Check action with procedural memory + vector DB + RL recommendation.
        
        Returns dict includes 'rl_recommendation' with RL-suggested action.
        """
        # Get base result (procedural memory + vector DB)
        result = super().check(action, context)

        # Override RL recommendation with full RLDecisionHelper
        if self.rl_helper:
            context_str = f"{action} {context or ''}"
            try:
                rec_action, confidence = self.rl_helper.get_recommendation(
                    state=context_str,
                    available_actions=self.ACTIONS
                )
                result['rl_recommendation'] = {
                    "recommended_action": rec_action,
                    "confidence": round(confidence, 3),
                    "source": "RLDecisionHelper"
                }
                if rec_action != action and confidence > 0.5:
                    result['warnings'].append(
                        f"RL suggests '{rec_action}' instead of '{action}'"
                    )
            except Exception as e:
                print(f"[LearningDecisionCheckPoint] RL recommendation failed: {e}")

        return result


# Default export
DecisionCheckPoint = LearningDecisionCheckPoint

__all__ = ["DecisionCheckPoint", "LearningDecisionCheckPoint"]
