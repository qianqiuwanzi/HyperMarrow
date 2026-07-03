"""
Learning System - Independent Q-Learning Agent
This is a standalone implementation that does NOT depend on memory_core.
It maintains its own Q-table and experience buffer.
"""

import json
import random
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# Default Q-table parameters
DEFAULT_STATE_SIZE = 50
DEFAULT_ACTION_SIZE = 5
DEFAULT_ALPHA = 0.1
DEFAULT_GAMMA = 0.9
DEFAULT_EPSILON = 0.1

# Action space for learning system
ACTIONS = ["explore", "exploit", "consolidate", "transfer", "meta_learn"]
ACTION_MAP = {i: a for i, a in enumerate(ACTIONS)}


class IndependentQLearningAgent:
    """
    Independent Q-Learning agent for the learning system.
    
    This agent is specialized for meta-learning decisions:
    - explore: try new strategies
    - exploit: use known good strategies
    - consolidate: trigger memory consolidation
    - transfer: apply transfer learning
    - meta_learn: update meta-parameters
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            # Default: openclaw-learning-system/data/
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_size = DEFAULT_STATE_SIZE
        self.action_size = DEFAULT_ACTION_SIZE
        self.alpha = DEFAULT_ALPHA
        self.gamma = DEFAULT_GAMMA
        self.epsilon = DEFAULT_EPSILON
        
        self.q_table = self._load_or_init_q_table()
        self.experience_buffer = []
        self.meta = self._load_meta()
    
    def _load_or_init_q_table(self) -> np.ndarray:
        q_path = self.data_dir / "learning_q_table.json"
        if q_path.exists():
            with open(q_path, encoding="utf-8") as f:
                data = json.load(f)
            table = np.array(data["q_table"])
            self.state_size = data.get("state_size", DEFAULT_STATE_SIZE)
            self.action_size = data.get("action_size", DEFAULT_ACTION_SIZE)
            self.alpha = data.get("alpha", DEFAULT_ALPHA)
            self.gamma = data.get("gamma", DEFAULT_GAMMA)
            self.epsilon = data.get("epsilon", DEFAULT_EPSILON)
            return table
        
        return np.zeros((self.state_size, self.action_size), dtype=np.float32)
    
    def _load_meta(self) -> Dict:
        meta_path = self.data_dir / "learning_meta.json"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_decisions": 0,
            "total_experiences": 0,
            "last_consolidation": None,
        }
    
    def save(self):
        """Save Q-table and meta to disk"""
        q_path = self.data_dir / "learning_q_table.json"
        data = {
            "state_size": self.state_size,
            "action_size": self.action_size,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "q_table": self.q_table.tolist(),
            "metadata": {
                "last_saved": datetime.now().isoformat(),
                "total_decisions": self.meta["total_decisions"],
            }
        }
        with open(q_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        meta_path = self.data_dir / "learning_meta.json"
        self.meta["updated_at"] = datetime.now().isoformat()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def _encode_state(self, context: Dict) -> int:
        """Encode context dict into a state index"""
        # Simple hash-based encoding
        ctx_str = json.dumps(context, sort_keys=True)
        return hash(ctx_str) % self.state_size
    
    def decide(self, context: Dict) -> Tuple[int, str]:
        """
        Decide an action based on current context.
        
        Returns:
            (action_index, action_name)
        """
        state = self._encode_state(context)
        
        if random.random() < self.epsilon:
            action_idx = random.randint(0, self.action_size - 1)
        else:
            action_idx = np.argmax(self.q_table[state])
        
        self.meta["total_decisions"] += 1
        return action_idx, ACTION_MAP[action_idx]
    
    def add_experience(self, state: int, action: int, reward: float,
                       next_state: int, done: bool = False):
        """Add a new experience to the buffer"""
        self.experience_buffer.append({
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state,
            "done": done,
            "timestamp": datetime.now().isoformat(),
        })
        self.meta["total_experiences"] += 1
        
        # Periodic save
        if self.meta["total_experiences"] % 10 == 0:
            self.save()
    
    def batch_learn(self, batch_size: int = 32):
        """Learn from a batch of experiences"""
        if len(self.experience_buffer) < batch_size:
            return
        
        batch = random.sample(self.experience_buffer[-100:], batch_size)
        for exp in batch:
            s, a = exp["state"], exp["action"]
            r, ns = exp["reward"], exp["next_state"]
            done = exp["done"]
            
            max_next_q = 0 if done else np.max(self.q_table[ns])
            target = r + self.gamma * max_next_q
            self.q_table[s][a] += self.alpha * (target - self.q_table[s][a])
        
        self.save()
    
    def get_stats(self) -> Dict:
        """Get statistics about the Q-table"""
        nonzero = np.count_nonzero(self.q_table)
        total = self.state_size * self.action_size
        return {
            "state_size": self.state_size,
            "action_size": self.action_size,
            "non_zero": int(nonzero),
            "total": int(total),
            "coverage": float(nonzero / total),
            "total_decisions": self.meta["total_decisions"],
            "total_experiences": self.meta["total_experiences"],
            "epsilon": self.epsilon,
        }
