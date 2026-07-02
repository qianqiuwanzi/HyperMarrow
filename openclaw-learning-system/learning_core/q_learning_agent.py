#!/usr/bin/env python3
"""
Q-Learning Agent for OpenClaw Learning System

Implements Q-Learning algorithm for decision making.
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional


class QLearningAgent:
    """
    Q-Learning Agent for reinforcement learning.
    
    State space: decision contexts (e.g., "import_error", "script_not_found")
    Action space: possible actions (e.g., "try_fix", "report_user")
    """
    
    def __init__(
        self,
        state_space_size: int = 100,
        action_space_size: int = 7,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon: float = 0.1,
        q_table_path: Optional[str] = None
    ):
        """
        Initialize Q-Learning Agent.
        
        Args:
            state_space_size: Number of possible states
            action_space_size: Number of possible actions
            learning_rate: Learning rate (alpha)
            discount_factor: Discount factor (gamma)
            epsilon: Exploration rate (epsilon-greedy)
            q_table_path: Path to load/save Q-table
        """
        self.state_space_size = state_space_size
        self.action_space_size = action_space_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table_path = q_table_path
        
        # Initialize Q-table with zeros
        self.q_table = np.zeros((state_space_size, action_space_size))
        
        # Load Q-table if path provided
        if q_table_path and Path(q_table_path).exists():
            self.load_q_table(q_table_path)
        
        # Experience replay buffer
        self.experience_buffer = []
        self.max_buffer_size = 1000
        
        print(f"[Q-Learning] Initialized with state_space={state_space_size}, "
              f"action_space={action_space_size}")
    
    def get_action(self, state: int, training: bool = True) -> int:
        """
        Get action using epsilon-greedy policy.
        
        Args:
            state: Current state index
            training: If True, use epsilon-greedy; else greedy
            
        Returns:
            Action index
        """
        if training and np.random.random() < self.epsilon:
            # Explore: random action
            return np.random.randint(self.action_space_size)
        else:
            # Exploit: best action
            return np.argmax(self.q_table[state, :])
    
    def update(
        self,
        state: int,
        action: int,
        reward: float,
        next_state: int,
        done: bool = False
    ):
        """
        Update Q-table using Q-Learning algorithm.
        
        Q(s,a) = Q(s,a) + alpha * [R(s,a) + gamma * max_a' Q(s',a') - Q(s,a)]
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        # Current Q-value
        current_q = self.q_table[state, action]
        
        # Next max Q-value
        if done:
            next_max_q = 0
        else:
            next_max_q = np.max(self.q_table[next_state, :])
        
        # Q-Learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * next_max_q - current_q
        )
        
        self.q_table[state, action] = new_q
        
        # Add to experience buffer
        self.experience_buffer.append({
            'state': state,
            'action': action,
            'reward': reward,
            'next_state': next_state,
            'done': done
        })
        
        # Limit buffer size
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer.pop(0)
    
    def save_q_table(self, path: Optional[str] = None):
        """Save Q-table to file"""
        save_path = path or self.q_table_path
        if save_path:
            np.save(save_path, self.q_table)
            print(f"[Q-Learning] Q-table saved to {save_path}")
    
    def load_q_table(self, path: str):
        """Load Q-table from file"""
        self.q_table = np.load(path)
        print(f"[Q-Learning] Q-table loaded from {path}")
    
    def get_q_table(self) -> np.ndarray:
        """Get current Q-table"""
        return self.q_table

    def get_stats(self) -> dict:
        """
        Get Q-Learning agent statistics.

        Returns:
            dict with keys: n_states, n_actions, total_experiences,
                            nonzero_entries, total_entries, nonzero_pct, q_sum,
                            alpha, gamma, epsilon
        """
        nonzero = int(np.count_nonzero(self.q_table))
        total = float(np.sum(self.q_table))
        return {
            "n_states": self.state_space_size,
            "n_actions": self.action_space_size,
            "total_experiences": len(self.experience_buffer),
            "nonzero_entries": nonzero,
            "total_entries": self.q_table.size,
            "nonzero_pct": round(nonzero / self.q_table.size * 100, 2) if self.q_table.size > 0 else 0,
            "q_sum": round(total, 4),
            "alpha": self.learning_rate,
            "gamma": self.discount_factor,
            "epsilon": self.epsilon,
        }
    
    def state_to_index(self, state_str: str) -> int:
        """
        Convert state string to index.
        
        Args:
            state_str: State description string
            
        Returns:
            State index (hashed)
        """
        # Simple hash to index
        return hash(state_str) % self.state_space_size
    
    def add_experience(self, experience: Dict[str, Any]):
        """
        Add experience to buffer for experience replay.
        
        Args:
            experience: Experience dict with keys:
                - state, action, reward, next_state, done
        """
        self.experience_buffer.append(experience)
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer.pop(0)
    
    def experience_replay(self, batch_size: int = 32):
        """
        Perform experience replay to update Q-table.
        
        Args:
            batch_size: Number of experiences to sample
        """
        if len(self.experience_buffer) < batch_size:
            return
        
        # Sample batch
        indices = np.random.choice(
            len(self.experience_buffer),
            batch_size,
            replace=False
        )
        
        for idx in indices:
            exp = self.experience_buffer[idx]
            self.update(
                exp['state'],
                exp['action'],
                exp['reward'],
                exp['next_state'],
                exp['done']
            )
        
        print(f"[Q-Learning] Experience replay: {batch_size} samples")


if __name__ == "__main__":
    # Test Q-Learning agent
    agent = QLearningAgent(
        state_space_size=10,
        action_space_size=3,
        learning_rate=0.1,
        discount_factor=0.9,
        epsilon=0.1
    )
    
    # Test update
    agent.update(state=0, action=1, reward=1.0, next_state=1, done=False)
    
    # Test get action
    action = agent.get_action(state=0, training=True)
    print(f"Selected action: {action}")
    
    print("\n[Q-Learning] Test passed!")
