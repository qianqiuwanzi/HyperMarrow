"""
Decision Check Point — Memory System Integration

This module integrates ProceduralMemory and VectorMemoryDB into the decision-making process.
"""

import os
import sys as _sys
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
from memory_core.q_learning_agent import QLearningAgent, ACTIONS, ACTION_MAP, _stable_hash
from memory_core.vector_memory_db import VectorMemoryDB
from memory_core.working_memory_db import WorkingMemoryDB
from memory_core.episodic_memory_db import EpisodicMemoryDB
from memory_core.knowledge_graph import KnowledgeGraph
from memory_core.perception_channels import PerceptionOrchestrator
from memory_core.metacognition_monitor import MetacognitionMonitor
from memory_core.transfer_learner import TransferLearner
from memory_core.memory_consolidator import MemoryConsolidator
from memory_core.prospective_memory import ProspectiveMemory
from memory_core.meta_learner import MetaLearner, SkillExtractor
from memory_core.episodic_memory_db import set_knowledge_graph


# ─────────────────────────────────────────────────────────────────────────────
# Lazy singletons for foundational memory types (P1, P3, KG)
# ─────────────────────────────────────────────────────────────────────────────
_wm_instance = None
_em_instance = None
_kg_instance = None
_mc_instance = None
_tl_instance = None
_con_instance = None
_pm_instance = None
_ml_instance = None
_se_instance = None

# ─────────────────────────────────────────────────────────────────────────────
# Shared layer registry — one set of shared instances for all agents
# ─────────────────────────────────────────────────────────────────────────────
_shared_layer = None
_shared_layer_ready = False


def _get_or_create_shared_layer() -> dict:
    """
    Get or create the shared layer (ProceduralMemory, KG, Perception, etc.).
    All agents see the same shared layer; isolation is per-agent.
    """
    global _shared_layer, _shared_layer_ready
    if _shared_layer is not None:
        return _shared_layer

    print("[DecisionCheckPoint] Creating shared layer...", file=_sys.stderr)
    shared = {}

    # ProceduralMemory — shared across all agents
    shared["procedural_memory"] = ProceduralMemory()

    # KnowledgeGraph — shared (entity/relationship corpus)
    kg = KnowledgeGraph()
    set_knowledge_graph(kg)
    shared["knowledge_graph"] = kg

    # Perception — shared (orchestrates sensors)
    shared["perception"] = PerceptionOrchestrator()

    # MemoryConsolidator — shared (LTP/LTD across all agents)
    shared["consolidator"] = MemoryConsolidator(
        episodic_memory=None,  # set per-agent below
        knowledge_graph=kg,
        q_agent=None,
    )

    # TransferLearner — shared (cold-start Q seeding from other agents)
    shared["transfer_learner"] = TransferLearner(
        episodic_memory=None,
        knowledge_graph=kg,
    )

    # ProspectiveMemory — shared (intention triggers)
    shared["prospective"] = ProspectiveMemory()

    # MetaLearner + SkillExtractor — shared (hyperparam tuning)
    shared["meta_learner"] = MetaLearner()
    shared["skill_extractor"] = SkillExtractor(
        episodic_memory=None,
        knowledge_graph=kg,
    )

    # VectorMemoryDB — shared (semantic memory across agents)
    try:
        shared["vector_db"] = VectorMemoryDB()
        print("[DecisionCheckPoint] Shared VectorDB: OK", file=_sys.stderr)
    except Exception as e:
        print(f"[DecisionCheckPoint] Shared VectorDB: failed ({e})", file=_sys.stderr)
        shared["vector_db"] = None

    _shared_layer = shared
    _shared_layer_ready = True
    print(f"[DecisionCheckPoint] Shared layer ready: "
          f"PM=✓ KG=✓ Perception=✓ Consolidator=✓ TL=✓ PM2=✓ ML=✓ SE=✓ VecDB={'✓' if shared['vector_db'] else '✗'}", file=_sys.stderr)
    return shared


# ─────────────────────────────────────────────────────────────────────────────
# Agent Registry integration
# ─────────────────────────────────────────────────────────────────────────────
_agent_registry = None          # AgentRegistry instance
_agent_dc_map = {}              # agent_id -> DecisionCheckPoint instance
_current_agent_id = "openclaw"  # default


def get_agent_registry():
    """Return the global AgentRegistry instance."""
    global _agent_registry
    if _agent_registry is not None:
        return _agent_registry
    from memory_core.agent_registry import AgentRegistry
    _agent_registry = AgentRegistry()
    return _agent_registry


def create_for_agent(agent_id: str, action_space: list = None,
                     enable_vector_db=True, enable_rl=True,
                     enable_metacognition=True, enable_world_model=True,
                     enable_prospective=True) -> 'DecisionCheckPoint':
    """
    Factory: create (or return cached) DecisionCheckPoint for a specific agent.

    Each agent gets its own DC with:
      - Isolated memory: WorkingMemoryDB, EpisodicMemoryDB, QLearningAgent,
        MetacognitionMonitor (per-agent file paths via AgentBundle)
      - Shared memory: ProceduralMemory, KnowledgeGraph, Perception,
        MemoryConsolidator, TransferLearner, ProspectiveMemory,
        MetaLearner, SkillExtractor, VectorMemoryDB (one instance, all agents)

    Args:
        agent_id: Agent identifier (e.g., 'openclaw', 'luci')
        action_space: Action list (only used on first creation)

    Returns:
        DecisionCheckPoint bound to the agent's isolated memory instances
    """
    global _agent_dc_map, _current_agent_id

    if agent_id in _agent_dc_map:
        print(f"[DC Factory] Returning cached DC for '{agent_id}'", file=_sys.stderr)
        return _agent_dc_map[agent_id]

    print(f"[DC Factory] Creating DC for agent '{agent_id}'...", file=_sys.stderr)
    shared = _get_or_create_shared_layer()
    reg = get_agent_registry()

    # Register agent if not yet registered
    if action_space is None:
        action_space = [
            "follow_rule_strictly", "use_existing_tool", "try_fix_three_times",
            "report_before_bypass", "switch_skill", "request_user_input", "defer_to_rl",
        ]

    bundle = reg.register(agent_id, action_space=action_space)

    # Inject shared layer into AgentBundle (so bundle.knowledge_graph works)
    bundle.knowledge_graph = shared.get("knowledge_graph")
    bundle.vector_db = shared.get("vector_db")
    bundle.procedural_memory = shared.get("procedural_memory")
    bundle.consolidator = shared.get("consolidator")
    bundle.transfer_learner = shared.get("transfer_learner")
    bundle.perception = shared.get("perception")

    # Wire shared consolidator + skill_extractor to the agent's episodic memory
    # Note: MemoryConsolidator uses self.em (not self.episodic_memory)
    shared["consolidator"].em = bundle.episodic_memory
    shared["skill_extractor"].episodic_memory = bundle.episodic_memory
    shared["transfer_learner"].episodic_memory = bundle.episodic_memory

    # Create DC with agent's isolated instances + shared layer
    dc = DecisionCheckPoint(
        agent_bundle=bundle,
        shared_layer=shared,
        enable_vector_db=enable_vector_db and shared["vector_db"] is not None,
        enable_rl=enable_rl,
        enable_metacognition=enable_metacognition,
        enable_world_model=enable_world_model,
        enable_prospective=enable_prospective,
    )

    _agent_dc_map[agent_id] = dc
    bundle.decision_checkpoint = dc  # Wire DC back to bundle
    _current_agent_id = agent_id
    print(f"[DC Factory] DC for '{agent_id}': "
          f"WM={bundle.working_memory is not None}, "
          f"EM={bundle.episodic_memory is not None}, "
          f"QL={bundle.ql_agent is not None}", file=_sys.stderr)
    return dc


def get_current_dc() -> Optional['DecisionCheckPoint']:
    """Return the DC for the current active agent."""
    return _agent_dc_map.get(_current_agent_id)


def set_current_agent(agent_id: str):
    """Switch the current active agent context."""
    global _current_agent_id
    if agent_id not in _agent_dc_map:
        create_for_agent(agent_id)
    _current_agent_id = agent_id
    print(f"[DC] Current agent switched to '{agent_id}'", file=_sys.stderr)


def _get_wm() -> WorkingMemoryDB:
    global _wm_instance
    if _wm_instance is None:
        _wm_instance = WorkingMemoryDB()
    return _wm_instance


def _get_em() -> EpisodicMemoryDB:
    global _em_instance
    if _em_instance is None:
        _em_instance = EpisodicMemoryDB()
    return _em_instance


def _get_kg() -> KnowledgeGraph:
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = KnowledgeGraph()
        set_knowledge_graph(_kg_instance)
    return _kg_instance


def _get_mc() -> MetacognitionMonitor:
    global _mc_instance
    if _mc_instance is None:
        _mc_instance = MetacognitionMonitor()
    return _mc_instance


def _get_tl() -> TransferLearner:
    global _tl_instance
    if _tl_instance is None:
        _tl_instance = TransferLearner(
            episodic_memory=_get_em(),
            knowledge_graph=_get_kg(),
        )
    return _tl_instance


def _get_con() -> MemoryConsolidator:
    global _con_instance
    if _con_instance is None:
        _con_instance = MemoryConsolidator(
            episodic_memory=_get_em(),
            knowledge_graph=_get_kg(),
            q_agent=None,  # set after ql_agent is created
        )
    return _con_instance


def _get_pm() -> ProspectiveMemory:
    global _pm_instance
    if _pm_instance is None:
        _pm_instance = ProspectiveMemory()
    return _pm_instance


def _get_ml() -> MetaLearner:
    global _ml_instance
    if _ml_instance is None:
        _ml_instance = MetaLearner()
    return _ml_instance


def _get_se() -> SkillExtractor:
    global _se_instance
    if _se_instance is None:
        _se_instance = SkillExtractor(
            episodic_memory=_get_em(),
            knowledge_graph=_get_kg(),
        )
    return _se_instance


# ─────────────────────────────────────────────────────────────────────────────
# Shared data path helper
# ─────────────────────────────────────────────────────────────────────────────
def _data_dir() -> Path:
    """Return the canonical data directory (delegates to config.get_data_dir)."""
    from memory_core.config import get_data_dir
    return get_data_dir()


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
# _bootstrap_q_table moved into QLearningAgent


def _infer_action_from_rule(rule_name: str) -> str:
    """Infer the recommended action from a procedural rule name."""
    mapping = {
        "follow_rule_strictly": "follow_rule_strictly",
        "use_existing_tool": "use_existing_tool",
        "try_fix": "try_fix_three_times",
        "retry": "try_fix_three_times",
        "report": "report_user",
        "write_script": "write_script",
        "switch": "switch_skill",
        "skip": "skip_phase",
    }
    rl = rule_name.lower()
    for key, action in mapping.items():
        if key in rl:
            return action
    return None


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

    def __init__(self, enable_vector_db=True, enable_rl=True,
                 agent_bundle=None, shared_layer=None,
                 enable_metacognition=True, enable_world_model=True,
                 enable_prospective=True):
        """
        Initialize DecisionCheckPoint.

        Two modes:
        - Global mode (agent_bundle=None): all subsystems from shared singletons
          (backward-compatible, used by standalone DC())
        - Agent mode (agent_bundle provided): isolated per-agent memory instances
          + shared layer for cross-agent knowledge

        Args:
            agent_bundle: AgentBundle with isolated memory instances (WM, EM, QL, Meta)
            shared_layer: dict of shared layer instances (PM, KG, Perception, etc.)
            enable_vector_db: whether to init VectorMemoryDB (shared_layer['vector_db'] if available)
            enable_rl: whether to bootstrap QLearningAgent (from agent_bundle.ql_agent)
        """
        self._agent_bundle = agent_bundle

        # ── Isolated memory (per-agent) or global singletons ─────────────────
        if agent_bundle is not None:
            # Agent mode: use the bundle's isolated instances
            self.working_memory   = agent_bundle.working_memory
            self.episodic_memory  = agent_bundle.episodic_memory
            self.metacognition    = agent_bundle.metacognition
            self.ql_agent         = agent_bundle.ql_agent
            self._is_agent_mode   = True
            self._agent_id        = agent_bundle.agent_id
            self._isolated_path   = f"[agent={agent_bundle.agent_id}]"
        else:
            # Global mode: use shared singletons (backward-compatible)
            self.working_memory   = _get_wm()
            self.episodic_memory  = _get_em()
            self.knowledge_graph  = _get_kg()
            self.metacognition    = _get_mc()
            self.perception       = PerceptionOrchestrator(working_memory=self.working_memory)
            self.transfer_learner = _get_tl()
            self.consolidator     = _get_con()
            self.prospective      = _get_pm()
            self.meta_learner      = _get_ml()
            self.skill_extractor   = _get_se()
            self._is_agent_mode   = False
            self._agent_id        = "__global__"
            self._isolated_path   = "[global]"
            self.last_activity_at = None  # Track last check/record timestamp

        # ── Shared layer ───────────────────────────────────────────────────
        if shared_layer is not None:
            self.procedural_memory = shared_layer.get("procedural_memory")
            self.knowledge_graph   = shared_layer.get("knowledge_graph")
            self.perception        = shared_layer.get("perception")
            self.consolidator      = shared_layer.get("consolidator")
            self.transfer_learner  = shared_layer.get("transfer_learner")
            self.prospective       = shared_layer.get("prospective")
            self.meta_learner      = shared_layer.get("meta_learner")
            self.skill_extractor   = shared_layer.get("skill_extractor")
            self.vector_db         = shared_layer.get("vector_db")
            if self.vector_db is not None:
                print(f"[DecisionCheckPoint] Shared VectorDB from layer: OK", file=_sys.stderr)
        else:
            # Fallback: create own ProceduralMemory if not in shared_layer
            if not hasattr(self, 'procedural_memory') or self.procedural_memory is None:
                self.procedural_memory = ProceduralMemory()
            # Vector DB only in global mode
            self.vector_db = None
            if enable_vector_db and shared_layer is None:
                try:
                    self.vector_db = VectorMemoryDB()
                    print("[DecisionCheckPoint] VectorMemoryDB initialized", file=_sys.stderr)
                except Exception as e:
                    print(f"[DecisionCheckPoint] VectorMemoryDB init failed: {e}", file=_sys.stderr)

        self.enable_vector_db = enable_vector_db
        self.enable_rl = enable_rl
        self.q_table_meta = {}

        # RL: use agent's ql_agent if in agent mode, else bootstrap
        if self.enable_rl:
            self._bootstrap_and_load_q_table()

        print(f"[DecisionCheckPoint] Initialized "
              f"agent={self._agent_id} "
              f"(vector_db={self.vector_db is not None}, "
              f"rl={self.ql_agent is not None}, "
              f"isolated={self._is_agent_mode})", file=_sys.stderr)

    def _bootstrap_and_load_q_table(self):
        """
        Load Q-table from the JSON file and wrap in QLearningAgent.

        The QLearningAgent instance:
        - Loads the already-bootstrapped Q-table (from JSON via _load_q_table_json)
        - Loads historical experiences into its experience_buffer
        - Provides update() / batch_learn() / get_stats() / get_action() methods

        Bootstrap is assumed already done (phase1_fix.py or prior session).
        If q_table.json is missing the bootstrapped_v2 flag, QLearningAgent
        will still load the raw Q-table values — the flag only gates a
        redundant re-bootstrap that is no longer needed.
        """
        try:
            import numpy as np
            data_dir = _data_dir()
            qtable_path = data_dir / "q_table.json"

            # Create QLearningAgent — it loads the Q-table and buffer experiences
            self.ql_agent = QLearningAgent(
                state_space_size=100,
                action_space_size=7,
                learning_rate=0.1,
                discount_factor=0.9,
                epsilon=0.1,
                q_table_path=str(qtable_path),
            )
            # Ensure buffer is populated (belt-and-suspenders)
            if len(self.ql_agent.experience_buffer) == 0:
                self.ql_agent._load_experience_buffer()

            # Wire consolidator to the agent
            self.consolidator.ql_agent = self.ql_agent

            self.q_table_meta = {"bootstrapped_v2": True}
            n_exp = len(self.ql_agent.experience_buffer)
            nonzero = int(np.count_nonzero(self.ql_agent.q_table))
            print(f"[DecisionCheckPoint] QLearningAgent: buffer={n_exp}, "
                  f"qtable_nonzero={nonzero}/{self.ql_agent.q_table.size}", file=_sys.stderr)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[DecisionCheckPoint] Q-table bootstrap failed: {e}", file=_sys.stderr)
            self.ql_agent = None


    def _rl_recommendation_from_agent(self, context_str: str, current_action: str = None) -> dict:
        """
        RL recommendation using the QLearningAgent instance.
        Provides cross-state fallback when the current state has no positive Q-values.
        """
        import numpy as np

        state_idx = _stable_hash(context_str, self.ql_agent.state_space_size)
        q_values = self.ql_agent.q_table[state_idx, :].copy()
        fallback_used = False

        # Fallback: if no positive Q in this state, use cross-state average
        if float(np.max(q_values)) <= 0:
            if current_action and current_action in ACTION_MAP:
                action_idx = ACTION_MAP[current_action]
                action_col = self.ql_agent.q_table[:, action_idx]
                nonzero_mask = action_col > 0
                if nonzero_mask.any():
                    avg_q = float(np.mean(action_col[nonzero_mask]))
                    q_values[action_idx] = avg_q
                    global_best_idx = int(np.argmax(self.ql_agent.q_table.mean(axis=0)))
                    q_values[global_best_idx] = float(np.max(self.ql_agent.q_table[:, global_best_idx]))
                    fallback_used = True
                    state_idx = -1

        all_q = {ACTIONS[i]: round(float(q_values[i]), 4) for i in range(len(ACTIONS))}
        best_action_idx = int(np.argmax(q_values))
        best_q = float(q_values[best_action_idx])

        max_abs = float(np.max(np.abs(q_values)))
        if max_abs > 0 and best_q > 0:
            confidence = float(np.clip(best_q / (max_abs + 1e-8), 0, 1))
        else:
            confidence = 0.0

        same_state_note = None
        if current_action and current_action in ACTIONS:
            action_idx = ACTIONS.index(current_action)
            action_q = float(q_values[action_idx])
            if action_q > 0 and action_q < best_q:
                same_state_note = (f"'{current_action}' Q={action_q:.3f}, "
                                   f"best '{ACTIONS[best_action_idx]}' Q={best_q:.3f}")

        sorted_indices = np.argsort(q_values)[::-1]
        alternatives = []
        for idx in sorted_indices[1:4]:
            if float(q_values[idx]) > 0:
                alternatives.append({"action": ACTIONS[idx],
                                     "q_value": round(float(q_values[idx]), 4)})

        return {
            "recommended_action": ACTIONS[best_action_idx],
            "confidence": round(confidence, 3),
            "q_value": round(best_q, 4),
            "state_index": state_idx,
            "all_q_values": all_q,
            "alternatives": alternatives,
            "same_state_note": same_state_note,
            "fallback_used": fallback_used,
        }

    def check(self, action: str, context: Any = None, agent_id: str = None) -> dict:
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
            "related_entities": [],
            "working_memory_summary": "",  # filled after full_context is built
            "_agent_id": self._agent_id,  # tag the result with which agent decided
        }


        # ── Agent routing: delegate to agent-specific DC if agent_id specified ─
        if agent_id is not None and agent_id != self._agent_id:
            target_dc = _agent_dc_map.get(agent_id)
            if target_dc is not None:
                print(f"[DC.check] Routing '{agent_id}' -> {target_dc._isolated_path}", file=_sys.stderr)
                return target_dc.check(action, context, agent_id=None)
            else:
                result["warnings"].append(
                    f"[DC] Agent '{agent_id}' not registered; using current DC"
                )

        # Build context string
        if isinstance(context, dict):
            context_str = json.dumps(context, ensure_ascii=False)
        elif context is None:
            context_str = action
        else:
            context_str = str(context)

        # ─── 0. Perception — observe environment ────────────────────────
        try:
            observations = self.perception.observe_all()
            for obs in observations:
                self.perception.inject_to_working_memory(obs)
        except Exception as e:
            print(f"[DecisionCheckPoint] Non-critical operation failed: {e}", file=_sys.stderr)

        # ─── 0b. Prospective memory — check intention triggers ──────────
        try:
            triggers = self.prospective.check_triggers(full_context)
            if triggers:
                for t in triggers[:3]:
                    result["warnings"].append(
                        f"[PM] 前瞻记忆触发: '{t['action']}' "
                        f"(match={t['match_score']}, priority={t['priority']})"
                    )
        except Exception:
            pass

        # Inject working memory context into decision context
        wm_summary = self.working_memory.get_context_summary()

        # Always prepend the action itself
        full_context = f"{action} {context_str} [WM:{wm_summary}]"

        # ── 0c. Auto-fill WorkingMemory from incoming context ────────────────
        try:
            self.working_memory.auto_update_from_context(full_context, action=action)
        except Exception as e:
            print(f"[DecisionCheckPoint] WorkingMemory auto-update failed (non-critical): {e}",
                  file=_sys.stderr)

        # Populate working_memory_summary for build_context_prompt
        result["working_memory_summary"] = wm_summary

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
        if self.ql_agent is not None:
            rl_rec = self._rl_recommendation_from_agent(full_context, current_action=action)
        else:
            rl_rec = {"recommended_action": None, "confidence": 0.0,
                      "all_q_values": {}, "fallback_used": False}
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

        # ─── 2b. Conflict Arbitration — resolve PM vs RL disagreements ──
        result["arbitration"] = None
        if pm_matches and rl_rec.get("recommended_action"):
            top_pm = pm_matches[0]
            pm_action = _infer_action_from_rule(top_pm.get("rule_name", ""))
            rl_action = rl_rec["recommended_action"]
            pm_conf = top_pm.get("success_rate", 0.5) or 0.5
            rl_conf = rl_rec["confidence"]

            if pm_action and pm_action != rl_action:
                # Conflict detected — arbitrate
                pm_reliability = min(0.95, top_pm.get("success_rate", 0.5) or 0.5)
                rl_reliability = rl_conf if rl_conf > 0 else 0.1

                if pm_reliability > rl_reliability + 0.2:
                    winner, reason = "PM", f"Programmatic memory more reliable ({pm_reliability:.0%} vs {rl_reliability:.0%})"
                elif rl_reliability > pm_reliability + 0.2:
                    winner, reason = "RL", f"RL more reliable ({rl_reliability:.0%} vs {pm_reliability:.0%})"
                else:
                    winner, reason = "UNRESOLVED", f"Reliability too close ({pm_reliability:.0%} vs {rl_reliability:.0%})"

                result["arbitration"] = {
                    "conflict": True,
                    "pm_action": pm_action,
                    "rl_action": rl_action,
                    "pm_confidence": round(pm_reliability, 3),
                    "rl_confidence": round(rl_reliability, 3),
                    "winner": winner,
                    "reason": reason,
                }
                result["warnings"].append(
                    f"[ARB] PM→'{pm_action}' vs RL→'{rl_action}': {winner} wins ({reason})"
                )

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

        # ─── 4. Knowledge Graph — related entities ──────────────────────
        try:
            extracted = self.knowledge_graph.extract_entities_from_text(full_context)
            if extracted:
                all_related = []
                for ent in extracted[:3]:
                    related = self.knowledge_graph.find_related(ent["id"], max_depth=1)
                    for r in related:
                        all_related.append({
                            "source": ent["name"],
                            "related": r["entity"]["name"],
                            "type": r["entity"]["type"],
                            "distance": r["distance"],
                        })
                result["related_entities"] = all_related[:10]
        except Exception as e:
            print(f"[DecisionCheckPoint] Non-critical operation failed: {e}", file=_sys.stderr)

        # ─── 4b. Metacognition — self-reflection check ─────────────────
        try:
            refl = self.metacognition.evaluate_self_reflection_needed()
            if refl:
                result["warnings"].append(
                    f"[Meta] 自我反思触发: {refl['reason']} (severity={refl['severity']})"
                )
        except Exception as e:
            print(f"[DecisionCheckPoint] Non-critical operation failed: {e}", file=_sys.stderr)

        # ─── 5. Block rule ────────────────────────────────────────────────
        # If a Level 5 rule explicitly blocks this action
        for match in pm_matches:
            if match["level"] >= 5:
                block_keywords = ["skip", "block", "never", "禁止", "禁用"]
                if any(kw in match.get("rule_name", "").lower() for kw in block_keywords):
                    result["allowed"] = False
                    result["suggestion"] = f"[BLOCKED] Rule '{match['rule_name']}' (Level 5) blocks this action"
                    result["confidence"] = 0.0

        # ─── P0-2: Memory-first lookup path ────────────────────────────────
        result["lookup_path"] = []
        if result.get("procedural_hints"):
            result["lookup_path"].append(
                f"PM: {len(result['procedural_hints'])} rules matched")
        if result["rl_recommendation"] and result["rl_recommendation"].get("recommended_action"):
            rl = result["rl_recommendation"]
            result["lookup_path"].append(
                f"RL: recommends '{rl['recommended_action']}' "
                f"(conf={rl.get('confidence',0):.0%})")
        if result.get("related_entities"):
            result["lookup_path"].append(
                f"KG: {len(result['related_entities'])} entities related")
        if result.get("similar_memories"):
            result["lookup_path"].append(
                f"EM: {len(result['similar_memories'])} similar memories found")
        if result.get("arbitration"):
            arb = result["arbitration"]
            result["lookup_path"].append(
                f"ARB: {arb.get('winner','?')} wins ({arb.get('reason','')[:60]})")

        return result

    def record(self, action: str, context: Any, outcome: str, reward: float = None,
               note: str = "", agent_id: str = None, async_mode: bool = False) -> None:
        """
        Record a decision outcome and update all memory subsystems.

        Args:
            action: Action taken
            context: Context dict or string
            outcome: 'success' or 'failure'
            reward: Explicit reward (auto-computed if None)
            note: Optional note
            agent_id: If provided, route to that agent's DC (for cross-agent call)
            async_mode: If True, execute in background daemon thread (V2: non-blocking)
        """
        if async_mode:
            import threading
            t = threading.Thread(
                target=self.record,
                args=(action, context, outcome, reward, note, agent_id, False),
                daemon=True, name=f"hm_record_{action}"
            )
            t.start()
            print(f"[DC.record] Queued async: {action} -> {outcome}", file=_sys.stderr)
            return

        # ── Agent routing ────────────────────────────────────────────────
        if agent_id is not None and agent_id != self._agent_id:
            target_dc = _agent_dc_map.get(agent_id)
            if target_dc is not None:
                print(f"[DC.record] Routing '{agent_id}' -> {target_dc._isolated_path}", file=_sys.stderr)
                target_dc.record(action, context, outcome, reward, note, agent_id=None)
                return
            else:
                print(f"[DC.record] Agent '{agent_id}' not registered; recording locally", file=_sys.stderr)

        if reward is None:
            reward = 1.0 if outcome == "success" else -1.0

        context_str = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context)
        wm_summary = self.working_memory.get_context_summary()
        full_context = f"{action} {context_str} [WM:{wm_summary}]"

        # ── Auto-fill WorkingMemory from record context ────────────────────────
        try:
            self.working_memory.auto_update_from_context(full_context, action=action)
        except Exception as e:
            print(f"[DC.record] WorkingMemory auto-update failed (non-critical): {e}",
                  file=_sys.stderr)

        # ── Auto-extract entities to KnowledgeGraph ───────────────────────────
        try:
            extracted_entities = self.knowledge_graph.extract_entities_from_text(full_context)
            for ent in (extracted_entities or [])[:5]:
                entity = self.knowledge_graph.add_entity(
                    name=ent.get("name", ""),
                    entity_type=ent.get("type", "concept"),
                    properties={"source": "record_auto", "action": action, "outcome": outcome},
                )
                # Auto-link to action entity
                if entity and entity.get("id"):
                    action_entity = self.knowledge_graph.add_entity(
                        name=action,
                        entity_type="action",
                        properties={"outcome": outcome, "reward": reward},
                    )
                    if action_entity and action_entity.get("id"):
                        self.knowledge_graph.add_relationship(
                            source_id=entity["id"],
                            target_id=action_entity["id"],
                            relation_type="triggers",
                        )
        except Exception as e:
            print(f"[DC.record] KG auto-extract failed (non-critical): {e}",
                  file=_sys.stderr)

        # ── Auto-add to VectorDB for semantic memory ──────────────────────────
        if self.vector_db and outcome in ("success", "failure"):
            try:
                import uuid
                import hashlib
                # Deduplicate by content hash
                content_hash = hashlib.sha256(full_context.encode()).hexdigest()[:16]
                mem_id = f"record_{content_hash}_{int(datetime.now().timestamp())}"
                self.vector_db.add_memory(
                    memory_id=mem_id,
                    content=full_context,
                    metadata={
                        "action": action,
                        "outcome": outcome,
                        "reward": reward,
                        "source": "record_auto",
                        "quality": 5 if outcome == "success" else 3,
                    },
                )
            except Exception as e:
                print(f"[DC.record] VectorDB auto-add failed (non-critical): {e}",
                      file=_sys.stderr)

        # Update procedural memory (use same full_context as check() for consistency)
        pm_matches = self.procedural_memory.check_context(full_context)
        if pm_matches:
            rule_id = pm_matches[0].get("rule_id")
            if rule_id:
                try:
                    self.procedural_memory.record_outcome(
                        rule_id=rule_id,
                        success=(outcome == "success"),
                        context=full_context,
                        note=note,
                    )
                except Exception as e:
                    print(f"[DecisionCheckPoint] Failed to record PM outcome: {e}", file=_sys.stderr)

        # Append to RL history
        self._append_rl_history(action, context, outcome, reward, note)

        # Record as episodic memory
        emotion_map = {"success": "positive", "failure": "negative", "partial": "neutral"}
        self.episodic_memory.add_episode(
            what=f"Action '{action}': {outcome}",
            context={
                "action": action,
                "context_raw": context_str,
                "wm_summary": self.working_memory.get_context_summary(),
                "reward": reward,
                "note": note,
            },
            outcome=outcome,
            emotion=emotion_map.get(outcome, "neutral"),
            tags=["decision", "RL"],
            importance=4 if outcome == "failure" else 3,
        )

        # Online update via QLearningAgent (populates buffer + Q-table)
        state_idx = -1  # initialized for metacognition use below
        if self.ql_agent is not None and action in ACTIONS:
            state_idx = _stable_hash(full_context, self.ql_agent.state_space_size)
            # Use identity transition: actual next state is not tracked,
            # so Q(s,a) represents immediate expected reward for (state, action).
            next_state_idx = state_idx
            done = outcome == "failure"

            # Use agent's add_experience() which updates both buffer and Q-table
            self.ql_agent.add_experience(state_idx, action, reward, next_state_idx, done)

            # Periodic batch learning (every 10 records) + persistence
            if not hasattr(self, '_record_counter'):
                self._record_counter = 0
            self._record_counter += 1
            if self._record_counter % 10 == 0:
                self.ql_agent.batch_learn(batch_size=32)
                self._persist_q_table()

            # Periodic memory consolidation (every 20 records)
            if self._record_counter % 20 == 0:
                try:
                    self.consolidator.consolidate()
                    # Wave 3: auto-extract skills after consolidation
                    extracted = self.skill_extractor.extract_skills()
                    if extracted > 0:
                        self.skill_extractor.feed_procedural(self.procedural_memory)
                except Exception:
                    pass

        # ── Metacognition: record outcome for calibration + anomaly check
        try:
            rl_rec = {}  # get from the check result if available, else build minimal
            rl_conf = 0.5
            if action in ACTIONS:
                rl_conf = float(self.ql_agent.q_table[
                    _stable_hash(full_context, self.ql_agent.state_space_size),
                    ACTIONS.index(action)
                ]) if self.ql_agent else 0.5
                rl_conf = max(0.0, min(1.0, rl_conf))
            self.metacognition.record_decision_outcome(
                predicted_confidence=rl_conf,
                actual_outcome=outcome,
                action=action,
                state_context=full_context[:80],
            )
            self.metacognition.check_anomaly({
                "confidence": rl_conf,
                "outcome": outcome,
                "action": action,
                "state_index": state_idx,
            })
        except Exception as e:
            print(f"[DecisionCheckPoint] Non-critical operation failed: {e}", file=_sys.stderr)

        # ── Meta-learning: observe metrics, adjust hyperparams periodically ──
        try:
            self.meta_learner.observe(
                success=(outcome == "success"),
                state_count=len(self.ql_agent._state_map) if self.ql_agent else 0,
            )
            if self._record_counter % 50 == 0:  # Every 50 decisions
                self.meta_learner.adjust(
                    q_agent=self.ql_agent,
                    world_model=self.ql_agent._world_model if self.ql_agent else None,
                    consolidator=self.consolidator,
                )
        except Exception:
            pass

        print(f"[DecisionCheckPoint] Recorded: {action} -> {outcome} (reward={reward})", file=_sys.stderr)

    def _persist_q_table(self):
        """
        Persist ql_agent's Q-table to its own JSON file.

        In agent mode: uses ql_agent.q_table_path (agent-specific, e.g. data/q_table_openclaw.json)
        In global mode: uses the global path via _data_dir()
        """
        try:
            # Use the ql_agent's own path (agent-specific) if available
            qtable_path = getattr(self.ql_agent, 'q_table_path', None)
            if qtable_path is None:
                qtable_path = _data_dir() / "q_table.json"
            elif isinstance(qtable_path, str):
                qtable_path = Path(qtable_path)

            if not qtable_path.exists():
                return  # Agent's Q-table file may not exist yet

            with open(qtable_path, 'r', encoding='utf-8') as f:
                qdata = json.load(f)
            qdata["q_table"] = self.ql_agent.q_table.tolist()
            with open(qtable_path, 'w', encoding='utf-8') as f:
                json.dump(qdata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DecisionCheckPoint] Failed to persist Q-table: {e}", file=_sys.stderr)

    def _append_rl_history(self, action: str, context: Any, outcome: str, reward: float, note: str) -> None:
        """
        Append a decision entry to rl_decision_history.json.

        In agent mode: uses ql_agent's path (agent-specific, e.g. data/rl_decision_history_openclaw.json)
        In global mode: uses the global path via _data_dir()
        This ensures consistency — both _append_rl_history() and ql_agent.add_experience()
        write to the same file.
        """
        try:
            context_str = json.dumps(context, ensure_ascii=False) if isinstance(context, dict) else str(context)
            wm_summary = self.working_memory.get_context_summary()
            full_ctx = f"{action} {context_str} [WM:{wm_summary}]"
            state_idx = _stable_hash(full_ctx, 100)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "context": context if isinstance(context, dict) else {"raw": str(context)},
                "action": action,
                "outcome": outcome,
                "reward": reward,
                "state": state_idx,
                "next_state": state_idx,
                "note": note,
                "source": "runtime_record",
                "agent_id": self._agent_id,  # tag with agent for audit
            }

            # Use per-agent path: rl_decision_history_{agent_id}.json
            if self.ql_agent is not None and hasattr(self.ql_agent, 'q_table_path'):
                history_path = Path(self.ql_agent.q_table_path).parent / f"rl_decision_history_{self._agent_id}.json"
            else:
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
            print(f"[DecisionCheckPoint] Failed to append RL history: {e}", file=_sys.stderr)


__all__ = [
    "DecisionCheckPoint",
    # Factory functions
    "create_for_agent",
    "get_current_dc",
    "set_current_agent",
    "get_agent_registry",
]
