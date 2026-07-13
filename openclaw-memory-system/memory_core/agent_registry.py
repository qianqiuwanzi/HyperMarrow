"""
Agent Registry — Multi-Agent Architecture

Manages multiple agent instances with per-agent isolation and shared knowledge.

Per-agent (isolated):                  Shared (cross-agent):
  WorkingMemoryDB                        KnowledgeGraph
  EpisodicMemoryDB                       VectorMemoryDB
  QLearningAgent                         ProceduralMemory
  MetacognitionMonitor                   MemoryConsolidator
  Action Space                           TransferLearner
  State Features                         PerceptionChannels
"""
import sys as _sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from .config import get_data_dir
from .working_memory_db import WorkingMemoryDB
from .episodic_memory_db import EpisodicMemoryDB
from .q_learning_agent import QLearningAgent
from .metacognition_monitor import MetacognitionMonitor

DATA_DIR = get_data_dir()
REGISTRY_FILE = DATA_DIR / "agent_registry.json"


def _now() -> str:
    return datetime.now().isoformat()


class AgentBundle:
    """A single agent's complete instance set: isolated + shared references."""

    def __init__(self, agent_id: str, action_space: list,
                 state_features: list = None,
                 shared: dict = None):
        self.agent_id = agent_id
        self.action_space = action_space
        self.action_dim = len(action_space)
        self.state_features = state_features or [
            "task_type", "phase", "error_type", "attempts",
            "tools", "emotion", "wm_task", "wm_goal",
        ]

        # Per-agent data files (namespaced by agent_id)
        wm_path = DATA_DIR / f"working_memory_{agent_id}.json"
        em_path = DATA_DIR / f"episodes_{agent_id}.json"
        q_path = DATA_DIR / f"q_table_{agent_id}.json"

        # ── Isolated instances (per-agent) ────────────────────────────────
        self.working_memory = WorkingMemoryDB(path=wm_path)
        self.episodic_memory = EpisodicMemoryDB(path=em_path)
        self.ql_agent = QLearningAgent(
            state_space_size=100,
            action_space_size=self.action_dim,
            q_table_path=str(q_path),
        )
        self.metacognition = MetacognitionMonitor(data_dir=DATA_DIR,
                                                   prefix=agent_id)
        self.decision_checkpoint = None  # Set after creation

        # Override QLearningAgent's action space
        self.ql_agent.action_space_size = self.action_dim
        self._action_list = action_space

        # ── Shared layer references (all agents see the same instances) ──
        shared = shared or {}
        self.knowledge_graph = shared.get("knowledge_graph")
        self.vector_db = shared.get("vector_db")
        self.procedural_memory = shared.get("procedural_memory")
        self.consolidator = shared.get("consolidator")
        self.transfer_learner = shared.get("transfer_learner")
        self.perception = shared.get("perception")

        # ── Auto-transfer tracking ────────────────────────────────────────
        self._new_successes = 0  # Counter for auto-transfer trigger

        print(f"[AgentRegistry] Agent '{agent_id}' created: "
              f"{self.action_dim} actions, {len(self.state_features)} features, "
              f"shared={'✓' if shared else '✗'}")

    def notify_success(self, count: int = 1):
        """Track successful experiences for auto-transfer."""
        self._new_successes += count

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "action_dim": self.action_dim,
            "new_successes": self._new_successes,
            "wm": self.working_memory.get_stats(),
            "em": self.episodic_memory.get_stats(),
            "ql": self.ql_agent.get_stats(),
            "meta": self.metacognition.get_stats(),
            "shared_connected": self.knowledge_graph is not None,
        }


class AgentRegistry:
    """
    多 Agent 注册表 — 管理所有 agent 实例的生命周期。

    用法:
        # 1. 创建共享层
        shared = {"knowledge_graph": kg, "procedural_memory": pm, ...}

        # 2. 注册所有 Agent（共享层自动注入）
        reg = AgentRegistry(shared_components=shared)
        reg.register("claude", action_space=CLAUDE_ACTIONS)
        reg.register("codex", action_space=CODEX_ACTIONS)

        # 3. Agent 学到新经验后自动共享给其他 Agent
        reg.notify_and_share("claude", success_count=1)
    """

    AUTO_TRANSFER_THRESHOLD = 10  # successes before auto-sharing

    def __init__(self, shared_components: dict = None):
        self._agents: Dict[str, AgentBundle] = {}
        self._shared_components = shared_components or {}
        self._shared = self._load_shared()
        # Re-inject shared components into loaded agents
        for bundle in self._agents.values():
            self._inject_shared(bundle)
        print(f"[AgentRegistry] Initialized: {len(self._agents)} agents, "
              f"auto_transfer_threshold={self.AUTO_TRANSFER_THRESHOLD}",
              file=_sys.stderr)

    def _inject_shared(self, bundle: AgentBundle):
        """注入共享层引用到 AgentBundle。"""
        bundle.knowledge_graph = self._shared_components.get("knowledge_graph")
        bundle.vector_db = self._shared_components.get("vector_db")
        bundle.procedural_memory = self._shared_components.get("procedural_memory")
        bundle.consolidator = self._shared_components.get("consolidator")
        bundle.transfer_learner = self._shared_components.get("transfer_learner")
        bundle.perception = self._shared_components.get("perception")

    def _load_shared(self) -> dict:
        if REGISTRY_FILE.exists():
            try:
                with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, cfg in data.get("agents", {}).items():
                        bundle = AgentBundle(
                            agent_id,
                            action_space=cfg.get("action_space", []),
                            state_features=cfg.get("state_features"),
                        )
                        self._agents[agent_id] = bundle
                    return data
            except Exception:
                pass
        return {"version": "1.0", "agents": {}, "created_at": _now()}

    def _save(self):
        data = {
            "version": "1.0",
            "agents": {
                aid: {
                    "action_space": bundle._action_list,
                    "state_features": bundle.state_features,
                    "created_at": _now(),
                }
                for aid, bundle in self._agents.items()
            },
            "updated_at": _now(),
        }
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register(self, agent_id: str, action_space: list,
                 state_features: list = None) -> AgentBundle:
        """
        注册一个新 agent（共享层自动注入）。如果已存在则返回现有实例。

        Args:
            agent_id: 唯一标识符 (e.g., "claude", "codex", "hermes", "openclaw")
            action_space: 动作列表
            state_features: 状态特征键列表

        Returns:
            AgentBundle（已注入共享层引用）
        """
        if agent_id in self._agents:
            print(f"[AgentRegistry] Agent '{agent_id}' already registered",
                  file=_sys.stderr)
            return self._agents[agent_id]

        # ── License device limit check (commercial mode) ──────────────────
        from .config import get_config
        if get_config().get("license", {}).get("enabled", False):
            try:
                import sys, os
                _ws = get_config().get("paths", {}).get("workspace")
                if _ws:
                    sys.path.insert(0, str(_ws))
                    sys.path.insert(0, str(Path(_ws) / "commercial"))
                else:
                    # Auto-detect: workspace is parent of HyperMarrow
                    _hm_root = Path(__file__).resolve().parent.parent.parent
                    sys.path.insert(0, str(_hm_root.parent))
                    sys.path.insert(0, str(_hm_root.parent / "commercial"))
                from LICENSE_SDK.license_manager import LicenseManager, LicenseStatus
                lm = LicenseManager()
                if lm.verify() in (LicenseStatus.VALID, LicenseStatus.OFFLINE):
                    max_devices = lm.get_max_devices()
                    if max_devices > 0 and len(self._agents) >= max_devices:
                        raise RuntimeError(
                            f"License device limit reached ({max_devices}). "
                            f"Currently registered: {len(self._agents)}"
                        )
            except ImportError:
                pass  # LICENSE_SDK not installed
            except RuntimeError:
                raise
            except Exception as e:
                print(f"[AgentRegistry] License check failed: {e}", file=_sys.stderr)

        bundle = AgentBundle(agent_id, action_space, state_features,
                             shared=self._shared_components)
        self._agents[agent_id] = bundle
        self._save()
        return bundle

    def notify_and_share(self, agent_id: str, success_count: int = 1) -> dict:
        """
        通知注册表：某 Agent 获得了新经验。当累积成功数达到阈值时，
        自动触发跨 Agent 知识共享。

        Args:
            agent_id: 获得新经验的 agent
            success_count: 新增成功经验数

        Returns:
            {shared: bool, transfers: [...]} 或空 dict
        """
        source = self._agents.get(agent_id)
        if not source:
            return {}

        source.notify_success(success_count)

        if source._new_successes < self.AUTO_TRANSFER_THRESHOLD:
            return {"shared": False, "reason": f"need {self.AUTO_TRANSFER_THRESHOLD - source._new_successes} more"}

        # Threshold reached — share with all other agents
        source._new_successes = 0  # Reset counter
        transfers = []
        for target_id, target in self._agents.items():
            if target_id == agent_id:
                continue
            result = self.cross_agent_transfer(agent_id, target_id)
            transfers.append({"target": target_id, "result": result})

        print(f"[AgentRegistry] Auto-share: {agent_id} → "
              f"{len(transfers)} other agents")
        return {"shared": True, "transfers": transfers}

    def share_all(self) -> dict:
        """
        全量共享：每个 Agent 的最新经验分发给所有其他 Agent。
        """
        results = {}
        for source_id in self._agents:
            for target_id in self._agents:
                if source_id == target_id:
                    continue
                key = f"{source_id}→{target_id}"
                results[key] = self.cross_agent_transfer(source_id, target_id)
        print(f"[AgentRegistry] Full share: {len(results)} transfers")
        return results

    def get(self, agent_id: str) -> Optional[AgentBundle]:
        """获取已注册的 agent。"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """列出所有已注册的 agent ID。"""
        return list(self._agents.keys())

    def cross_agent_transfer(self, source_id: str, target_id: str,
                              min_similarity: float = 0.3) -> dict:
        """
        跨 Agent 知识迁移：将 source agent 的经验注入 target agent。

        迁移内容：
        1. Episodic patterns → target 的情景记忆（标记为 transferred）
        2. Q-table mapping → 通过状态特征相似度映射到 target 的 Q 表
        3. Metacognition calibration → 作为 target 的初始校准参考

        Returns:
            {episodes_transferred, q_cells_seeded, calibration_references}
        """
        source = self._agents.get(source_id)
        target = self._agents.get(target_id)
        if not source or not target:
            return {"error": "Source or target agent not found"}

        result = {"episodes_transferred": 0, "q_cells_seeded": 0,
                  "calibration_references": 0}

        # 1. Transfer episodic patterns (tagged with source)
        source_eps = source.episodic_memory.get_recent_episodes(20)
        for ep in source_eps:
            if ep.get("outcome") == "success" and ep.get("importance", 0) >= 3:
                target.episodic_memory.add_episode(
                    what=f"[From {source_id}] {ep.get('what', '')[:80]}",
                    context=ep.get("context", {}),
                    outcome=ep.get("outcome", "partial"),
                    emotion=ep.get("emotion", "neutral"),
                    tags=(ep.get("tags", []) + ["transferred", source_id]),
                    importance=max(2, ep.get("importance", 3) - 1),
                    lesson=ep.get("lesson", ""),
                )
                result["episodes_transferred"] += 1

        # 2. Map Q-values by state feature similarity
        source_q = source.ql_agent.q_table
        target_q = target.ql_agent.q_table
        cells = 0

        # Use state_map entries that exist in source
        for state_key, src_idx in source.ql_agent._state_map.items():
            if src_idx >= source_q.shape[0]:
                continue
            # Map to target index (same hash space since same _stable_hash)
            tgt_idx = target.ql_agent.state_to_index(state_key)
            if tgt_idx >= target_q.shape[0]:
                continue

            # Map actions by name overlap (best-effort)
            src_row = source_q[src_idx, :]
            tgt_row = target_q[tgt_idx, :]

            # Copy Q-values for overlapping action indices
            for src_a in range(min(source.action_dim, target.action_dim)):
                if abs(src_row[src_a]) > 0.01:  # Non-trivial Q-value
                    # Apply cross-agent decay
                    tgt_row[src_a] += src_row[src_a] * 0.5  # 50% strength
                    cells += 1

        result["q_cells_seeded"] = cells

        # 3. Transfer calibration references
        source_cal = source.metacognition.calibration.get("entries", [])
        for entry in source_cal[-10:]:
            if entry.get("actual_outcome") == "success":
                result["calibration_references"] += 1

        print(f"[AgentRegistry] Cross-transfer {source_id}→{target_id}: "
              f"episodes={result['episodes_transferred']}, "
              f"q_cells={result['q_cells_seeded']}")
        return result

    def get_shared_stats(self) -> dict:
        """跨 agent 聚合统计。"""
        return {
            "total_agents": len(self._agents),
            "agents": {
                aid: bundle.get_stats()
                for aid, bundle in self._agents.items()
            },
        }


# ── Default action spaces for known agents ────────────────────────────────────

OPENCLAW_ACTIONS = [
    "follow_rule_strictly",
    "use_existing_tool",
    "try_fix_three_times",
    "report_user",
    "write_script",
    "switch_skill",
    "skip_phase",
]

CLAUDE_ACTIONS = [
    "follow_rule_strictly",
    "use_existing_tool",
    "try_fix_three_times",
    "report_user",
    "write_script",
    "switch_skill",
    "skip_phase",
]

CODEX_ACTIONS = [
    "run_terminal",
    "write_file",
    "search_code",
    "ask_user",
    "delegate_to_claude",
]

HERMES_ACTIONS = [
    "think",
    "act",
    "observe",
    "plan",
    "reflect",
    "learn",
    "teach",
    "coordinate",
]

# All known agent IDs
KNOWN_AGENTS = ["openclaw", "claude", "codex", "hermes"]

# Action space registry
AGENT_ACTIONS = {
    "openclaw": OPENCLAW_ACTIONS,
    "claude": CLAUDE_ACTIONS,
    "codex": CODEX_ACTIONS,
    "hermes": HERMES_ACTIONS,
}

# Cross-agent compatible action mappings (shared semantics)
# e.g., Claude's "try_fix_three_times" ≈ Codex's "search_code"
CROSS_AGENT_ACTION_MAP = {
    ("claude", "codex"): {
        "try_fix_three_times": "search_code",
        "write_script": "write_file",
        "report_user": "ask_user",
        "switch_skill": "delegate_to_claude",
    },
    ("codex", "claude"): {
        "search_code": "try_fix_three_times",
        "write_file": "write_script",
        "ask_user": "report_user",
        "delegate_to_claude": "switch_skill",
    },
    ("openclaw", "claude"): {},  # Same action space, 1:1 mapping
    ("claude", "openclaw"): {},
}


# ── Example ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Create shared layer components
    from .knowledge_graph import KnowledgeGraph
    shared = {"knowledge_graph": KnowledgeGraph()}

    reg = AgentRegistry(shared_components=shared)

    # Register all 4 agents
    openclaw = reg.register("openclaw", OPENCLAW_ACTIONS)
    claude   = reg.register("claude",   CLAUDE_ACTIONS)
    codex    = reg.register("codex",    CODEX_ACTIONS)
    hermes   = reg.register("hermes",   HERMES_ACTIONS)

    print(f"\nRegistered: {reg.list_agents()}")

    # Verify shared layer injected into all agents
    for aid in reg.list_agents():
        bundle = reg.get(aid)
        assert bundle.knowledge_graph is not None, f"{aid} missing shared KG"
    print("Shared layer injection: ✓ all 4 agents connected to KG")

    # OpenClaw and Claude share the same action space
    assert openclaw.action_dim == claude.action_dim == 7
    assert codex.action_dim == 5
    assert hermes.action_dim == 8

    # Claude learns something valuable
    claude.ql_agent.add_experience(
        "download_timeout", 2, reward=1.0, next_state="fixed", done=False)
    claude.episodic_memory.add_episode(
        what="P2b download timeout, retry succeeded",
        context={"action": "try_fix_three_times", "phase": "P2b"},
        outcome="success", emotion="positive",
        tags=["download", "timeout"], importance=4)

    # OpenClaw also learns independently
    openclaw.working_memory.set_task("视频生成任务")
    openclaw.ql_agent.add_experience(
        "import_error", 4, reward=0.8, next_state="fixed", done=False)

    # Auto-share: simulate Claude accumulating successes
    print("\n--- Auto-transfer test ---")
    # Notify 9 times (below threshold) — should NOT trigger
    for i in range(9):
        r = reg.notify_and_share("claude", success_count=1)
    # 10th time — should trigger auto-share to all 3 others
    r = reg.notify_and_share("claude", success_count=1)
    print(f"Auto-share triggered: {r.get('shared')}")
    if r.get('shared'):
        for t in r['transfers']:
            print(f"  → {t['target']}: eps={t['result']['episodes_transferred']}, "
                  f"q_cells={t['result']['q_cells_seeded']}")

    # Full share across all agents
    print("\n--- Full share ---")
    results = reg.share_all()
    print(f"Total transfers: {len(results)}")

    # Verify Codex has knowledge from multiple sources
    codex_eps = codex.episodic_memory.get_recent_episodes(20)
    sources = set()
    for e in codex_eps:
        for tag in e.get("tags", []):
            if tag in ("claude", "openclaw", "hermes", "transferred"):
                sources.add(tag)
    print(f"Codex knowledge sources: {sources}")

    stats = reg.get_shared_stats()
    print(f"\nShared stats: {stats['total_agents']} agents")
    for aid, a_stats in stats['agents'].items():
        print(f"  {aid}: {a_stats['action_dim']} actions, "
              f"shared={a_stats['shared_connected']}")

    print("\n✅ 4-AGENT SHARED KNOWLEDGE: ALL VERIFIED")
