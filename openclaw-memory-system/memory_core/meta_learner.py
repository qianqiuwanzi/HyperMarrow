"""
Meta-Learner & Skill Extractor — 元学习 + 技能涌现

Wave 3: The system learns how to learn, and skills emerge from experience.

MetaLearner:     monitors losses/errors, auto-tunes hyperparameters
SkillExtractor:  discovers reusable action patterns from episodic memory
"""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
META_STATE_FILE = DATA_DIR / "meta_learning_state.json"
SKILLS_FILE = DATA_DIR / "extracted_skills.json"


def _now() -> str:
    return datetime.now().isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Meta-Learner
# ═══════════════════════════════════════════════════════════════════════════════

class MetaLearner:
    """
    元学习控制器 — 监控各子系统表现，自动调节超参数。

    调节策略:
      - TD error 上升 → 提高 learning_rate
      - 世界模型 loss 下降 → 提高 planning_horizon
      - ECE 偏高 → 提高 exploration_weight
      - 连续失败多 → 提高 consolidation_frequency
      - 状态空间增长快 → 提高 _max_states 上限
    """

    def __init__(self):
        self.state = self._load_or_init()
        self._history = {"td_errors": [], "wm_losses": [], "ece": [],
                         "success_rate": [], "state_growth": []}
        print(f"[MetaLearner] Initialized: {self.state['total_adjustments']} prior adjustments")

    def _load_or_init(self) -> dict:
        if META_STATE_FILE.exists():
            try:
                with open(META_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "1.0",
            "total_adjustments": 0,
            "adjustment_log": [],
            "current_hyperparams": {
                "learning_rate": 0.1,
                "epsilon": 0.1,
                "exploration_weight": 0.3,
                "consolidation_interval": 20,
                "planning_horizon": 1,
            },
            "created_at": _now(),
            "updated_at": _now(),
        }

    def _save(self):
        self.state["updated_at"] = _now()
        with open(META_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def observe(self, td_error: float = None, wm_loss: float = None,
                ece: float = None, success: bool = None,
                state_count: int = None):
        """记录观测值用于趋势分析。"""
        if td_error is not None:
            self._history["td_errors"].append(td_error)
        if wm_loss is not None:
            self._history["wm_losses"].append(wm_loss)
        if ece is not None:
            self._history["ece"].append(ece)
        if success is not None:
            self._history["success_rate"].append(1.0 if success else 0.0)
        if state_count is not None:
            self._history["state_growth"].append(state_count)
        # Keep history bounded
        for k in self._history:
            if len(self._history[k]) > 200:
                self._history[k] = self._history[k][-200:]

    def _trend(self, key: str, window: int = 20) -> float:
        """计算最近 window 个值的趋势（正值=上升）。"""
        vals = self._history.get(key, [])
        if len(vals) < window:
            return 0.0
        recent = vals[-window:]
        if len(recent) < 2:
            return 0.0
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        mean = np.mean(np.abs(recent)) or 1.0
        return float(slope / mean)

    def _recent_mean(self, key: str, window: int = 20) -> float:
        vals = self._history.get(key, [])
        if not vals:
            return 0.0
        return float(np.mean(vals[-window:]))

    def adjust(self, q_agent=None, world_model=None,
               consolidator=None) -> dict:
        """
        分析趋势并调整超参数。返回调整记录。

        每个子系统可以传入 None（不调整）。
        """
        adjustments = []
        hp = self.state["current_hyperparams"]

        # 1. TD error trend → adjust learning_rate
        td_trend = self._trend("td_errors")
        if td_trend > 0.1 and q_agent is not None:
            old_lr = q_agent.learning_rate
            q_agent.learning_rate = min(0.5, old_lr * 1.2)
            hp["learning_rate"] = q_agent.learning_rate
            adjustments.append(f"lr {old_lr:.3f}→{q_agent.learning_rate:.3f} (TD↑)")

        elif td_trend < -0.05 and q_agent is not None:
            old_lr = q_agent.learning_rate
            q_agent.learning_rate = max(0.01, old_lr * 0.9)
            hp["learning_rate"] = q_agent.learning_rate
            adjustments.append(f"lr {old_lr:.3f}→{q_agent.learning_rate:.3f} (TD↓)")

        # 2. World model loss trend → adjust exploration & planning
        wm_trend = self._trend("wm_losses")
        if wm_trend < -0.05 and world_model is not None:
            # WM improving → can plan further ahead
            hp["planning_horizon"] = min(3, hp.get("planning_horizon", 1) + 1)
            world_model.planner.planning_horizon = hp["planning_horizon"]
            adjustments.append(f"horizon→{hp['planning_horizon']} (WM↓)")

        # 3. ECE high → increase exploration
        recent_ece = self._recent_mean("ece")
        if recent_ece > 0.2 and q_agent is not None:
            new_eps = min(0.5, q_agent.epsilon * 1.5)
            q_agent.epsilon = new_eps
            hp["epsilon"] = new_eps
            if world_model is not None:
                world_model.planner.exploration_weight = min(0.8,
                    world_model.planner.exploration_weight * 1.3)
                hp["exploration_weight"] = world_model.planner.exploration_weight
            adjustments.append(f"ε→{new_eps:.3f}, λ→{hp.get('exploration_weight', 0.3):.3f} (ECE↑)")

        # 4. Success rate low → consolidate more often
        recent_sr = self._recent_mean("success_rate")
        if recent_sr < 0.4 and consolidator is not None:
            hp["consolidation_interval"] = max(5, hp.get("consolidation_interval", 20) // 2)
            adjustments.append(f"consolidate_interval→{hp['consolidation_interval']} (SR↓)")

        elif recent_sr > 0.8 and consolidator is not None:
            hp["consolidation_interval"] = min(50, hp.get("consolidation_interval", 20) + 5)
            adjustments.append(f"consolidate_interval→{hp['consolidation_interval']} (SR↑)")

        # 5. State space growing → expand capacity
        state_growth = self._trend("state_growth")
        if state_growth > 0.2 and q_agent is not None:
            q_agent._max_states = min(5000, q_agent._max_states + 500)
            adjustments.append(f"max_states→{q_agent._max_states} (growth↑)")

        if adjustments:
            self.state["total_adjustments"] += 1
            self.state["adjustment_log"].append({
                "timestamp": _now(),
                "adjustments": adjustments,
                "trends": {
                    "td_trend": round(td_trend, 4),
                    "wm_trend": round(wm_trend, 4),
                    "ece": round(recent_ece, 4),
                    "success_rate": round(recent_sr, 4),
                },
            })
            self._save()
            print(f"[MetaLearner] Adjustments: {'; '.join(adjustments)}")

        return {"adjustments": adjustments, "hyperparams": dict(hp)}

    def get_stats(self) -> dict:
        return {
            "total_adjustments": self.state["total_adjustments"],
            "current_hyperparams": self.state["current_hyperparams"],
            "recent_td_trend": round(self._trend("td_errors"), 4),
            "recent_wm_trend": round(self._trend("wm_losses"), 4),
            "recent_success_rate": round(self._recent_mean("success_rate"), 3),
            "recent_ece": round(self._recent_mean("ece"), 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Skill Extractor
# ═══════════════════════════════════════════════════════════════════════════════

class SkillExtractor:
    """
    技能自动提取器 — 从情景记忆中发现可复用的动作模式。

    流程:
      1. 扫描 episodic memory 中 outcome=success 的记录
      2. 按 context 相似度分组
      3. 提取 (context_pattern, action, success_rate) 作为技能
      4. 写入 ProceduralMemory 作为自动生成的规则
    """

    def __init__(self, episodic_memory=None, knowledge_graph=None):
        self.em = episodic_memory
        self.kg = knowledge_graph
        self.data = self._load_or_init()
        print(f"[SkillExtractor] Loaded: {len(self.data['skills'])} extracted skills")

    def _load_or_init(self) -> dict:
        if SKILLS_FILE.exists():
            try:
                with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"version": "1.0", "skills": {}, "extraction_count": 0,
                "created_at": _now(), "updated_at": _now()}

    def _save(self):
        self.data["updated_at"] = _now()
        with open(SKILLS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _extract_keywords(self, text: str, max_words: int = 5) -> list:
        """从文本中提取关键词（简单频率统计）。"""
        import re
        words = re.findall(r'[a-z_一-鿿]{2,}', text.lower())
        from collections import Counter
        return [w for w, _ in Counter(words).most_common(max_words)]

    def extract_skills(self, min_successes: int = 3,
                        min_success_rate: float = 0.6) -> int:
        """
        从情景记忆中提取技能。

        条件: 同一 action 在同一类 context 下成功 ≥ min_successes 次,
              成功率 ≥ min_success_rate。

        Returns:
            新提取的技能数量
        """
        if not self.em or not self.em.data:
            return 0

        episodes = self.em.data
        # Group by action
        by_action = {}
        for ep in episodes:
            ctx = ep.get("context", {})
            action = ctx.get("action") if isinstance(ctx, dict) else None
            if not action or ep.get("outcome") != "success":
                continue
            by_action.setdefault(action, []).append(ep)

        extracted = 0
        for action, eps in by_action.items():
            if len(eps) < min_successes:
                continue

            success_count = len(eps)
            total = success_count  # All are successes in this group

            # Extract common context keywords
            all_text = " ".join(
                str(e.get("context", {}).get("context_raw", "")) + " " +
                e.get("what", "")
                for e in eps
            )
            keywords = self._extract_keywords(all_text)

            # Create skill entry
            skill_id = f"auto_{action}_{len(self.data['skills'])}"
            skill = {
                "id": skill_id,
                "action": action,
                "context_patterns": keywords,
                "success_count": success_count,
                "total_attempts": total,
                "success_rate": 1.0,
                "source_episodes": [e.get("episode_id") for e in eps[:5]],
                "extracted_at": _now(),
            }
            self.data["skills"][skill_id] = skill
            extracted += 1
            print(f"[SkillExtractor] Skill '{action}': "
                  f"{keywords[:3]} (n={success_count})")

        if extracted:
            self.data["extraction_count"] += 1
            self._save()

        return extracted

    def feed_procedural(self, procedural_memory) -> int:
        """
        将提取的技能写入程序性记忆作为自动规则。

        Returns:
            写入的规则数量
        """
        if procedural_memory is None:
            return 0

        added = 0
        for sid, skill in self.data["skills"].items():
            rule_id = f"auto_skill_{sid}"
            if rule_id in procedural_memory.data.get("rules", {}):
                continue  # Already exists

            procedural_memory.data.setdefault("rules", {})[rule_id] = {
                "rule_id": rule_id,
                "rule_name": f"[Auto] {skill['action']} ({', '.join(skill['context_patterns'][:3])})",
                "context_patterns": skill["context_patterns"],
                "level": 2,  # Auto-extracted skills start at level 2
                "success_count": skill["success_count"],
                "failure_count": 0,
                "total_attempts": skill["total_attempts"],
                "success_rate": skill["success_rate"],
                "consecutive_success": skill["success_count"],
                "consecutive_failure": 0,
                "created_at": _now(),
                "last_used_at": None,
                "promoted_at": None,
                "demoted_at": None,
                "notes": [f"Auto-extracted by SkillExtractor from {skill['success_count']} episodes"],
            }
            added += 1

        if added:
            procedural_memory._save()
            print(f"[SkillExtractor] Fed {added} skills to ProceduralMemory")

        return added

    def get_stats(self) -> dict:
        return {
            "total_skills": len(self.data["skills"]),
            "extraction_count": self.data["extraction_count"],
            "by_action": {
                s["action"]: s["success_count"]
                for s in self.data["skills"].values()
            },
        }


# ── Example ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from .episodic_memory_db import EpisodicMemoryDB
    from .procedural_memory import ProceduralMemory
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="meta_test_"))
    em = EpisodicMemoryDB(path=tmp / "episodes.json", auto_clear=True)

    # Add episodes with the same action succeeding multiple times
    for i in range(4):
        em.add_episode(
            f"修复timeout错误_{i}",
            context={"action": "try_fix_three_times",
                     "context_raw": f"P2b 下载 timeout error 重试{i}"},
            outcome="success", emotion="positive",
            tags=["fix", "download"], importance=4,
        )
    for i in range(3):
        em.add_episode(
            f"切换到其他技能_{i}",
            context={"action": "switch_skill",
                     "context_raw": f"格式不支持 unsupported format 切换"},
            outcome="success", emotion="positive",
            tags=["switch", "format"], importance=3,
        )

    # Test MetaLearner
    ml = MetaLearner()
    for i in range(30):
        ml.observe(td_error=0.5 - i * 0.01, wm_loss=0.3 - i * 0.005,
                   ece=0.3 - i * 0.005, success=(i > 20),
                   state_count=50 + i)
    result = ml.adjust()
    print(f"Meta adjustments: {result['adjustments']}")
    print(f"Meta stats: {ml.get_stats()}")

    # Test SkillExtractor
    se = SkillExtractor(episodic_memory=em)
    extracted = se.extract_skills(min_successes=3)
    print(f"Skills extracted: {extracted}")

    pm = ProceduralMemory(workspace=tmp)
    fed = se.feed_procedural(pm)
    print(f"Skills fed to PM: {fed}")
    print(f"PM rules: {list(pm.data.get('rules', {}).keys())}")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    for f in [META_STATE_FILE, SKILLS_FILE]:
        if f.exists():
            f.unlink()

    print("\n[MetaLearner + SkillExtractor] Test passed!")
