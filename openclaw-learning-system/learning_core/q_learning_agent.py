#!/usr/bin/env python3
"""
Q-Learning Agent for OpenClaw Learning System

Implements Q-Learning algorithm for decision making.
"""

import hashlib
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import sys as _sys


def _stable_hash(s: str, modulus: int) -> int:
    """
    Deterministic hash from string to [0, modulus).
    Uses MD5 to avoid Python's per-process hash randomization (PYTHONHASHSEED).
    """
    h = hashlib.md5(s.encode('utf-8')).hexdigest()
    return int(h, 16) % modulus


# Module-level ACTIONS constant (must be defined before QLearningAgent.__init__ uses it)
ACTIONS = [
    "follow_rule_strictly",   # 0
    "use_existing_tool",       # 1
    "try_fix_three_times",     # 2
    "report_user",            # 3
    "write_script",           # 4
    "switch_skill",           # 5
    "skip_phase",              # 6
]
ACTION_MAP = {a: i for i, a in enumerate(ACTIONS)}


def _load_q_table_json(agent, path: str):
    """
    Load a trained Q-table from a JSON file into agent.q_table.

    Handles both old "metadata" format and bare list-of-lists format.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'q_table' in data:
            qtable_list = data['q_table']
        elif isinstance(data, list):
            qtable_list = data
        else:
            print(f"[Q-Learning] Unknown Q-table JSON format in {path}")
            return

        qtable_arr = np.array(qtable_list)
        if qtable_arr.shape == (agent.state_space_size, agent.action_space_size):
            agent.q_table = qtable_arr
            # Restore state map if saved
            if isinstance(data, dict) and "metadata" in data:
                saved_map = data["metadata"].get("state_map", {})
                if saved_map:
                    agent._state_map = {k: int(v) for k, v in saved_map.items()}
                    agent._state_counter = data["metadata"].get("state_counter",
                        max(agent._state_map.values()) + 1 if agent._state_map else 0)
                    print(f"[Q-Learning] State map restored: {len(agent._state_map)} entries")
            nonzero = int(np.count_nonzero(agent.q_table))
            total = float(np.sum(agent.q_table))
            print(f"[Q-Learning] Q-table loaded from JSON: shape={qtable_arr.shape}, "
                  f"nonzero={nonzero}/{qtable_arr.size}, q_sum={total:.4f}")
        else:
            print(f"[Q-Learning] Q-table JSON shape mismatch: {qtable_arr.shape} "
                  f"!= ({agent.state_space_size}, {agent.action_space_size})")
    except Exception as e:
        print(f"[Q-Learning] Failed to load Q-table JSON from {path}: {e}")


class QLearningAgent:
    """
    Q-Learning Agent for reinforcement learning.

    State space: decision contexts (e.g., "import_error", "script_not_found")
    Action space: possible actions (e.g., "try_fix", "report_user")

    Supports three modes:
      - 'tabular' (default): pure Q-table, backward compatible
      - 'neural': learned embeddings + neural Q-function (requires PyTorch)
      - 'hybrid': neural encoding with tabular Q-table (best of both)
    """

    def __init__(
        self,
        state_space_size: int = 100,
        action_space_size: int = 7,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon: float = 0.1,
        q_table_path: Optional[str] = None,
        neural_mode: str = "tabular",
    ):
        """
        Initialize Q-Learning Agent.

        Args:
            state_space_size: Number of tabular states
            action_space_size: Number of possible actions
            learning_rate: Learning rate (alpha)
            discount_factor: Discount factor (gamma)
            epsilon: Exploration rate (epsilon-greedy)
            q_table_path: Path to load/save Q-table
            neural_mode: 'tabular' | 'neural' | 'hybrid'
        """
        self.state_space_size = state_space_size
        self.action_space_size = action_space_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.q_table_path = q_table_path

        # ── State mapping: string → index with collision detection ─────
        # Must be initialized BEFORE loading Q-table so _load_q_table_json can restore it
        self._state_map: dict = {}       # state_key → index
        self._state_counter = 0          # next available index for new states
        self._auto_expand = True         # allow dynamic state space expansion
        self._max_states = max(state_space_size * 2, 1000)  # hard cap

        # Initialize Q-table with zeros
        self.q_table = np.zeros((state_space_size, action_space_size))

        # Load trained Q-table from JSON if available (avoid np.load which needs .npy)
        if q_table_path and Path(q_table_path).exists():
            _load_q_table_json(self, q_table_path)

        # Experience replay buffer
        self.experience_buffer = []
        self.max_buffer_size = 1000

        # ── Adaptive hyperparameters ────────────────────────────────────
        self._state_visits: dict = {}     # state_idx → visit_count (for dynamic epsilon)
        self._td_errors: list = []        # recent TD errors (for adaptive LR, max 100)
        self._base_learning_rate = learning_rate
        self._base_epsilon = epsilon
        self._min_epsilon = 0.02          # never go below 2% exploration
        self._max_epsilon = 0.5           # cap exploration at 50%
        self._adaptive_lr = True
        self._adaptive_epsilon = True

        # ── Neural backend (Wave 1) + World Model (Wave 2) ───────────────
        self.neural_mode = neural_mode
        self._neural_agent = None
        self._world_model = None
        self._active_inference = False
        if neural_mode in ("neural", "hybrid"):
            from .neural_state import NeuralAgent
            self._neural_agent = NeuralAgent()
            print(f"[Q-Learning] Neural mode: {neural_mode} "
                  f"(PyTorch={self._neural_agent.torch_available})", file=_sys.stderr)

        # ── Load historical experiences into buffer ──────────────────────
        self._load_experience_buffer()

        print(f"[Q-Learning] Initialized with state_space={self.state_space_size}, "
              f"action_space={self.action_space_size}, auto_expand={self._auto_expand}",
              file=_sys.stderr)

    def enable_world_model(self):
        """启用基于模型的主动推理（Wave 2）。"""
        from memory_core.world_model import ModelBasedAgent
        self._world_model = ModelBasedAgent()
        self._active_inference = True
        print(f"[Q-Learning] World model enabled (active inference)", file=_sys.stderr)


    def _load_experience_buffer(self):
        """
        Load historical experiences from rl_decision_history.json into buffer.
        Called at init time. Safe to call multiple times (idempotent).
        """
        if not self.q_table_path:
            return
        hist_path = Path(self.q_table_path).parent / "rl_decision_history.json"
        if not hist_path.exists():
            return

        # Skip if already loaded (by checking buffer size)
        if len(self.experience_buffer) > 0:
            print(f"[Q-Learning] Buffer already has {len(self.experience_buffer)} experiences, skipping load",
                  file=_sys.stderr)
            return

        try:
            with open(hist_path, 'r', encoding='utf-8') as f:
                history = json.load(f)

            loaded = 0
            for exp in history:
                action_name = exp.get("action", "")
                if action_name not in ACTION_MAP:
                    continue
                state = int(exp.get("state", 0)) % self.state_space_size
                next_state = int(exp.get("next_state", 0)) % self.state_space_size
                reward = float(exp.get("reward", 0))
                done = exp.get("outcome") == "failure"

                self.experience_buffer.append({
                    "state": state,
                    "action": ACTION_MAP[action_name],
                    "reward": reward,
                    "next_state": next_state,
                    "done": done,
                    "source": exp.get("source", "historical"),
                })
                loaded += 1

            print(f"[Q-Learning] Loaded {loaded}/{len(history)} historical experiences into buffer "
                  f"(buffer_size={len(self.experience_buffer)})", file=_sys.stderr)
        except Exception as e:
            print(f"[Q-Learning] Failed to load experience buffer: {e}", file=_sys.stderr)

    def add_experience(self, state, action, reward, next_state, done=False):
        """
        Add a single experience to the replay buffer and update Q-table.

        This is the primary interface DecisionCheckPoint should call.

        Args:
            state: State index or hashable state identifier
            action: Action name (str) or index (int)
            reward: float
            next_state: Next state index
            done: bool
        """
        # Normalize action
        if isinstance(action, str):
            if action not in ACTION_MAP:
                print(f"[Q-Learning] WARNING: unknown action '{action}', defaulting to index 0")
            action_idx = ACTION_MAP.get(action, 0)
        else:
            action_idx = int(action)

        # Normalize state (use collision-aware state_to_index for str/dict)
        if isinstance(state, (str, dict)):
            state_idx = self.state_to_index(state)
        else:
            state_idx = int(state) % self.state_space_size

        if isinstance(next_state, (str, dict)):
            next_state_idx = self.state_to_index(next_state)
        else:
            next_state_idx = int(next_state) % self.state_space_size

        # Add to buffer
        self.experience_buffer.append({
            "state": state_idx,
            "action": action_idx,
            "reward": reward,
            "next_state": next_state_idx,
            "done": done,
        })

        # Trim buffer
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer.pop(0)

        # Online Q-update
        self.update(state_idx, action_idx, reward, next_state_idx, done)

        # Neural training step (Wave 1)
        if self._neural_agent is not None:
            # Compute TD target
            if done:
                target_q = reward
            else:
                next_qs = (self._neural_agent.predict_all_q(next_state)
                           if self.neural_mode == "neural"
                           else self.q_table[next_state_idx, :])
                target_q = reward + self.discount_factor * float(np.max(next_qs))
            self._neural_agent.train_step(state, action_idx, target_q,
                                          learning_rate=self.learning_rate * 0.1)

        # World model training (Wave 2)
        if self._world_model is not None and self._neural_agent is not None:
            s_emb = self._neural_agent.encode(state)
            ns_emb = self._neural_agent.encode(next_state)
            self._world_model.wm.train_step(
                s_emb, action_idx, ns_emb, reward,
                learning_rate=0.001,
            )

    def batch_learn(self, batch_size: int = 32):
        """
        Perform experience replay batch update.

        Call this periodically (e.g., every N decisions) rather than after
        every single update, to stabilize learning.

        Args:
            batch_size: Number of experiences to sample from buffer
        """
        if len(self.experience_buffer) < batch_size:
            return 0

        indices = list(range(len(self.experience_buffer)))
        np.random.shuffle(indices)
        batch = indices[:batch_size]

        for idx in batch:
            exp = self.experience_buffer[idx]
            self.update(
                exp["state"], exp["action"], exp["reward"],
                exp["next_state"], exp.get("done", False)
            )

        print(f"[Q-Learning] Batch learn: {batch_size} samples from "
              f"{len(self.experience_buffer)}-size buffer")
        return batch_size

    def get_action(self, state: int, training: bool = True) -> int:
        """
        Get action using epsilon-greedy policy with adaptive epsilon.

        Dynamic epsilon: frequently-visited states get lower exploration
        (well-known → exploit more), rarely-visited states get higher
        exploration (uncertain → explore more).

        Args:
            state: Current state index
            training: If True, use epsilon-greedy; else greedy

        Returns:
            Action index
        """
        # Compute adaptive epsilon based on visit count
        eff_epsilon = self.epsilon
        if self._adaptive_epsilon and training:
            visits = self._state_visits.get(state, 0)
            if visits > 10:
                # Well-known state: reduce exploration
                eff_epsilon = max(self._min_epsilon,
                                  self._base_epsilon * (10.0 / max(visits, 1)))
            elif visits == 0:
                # Never seen: boost exploration
                eff_epsilon = min(self._max_epsilon, self._base_epsilon * 3.0)

        # ── Active Inference planning (Wave 2) ──────────────────────────
        if (self._active_inference and self._world_model is not None
                and self._neural_agent is not None
                and self._world_model.wm._train_steps >= 5):
            s_emb = self._neural_agent.encode(state)
            q_vals = None
            if self.neural_mode != "neural":
                state_idx = (self.state_to_index(state)
                             if isinstance(state, (str, dict))
                             else int(state) % self.state_space_size)
                q_vals = self.q_table[state_idx, :]
            action, _plan = self._world_model.decide(s_emb, q_vals)
            return action

        if training and np.random.random() < eff_epsilon:
            # Explore: random action
            return np.random.randint(self.action_space_size)

        # Neural Q-function path
        if self.neural_mode == "neural" and self._neural_agent is not None:
            qs = self._neural_agent.predict_all_q(state)
            if np.all(qs == 0):
                return np.random.randint(self.action_space_size)
            return int(np.argmax(qs))

        # Tabular / hybrid path
        if isinstance(state, (str, dict)):
            state_idx = self.state_to_index(state)
        else:
            state_idx = int(state) % self.state_space_size

        row = self.q_table[state_idx, :]
        if not training and np.all(row == 0):
            return np.random.randint(self.action_space_size)
        return int(np.argmax(row))

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
        td_error = reward + self.discount_factor * next_max_q - current_q
        new_q = current_q + self.learning_rate * td_error

        self.q_table[state, action] = new_q

        # Track state visits for dynamic epsilon
        self._state_visits[state] = self._state_visits.get(state, 0) + 1

        # Track TD error for adaptive learning rate
        if self._adaptive_lr:
            self._td_errors.append(abs(td_error))
            if len(self._td_errors) > 100:
                self._td_errors = self._td_errors[-100:]
            # Adjust LR: high recent error → increase LR, low error → decrease
            if len(self._td_errors) >= 10:
                recent_mean = np.mean(self._td_errors[-10:])
                overall_mean = np.mean(self._td_errors)
                if overall_mean > 0:
                    ratio = recent_mean / overall_mean
                    # Clamp LR between 0.01 and 0.5
                    self.learning_rate = max(0.01, min(0.5,
                        self._base_learning_rate * ratio))

    def save_q_table(self, path: Optional[str] = None):
        """Save Q-table and state map to JSON file."""
        save_path = path or self.q_table_path
        if save_path:
            data = {
                "q_table": self.q_table.tolist(),
                "metadata": {
                    "bootstrapped_v2": True,
                    "state_space_size": self.state_space_size,
                    "action_space_size": self.action_space_size,
                    "state_map": self._state_map,
                    "state_counter": self._state_counter,
                    "auto_expand": self._auto_expand,
                },
            }
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # Also save neural weights if in neural mode
            if self._neural_agent is not None:
                neural_path = str(Path(save_path).with_suffix('.pt'))
                self._neural_agent.save(neural_path)
            print(f"[Q-Learning] Q-table saved to {save_path}")

    def load_q_table(self, path: str):
        """Load Q-table from JSON file (delegates to _load_q_table_json)."""
        _load_q_table_json(self, path)

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
            "distinct_states": len(self._state_map),
            "collisions_resolved": max(0, len(self._state_map) - self.state_space_size),
            "total_experiences": len(self.experience_buffer),
            "nonzero_entries": nonzero,
            "total_entries": self.q_table.size,
            "nonzero_pct": round(nonzero / self.q_table.size * 100, 2) if self.q_table.size > 0 else 0,
            "q_sum": round(total, 4),
            "alpha": self.learning_rate,
            "gamma": self.discount_factor,
            "epsilon": self.epsilon,
            "auto_expand": self._auto_expand,
            "neural_mode": self.neural_mode,
            "neural_stats": self._neural_agent.get_stats() if self._neural_agent else None,
            "world_model_stats": self._world_model.get_stats() if self._world_model else None,
        }

    def state_to_index(self, state) -> int:
        """
        Map a state (string or structured dict) to a deterministic index.

        For strings: uses MD5 stable hash, with collision-aware state_map.
        For dicts: serializes with sorted keys for deterministic hashing.

        If auto_expand is True and the state space is full, the Q-table
        grows dynamically (up to _max_states).

        Args:
            state: str or dict — the state to encode

        Returns:
            State index (deterministic across restarts for known states)
        """
        # Normalize to string key
        if isinstance(state, dict):
            state_key = json.dumps(state, sort_keys=True, ensure_ascii=False, default=str)
        else:
            state_key = str(state)

        # Return existing mapping if known
        if state_key in self._state_map:
            return self._state_map[state_key]

        # Compute candidate hash index
        hash_idx = _stable_hash(state_key, self.state_space_size)

        # Check for collision: if hash_idx maps to a DIFFERENT state_key
        existing = None
        for k, v in self._state_map.items():
            if v == hash_idx and k != state_key:
                existing = k
                break

        if existing is not None:
            # Collision detected: assign new unique index
            if self._auto_expand and self._state_counter < self._max_states:
                new_idx = self._state_counter
                self._state_counter += 1
                # Expand Q-table if needed
                if new_idx >= self.q_table.shape[0]:
                    self._expand_q_table(new_idx + 1)
                self._state_map[state_key] = new_idx
                self.state_space_size = max(self.state_space_size, new_idx + 1)
                print(f"[Q-Learning] Hash collision resolved: '{state_key[:40]}' "
                      f"→ index {new_idx} (hash {hash_idx} already used by '{existing[:40]}')")
                return new_idx
            else:
                # Cannot expand: reuse hash_idx (silent collision)
                print(f"[Q-Learning] WARNING: Hash collision, reusing index {hash_idx}: "
                      f"'{state_key[:40]}' and '{existing[:40]}'")
                return hash_idx
        else:
            # No collision: use hash index
            self._state_map[state_key] = hash_idx
            self._state_counter = max(self._state_counter, hash_idx + 1)
            return hash_idx

    def _expand_q_table(self, new_size: int):
        """Expand Q-table to accommodate more states."""
        if new_size <= self.q_table.shape[0]:
            return
        old_size = self.q_table.shape[0]
        new_table = np.zeros((new_size, self.action_space_size))
        new_table[:old_size, :] = self.q_table
        self.q_table = new_table
        print(f"[Q-Learning] Q-table expanded: {old_size} → {new_size} states")

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
