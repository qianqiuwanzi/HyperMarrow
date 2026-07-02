"""
Decision Check Point — Memory System Integration

This module integrates ProceduralMemory and VectorMemoryDB into the decision-making process.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Set HF environment BEFORE any import
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'

# Import memory_core config
from memory_core.config import get_workspace, get_hf_cache_dir

# Set HF cache paths dynamically
_hf_cache = get_hf_cache_dir()
os.environ['HUGGINGFACE_HUB_CACHE'] = str(_hf_cache / 'hub')
os.environ['HF_HOME'] = str(_hf_cache)

# Import memory modules
from memory_core.procedural_memory import ProceduralMemory
from memory_core.vector_memory_db import VectorMemoryDB


# ─────────────────────────────────────────────────────────────────────────────
# Shared data path helper
# ─────────────────────────────────────────────────────────────────────────────
def _data_dir() -> Path:
    """Return the canonical HyperMarrow data directory (under openclaw-memory-system)."""
    return get_workspace() / "HyperMarrow" / "openclaw-memory-system" / "data"


# ─────────────────────────────────────────────────────────────────────────────
# Keyword expansion for procedural memory matching
# ─────────────────────────────────────────────────────────────────────────────
# Maps a small set of high-signal keywords → related patterns in rules
_KEYWORD_ALIASES = {
    "skill":      ["skill", "scripts", "script", "tool", "技能", "脚本", "工具"],
    "error":      ["error", "bug", "fix", "issue", "problem", "failed", "失败", "错误", "修复"],
    "download":   ["download", "downloads", "下载", "素材", "media"],
    "decision":   ["decision", "recommend", "suggest", "choose", "决策", "建议"],
    "git":        ["git", "commit", "push", "branch", "github"],
    "memory":     ["memory", "remember", "forget", "learn", "记忆", "学习"],
    "video":      ["video", "clip", "scene", "视频", "场景", "竖屏"],
    "phase":      ["phase", "stage", "step", "阶段", "步骤"],
}

# Expand a raw context string into multiple searchable tokens
def _expand_context(context_str: str) -> List[str]:
    """Expand context into keyword tokens for better matching."""
    tokens = set()
    # Lowercase version
    lc = context_str.lower()
    tokens.add(lc)

    # Extract alphanumeric words
    words = re.findall(r'\b[a-z_]+\b', lc)
    tokens.update(words)

    # Add aliased expansions
    for key, aliases in _KEYWORD_ALIASES.items():
        for alias in aliases:
            if alias in lc:
                tokens.update(aliases)
                break

    # Try to parse JSON dict context
    try:
        ctx_dict = json.loads(context_str)
        if isinstance(ctx_dict, dict):
            values_str = " ".join(str(v) for v in ctx_dict.values() if isinstance(v, str))
            tokens.add(values_str.lower())
            words2 = re.findall(r'\b[a-z_]+\b', values_str.lower())
            tokens.update(words2)
    except (json.JSONDecodeError, TypeError):
        pass

    return list(tokens)


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap Q-table from history at startup
# ─────────────────────────────────────────────────────────────────────────────
def _bootstrap_q_table(q_table: List[List[float]], history: List[dict]) -> List[List[float]]:
    """
    Run Q-learning updates from historical experiences to populate Q-table.
    Modifies q_table in place and returns it.
    """
    import numpy as np

    ACTIONS = [
        "follow_rule_strictly", "use_existing_tool", "try_fix_three_times",
        "report_user", "write_script", "switch_skill", "skip_phase",
    ]
    ACTION_MAP = {a: i for i, a in enumerate(ACTIONS)}
    ALPHA, GAMMA = 0.1, 0.9
    STATE_SPACE = len(q_table)

    arr = np.array(q_table)
    for exp in history:
        action_name = exp.get("action", "")
        if action_name not in ACTION_MAP:
            continue
        state = int(exp.get("state", 0)) % STATE_SPACE
        next_state = int(exp.get("next_state", 0)) % STATE_SPACE
        reward = float(exp.get("reward", 0))
        done = exp.get("outcome") == "failure"
        action = ACTION_MAP[action_name]

        current_q = arr[state, action]
        next_max_q = 0.0 if done else float(np.max(arr[next_state, :]))
        new_q = current_q + ALPHA * (reward + GAMMA * next_max_q - current_q)
        arr[state, action] = new_q

    return arr.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# DecisionCheckPoint
# ─────────────────────────────────────────────────────────────────────────────
class DecisionCheckPoint:
    """
    Decision Check Point integrated with Memory System.

    Integrates three subsystems:
    1. ProceduralMemory  — rule-based habits
    2. VectorMemoryDB    — semantic memory search
    3. Q-Learning        — learned decision policy (bootstrap from history)
    """

    ACTIONS = [
        "follow_rule_strictly",   # 0
        "use_existing_tool",       # 1
        "try_fix_three_times",     # 2
        "report_user",             # 3
        "write_script",            # 4
        "switch_skill",            # 5
        "skip_phase",              # 6
    ]

    def __init__(self, enable_vector_db=True, enable_rl=True):
        self.procedural_memory = ProceduralMemory()
        self.enable_vector_db = enable_vector_db
        self.vector_db = None
        self.enable_rl = enable_rl
        self.q_table = None
        self.q_table_meta = {}

        # Vector DB
        if self.enable_vector_db:
            try:
                self.vector_db = VectorMemoryDB()
                print("[DecisionCheckPoint] VectorMemoryDB initialized")
            except Exception as e:
                print(f"[DecisionCheckPoint] VectorMemoryDB init failed: {e}")

        # RL: bootstrap Q-table from history
        if self.enable_rl:
            self._bootstrap_and_load_q_table()

        print(f"[DecisionCheckPoint] Initialized "
              f"(vector_db={self.vector_db is not None}, rl={self.q_table is not None})")

    def _bootstrap_and_load_q_table(self):
        """Load and bootstrap Q-table from the JSON file."""
        try:
            data_dir = _data_dir()
            qtable_path = data_dir / "q_table.json"
            history_path = data_dir / "rl_decision_history.json"

            with open(qtable_path, 'r', encoding='utf-8') as f:
                qdata = json.load(f)

            history = []
            if history_path.exists():
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            # Bootstrap if not already done
            if not qdata.get("metadata", {}).get("bootstrapped_v2"):
                print("[DecisionCheckPoint] Bootstrapping Q-table from history...")
                qdata["q_table"] = _bootstrap_q_table(qdata["q_table"], history)
                qdata["metadata"]["bootstrapped_v2"] = True
                with open(qtable_path, 'w', encoding='utf-8') as f:
                    json.dump(qdata, f, ensure_ascii=False, indent=2)
                print("[DecisionCheckPoint] Bootstrap Q-table saved")

            import numpy as np
            self.q_table = np.array(qdata["q_table"])
            self.q_table_meta = qdata.get("metadata", {})
            n_exp = self.q_table_meta.get("total_experiences", len(history))
            nonzero = int(np.count_nonzero(self.q_table))
            print(f"[DecisionCheckPoint] Q-table: shape={self.q_table.shape}, "
                  f"experiences={n_exp}, nonzero={nonzero}/{self.q_table.size}")

        except Exception as e:
            print(f"[DecisionCheckPoint] Q-table bootstrap failed: {e}")
            self.q_table = None

    def _get_rl_recommendation(self, context_str: str, current_action: str = None) -> dict:
        """
        Get RL recommendation based on trained Q-table.

        Args:
            context_str: Full context string
            current_action: The action being checked (optional, for same-state comparison)

        Returns:
            dict with recommended_action, confidence, q_value, all_q_values, state_index
        """
        if self.q_table is None:
            return {"recommended_action": None, "confidence": 0.0,
                    "all_q_values": {}, "fallback_used": False}

        import numpy as np

        # Primary: direct state lookup
        state_idx = hash(context_str) % self.q_table.shape[0]
        q_values = self.q_table[state_idx, :].copy()
        fallback_used = False

        # Fallback: if no positive Q-values in this state, use cross-state pattern average
        # (handles context serialization differences that cause hash misses)
        if float(np.max(q_values)) <= 0:
            if current_action and current_action in self.ACTIONS:
                action_idx = self.ACTIONS.index(current_action)
                action_col = self.q_table[:, action_idx]
                nonzero_mask = action_col > 0
                if nonzero_mask.any():
                    avg_q = float(np.mean(action_col[nonzero_mask]))
                    q_values[action_idx] = avg_q
                    global_best_idx = int(np.argmax(self.q_table.mean(axis=0)))
                    q_values[global_best_idx] = float(np.max(self.q_table[:, global_best_idx]))
                    fallback_used = True
                    state_idx = -1   # signals cross-state fallback

        # All action Q-values as dict
        all_q = {self.ACTIONS[i]: round(float(q_values[i]), 4) for i in range(len(self.ACTIONS))}
        best_action_idx = int(np.argmax(q_values))
        best_q = float(q_values[best_action_idx])

        # Confidence
        max_abs = float(np.max(np.abs(q_values)))
        if max_abs > 0 and best_q > 0:
            confidence = float(np.clip(best_q / (max_abs + 1e-8), 0, 1))
        elif best_q > 0:
            confidence = float(np.clip(best_q, 0, 1))
        else:
            confidence = 0.0

        # Same-state note
        same_state_note = None
        if current_action and current_action in self.ACTIONS:
            action_idx = self.ACTIONS.index(current_action)
            action_q = float(q_values[action_idx])
            if action_q > 0 and action_q < best_q:
                same_state_note = (f"'{current_action}' Q={action_q:.3f}, "
                                   f"best '{self.ACTIONS[best_action_idx]}' Q={best_q:.3f}")

        # Top-3 alternatives
        sorted_indices = np.argsort(q_values)[::-1]
        alternatives = []
        for idx in sorted_indices[1:4]:
            if float(q_values[idx]) > 0:
                alternatives.append({"action": self.ACTIONS[idx],
                                     "q_value": round(float(q_values[idx]), 4)})

        return {
            "recommended_action": self.ACTIONS[best_action_idx],
            "confidence": round(confidence, 3),
            "q_value": round(best_q, 4),
            "state_index": state_idx,
            "all_q_values": all_q,
            "alternatives": alternatives,
            "same_state_note": same_state_note,
            "fallback_used": fallback_used,
        }

    def check(self, action: str, context: Any = None) -> dict:
        """
        Check if an action should be executed, consulting all memory subsystems.

        Args:
            action: Action to check (e.g., 'switch_skill', 'write_script')
            context: Context dict or string

        Returns:
            dict: {allowed, rule, suggestion, confidence,
                   rl_recommendation, similar_memories, warnings}
        """
        import numpy as np

        result = {
            "allowed": True,
            "rule": None,
            "suggestion": None,
            "confidence": 1.0,
            "rl_recommendation": None,
            "similar_memories": [],
            "warnings": [],
            "procedural_hints": [],
            "vector_results": [],
        }

        # Build context string
        if isinstance(context, dict):
            context_str = json.dumps(context, ensure_ascii=False)
        elif context is None:
            context_str = action
        else:
            context_str = str(context)

        # Always prepend the action itself
        full_context = f"{action} {context_str}"

        # ─── 1. Procedural memory — expanded keyword matching ───────────────
        expanded_tokens = _expand_context(full_context)
        pm_matches = []

        for rule_id, rule in self.procedural_memory.data.get("rules", {}).items():
            patterns = rule.get("context_patterns", [])
            matched_pattern = None
            for token in expanded_tokens:
                for pattern in patterns:
                    p = pattern.lower()
                    if p in token or token in p:
                        matched_pattern = p
                        break
                if matched_pattern:
                    break

            if matched_pattern:
                pm_matches.append({
                    "rule_id": rule_id,
                    "rule_name": rule.get("rule_name"),
                    "level": rule.get("level", 1),
                    "success_rate": rule.get("success_rate", 0.0),
                    "total_attempts": rule.get("total_attempts", 0),
                    "matched_pattern": matched_pattern,
                    "last_used": rule.get("last_used_at"),
                })

        # Sort by level desc, then success_rate desc
        pm_matches.sort(key=lambda x: (x["level"], x["success_rate"]), reverse=True)
        result["procedural_hints"] = pm_matches

        if pm_matches:
            top = pm_matches[0]
            result["rule"] = top["rule_name"]
            result["confidence"] = round(top["success_rate"] or 0.5, 3)
            level = top["level"]
            if level >= 4:
                result["suggestion"] = (f"[PM] Rule '{top['rule_name']}' is Level {level} — auto-approved")
            elif level >= 2:
                result["suggestion"] = (f"[PM] Rule '{top['rule_name']}' applies (Level {level}, "
                                        f"{top['success_rate']:.0%} success)")
            else:
                result["suggestion"] = (f"[PM] '{top['rule_name']}' is Level 1 — manual review suggested")

        # ─── 2. RL recommendation ─────────────────────────────────────────
        rl_rec = self._get_rl_recommendation(full_context, current_action=action)
        result["rl_recommendation"] = rl_rec

        if rl_rec.get("recommended_action"):
            rec_action = rl_rec["recommended_action"]
            rec_conf = rl_rec["confidence"]
            rec_q = rl_rec["q_value"]

            if rec_action != action:
                result["warnings"].append(
                    f"[RL] Suggests '{rec_action}' (Q={rec_q:.3f}, conf={rec_conf:.0%}) "
                    f"instead of '{action}'"
                )
            elif rec_conf < 0.3 and rec_q <= 0:
                result["warnings"].append(
                    f"[RL] No positive经验 for '{action}' in this context (Q={rec_q:.3f})"
                )

            if rl_rec.get("same_state_note"):
                result["warnings"].append(f"[RL] {rl_rec['same_state_note']}")

        # ─── 3. Vector memory — similar past decisions ────────────────────
        if self.vector_db and context:
            try:
                # Search with the full context
                results = self.vector_db.search(full_context, n_results=3)
                if results and results.get("ids") and results["ids"][0]:
                    for i, mem_id in enumerate(results["ids"][0]):
                        score = float(results["distances"][0][i]) if results.get("distances") else None
                        text = results.get("documents", [[]])[0][i] if results.get("documents") else ""
                        result["vector_results"].append({
                            "id": mem_id,
                            "score": round(score, 4) if score else None,
                            "preview": text[:120] if text else "",
                        })
                        result["similar_memories"].append(mem_id)

                if result["similar_memories"]:
                    result["suggestion"] = (result["suggestion"] or "") + \
                        f" | [VecDB] Found {len(result['similar_memories'])} similar memories"
            except Exception as e:
                result["warnings"].append(f"[VecDB] Search failed: {e}")

        # ─── 4. Block rule ────────────────────────────────────────────────
        # If a Level 5 rule explicitly blocks this action
        for match in pm_matches:
            if match["level"] >= 5:
                block_keywords = ["skip", "block", "never", "禁止", "禁用"]
                if any(kw in match.get("rule_name", "").lower() for kw in block_keywords):
                    result["allowed"] = False
                    result["suggestion"] = f"[BLOCKED] Rule '{match['rule_name']}' (Level 5) blocks this action"
                    result["confidence"] = 0.0

        return result

    def record(self, action: str, context: Any, outcome: str, reward: float = None, note: str = "") -> None:
        """
        Record a decision outcome and update all memory subsystems.

        Args:
            action: Action taken
            context: Context dict or string
            outcome: 'success' or 'failure'
            reward: Explicit reward (auto-computed if None)
            note: Optional note
        """
        if reward is None:
            reward = 1.0 if outcome == "success" else -1.0

        context_str = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context)
        full_context = f"{action} {context_str}"

        # Update procedural memory
        pm_matches = self.procedural_memory.check_context(full_context)
        if pm_matches:
            rule_id = pm_matches[0].get("rule_id")
            if rule_id:
                try:
                    self.procedural_memory.record_outcome(
                        rule_id=rule_id,
                        success=(outcome == "success"),
                        context=context_str,
                        note=note,
                    )
                except Exception as e:
                    print(f"[DecisionCheckPoint] Failed to record PM outcome: {e}")

        # Append to RL history
        self._append_rl_history(action, context, outcome, reward, note)

        # Online Q-table update
        if self.q_table is not None and action in self.ACTIONS:
            import numpy as np
            state_idx = hash(full_context) % self.q_table.shape[0]
            next_state = (state_idx + 7) % self.q_table.shape[0]
            action_idx = self.ACTIONS.index(action)
            done = outcome == "failure"

            current_q = self.q_table[state_idx, action_idx]
            next_max = 0.0 if done else float(np.max(self.q_table[next_state, :]))
            new_q = current_q + 0.1 * (reward + 0.9 * next_max - current_q)
            self.q_table[state_idx, action_idx] = new_q

            # Persist updated Q-table
            try:
                qtable_path = _data_dir() / "q_table.json"
                with open(qtable_path, 'r', encoding='utf-8') as f:
                    qdata = json.load(f)
                qdata["q_table"] = self.q_table.tolist()
                with open(qtable_path, 'w', encoding='utf-8') as f:
                    json.dump(qdata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[DecisionCheckPoint] Failed to persist Q-table: {e}")

        print(f"[DecisionCheckPoint] Recorded: {action} -> {outcome} (reward={reward})")

    def _append_rl_history(self, action: str, context: Any, outcome: str, reward: float, note: str) -> None:
        """Append a decision entry to rl_decision_history.json."""
        try:
            context_str = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context)
            state_idx = hash(f"{action} {context_str}") % 100
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
                "source": "runtime_record",
            }

            history_path = _data_dir() / "rl_decision_history.json"
            if history_path.exists():
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []

            history.append(entry)

            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DecisionCheckPoint] Failed to append RL history: {e}")


__all__ = ["DecisionCheckPoint"]
