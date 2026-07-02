"""
Transfer Learner — 迁移学习 (冷启动复用)

Fingerprints projects, finds similar historical projects, and seeds new Q-tables
from weighted experience transfer. Integrates with KnowledgeGraph and EpisodicMemoryDB.
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
PROFILES_FILE = DATA_DIR / "transfer_profiles.json"

# Predefined task categories for one-hot encoding
_TASK_CATEGORIES = [
    "video_generation", "code_review", "research",
    "memory_management", "decision_making", "debugging",
    "data_processing", "deployment", "testing", "unknown",
]

# Tool vocabulary for binary feature vectors
_TOOL_VOCABULARY = [
    "daily-video-factory", "cover-generator", "deep-research",
    "html-ppt-to-video", "chromadb", "python", "git",
    "sentence-transformers", "numpy",
]

# Error pattern vocabulary
_ERROR_VOCABULARY = [
    "import_error", "timeout", "download_stuck",
    "format_unsupported", "script_not_found", "network_error",
    "permission_denied", "out_of_memory",
]


def _now() -> str:
    return datetime.now().isoformat()


def _make_feature_vector(task_type: str, tools: list, error_patterns: list) -> np.ndarray:
    """Build a normalized feature vector from project attributes."""
    features = []

    # Task type one-hot
    task_lower = task_type.lower().replace(" ", "_")
    for cat in _TASK_CATEGORIES:
        features.append(1.0 if cat in task_lower else 0.0)

    # Tool presence binary
    tools_lower = [t.lower().replace(" ", "_") for t in tools]
    for tool in _TOOL_VOCABULARY:
        features.append(1.0 if any(tool in t for t in tools_lower) else 0.0)

    # Error pattern TF
    errors_lower = [e.lower().replace(" ", "_") for e in error_patterns]
    for err in _ERROR_VOCABULARY:
        features.append(float(sum(1 for e in errors_lower if err in e)))

    vec = np.array(features, dtype=float)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


class TransferLearner:
    """
    迁移学习 — 冷启动新项目时复用过往经验。

    核心流程：
      fingerprint → find_similar → weighted_q_init → inject into agent
    """

    def __init__(self, episodic_memory=None, knowledge_graph=None):
        self.em = episodic_memory
        self.kg = knowledge_graph
        self.data = self._load_or_init()
        self.feature_dim = len(_TASK_CATEGORIES) + len(_TOOL_VOCABULARY) + len(_ERROR_VOCABULARY)

    # ── Persistence ────────────────────────────────────────────────────────

    def _load_or_init(self) -> dict:
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("project_profiles", {})
                        data.setdefault("transfer_log", [])
                        data.setdefault("feature_dim", self.feature_dim if hasattr(self, 'feature_dim') else 27)
                        return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[TransferLearner] Load failed, using defaults: {e}")
        return {
            "version": "1.0",
            "project_profiles": {},
            "transfer_log": [],
            "feature_dim": self.feature_dim if hasattr(self, 'feature_dim') else 27,
            "updated_at": _now(),
        }

    def _save(self):
        self.data["updated_at"] = _now()
        with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── Project Fingerprinting ─────────────────────────────────────────────

    def extract_project_fingerprint(self, task_type: str,
                                     tools: list,
                                     error_patterns: list,
                                     context_tags: list = None) -> dict:
        """
        从项目信息中提取指纹。

        Returns:
            {task_type, tools, error_patterns, signature_vector, feature_dim}
        """
        vec = _make_feature_vector(task_type, tools, error_patterns)
        return {
            "task_type": task_type,
            "tools": tools,
            "error_patterns": error_patterns,
            "context_tags": context_tags or [],
            "signature_vector": vec.tolist(),
            "feature_dim": len(vec),
        }

    # ── Similarity Matching ────────────────────────────────────────────────

    def cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """余弦相似度。"""
        dot = np.dot(v1, v2)
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(dot / (n1 * n2))

    def find_similar_projects(self, fingerprint: dict,
                               top_k: int = 5,
                               min_similarity: float = 0.3) -> list:
        """
        查找与当前项目相似的历史项目。

        Steps:
        1. 遍历所有已存储的项目档案
        2. 计算余弦相似度
        3. 排序返回 top_k

        Returns:
            [{project_id, similarity, profile, ...}, ...]
        """
        if not self.data["project_profiles"]:
            return []

        target_vec = np.array(fingerprint["signature_vector"])
        scored = []

        for pid, profile in self.data["project_profiles"].items():
            # signature_vector is inside the fingerprint dict
            fp = profile.get("fingerprint", {})
            stored_vec = np.array(fp.get("signature_vector", []))
            if len(stored_vec) != len(target_vec):
                continue
            sim = self.cosine_similarity(target_vec, stored_vec)
            if sim >= min_similarity:
                scored.append({
                    "project_id": pid,
                    "similarity": round(sim, 4),
                    "profile": profile,
                })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    # ── Q-Value Initialization ─────────────────────────────────────────────

    def weighted_q_initialization(self,
                                   similar_projects: list,
                                   target_q_table: np.ndarray,
                                   decay_factor: float = 0.5) -> np.ndarray:
        """
        从相似项目加权平均初始化 Q 表。

        Q_new[s,a] = Σ(sim_i * decay^rank_i * Q_i[s,a]) / Σ(sim_i * decay^rank_i)

        Args:
            similar_projects: find_similar_projects() 的结果
            target_q_table: 待填充的 Q 表
            decay_factor: 相似度权重衰减因子

        Returns:
            (filled_q_table, cells_initialized)
        """
        if not similar_projects:
            return target_q_table

        weighted_sum = np.zeros_like(target_q_table)
        weight_sum = 0.0
        initialized = 0

        for rank, proj in enumerate(similar_projects):
            sim = proj["similarity"]
            q_snapshot = proj["profile"].get("q_table_snapshot")
            if q_snapshot is None:
                continue

            q_arr = np.array(q_snapshot)
            if q_arr.shape != target_q_table.shape:
                continue

            weight = sim * (decay_factor ** rank)
            weighted_sum += weight * q_arr
            weight_sum += weight
            initialized += 1

        if weight_sum > 0:
            target_q_table = weighted_sum / weight_sum

        return target_q_table

    def init_new_project(self, task_type: str, tools: list,
                          error_patterns: list,
                          context_tags: list = None,
                          agent=None) -> dict:
        """
        一键初始化新项目：指纹 → 相似搜索 → Q 表填充。

        Args:
            task_type, tools, error_patterns: 项目描述
            agent: QLearningAgent 实例 (可选)，若提供则直接写入其 q_table

        Returns:
            {fingerprint, similar_projects, q_values_initialized, top_actions}
        """
        fp = self.extract_project_fingerprint(task_type, tools, error_patterns, context_tags)
        similar = self.find_similar_projects(fp)

        result = {
            "fingerprint": fp,
            "similar_projects": similar,
            "q_values_initialized": 0,
            "top_actions": [],
        }

        if similar and agent is not None:
            agent.q_table = self.weighted_q_initialization(
                similar, agent.q_table, decay_factor=0.5,
            )
            result["q_values_initialized"] = int(np.count_nonzero(agent.q_table))

            # Top actions by average Q-value
            avg_q = agent.q_table.mean(axis=0)
            top_indices = np.argsort(avg_q)[::-1][:3]
            from .q_learning_agent import ACTIONS
            result["top_actions"] = [
                (ACTIONS[i], round(float(avg_q[i]), 4)) for i in top_indices
            ]

        return result

    def store_project_profile(self, project_name: str,
                                fingerprint: dict,
                                q_table: np.ndarray = None,
                                summary: str = "") -> str:
        """
        将项目存档，后续可用于迁移。

        Returns:
            project_id (存储于 KnowledgeGraph 的 entity_id)
        """
        import uuid
        pid = str(uuid.uuid4())[:8]

        profile = {
            "project_name": project_name,
            "fingerprint": fingerprint,
            "q_table_snapshot": q_table.tolist() if q_table is not None else None,
            "episode_count": 0,
            "summary": summary,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.data["project_profiles"][pid] = profile
        self._save()

        # Also register in KnowledgeGraph
        if self.kg is not None:
            try:
                ent = self.kg.add_entity(project_name, "project",
                                         {"project_id": pid, "summary": summary})
                pid = ent["id"]
            except Exception as e:
                print(f"[TransferLearner] KG entity registration failed (non-critical): {e}")

        print(f"[TransferLearner] Project '{project_name}' stored (id={pid})")
        return pid

    def log_transfer(self, source_project: str, target_name: str,
                      similarity: float, cells: int):
        """记录一次迁移操作。"""
        self.data["transfer_log"].append({
            "timestamp": _now(),
            "source_project": source_project,
            "target_project": target_name,
            "similarity": round(similarity, 4),
            "cells_initialized": cells,
        })
        self._save()

    def get_stats(self) -> dict:
        return {
            "total_profiles": len(self.data["project_profiles"]),
            "total_transfers": len(self.data["transfer_log"]),
            "feature_dim": self.data.get("feature_dim", self.feature_dim),
            "recent_transfers": self.data["transfer_log"][-5:],
        }


if __name__ == "__main__":
    tl = TransferLearner()

    # Test fingerprinting
    fp = tl.extract_project_fingerprint(
        task_type="video_generation",
        tools=["daily-video-factory", "cover-generator"],
        error_patterns=["import_error", "timeout"],
    )
    print(f"Fingerprint dim: {len(fp['signature_vector'])}")

    # Test with a dummy profile
    import numpy as np
    dummy_q = np.random.randn(100, 7) * 0.1
    pid = tl.store_project_profile(
        "test-video-project",
        fp,
        q_table=dummy_q,
        summary="Test project for transfer",
    )

    # Find similar
    similar = tl.find_similar_projects(fp)
    print(f"Similar projects: {len(similar)}")

    # Test init_new_project
    from .q_learning_agent import QLearningAgent
    agent = QLearningAgent(state_space_size=100, action_space_size=7)
    result = tl.init_new_project(
        "video_generation", ["daily-video-factory"], ["timeout"],
        agent=agent,
    )
    print(f"Q-values initialized: {result['q_values_initialized']}")
    if result["top_actions"]:
        print(f"Top actions: {result['top_actions']}")

    stats = tl.get_stats()
    print(f"Stats: {stats['total_profiles']} profiles, "
          f"{stats['total_transfers']} transfers")

    print("\n[TransferLearner] Test passed!")
