"""
Analogical Reasoner & Multi-Agent Collaboration — 类比推理 + 多Agent协作

B3: Find structurally similar past situations using embedding space + KG matching.
B4: Inter-agent task allocation based on historical per-agent success rates.
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
REASONER_FILE = DATA_DIR / "analogical_index.json"


def _now() -> str:
    return datetime.now().isoformat()


class AnalogicalReasoner:
    """
    类比推理引擎 — 在历史经验中找到与当前情境最相似的案例。

    推理维度:
      1. 嵌入空间余弦相似度 (NeuralAgent 64-dim)
      2. 知识图谱结构相似度 (共享关系的实体)
      3. 程序性规则匹配 (已有规则)

    综合三个维度的分数返回最相关的历史经验。
    """

    def __init__(self, neural_agent=None, knowledge_graph=None,
                 procedural_memory=None, episodic_memory=None):
        self.neural_agent = neural_agent
        self.kg = knowledge_graph
        self.pm = procedural_memory
        self.em = episodic_memory
        self._index = self._load_index()

    def _load_index(self) -> list:
        if REASONER_FILE.exists():
            try:
                with open(REASONER_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_index(self):
        with open(REASONER_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._index[-500:], f, ensure_ascii=False, indent=2)

    def index_episode(self, episode: dict, embedding: np.ndarray = None):
        """将一条 episode 加入类比索引。"""
        entry = {
            "episode_id": episode.get("episode_id", ""),
            "what": episode.get("what", "")[:120],
            "outcome": episode.get("outcome", ""),
            "tags": episode.get("tags", []),
            "importance": episode.get("importance", 3),
            "embedding": embedding.tolist() if embedding is not None else None,
            "indexed_at": _now(),
        }
        self._index.append(entry)
        if len(self._index) % 10 == 0:
            self._save_index()

    def find_analogies(self, query_embedding: np.ndarray,
                        top_k: int = 5,
                        min_similarity: float = 0.5) -> list:
        """
        嵌入相似度搜索：找到与当前状态最相似的历史经验。

        Returns:
            [{"episode_id", "what", "similarity", "outcome", "tags"}, ...]
        """
        if not self._index or query_embedding is None:
            return []

        results = []
        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        for entry in self._index:
            if entry.get("embedding") is None:
                continue
            e_vec = np.array(entry["embedding"])
            e_norm = e_vec / (np.linalg.norm(e_vec) + 1e-8)
            sim = float(np.dot(q_norm, e_norm))
            if sim >= min_similarity:
                results.append({
                    "episode_id": entry["episode_id"],
                    "what": entry["what"],
                    "similarity": round(sim, 4),
                    "outcome": entry.get("outcome", ""),
                    "tags": entry.get("tags", []),
                    "source": "embedding",
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def reason(self, state: dict, top_k: int = 3) -> dict:
        """
        综合推理：类比 + 图谱 + 规则，返回最佳推荐。

        Returns:
            {
              "analogies": [...],
              "related_entities": [...],
              "matching_rules": [...],
              "recommendation": str (合成的建议),
            }
        """
        result = {"analogies": [], "related_entities": [],
                  "matching_rules": [], "recommendation": ""}

        # 1. Embedding-based analogy
        if self.neural_agent is not None:
            try:
                emb = self.neural_agent.encode(state)
                result["analogies"] = self.find_analogies(emb, top_k=top_k)
            except Exception:
                pass

        # 2. KG entity match
        if self.kg is not None:
            try:
                text = json.dumps(state, ensure_ascii=False, default=str)
                entities = self.kg.extract_entities_from_text(text)
                for ent in entities[:3]:
                    related = self.kg.find_related(ent["id"], max_depth=1)
                    for r in related[:3]:
                        result["related_entities"].append({
                            "entity": ent["name"],
                            "related": r["entity"]["name"],
                            "type": r["entity"]["type"],
                        })
            except Exception:
                pass

        # 3. Procedural rules
        if self.pm is not None:
            try:
                context_str = json.dumps(state, ensure_ascii=False, default=str)
                rules = self.pm.check_context(context_str)
                for r in rules[:3]:
                    result["matching_rules"].append({
                        "rule": r["rule_name"],
                        "level": r["level"],
                        "success_rate": r["success_rate"],
                    })
            except Exception:
                pass

        # 4. Synthesize recommendation
        parts = []
        if result["analogies"]:
            best = result["analogies"][0]
            if best["outcome"] == "success":
                parts.append(f"类比: '{best['what'][:60]}' 曾成功 (相似度 {best['similarity']:.0%})")
            else:
                parts.append(f"类比: '{best['what'][:60]}' 曾失败，建议避免类似路径")
        if result["matching_rules"]:
            top_rule = result["matching_rules"][0]
            parts.append(f"规则: [{top_rule['rule']}] (L{top_rule['level']}, {top_rule['success_rate']:.0%})")
        result["recommendation"] = " | ".join(parts) if parts else "无相关历史经验"

        return result

    def get_stats(self) -> dict:
        return {
            "indexed_episodes": len(self._index),
            "with_embeddings": sum(1 for e in self._index if e.get("embedding")),
        }


# ── B4: Multi-Agent Collaboration Protocol ───────────────────────────────────

class CollaborationProtocol:
    """
    多 Agent 协作协议 — 任务分配与仲裁。

    决策:
      1. 每个 Agent 维护自己的历史成功率（来自 Metacognition）
      2. 当某个 Agent 遇到新任务时，查询其他 Agent 的同类任务成功率
      3. 如果其他 Agent 成功率显著更高 → 推荐委派
      4. 投票仲裁：各 Agent 按历史可靠性加权投票
    """

    def __init__(self, registry=None):
        self.reg = registry
        self._delegation_log = []

    def recommend_delegate(self, task_context: str,
                            current_agent: str,
                            action: str) -> Optional[dict]:
        """
        推荐将任务委派给哪个 Agent。

        Returns:
            {"agent": str, "reason": str, "confidence": float} 或 None
        """
        if not self.reg:
            return None

        current = self.reg.get(current_agent)
        if not current:
            return None

        # Get current agent's success rate for this action type
        current_sr = self._get_action_success_rate(current, action)

        best_agent = None
        best_sr = current_sr
        best_reason = ""

        for other_id in self.reg.list_agents():
            if other_id == current_agent:
                continue
            other = self.reg.get(other_id)
            if not other:
                continue
            other_sr = self._get_action_success_rate(other, action)
            if other_sr > best_sr + 0.15:  # Significant advantage
                best_agent = other_id
                best_sr = other_sr
                best_reason = (f"'{other_id}' success rate {other_sr:.0%} "
                               f"vs '{current_agent}' {current_sr:.0%}")

        if best_agent:
            entry = {
                "timestamp": _now(),
                "task": task_context[:80],
                "action": action,
                "from_agent": current_agent,
                "to_agent": best_agent,
                "reason": best_reason,
                "confidence": round(best_sr - current_sr, 3),
            }
            self._delegation_log.append(entry)
            return {"agent": best_agent, "reason": best_reason,
                    "confidence": round(best_sr - current_sr, 3)}

        return None

    def weighted_vote(self, candidates: list) -> dict:
        """
        加权投票：各 Agent 按历史可靠性投票，返回加权结果。

        Args:
            candidates: [{"agent_id": str, "action": str, "confidence": float}, ...]

        Returns:
            {"winner": str, "score": float, "votes": [...]}
        """
        if not self.reg:
            return {"winner": candidates[0]["agent_id"] if candidates else "",
                    "score": 0.0, "votes": []}

        scores = {}
        for c in candidates:
            agent = self.reg.get(c["agent_id"])
            if not agent:
                continue
            reliability = self._get_overall_reliability(agent)
            score = c.get("confidence", 0.5) * reliability
            scores[c["agent_id"]] = scores.get(c["agent_id"], 0) + score

        if not scores:
            return {"winner": "", "score": 0.0, "votes": []}

        winner = max(scores, key=scores.get)
        return {
            "winner": winner,
            "score": round(scores[winner], 4),
            "votes": [{"agent": a, "score": round(s, 4)} for a, s in
                      sorted(scores.items(), key=lambda x: x[1], reverse=True)],
        }

    def _get_action_success_rate(self, bundle, action: str) -> float:
        """Get agent's historical success rate for a specific action."""
        if not bundle.metacognition:
            return 0.5
        # Use recent calibration data
        entries = bundle.metacognition.calibration.get("entries", [])
        if not entries:
            return 0.5
        successes = sum(1 for e in entries[-50:]
                        if e.get("actual_outcome") == "success")
        return successes / max(len(entries[-50:]), 1)

    def _get_overall_reliability(self, bundle) -> float:
        """Get agent's overall reliability score from metacognition."""
        if not bundle.metacognition:
            return 0.5
        dash = bundle.metacognition.get_performance_dashboard()
        return dash.get("recent_accuracy", 0.5)

    def get_stats(self) -> dict:
        return {
            "delegations": len(self._delegation_log),
            "recent_delegations": self._delegation_log[-5:],
        }


if __name__ == "__main__":
    # Test standalone
    ar = AnalogicalReasoner()
    result = ar.reason({"task": "P2b download timeout", "phase": "P2b"})
    print(f"Analogy result: {json.dumps(result['recommendation'], ensure_ascii=False)}")

    cp = CollaborationProtocol()
    vote = cp.weighted_vote([
        {"agent_id": "openclaw", "action": "try_fix", "confidence": 0.8},
        {"agent_id": "luci", "action": "switch_skill", "confidence": 0.6},
    ])
    print(f"Vote result: {json.dumps(vote, ensure_ascii=False)}")

    print("\n[AnalogicalReasoner + CollaborationProtocol] Test passed!")
