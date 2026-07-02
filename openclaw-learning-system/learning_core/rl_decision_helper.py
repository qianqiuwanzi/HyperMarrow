#!/usr/bin/env python3
"""
Reinforcement Learning Decision Helper

Uses Q-Learning agent to provide decision recommendations.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from .q_learning_agent import QLearningAgent


class RLDecisionHelper:
    """
    Decision helper using RL agent.
    
    Provides decision recommendations based on:
    1. Q-table (learned experiences)
    2. Rules (if any)
    """
    
    def __init__(
        self,
        q_table_path: Optional[str] = None,
        rules_path: Optional[str] = None
    ):
        """
        Initialize RL Decision Helper.
        
        Args:
            q_table_path: Path to Q-table file
            rules_path: Path to rules file (for hybrid decisions)
        """
        self.q_agent = QLearningAgent(
            state_space_size=100,
            action_space_size=7,
            q_table_path=q_table_path
        )
        
        self.rules = []
        if rules_path and Path(rules_path).exists():
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
        
        print(f"[RL-Helper] Initialized with {len(self.rules)} rules")
    
    def get_recommendation(
        self,
        state: str,
        available_actions: List[str]
    ) -> Tuple[str, float]:
        """
        Get decision recommendation.
        
        Args:
            state: Current state description
            available_actions: List of available action names
            
        Returns:
            Tuple of (recommended_action, confidence)
        """
        # Convert state to index
        state_idx = self.q_agent.state_to_index(state)
        
        # Get action index from Q-agent
        action_idx = self.q_agent.get_action(state_idx, training=False)
        
        # Bound check
        if action_idx >= len(available_actions):
            action_idx = 0
        
        recommended_action = available_actions[action_idx]
        
        # Calculate confidence (normalized Q-value)
        q_values = self.q_agent.q_table[state_idx, :]
        confidence = float(q_values[action_idx]) / (np.max(q_values) + 1e-6)
        
        return recommended_action, confidence
    
    def update_from_feedback(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        available_actions: List[str]
    ):
        """
        Update Q-table from user feedback.
        
        Args:
            state: Previous state
            action: Action taken
            reward: Reward received (-1 to 1)
            next_state: New state
            available_actions: Available actions (for mapping)
        """
        state_idx = self.q_agent.state_to_index(state)
        action_idx = available_actions.index(action)
        next_state_idx = self.q_agent.state_to_index(next_state)
        
        self.q_agent.update(state_idx, action_idx, reward, next_state_idx)
        
        print(f"[RL-Helper] Updated Q-table: {state} -> {action} (reward={reward})")
    
    def add_rule(self, rule: Dict[str, Any]):
        """
        Add a rule to hybrid decision making.
        
        Args:
            rule: Rule dict with keys: condition, action, priority
        """
        self.rules.append(rule)
        print(f"[RL-Helper] Added rule: {rule['condition']}")
    
    def save_rules(self, path: str):
        """Save rules to file"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=2)
        print(f"[RL-Helper] Rules saved to {path}")


def main():
    """Test RL Decision Helper"""
    helper = RLDecisionHelper()
    
    # Test recommendation
    state = "import_error"
    available_actions = ["try_fix", "report_user", "switch_skill"]
    
    recommended_action, confidence = helper.get_recommendation(state, available_actions)
    print(f"\nTest state: {state}")
    print(f"Recommended: {recommended_action} (confidence={confidence:.2f})")
    
    # Test update
    helper.update_from_feedback(
        state="import_error",
        action="try_fix",
        reward=1.0,
        next_state="fixed",
        available_actions=available_actions
    )
    
    print("\n[RL-Helper] Test passed!")


if __name__ == "__main__":
    main()
