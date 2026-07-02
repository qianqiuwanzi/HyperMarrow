"""
Decision Check Point — Memory System Integration

This module integrates ProceduralMemory and VectorMemoryDB into the decision-making process.
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

# Import memory modules
from memory_core.procedural_memory import ProceduralMemory
from memory_core.vector_memory_db import VectorMemoryDB

import json
import numpy as np
from datetime import datetime


class DecisionCheckPoint:
    """
    Decision Check Point integrated with Memory System.
    
    This class provides decision support by checking procedural memory,
    querying vector memory, and applying reinforcement learning suggestions.
    """
    
    # Action space (must match RL training)
    ACTIONS = [
        "follow_rule_strictly",   # 0: Highest success rate
        "use_existing_tool",       # 1: High success rate
        "try_fix_three_times",     # 2: Recommended when uncertain
        "report_user",             # 3: Only after 3 failed attempts
        "switch_skill",            # 4: Low success rate
        "write_script",            # 5: When no existing tool available
        "skip_phase",              # 6: Last resort, high penalty
    ]
    
    def __init__(self, enable_vector_db=True, enable_rl=True):
        """
        Initialize Decision Check Point.
        
        Args:
            enable_vector_db: Whether to enable vector memory database
            enable_rl: Whether to enable reinforcement learning
        """
        self.procedural_memory = ProceduralMemory()
        
        self.enable_vector_db = enable_vector_db
        self.vector_db = None
        
        self.enable_rl = enable_rl
        self.q_table = None
        
        # Initialize vector database
        if self.enable_vector_db:
            try:
                self.vector_db = VectorMemoryDB()
                print("[DecisionCheckPoint] VectorMemoryDB initialized")
            except Exception as e:
                print(f"[DecisionCheckPoint] VectorMemoryDB init failed: {e}")
                self.vector_db = None
        
        # Initialize RL from trained Q-table
        if self.enable_rl:
            self._load_q_table()
        
        print(f"[DecisionCheckPoint] Initialized (vector_db={self.vector_db is not None}, rl={self.q_table is not None})")
    
    def _load_q_table(self):
        """Load trained Q-table from data directory."""
        try:
            ws = get_workspace()
            qtable_path = ws / "HyperMarrow" / "openclaw-memory-system" / "data" / "q_table.json"
            with open(qtable_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.q_table = np.array(data['q_table'])
            meta = data.get('metadata', {})
            total_exp = meta.get('total_experiences', '?')
            print(f"[DecisionCheckPoint] Q-table loaded: {self.q_table.shape}, {total_exp} experiences")
        except Exception as e:
            print(f"[DecisionCheckPoint] Q-table load failed: {e}")
            self.q_table = None
    
    def _get_rl_recommendation(self, context_str: str) -> dict:
        """
        Get RL-based recommendation from trained Q-table.
        
        Args:
            context_str: Concatenated context string
        
        Returns:
            dict with keys: recommended_action, confidence, alternative_actions
        """
        if self.q_table is None:
            return {"recommended_action": None, "confidence": 0.0, "alternative_actions": []}
        
        # Hash context to state index
        state_idx = hash(context_str) % self.q_table.shape[0]
        
        # Get Q-values for this state
        q_values = self.q_table[state_idx, :]
        
        # Get best action
        best_action_idx = int(np.argmax(q_values))
        best_q = float(q_values[best_action_idx])
        
        # Normalize confidence (scale Q to 0-1, assuming max |Q| ~ 1.0)
        max_q = np.max(np.abs(q_values))
        if max_q > 0:
            confidence = min(abs(best_q) / max_q, 1.0)
        else:
            confidence = 0.0
        
        # Get top-3 alternatives
        sorted_indices = np.argsort(q_values)[::-1]
        alternatives = []
        for idx in sorted_indices[1:4]:  # skip best (already recommended)
            if q_values[idx] > 0:
                alternatives.append({
                    "action": self.ACTIONS[idx],
                    "q_value": float(q_values[idx])
                })
        
        return {
            "recommended_action": self.ACTIONS[best_action_idx],
            "confidence": round(confidence, 3),
            "q_value": round(best_q, 4),
            "alternative_actions": alternatives,
            "state_index": state_idx
        }
    
    def check(self, action, context=None):
        """
        Check if an action should be executed.
        
        Args:
            action: Action to check (e.g., 'switch_skill', 'write_script')
            context: Optional context dictionary
        
        Returns:
            dict: {
                'allowed': bool,
                'rule': str or None,
                'suggestion': str or None,
                'confidence': float,
                'rl_recommendation': dict or None
            }
        """
        result = {
            'allowed': True,
            'rule': None,
            'suggestion': None,
            'confidence': 1.0,
            'rl_recommendation': None,
            'warnings': []
        }
        
        # Build context string
        context_str = f"{action} {json.dumps(context) if context else ''}"
        
        # ─── Check procedural memory ───
        matches = self.procedural_memory.check_context(context_str)
        rule = matches[0] if matches else None
        
        if rule:
            result['rule'] = rule.get('rule_name')
            result['confidence'] = rule.get('success_rate', 1.0)
            if rule.get('level', 1) >= 4:
                result['suggestion'] = f"Rule '{rule['rule_name']}' is Level {rule['level']} — auto-approved"
            elif rule.get('level', 1) >= 2:
                result['suggestion'] = f"Rule '{rule['rule_name']}' applies (Level {rule['level']})"
        
        # ─── RL recommendation ───
        rl_rec = self._get_rl_recommendation(context_str)
        result['rl_recommendation'] = rl_rec
        
        if rl_rec.get('recommended_action') and rl_rec['confidence'] > 0.5:
            rec_action = rl_rec['recommended_action']
            if rec_action != action:
                result['warnings'].append(
                    f"RL suggests '{rec_action}' (Q={rl_rec['q_value']:.3f}) instead of '{action}'"
                )
        
        # ─── Vector memory for similar decisions ───
        if self.vector_db and context:
            try:
                similar = self.vector_db.search(context_str, n_results=3)
                if similar and len(similar['ids'][0]) > 0:
                    result['suggestion'] = (result['suggestion'] or '') + \
                        f" | Similar memory found: {similar['ids'][0][0]}"
            except Exception as e:
                print(f"[DecisionCheckPoint] Vector search failed: {e}")
        
        return result
    
    def record(self, action, context, outcome, reward=None, note=""):
        """
        Record a decision and its outcome to both memory and RL history.
        
        Args:
            action: Action taken
            context: Context dictionary
            outcome: 'success' or 'failure'
            reward: Optional explicit reward value
            note: Optional note
        """
        # Determine reward from outcome if not provided
        if reward is None:
            reward = 1.0 if outcome == 'success' else -1.0
        
        # ─── Record to procedural memory ───
        context_str = f"{action} {json.dumps(context) if context else ''}"
        pm_matches = self.procedural_memory.check_context(context_str)
        
        if pm_matches:
            rule_id = pm_matches[0].get('rule_id')
            if rule_id:
                try:
                    self.procedural_memory.record_outcome(
                        rule_id=rule_id,
                        success=(outcome == 'success'),
                        context=context_str,
                        note=note
                    )
                except Exception as e:
                    print(f"[DecisionCheckPoint] Failed to record outcome: {e}")
        elif outcome == 'failure':
            # Auto-create rule for repeated failures
            auto_id = f"auto_{action}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.procedural_memory.add_rule(
                rule_id=auto_id,
                rule_name=action,
                context_patterns=[action] + ([ctx] for ctx in context.values() if isinstance(ctx, str)),
                description=f"Auto-generated from failure: {note or outcome}"
            )
        
        # ─── Record to RL decision history ───
        self._append_rl_history(action, context, outcome, reward, note)
        
        print(f"[DecisionCheckPoint] Recorded: {action} -> {outcome} (reward={reward})")
    
    def _append_rl_history(self, action, context, outcome, reward, note):
        """Append decision to rl_decision_history.json."""
        try:
            ws = get_workspace()
            history_path = ws / "HyperMarrow" / "openclaw-memory-system" / "data" / "rl_decision_history.json"
            
            # Load existing
            if history_path.exists():
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Build context string for state hashing
            context_str = f"{action} {json.dumps(context) if context else ''}"
            state_idx = hash(context_str) % 100
            next_state = (state_idx + 7) % 100

            entry = {
                "timestamp": datetime.now().isoformat(),
                "context": context if isinstance(context, dict) else {"raw": str(context)},
                "action": action,
                "outcome": outcome,
                "reward": reward,
                "state": state_idx,
                "next_state": next_state,
                "note": note,
                "source": "runtime_record"
            }
            
            history.append(entry)
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DecisionCheckPoint] Failed to append RL history: {e}")


__all__ = ["DecisionCheckPoint"]
