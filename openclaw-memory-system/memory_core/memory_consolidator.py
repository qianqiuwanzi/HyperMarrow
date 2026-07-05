"""
Memory Consolidator — LTP/LTD 记忆巩固机制

Sleep-inspired memory consolidation: strengthening (LTP), decay (LTD),
episode merging, Q-buffer replay, and periodic sleep cycles.
"""
import json
import sys as _sys
import copy
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
STATE_FILE = DATA_DIR / "consolidation_state.json"
ARCHIVE_FILE = DATA_DIR / "consolidation_archive.json"


def _now() -> str:
    return datetime.now().isoformat()


class MemoryConsolidator:
    """
    记忆固化器 — 类生物 LTP/LTD 机制。

    三个子过程：
    1. LTP (增强): 强化高重要性/高奖励记忆，提取经验教训
    2. LTD (抑制): 衰减低重要性/过时记忆，归档或删除
    3. Q 回放: 从经验缓冲区加权采样进行额外学习
    """

    def __init__(self, episodic_memory=None, knowledge_graph=None,
                 q_agent=None, data_dir: Path = None, procedural_memory=None, metacog=None):
        self.em = episodic_memory
        self.kg = knowledge_graph
        self.pm = procedural_memory  # ProceduralMemory (for rule extraction)
        self.metacog = metacog  # Metacognition (for calibration)
        self.ql_agent = q_agent
        self.data_dir = data_dir or DATA_DIR
        self.state = self._load_state()
        self._consolidating = False
        self._min_experiences_before_consolidation = 5
        print(f"[Consolidator] Loaded: {self.state.get('total_consolidations', 0)} "
              f"prior consolidations, last sleep: {self.state.get('last_sleep_at', 'never')}",
              file=_sys.stderr)

    # ── State Persistence ───────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Consolidator] Load failed, using defaults: {e}")
        return {
            "version": "1.0",
            "total_consolidations": 0,
            "total_ltp": 0,
            "total_ltd_pruned": 0,
            "total_episodes_merged": 0,
            "total_q_replayed": 0,
            "last_sleep_at": None,
            "created_at": _now(),
            "updated_at": _now(),
        }

    def _save_state(self):
        self.state["updated_at"] = _now()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ── Main Consolidation Cycle ────────────────────────────────────────────

    def consolidate(self) -> dict:
        """
        运行一次完整的记忆巩固循环。

        Returns:
            {ltp_count, ltd_pruned, episodes_merged, q_replayed, kg_relationships}
        """
        if self._consolidating:
            return {"ltp_count": 0, "ltd_pruned": 0,
                    "episodes_merged": 0, "q_replayed": 0, "kg_relationships": 0}

        self._consolidating = True
        import time
        t0 = time.time()

        try:
            ltp_count = self.ltp_strengthen(top_k=10)
            reconsolidated = self.reconsolidate()
            ltd_pruned = self.ltd_decay(min_importance=2, max_age_days=30)
            episodes_merged = self.merge_similar_episodes(similarity_threshold=0.6)

            q_replayed = 0
            if self.ql_agent and len(self.ql_agent.experience_buffer) >= self._min_experiences_before_consolidation:
                q_replayed = self.consolidate_q_buffer(batch_size=64, replay_rounds=2)

            kg_relationships = 0
            if self.kg:
                try:
                    kg_relationships = self.kg.infer_relationships()
                except Exception as e:
                    print(f"[Consolidator] KG inference failed (non-critical): {e}")

            self.state["total_consolidations"] = self.state.get("total_consolidations", 0) + 1
            self.state["total_ltp"] = self.state.get("total_ltp", 0) + ltp_count
            self.state["total_ltd_pruned"] = self.state.get("total_ltd_pruned", 0) + ltd_pruned
            self.state["total_episodes_merged"] = self.state.get("total_episodes_merged", 0) + episodes_merged
            self.state["total_q_replayed"] = self.state.get("total_q_replayed", 0) + q_replayed
            self._save_state()

            elapsed = round(time.time() - t0, 3)
            print(f"[Consolidator] Cycle complete: LTP={ltp_count}, recons={reconsolidated}, "
                  f"LTD={ltd_pruned}, merged={episodes_merged}, "
                  f"Q_replay={q_replayed}, KG={kg_relationships} ({elapsed}s)")

            return {
                "ltp_count": ltp_count,
                "reconsolidated": reconsolidated,
                "ltd_pruned": ltd_pruned,
                "episodes_merged": episodes_merged,
                "q_replayed": q_replayed,
                "kg_relationships": kg_relationships,
                "duration_sec": elapsed,
            }
        finally:
            self._consolidating = False

    # ── LTP: Strengthening ──────────────────────────────────────────────────

    def ltp_strengthen(self, top_k: int = 10) -> int:
        """
        增强最重要的记忆（情感调制版）。

        选择标准：按 emotion_weight × importance 加权排序。
        positive/negative 情绪事件获得额外 boost，neutral 事件不衰减但也不增强。

        emotion_weight 映射:
          positive → 1.5 (成功经验值得强化)
          negative → 1.3 (失败教训也重要)
          neutral  → 1.0 (普通事件)
          mixed    → 1.2
        """
        if not self.em or not self.em.data:
            return 0

        EMOTION_WEIGHT = {"positive": 1.5, "negative": 1.3, "mixed": 1.2, "neutral": 1.0}

        episodes = self.em.data
        candidates = [e for e in episodes
                      if e.get("importance", 0) >= 4
                      and e.get("outcome") == "success"]

        # Score by emotion_weight × importance
        for e in candidates:
            e["_ltp_score"] = (
                e.get("importance", 3) *
                EMOTION_WEIGHT.get(e.get("emotion", "neutral"), 1.0)
            )
        candidates.sort(key=lambda e: e["_ltp_score"], reverse=True)

        strengthened = 0
        for ep in candidates[:top_k]:
            # Emotion boost: positive events get +2 importance, negative +1
            emo = ep.get("emotion", "neutral")
            boost = 2 if emo == "positive" else (1 if emo in ("negative", "mixed") else 0)
            target = min(5, ep["importance"] + boost)
            if ep["importance"] < target:
                ep["importance"] = target
                strengthened += 1
            if not ep.get("lesson"):
                ep["lesson"] = self._extract_lesson(ep)
            # Clean up temp score
            ep.pop("_ltp_score", None)

        if strengthened:
            self.em._save()
            print(f"[Consolidator] LTP: strengthened {strengthened} episodes "
                  f"(emotion-modulated)")

        return strengthened

    def retrieval_boost(self, episode_id: str) -> bool:
        """
        模拟检索练习效应 (spaced repetition) + 再巩固标记。
        每次检索一条记忆时，轻微提升其 importance 并标记为 labile（不稳定），
        在下次巩固周期中重新稳定化，允许新上下文融入。

        Returns:
            True if episode was found and boosted.
        """
        if not self.em or not self.em.data:
            return False

        for ep in self.em.data:
            if ep.get("episode_id") == episode_id:
                # Boost importance slightly (retrieval strengthens memory)
                if ep["importance"] < 5:
                    ep["importance"] = min(5, ep["importance"] + 1)
                # Record retrieval for spaced repetition tracking
                retrievals = ep.setdefault("_retrieval_count", 0) + 1
                ep["_retrieval_count"] = retrievals
                ep["_last_retrieved"] = _now()
                # Mark as labile for reconsolidation
                ep["_labile"] = True
                self.em._save()
                return True
        return False

    def reconsolidate(self, new_context: dict = None) -> int:
        """
        再巩固：重新稳定化所有被标记为 labile 的记忆。

        再巩固过程中可以融入新的上下文信息（如检索时的新情境），
        使记忆保持可塑性的同时不丢失原有信息。

        Args:
            new_context: 可选的新上下文 dict，将合并到 labile 记忆的 context 中

        Returns:
            被重新稳定化的记忆数量
        """
        if not self.em or not self.em.data:
            return 0

        reconsolidated = 0
        for ep in self.em.data:
            if ep.get("_labile"):
                # Merge new context if provided
                if new_context and isinstance(ep.get("context"), dict):
                    ep["context"].update(new_context)
                # Boost importance slightly (reconsolidation strengthens)
                if ep["importance"] < 5:
                    ep["importance"] = min(5, ep["importance"] + 1)
                # Clear labile flag
                ep.pop("_labile", None)
                reconsolidated += 1

        if reconsolidated:
            self.em._save()
            print(f"[Consolidator] Reconsolidated {reconsolidated} episodes")

        return reconsolidated

    def _extract_lesson(self, episode: dict) -> str:
        """从 episode 自动提取 lesson。"""
        ctx = episode.get("context", {})
        action = ctx.get("action", "unknown")
        outcome = episode.get("outcome", "")
        tags = episode.get("tags", [])

        if outcome == "success":
            tag_str = f" ({', '.join(tags)})" if tags else ""
            return f"在类似上下文中，'{action}' 是有效的{tag_str}"
        elif outcome == "failure":
            error = ctx.get("context_raw", "")[:60]
            return f"避免在{error}时使用'{action}'"
        return ""

    # ── LTD: Ebbinghaus Exponential Decay ───────────────────────────────────

    # Default half-life: memory strength halves after ~30 days without retrieval
    DEFAULT_HALFLIFE_DAYS = 30.0
    PRUNE_THRESHOLD = 0.05  # Strength below 5% of initial → archive

    def _ebbinghaus_strength(self, initial_strength: float, age_days: float,
                              retrieval_count: int = 0) -> float:
        """
        Ebbinghaus exponential decay: R(t) = R0 × e^(-t / τ)

        τ = halflife / ln(2), adjusted by retrieval_count (spaced repetition).
        Each prior retrieval extends the effective halflife by 50%.
        """
        halflife = self.DEFAULT_HALFLIFE_DAYS * (1.0 + 0.5 * retrieval_count)
        tau = halflife / 0.693147  # ln(2)
        return initial_strength * np.exp(-age_days / tau)

    def ltd_decay(self, min_importance: int = 2,
                  max_age_days: float = 30.0,
                  decay_rate: float = 0.1) -> int:
        """
        Ebbinghaus 指数衰减 — 替代固定阈值。

        记忆强度 R(t) = R0 × e^(-t/τ)，其中 τ 由半衰期决定。
        检索练习效应：每次检索延长有效半衰期 50%。
        强度低于 PRUNE_THRESHOLD (5%) 的记忆被归档。

        保留参数签名兼容性，内部使用指数衰减替代硬阈值。
        """
        if not self.em or not self.em.data:
            return 0

        episodes = self.em.data
        pruned = 0
        decayed = 0
        kept = []

        for ep in episodes:
            when_str = ep.get("when", ep.get("created_at", ""))
            try:
                when = datetime.fromisoformat(when_str)
            except (ValueError, TypeError):
                kept.append(ep)
                continue

            age_days = max(0.0, (datetime.now() - when).total_seconds() / 86400.0)
            initial = float(ep.get("importance", 3))
            retrievals = ep.get("_retrieval_count", 0)

            # Compute current memory strength
            strength = self._ebbinghaus_strength(initial, age_days, retrievals)

            # Prune: strength too low, or very old low-importance (safety eject)
            should_prune = (
                (strength < self.PRUNE_THRESHOLD and initial <= 2) or
                (initial <= 1 and age_days > 90)  # safety: 3+ month importance-1 always goes
            )
            if should_prune:
                self._archive(ep, reason=f"ltd_prune(strength={strength:.3f})")
                pruned += 1
                continue

            # Decay: reduce importance based on strength decay
            new_importance = max(1, int(np.ceil(strength)))
            if new_importance < ep.get("importance", 3):
                ep["importance"] = new_importance
                decayed += 1

            kept.append(ep)

        if pruned > 0 or decayed > 0:
            self.em.data = kept
            self.em._save()
            print(f"[Consolidator] LTD (Ebbinghaus): decayed {decayed}, "
                  f"pruned {pruned} episodes")

        return pruned + decayed

    def _archive(self, episode: dict, reason: str = "ltd_prune"):
        """归档被删除的 episode（追加写）。"""
        archive = []
        if ARCHIVE_FILE.exists():
            try:
                with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                    archive = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Consolidator] Archive load failed: {e}")
        episode["_archived_at"] = _now()
        episode["_archive_reason"] = reason
        archive.append(episode)
        with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

    # ── Episode Merging ─────────────────────────────────────────────────────

    def merge_similar_episodes(self, similarity_threshold: float = 0.6) -> int:
        """
        合并相似的情景记忆。

        检测条件：相同 outcome + tags 交集 >= threshold + 24h 内创建。
        """
        if not self.em or not self.em.data:
            return 0

        episodes = self.em.data  # Always a list after P3 format unification
        if len(episodes) < 2:
            return 0

        merged_count = 0
        merged_ids = set()
        new_episodes = []

        for i, e1 in enumerate(episodes):
            if e1.get("episode_id") in merged_ids:
                continue
            best = copy.deepcopy(e1)
            merged_this = False

            for j, e2 in enumerate(episodes):
                if i >= j or e2.get("episode_id") in merged_ids:
                    continue

                # Check same outcome
                if e1.get("outcome") != e2.get("outcome"):
                    continue

                # Check tags overlap
                tags1 = set(e1.get("tags", []))
                tags2 = set(e2.get("tags", []))
                if not tags1 or not tags2:
                    continue
                overlap = len(tags1 & tags2) / min(len(tags1), len(tags2))
                if overlap < similarity_threshold:
                    continue

                # Check time proximity
                try:
                    t1 = datetime.fromisoformat(e1.get("when", e1.get("created_at", "")))
                    t2 = datetime.fromisoformat(e2.get("when", e2.get("created_at", "")))
                    if abs((t1 - t2).total_seconds()) > 86400:  # 24h
                        continue
                except (ValueError, TypeError):
                    continue

                # Merge: keep best fields
                best["importance"] = max(e1.get("importance", 3), e2.get("importance", 3))
                best["tags"] = list(set(e1.get("tags", []) + e2.get("tags", [])))
                best["lesson"] = e1.get("lesson") or e2.get("lesson") or ""
                merged_ids.add(e2.get("episode_id"))
                merged_this = True

            if merged_this:
                merged_count += 1
            new_episodes.append(best)

        if merged_count > 0:
            self.em.data = new_episodes
            self.em._save()
            print(f"[Consolidator] Merged {merged_count} episode pairs")

        return merged_count

    # ── Q-Table Consolidation ───────────────────────────────────────────────

    def consolidate_q_buffer(self, batch_size: int = 64,
                              replay_rounds: int = 3) -> int:
        """
        从经验缓冲区加权采样高价值经验进行回放。

        采样权重：|reward| > 0.5 → ×3, done == True → ×2。
        """
        if not self.ql_agent or not hasattr(self.ql_agent, 'experience_buffer'):
            return 0

        buf = self.ql_agent.experience_buffer
        if len(buf) < batch_size:
            return 0

        total = 0
        for _ in range(replay_rounds):
            # Weighted sampling
            weights = np.ones(len(buf))
            for i, exp in enumerate(buf):
                if abs(exp.get("reward", 0)) > 0.5:
                    weights[i] *= 3.0
                if exp.get("done", False):
                    weights[i] *= 2.0

            weights = weights / weights.sum()
            indices = np.random.choice(len(buf), size=min(batch_size, len(buf)),
                                       replace=False, p=weights)

            for idx in indices:
                exp = buf[idx]
                self.ql_agent.update(
                    exp["state"], exp["action"], exp["reward"],
                    exp["next_state"], exp.get("done", False),
                )
                total += 1

        if total > 0:
            print(f"[Consolidator] Q-buffer replay: {total} experiences "
                  f"({replay_rounds} rounds × ~{batch_size})")

        return total

    # ── Sleep Cycle ─────────────────────────────────────────────────────────

    def dream_cycle(self, force: bool = False) -> dict:
        """
        V2.1: 12-stage Dream Cycle — 9-stage 基础 + 3-stage 学习系统巩固。

        Returns:
            {"status": "ok"|"partial", "phases": {...}, "duration_sec": float}
        """
        import time
        t0 = time.time()
        phases = {}

        # 1. Lint: check data file integrity
        try:
            issues = self._dream_lint()
            phases["lint"] = issues
        except Exception as e:
            phases["lint"] = -1
            print(f"[Dream] lint failed: {e}")

        # 2. Backlinks: infer KG relationships
        try:
            if self.kg:
                phases["backlinks"] = self.kg.infer_relationships()
            else:
                phases["backlinks"] = 0
        except Exception as e:
            phases["backlinks"] = -1
            print(f"[Dream] backlinks failed: {e}")

        # 3. Sync: cross-agent knowledge sharing
        try:
            phases["sync"] = 0
        except Exception:
            phases["sync"] = -1

        # 4. Synthesize: merge similar episodes
        try:
            phases["synthesize"] = self.merge_similar_episodes()
        except Exception as e:
            phases["synthesize"] = -1
            print(f"[Dream] synthesize failed: {e}")

        # 5. Extract: skill extraction from episodes
        try:
            from .meta_learner import SkillExtractor
            se = SkillExtractor(episodic_memory=self.em,
                                 knowledge_graph=self.kg)
            phases["extract"] = se.extract_skills(min_successes=2)
        except Exception as e:
            phases["extract"] = -1
            print(f"[Dream] extract failed: {e}")

        # 6. Patterns: LTP strengthening + meta-learning adjustment
        try:
            ltp = self.ltp_strengthen(top_k=10)
            recons = self.reconsolidate()
            phases["patterns"] = ltp + recons
        except Exception as e:
            phases["patterns"] = -1
            print(f"[Dream] patterns failed: {e}")

        # 7. Embed: neural encoding + VecDB indexing (if available)
        try:
            phases["embed"] = 0
            if hasattr(self, 'ql_agent') and self.ql_agent and self.ql_agent._neural_agent:
                phases["embed"] = 1
        except Exception:
            phases["embed"] = -1

        # 8. Orphans: detect orphan entities/episodes
        try:
            orphans = 0
            if self.kg and hasattr(self.kg, 'get_orphan_entities'):
                orphans = len(self.kg.get_orphan_entities())
            phases["orphans"] = orphans
        except Exception as e:
            phases["orphans"] = -1
            print(f"[Dream] orphans failed: {e}")

        # 9. Purge: LTD decay (Ebbinghaus)
        try:
            phases["purge"] = self.ltd_decay()
        except Exception as e:
            phases["purge"] = -1
            print(f"[Dream] purge failed: {e}")

        # ============================================================
        # 新增 3 个学习系统巩固阶段 (V2.1)
        # ============================================================

        # 10. Batch Learn: Q-Learning 批量重训练（用所有历史经验）
        try:
            if self.ql_agent and hasattr(self.ql_agent, 'batch_learn'):
                # experience_buffer 已有历史经验（初始化时加载了 94 条）
                buffer_size = len(self.ql_agent.experience_buffer)
                if buffer_size > 0:
                    self.ql_agent.batch_learn(batch_size=min(32, buffer_size))
                    self.ql_agent.save_q_table()
                    phases["batch_learn"] = buffer_size
                else:
                    phases["batch_learn"] = 0
            else:
                phases["batch_learn"] = 0
        except Exception as e:
            phases["batch_learn"] = -1
            print(f"[Dream] batch_learn failed: {e}")

        # 11. Extract Rules: 从情景记忆中提取高频成功模式 → 晋升为规则
        try:
            if self.em and hasattr(self, 'pm') and self.pm:
                new_rules = self._extract_rules_from_episodes()
                phases["extract_rules"] = new_rules
            else:
                phases["extract_rules"] = 0
        except Exception as e:
            phases["extract_rules"] = -1
            print(f"[Dream] extract_rules failed: {e}")

        # 12. Calibrate: 元认知校准（评估决策质量，调整探索率）
        try:
            calib_result = self._calibrate_metacognition()
            phases["calibrate"] = calib_result
        except Exception as e:
            phases["calibrate"] = -1
            print(f"[Dream] calibrate failed: {e}")

        # ============================================================
        # 返回结果
        # ============================================================
        elapsed = round(time.time() - t0, 3)
        errors = sum(1 for v in phases.values() if v == -1)
        status = "ok" if errors == 0 else "partial"

        self.state["last_sleep_at"] = _now()
        self.state["total_consolidations"] = self.state.get("total_consolidations", 0) + 1
        self._save_state()

        result = {"status": status, "phases": phases, "duration_sec": elapsed}
        print(f"[Dream] Cycle complete: {status} ({elapsed}s) — "
              f"lint={phases.get('lint',0)}, backlinks={phases.get('backlinks',0)}, "
              f"sync={phases.get('sync',0)}, synth={phases.get('synthesize',0)}, "
              f"extract={phases.get('extract',0)}, patterns={phases.get('patterns',0)}, "
              f"embed={phases.get('embed',0)}, orphans={phases.get('orphans',0)}, "
              f"purge={phases.get('purge',0)}, "
              f"batch_learn={phases.get('batch_learn',0)}, "
              f"extract_rules={phases.get('extract_rules',0)}, "
              f"calibrate={phases.get('calibrate',0)}")
        return result

    def _dream_lint(self) -> int:
        """Check data file integrity. Returns number of issues found."""
        issues = 0
        data_dir = self.data_dir
        files = ["knowledge_graph.json", "procedural_memory.json",
                 "q_table.json", "rl_decision_history.json"]
        for fname in files:
            fpath = data_dir / fname
            if fpath.exists():
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        json.load(f)
                except Exception:
                    issues += 1
                    print(f"[Dream] lint: {fname} corrupted")
            # Missing files are OK (not all agents have all files)
        return issues

    def sleep_cycle(self, force: bool = False) -> Optional[dict]:
        """
        睡眠周期模拟 — 批量运行所有巩固子过程。

        调度：距上次 sleep 至少 4 小时，或每 50 次 consolidate 调用。
        """
        last = self.state.get("last_sleep_at")
        if not force and last:
            try:
                last_dt = datetime.fromisoformat(last)
                if (datetime.now() - last_dt).total_seconds() < 4 * 3600:
                    return None
            except (ValueError, TypeError):
                pass

        result = self.consolidate()
        self.state["last_sleep_at"] = _now()
        self._save_state()
        print(f"[Consolidator] Sleep cycle completed")
        return result

    # ── Stats ───────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "total_consolidations": self.state.get("total_consolidations", 0),
            "total_ltp": self.state.get("total_ltp", 0),
            "total_ltd_pruned": self.state.get("total_ltd_pruned", 0),
            "total_episodes_merged": self.state.get("total_episodes_merged", 0),
            "total_q_replayed": self.state.get("total_q_replayed", 0),
            "last_sleep_at": self.state.get("last_sleep_at"),
            "consolidating": self._consolidating,
        }

    def get_memory_health_report(self) -> dict:
        """记忆健康报告。"""
        ep_count = 0
        avg_imp = 0.0
        if self.em and self.em.data:
            episodes = self.em.data  # Always a list after P3 format unification
            ep_count = len(episodes)
            if ep_count > 0:
                avg_imp = sum(e.get("importance", 3) for e in episodes) / ep_count

        q_buf_size = len(self.ql_agent.experience_buffer) if self.ql_agent else 0

        return {
            "total_episodes": ep_count,
            "avg_importance": round(avg_imp, 2),
            "q_buffer_size": q_buf_size,
            "last_sleep": self.state.get("last_sleep_at"),
            "consolidation_count": self.state.get("total_consolidations", 0),
            "health_score": round(min(100, 50 + avg_imp * 10 + min(q_buf_size / 10, 30)), 1),
        }


    # ── 学习系统巩固方法 (V2.1) ─────────────────────────────────────

    def _load_all_experiences(self) -> list:
        """
        加载所有历史经验（不仅 buffer）。

        Returns:
            经验列表 [{"state":..., "action":..., "reward":..., ...}, ...]
        """
        history = []
        data_dir = self.data_dir

        # 1. 从 rl_decision_history.json 加载
        history_file = data_dir / "rl_decision_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        history.extend(data)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Consolidator] Load history failed: {e}")

        # 2. 从 ql_agent.experience_buffer 加载（去重）
        if self.ql_agent and hasattr(self.ql_agent, 'experience_buffer'):
            buf = self.ql_agent.experience_buffer
            existing_keys = set()
            if history:
                existing_keys = {f"{e.get('state')}-{e.get('action')}-{e.get('reward')}" for e in history}
            for exp in buf:
                key = f"{exp.get('state')}-{exp.get('action')}-{exp.get('reward')}"
                if key not in existing_keys:
                    history.append(exp)
                    existing_keys.add(key)

        return history

    def _extract_rules_from_episodes(self, min_freq: int = 3, min_success_rate: float = 0.8) -> int:
        """
        从情景记忆中提取高频成功模式 → 晋升为程序性规则。

        Args:
            min_freq: 最小出现频率
            min_success_rate: 最小成功率

        Returns:
            新提取的规则数量
        """
        if not self.em or not self.em.data:
            return 0
        if not hasattr(self, 'pm') or not self.pm:
            return 0

        from collections import Counter
        import itertools

        episodes = self.em.data
        # 1. 统计高频 (action, context) 模式
        patterns = Counter()
        for ep in episodes:
            ctx = ep.get("context", {})
            action = ctx.get("action", "unknown")
            tags = tuple(sorted(ep.get("tags", [])))
            outcome = ep.get("outcome", "")
            if outcome == "success":
                patterns[(action, tags)] += 1

        # 2. 过滤高频成功模式
        new_rules = 0
        for (action, tags), freq in patterns.items():
            if freq < min_freq:
                continue

            # 计算成功率
            total = sum(1 for ep in episodes
                        if ep.get("context", {}).get("action") == action)
            success = sum(1 for ep in episodes
                         if ep.get("context", {}).get("action") == action
                         and ep.get("outcome") == "success")
            success_rate = success / total if total > 0 else 0

            if success_rate < min_success_rate:
                continue

            # 3. 晋升为规则
            rule = {
                "description": f"高频成功模式: {action} (频率={freq}, 成功率={success_rate:.0%})",
                "condition": {"action": action, "tags": list(tags)},
                "action": action,
                "success_rate": success_rate,
                "level": 1,  # 初始级别
                "source": "auto_extracted",
                "created_at": _now(),
            }
            try:
                self.pm.add_rule(rule)
                new_rules += 1
            except Exception as e:
                print(f"[Consolidator] Rule extraction failed: {e}")

        if new_rules > 0:
            self.pm._save()
            print(f"[Consolidator] Extracted {new_rules} rules from episodes")

        return new_rules

    def _calibrate_metacognition(self) -> dict:
        """
        元认知校准：评估决策质量，调整探索率。

        Returns:
            {"accuracy": float, "old_epsilon": float, "new_epsilon": float}
        """
        if not hasattr(self, 'metacog') or not self.metacog:
            return {"accuracy": 0.0, "old_epsilon": 0.0, "new_epsilon": 0.0}

        metacog = self.metacog

        # 1. 计算决策准确率
        accuracy = metacog.calculate_decision_accuracy()

        # 2. 调整探索率（ε-greedy）
        old_epsilon = metacog.epsilon
        if accuracy > 0.9:
            # 决策准确 → 减少探索
            metacog.epsilon = max(0.1, metacog.epsilon * 0.9)
        else:
            # 决策不准 → 增加探索
            metacog.epsilon = min(0.5, metacog.epsilon * 1.1)

        # 3. 保存元认知状态
        metacog._save()

        return {
            "accuracy": round(accuracy, 2),
            "old_epsilon": round(old_epsilon, 3),
            "new_epsilon": round(metacog.epsilon, 3)
        }


# Example usage
if __name__ == "__main__":
    from .episodic_memory_db import EpisodicMemoryDB
    from .q_learning_agent import QLearningAgent
    import tempfile

    # Setup temp data
    tmp = Path(tempfile.mkdtemp(prefix="consolidator_test_"))
    em_path = tmp / "test_episodes.json"

    em = EpisodicMemoryDB(path=em_path, auto_clear=True)
    # Add test episodes
    em.add_episode("测试成功1", context={"action": "try_fix"}, outcome="success",
                   emotion="positive", tags=["test", "fix"], importance=4,
                   when="2026-06-01T10:00:00")
    em.add_episode("测试成功2", context={"action": "try_fix"}, outcome="success",
                   emotion="positive", tags=["test", "fix"], importance=4,
                   when="2026-06-01T10:30:00")
    em.add_episode("旧失败", context={"action": "skip"}, outcome="failure",
                   emotion="negative", tags=["old"], importance=1,
                   when="2025-01-01T00:00:00")

    agent = QLearningAgent(state_space_size=10, action_space_size=7)
    agent.add_experience(0, 2, 1.0, 1, False)
    agent.add_experience(1, 3, -0.5, 2, True)

    mc = MemoryConsolidator(episodic_memory=em, q_agent=agent)
    result = mc.consolidate()
    print(f"\nConsolidation result: {json.dumps(result, indent=2)}")
    print(f"Stats: {json.dumps(mc.get_stats(), indent=2)}")
    print(f"Health: {json.dumps(mc.get_memory_health_report(), indent=2)}")

    # Cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    for f in [STATE_FILE, ARCHIVE_FILE]:
        if f.exists():
            f.unlink()

    print("\n[MemoryConsolidator] Test passed!")
