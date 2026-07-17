"""
Episodic Memory — P3 Foundational Memory Type.

Structured memory records with {what, when, context, outcome, emotion, lesson}.
API: add_episode(), get_recent_episodes(), search_episodes(), get_outcome_stats()
"""
import json
import sys as _sys
import uuid
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from .config import get_data_dir

DATA_DIR = get_data_dir()
EPISODES_FILE = DATA_DIR / "episodes.json"

# Optional KnowledgeGraph hook for entity extraction
_kg_instance = None


def set_knowledge_graph(kg):
    """Register a KnowledgeGraph instance for automatic entity extraction."""
    global _kg_instance
    _kg_instance = kg


class EpisodicMemoryDB:
    """
    情景记忆 — 结构化记忆单元。

    相比纯文本 chunk，情景记忆有以下字段：
      what       — 事件本身（第一人称叙述）
      when       — 发生时间（ISO timestamp）
      context    — 触发这件事的上下文（dict）
      outcome    — 结果（success / failure / partial）
      emotion    — 情绪反应（positive / neutral / negative / mixed）
      lesson     — 从中学到的教训（可选）
      importance — 重要性 1-5

    用途：
      - 复盘（"上次做这个是什么结果？"）
      - 情绪追踪（negative 事件过多则预警）
      - 经验提取（lesson 字段）
    """

    EMOTION_VALUES   = ["positive", "neutral", "negative", "mixed"]
    OUTCOME_VALUES   = ["success", "failure", "partial"]
    IMPORTANCE_RANGE = (1, 5)

    def __init__(self, path=None, auto_clear=False):
        """
        Args:
            path: Path to episodes JSON file
            auto_clear: If True, delete existing file and start fresh
        """
        self.path = Path(path) if path else EPISODES_FILE
        if auto_clear and self.path.exists():
            self.path.unlink()
        self.data = self._load()
        print(f"[EpisodicMemory] Loaded {len(self.data)} episodes", file=_sys.stderr)

    def _load(self) -> list:
        """Load episodes from JSON. Always uses dict wrapper format."""
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and "episodes" in raw:
                    return raw.get("episodes", [])
                elif isinstance(raw, list):
                    # Migrate old list format on load
                    print("[EpisodicMemory] Migrating old list format to dict wrapper")
                    return raw
            except (json.JSONDecodeError, OSError) as e:
                print(f"[EpisodicMemory] Load failed, using defaults: {e}")
        return []

    def _save(self):
        # Preserve original created_at; only update updated_at
        old_wrapper = self._load_raw()
        created = old_wrapper.get("created_at") if isinstance(old_wrapper, dict) else None
        wrapper = {
            "version": "1.0",
            "episodes": self.data,
            "created_at": created or datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(wrapper, f, ensure_ascii=False, indent=2)

    def _load_raw(self) -> dict:
        """Load the raw wrapper dict without parsing into self.data."""
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        return raw
            except (json.JSONDecodeError, OSError) as e:
                print(f"[EpisodicMemory] Raw load failed: {e}")
        return {}

    # ── Core API ──────────────────────────────────────────────────────────────

    def add_episode(
        self,
        what: str,
        context: dict = None,
        outcome: str = "partial",
        emotion: str = "neutral",
        tags: list = None,
        importance: int = 3,
        lesson: str = "",
        duration_seconds: float = 0.0,
        linked_memory_ids: list = None,
        when: str = None,
    ) -> dict:
        """
        添加一条情景记忆。

        Args:
            what:       事件描述（必填，简洁）
            context:    上下文 dict（可选）
            outcome:    success | failure | partial (default: partial)
            emotion:    positive | neutral | negative | mixed (default: neutral)
            tags:       标签列表 (default: [])
            importance: 1-5 (default: 3)
            lesson:     学到的教训 (default: "")
            duration_seconds: 持续时间秒 (default: 0.0)
            linked_memory_ids: 关联向量记忆 ID (default: [])
            when:       ISO timestamp (default: now)

        Returns:
            新创建的 episode dict (包含 episode_id)
        """
        if outcome not in self.OUTCOME_VALUES:
            outcome = "partial"
        if emotion not in self.EMOTION_VALUES:
            emotion = "neutral"
        importance = max(1, min(5, int(importance)))

        episode = {
            "episode_id": str(uuid.uuid4())[:8],
            "what": what,
            "when": when or datetime.now().isoformat(),
            "context": context or {},
            "outcome": outcome,
            "emotion": emotion,
            "tags": tags or [],
            "importance": importance,
            "lesson": lesson,
            "duration_seconds": duration_seconds,
            "linked_memory_ids": linked_memory_ids or [],
            "created_at": datetime.now().isoformat(),
        }

        # Auto-inject source annotation (V2: GBrain-style [Source: ...])
        if "_source" not in episode:
            episode["_source"] = {
                "agent": getattr(self, '_agent_id', "unknown"),
                "channel": getattr(self, '_channel', "internal"),
                "captured_at": datetime.now().isoformat(),
            }

        self.data.append(episode)
        # Trim old episodes to prevent unbounded memory growth
        if len(self.data) > 500:
            self.data = sorted(self.data, key=lambda e: e.get('importance', 0))
            self.data = self.data[-300:]
        self._save()
        print(f"[EpisodicMemory] [{episode['episode_id']}] {outcome}/{emotion}: {what[:50]}")

        # Auto-extract entities into KnowledgeGraph if registered
        if _kg_instance is not None:
            try:
                _kg_instance.extract_episode_entities(episode)
            except Exception as e:
                print(f"[EpisodicMemory] KG extraction failed (non-critical): {e}")

        return episode

    def get_recent_episodes(self, n: int = 10, emotion_filter: str = None) -> list:
        """
        获取最近 N 条情景记忆。

        Args:
            n:             返回数量上限
            emotion_filter: 可选，筛选特定情绪

        Returns:
            list of episodes (按时间倒序)
        """
        eps = self.data[:]
        if emotion_filter:
            eps = [e for e in eps if e.get("emotion") == emotion_filter]
        eps.sort(key=lambda x: x.get("when", ""), reverse=True)
        return eps[:n]

    def set_embedder(self, model):
        """
        设置语义嵌入模型（复用 P2 VectorMemoryDB 的 SentenceTransformer）。

        Args:
            model: SentenceTransformer 实例或任何有 .encode() 方法的对象
        """
        self._embedder = model
        self._search_index = None  # Invalidate cache
        print(f"[EpisodicMemory] Embedder set: semantic search enabled")

    def build_search_index(self) -> int:
        """
        预计算所有 episode 的嵌入向量，加速后续搜索。
        Returns: 索引中的向量数量。
        """
        if not hasattr(self, '_embedder') or self._embedder is None:
            return 0
        if not self.data:
            return 0

        what_lesson = [f"{e.get('what','')} {e.get('lesson','')}" for e in self.data]
        try:
            embeddings = self._embedder.encode(what_lesson, show_progress_bar=False)
            self._search_index = np.array(embeddings)
            print(f"[EpisodicMemory] Search index built: {len(self._search_index)} vectors")
            return len(self._search_index)
        except Exception as e:
            print(f"[EpisodicMemory] Failed to build search index: {e}")
            return 0

    def semantic_search(self, query: str, n: int = 5) -> list:
        """
        语义向量搜索 — 使用嵌入模型计算余弦相似度。
        需要先调用 set_embedder() 和 build_search_index()。
        """
        if not hasattr(self, '_embedder') or self._embedder is None:
            return []
        if not self.data:
            return []

        # Build index on first use if not yet built
        if getattr(self, '_search_index', None) is None:
            self.build_search_index()
        if self._search_index is None or len(self._search_index) == 0:
            return []

        try:
            q_vec = self._embedder.encode([query], show_progress_bar=False)[0]
            # Cosine similarity
            q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-8)
            idx_norm = self._search_index / (np.linalg.norm(self._search_index, axis=1, keepdims=True) + 1e-8)
            scores = np.dot(idx_norm, q_norm)
            top_indices = np.argsort(scores)[::-1][:n]
            results = [self.data[i] for i in top_indices if scores[i] > 0.1]
            return results
        except Exception as e:
            print(f"[EpisodicMemory] Semantic search failed: {e}")
            return []

    def search_episodes(self, query: str, n: int = 5) -> list:
        """
        搜索情景记忆（语义优先，BM25/子串回退）。

        如果设置了 embedder，优先使用语义搜索；
        否则回退到 BM25 > 子串匹配。
        """
        if not self.data:
            return []

        # Try semantic search first
        if hasattr(self, '_embedder') and self._embedder is not None:
            results = self.semantic_search(query, n)
            if results:
                print(f"[EpisodicMemory] semantic_search('{query}'): {len(results)} results")
                return results

        # Fallback: BM25 or substring
        what_lesson = [f"{e.get('what','')} {e.get('lesson','')}" for e in self.data]

        try:
            from rank_bm25 import BM25Okapi
            import tokenizers.pre_tokenizers
            tok = tokenizers.pre_tokenizers.WhitespaceTokenizer()
            tokenized = [tok.encode(t).tokens for t in what_lesson]
            bm25 = BM25Okapi(tokenized)
            q_tokens = tok.encode(query).tokens
            scores = bm25.get_scores(q_tokens)
            ranked = sorted(zip(scores, self.data), reverse=True)
            results = [ep for score, ep in ranked if score > 0][:n]
        except ImportError:
            lc_q = query.lower()
            results = [
                e for e, t in zip(self.data, what_lesson)
                if lc_q in t.lower()
            ][:n]

        print(f"[EpisodicMemory] search('{query}'): {len(results)} results")
        return results

    def get_outcome_stats(self, days: int = 30) -> dict:
        """统计最近 N 天的 outcome / emotion 分布。"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        eps = [e for e in self.data if e.get("when", "") >= cutoff]
        outcomes = {}
        emotions = {}
        for e in eps:
            outcomes[e.get("outcome", "unknown")] = outcomes.get(e.get("outcome", "unknown"), 0) + 1
            emotions[e.get("emotion", "unknown")] = emotions.get(e.get("emotion", "unknown"), 0) + 1

        total = len(eps)
        return {
            "period_days": days,
            "total_episodes": total,
            "success_rate": round(outcomes.get("success", 0) / max(total, 1), 3),
            "outcomes": outcomes,
            "emotions": emotions,
            "avg_importance": round(sum(e.get("importance", 3) for e in eps) / max(len(eps), 1), 2),
        }

    def get_episode_by_id(self, episode_id: str) -> dict | None:
        """通过 ID 查找单条情景记忆。"""
        for e in self.data:
            if e.get("episode_id") == episode_id:
                return e
        return None

    def add_lesson(self, episode_id: str, lesson: str) -> bool:
        """为已有 episode 追加 lesson。"""
        ep = self.get_episode_by_id(episode_id)
        if ep:
            ep["lesson"] = lesson
            self._save()
            return True
        return False

    def get_lessons(self, n: int = 10) -> list:
        """获取所有包含 lesson 的情景记忆（经验沉淀）。"""
        lessons = [e for e in self.data if e.get("lesson")]
        lessons.sort(key=lambda x: x.get("when", ""), reverse=True)
        return lessons[:n]

    def upgrade_from_text(self, flat_records: list) -> int:
        """
        将旧的文本 chunk 记录升级为情景记忆结构。

        Args:
            flat_records: list of dicts with at least "content" or "text" key

        Returns:
            upgraded count
        """
        upgraded = 0
        for rec in flat_records:
            content = rec.get("content") or rec.get("text") or rec.get("what", "")
            if not content:
                continue
            lc = content.lower()
            if any(w in lc for w in ["error", "fail", "错误", "失败", "bug", "crash"]):
                emotion, outcome = "negative", "failure"
            elif any(w in lc for w in ["success", "成功", "pass", "通过", "ok"]):
                emotion, outcome = "positive", "success"
            else:
                emotion, outcome = "neutral", "partial"

            tags = rec.get("tags", [])
            importance = 3
            if "critical" in tags or "严重" in tags:
                importance = 5
            elif "warning" in tags or "重要" in tags:
                importance = 4

            self.add_episode(
                what=content[:200],
                context=rec.get("context", {}),
                outcome=outcome,
                emotion=emotion,
                tags=tags,
                importance=importance,
                lesson=rec.get("lesson", ""),
                when=rec.get("when") or rec.get("created_at") or rec.get("timestamp"),
                linked_memory_ids=rec.get("linked_memory_ids", []),
            )
            upgraded += 1
        return upgraded

    def get_stats(self) -> dict:
        """返回统计摘要。"""
        episodes = self.data  # Always a list
        return {
            "total_episodes": len(episodes),
            "with_lessons": sum(1 for e in episodes if e.get("lesson")),
            "by_outcome": {o: sum(1 for e in episodes if e.get("outcome") == o)
                           for o in self.OUTCOME_VALUES},
            "by_emotion": {em: sum(1 for e in episodes if e.get("emotion") == em)
                           for em in self.EMOTION_VALUES},
            "avg_importance": round(
                sum(e.get("importance", 3) for e in episodes) / max(len(episodes), 1), 2),
            "newest": episodes[-1]["when"] if episodes else None,
            "oldest": episodes[0]["when"] if episodes else None,
        }
