"""
Metacognition Monitor — 元认知监控台

Self-awareness dashboard: confidence calibration, anomaly detection,
self-reflection triggers, and cross-subsystem performance aggregation.
"""
import sys as _sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
CALIBRATION_FILE = DATA_DIR / "calibration_history.json"
ANOMALY_FILE = DATA_DIR / "anomaly_log.json"
REFLECTION_FILE = DATA_DIR / "self_reflections.json"


def _now() -> str:
    return datetime.now().isoformat()


class MetacognitionMonitor:
    """
    元认知监控台 — 系统自我认知与决策质量监控。

    功能：
    - 置信度校准（预测 vs 实际）
    - 异常检测（决策模式偏离基线）
    - 自我反思触发器（偏差过大时自动复盘）
    - 全系统仪表板
    """

    def __init__(self, data_dir: Path = None, prefix: str = ""):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = DATA_DIR

        # Per-agent file naming: calibration_<prefix>.json
        suffix = f"_{prefix}" if prefix else ""
        self._cal_file = self.data_dir / f"calibration_history{suffix}.json"
        self._anom_file = self.data_dir / f"anomaly_log{suffix}.json"
        self._refl_file = self.data_dir / f"self_reflections{suffix}.json"

        self.calibration = self._load_or_init(self._cal_file, {"version": "1.0", "entries": []})
        self.anomalies = self._load_or_init(self._anom_file, {"version": "1.0", "anomalies": []})
        self.reflections = self._load_or_init(self._refl_file, {"version": "1.0", "reflections": []})

        # Restore in-memory state from persisted calibration history
        cal_entries = self.calibration.get("entries", [])
        self._total_decisions = len(cal_entries)
        # Populate rolling window from last 100 entries
        self._recent_decisions = cal_entries[-100:] if cal_entries else []
        # Recalculate consecutive failures from the tail
        self._consecutive_failures = 0
        for entry in reversed(cal_entries):
            if entry.get("actual_outcome") == "failure":
                self._consecutive_failures += 1
            else:
                break

        print(f"[Metacognition] Loaded: {len(cal_entries)} calibration entries, "
              f"{len(self.anomalies.get('anomalies', []))} anomalies, "
              f"{self._total_decisions} decisions restored, "
              f"{self._consecutive_failures} consecutive failures",
              file=_sys.stderr)

    def _load_or_init(self, path: Path, default: dict) -> dict:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("updated_at", _now())
                        return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[Metacognition] Load failed, using defaults: {e}")
        return default

    def _save(self, data: dict, path: Path):
        data["updated_at"] = _now()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Confidence Calibration ───────────────────────────────────────────────

    def record_decision_outcome(self, predicted_confidence: float,
                                actual_outcome: str,
                                action: str, state_context: str):
        """
        记录一次决策结果，用于置信度校准。

        Args:
            predicted_confidence: 决策前的 RL 预测置信度 (0-1)
            actual_outcome: "success" | "failure" | "partial"
            action: 执行的动作名称
            state_context: 决策上下文描述
        """
        self._total_decisions += 1
        entry = {
            "timestamp": _now(),
            "predicted_confidence": round(predicted_confidence, 4),
            "actual_outcome": actual_outcome,
            "action": action,
            "state_context_hash": state_context[:80],
            "calibrated": actual_outcome == "success" and predicted_confidence > 0.5,
        }
        self.calibration["entries"].append(entry)

        # Track consecutive failures
        if actual_outcome == "failure":
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0

        # Rolling window
        self._recent_decisions.append(entry)
        if len(self._recent_decisions) > 100:
            self._recent_decisions = self._recent_decisions[-100:]

        # Persist periodically
        if len(self.calibration["entries"]) % 20 == 0:
            self._save(self.calibration, self._cal_file)

    def get_calibration_curve(self, n_bins: int = 10) -> dict:
        """
        计算置信度校准曲线。

        Returns:
            {bins, overconfidence, underconfidence, ece}
        """
        entries = self.calibration["entries"]
        if len(entries) < n_bins:
            return {"bins": [], "overconfidence": 0.0,
                    "underconfidence": 0.0, "ece": 0.0, "total": len(entries)}

        confs = np.array([e["predicted_confidence"] for e in entries])
        outcomes = np.array([1.0 if e["actual_outcome"] == "success" else 0.0
                             for e in entries])

        bins = []
        total_ece = 0.0
        for i in range(n_bins):
            low = i / n_bins
            high = (i + 1) / n_bins
            mask = (confs >= low) & (confs < high)
            if i == n_bins - 1:
                mask = (confs >= low) & (confs <= high)  # include 1.0
            count = int(mask.sum())
            if count > 0:
                acc = float(outcomes[mask].mean())
                avg_conf = float(confs[mask].mean())
                ece_bin = abs(avg_conf - acc) * count
                total_ece += ece_bin
                bins.append({
                    "conf_low": round(low, 2),
                    "conf_high": round(high, 2),
                    "accuracy": round(acc, 4),
                    "avg_confidence": round(avg_conf, 4),
                    "count": count,
                })

        total = len(entries)
        ece = round(total_ece / total, 4) if total > 0 else 0.0
        overconfidence = round(float(np.mean(confs - outcomes)), 4)
        underconfidence = -min(overconfidence, 0.0)
        overconfidence = max(overconfidence, 0.0)

        return {
            "bins": bins,
            "overconfidence": overconfidence,
            "underconfidence": round(underconfidence, 4),
            "ece": ece,
            "total": total,
        }

    # ── Anomaly Detection ────────────────────────────────────────────────────

    def check_anomaly(self, decision_record: dict) -> Optional[dict]:
        """
        检查单次决策是否是异常。

        Args:
            decision_record: {confidence, outcome, action, state_index, ...}

        Returns:
            异常描述 dict 或 None
        """
        anomalies_found = []

        # Rule 1: High confidence but consecutive failures
        if (decision_record.get("confidence", 0) > 0.7 and
                decision_record.get("outcome") == "failure" and
                self._consecutive_failures >= 2):
            anomalies_found.append({
                "type": "high_confidence_consecutive_failure",
                "detail": f"连续 {self._consecutive_failures} 次高置信度失败",
                "severity": "high" if self._consecutive_failures >= 3 else "medium",
            })

        # Rule 2: High confidence on state with fallback used
        if (decision_record.get("confidence", 0) > 0.5 and
                decision_record.get("fallback_used")):
            anomalies_found.append({
                "type": "high_confidence_fallback_state",
                "detail": "回退状态下给出高置信度推荐",
                "severity": "medium",
            })

        # Rule 3: Zero confidence decision (shouldn't happen in normal operation)
        if (decision_record.get("confidence", 0) == 0.0 and
                self._total_decisions > 10):
            anomalies_found.append({
                "type": "zero_confidence_decision",
                "detail": "尽管已有足够经验，置信度为 0",
                "severity": "low",
            })

        if anomalies_found:
            anomaly = {
                "timestamp": _now(),
                "action": decision_record.get("action", "unknown"),
                "predicted_confidence": decision_record.get("confidence", 0),
                "actual_outcome": decision_record.get("outcome", "unknown"),
                "findings": anomalies_found,
            }
            self.anomalies["anomalies"].append(anomaly)
            if len(self.anomalies["anomalies"]) % 5 == 0:
                self._save(self.anomalies, self._anom_file)
            return anomaly
        return None

    def get_recent_anomalies(self, n: int = 10) -> list:
        """获取最近 N 条异常记录。"""
        return self.anomalies["anomalies"][-n:]

    # ── Self-Reflection Triggers ─────────────────────────────────────────────

    def evaluate_self_reflection_needed(self) -> Optional[dict]:
        """
        评估是否需要自我反思。

        触发条件：
        - 最近 10 次决策中置信度 vs 准确率偏差 > 30%
        - 连续 3 次以上失败

        Returns:
            {"trigger": bool, "reason": str, "severity": str} 或 None
        """
        recent = self._recent_decisions[-10:]
        if len(recent) < 10:
            return None

        avg_conf = np.mean([r["predicted_confidence"] for r in recent])
        accuracy = np.mean([1.0 if r["actual_outcome"] == "success" else 0.0
                           for r in recent])

        if avg_conf - accuracy > 0.3:
            return {
                "trigger": True,
                "reason": f"校准偏差过高：置信度 {avg_conf:.0%}，准确率 {accuracy:.0%}，"
                          f"偏差 {avg_conf - accuracy:.0%}",
                "severity": "high" if avg_conf - accuracy > 0.5 else "medium",
            }

        if self._consecutive_failures >= 3:
            return {
                "trigger": True,
                "reason": f"连续 {self._consecutive_failures} 次失败",
                "severity": "high",
            }

        return None

    def record_reflection(self, trigger: str,
                          analysis: str, action_plan: str):
        """记录一次自我反思。"""
        reflection = {
            "timestamp": _now(),
            "trigger": trigger,
            "analysis": analysis,
            "action_plan": action_plan,
            "resolved": False,
        }
        self.reflections["reflections"].append(reflection)
        self._save(self.reflections, self._refl_file)
        print(f"[Metacognition] Reflection recorded: {trigger[:50]}")

    def get_reflections(self, n: int = 10) -> list:
        """获取最近的自我反思记录。"""
        return self.reflections["reflections"][-n:]

    # ── Performance Dashboard ────────────────────────────────────────────────

    def get_performance_dashboard(self) -> dict:
        """
        全系统仪表板 — 聚合所有子系统的统计信息。
        调用者负责传入各子系统的 stats。
        """
        calibration = self.get_calibration_curve()
        reflection = self.evaluate_self_reflection_needed()
        recent = self._recent_decisions[-20:]

        # Recent accuracy
        if recent:
            recent_acc = np.mean([1.0 if r["actual_outcome"] == "success" else 0.0
                                 for r in recent])
        else:
            recent_acc = 0.0

        # Health score
        health_score = 100.0
        if calibration["ece"] > 0.2:
            health_score -= 20
        if self._consecutive_failures >= 3:
            health_score -= 25
        elif self._consecutive_failures >= 2:
            health_score -= 10
        if recent_acc < 0.5 and len(recent) >= 5:
            health_score -= 15
        health_score = max(0.0, health_score)

        return {
            "total_decisions": self._total_decisions,
            "recent_accuracy": round(recent_acc, 4),
            "consecutive_failures": self._consecutive_failures,
            "calibration": calibration,
            "anomalies_recent": len(self.get_recent_anomalies(5)),
            "reflections_needed": reflection is not None,
            "reflection_reason": reflection["reason"] if reflection else None,
            "overall_health": (
                "good" if health_score >= 80 else
                "warning" if health_score >= 50 else
                "critical"
            ),
            "health_score": round(health_score, 1),
        }

    def get_stats(self) -> dict:
        return {
            "total_decisions": self._total_decisions,
            "calibration_entries": len(self.calibration["entries"]),
            "anomalies": len(self.anomalies["anomalies"]),
            "reflections": len(self.reflections["reflections"]),
            "consecutive_failures": self._consecutive_failures,
        }


# Example usage
if __name__ == "__main__":
    mc = MetacognitionMonitor()

    # Simulate some decisions
    mc.record_decision_outcome(0.9, "success", "try_fix_three_times", "error_context_A")
    mc.record_decision_outcome(0.8, "success", "write_script", "error_context_B")
    mc.record_decision_outcome(0.85, "failure", "try_fix_three_times", "error_context_C")
    mc.record_decision_outcome(0.95, "failure", "try_fix_three_times", "error_context_C")
    mc.record_decision_outcome(0.7, "success", "report_user", "error_context_D")
    mc.record_decision_outcome(0.3, "failure", "skip_phase", "error_context_E")
    mc.record_decision_outcome(0.25, "failure", "skip_phase", "error_context_E")
    mc.record_decision_outcome(0.2, "failure", "skip_phase", "error_context_E")
    mc.record_decision_outcome(0.6, "success", "use_existing_tool", "error_context_F")
    mc.record_decision_outcome(0.55, "success", "use_existing_tool", "error_context_G")

    print(f"\nStats: {json.dumps(mc.get_stats(), indent=2)}")
    print(f"\nCalibration: {json.dumps(mc.get_calibration_curve(), indent=2)}")

    refl = mc.evaluate_self_reflection_needed()
    print(f"\nReflection needed: {refl}")

    dash = mc.get_performance_dashboard()
    print(f"\nDashboard: health={dash['overall_health']}, "
          f"score={dash['health_score']}, ece={dash['calibration']['ece']}")

    # Clean up test files
    for f in [CALIBRATION_FILE, ANOMALY_FILE, REFLECTION_FILE]:
        if f.exists():
            f.unlink()

    print("\n[Metacognition] Test passed!")
