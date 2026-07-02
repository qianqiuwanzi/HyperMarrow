"""
Prospective Memory — 前瞻记忆调度器

"Remember to do X when condition Y is met."
Maintains intention list: (trigger_condition, action, deadline, created_at).
Checked on each decision loop; auto-triggers when conditions match.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .config import get_data_dir

DATA_DIR = get_data_dir()
INTENTIONS_FILE = DATA_DIR / "prospective_intentions.json"


def _now() -> str:
    return datetime.now().isoformat()


def _make_id() -> str:
    return str(uuid.uuid4())[:8]


class ProspectiveMemory:
    """
    前瞻记忆 — 条件-动作触发器系统。

    人类前瞻记忆模型：
    - 意图编码: "在 X 条件下执行 Y"
    - 线索监控: 持续检查环境是否匹配触发条件
    - 意图执行: 条件满足时自动触发

    用法:
        pm = ProspectiveMemory()
        pm.add_intention("下载超时", "try_fix_three_times", deadline_hours=2)
        triggered = pm.check_triggers("当前下载卡住了超时")
        # → ["try_fix_three_times"]
    """

    def __init__(self, path=None):
        self.path = Path(path) if path else INTENTIONS_FILE
        self.data = self._load_or_init()
        self._completed_log = []
        print(f"[ProspectiveMemory] Loaded: {len(self.data['intentions'])} active intentions")

    # ── Persistence ────────────────────────────────────────────────────────

    def _load_or_init(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[ProspectiveMemory] Load failed, using defaults: {e}")
        return {
            "version": "1.0",
            "intentions": {},
            "completed": [],
            "created_at": _now(),
            "updated_at": _now(),
        }

    def _save(self):
        self.data["updated_at"] = _now()
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── Intention CRUD ─────────────────────────────────────────────────────

    def add_intention(self, trigger_keywords: str, action: str,
                      deadline_hours: float = None,
                      priority: int = 3,
                      metadata: dict = None) -> dict:
        """
        注册一条前瞻意图。

        Args:
            trigger_keywords: 触发条件关键词 (空格分隔)
            action: 条件满足时执行的动作
            deadline_hours: 过期时间（小时），None = 永不过期
            priority: 优先级 1-5
            metadata: 附加元数据

        Returns:
            新创建的 intention dict
        """
        iid = _make_id()
        intention = {
            "id": iid,
            "trigger_keywords": trigger_keywords.lower().split(),
            "action": action,
            "deadline": (_now() if deadline_hours is None else
                         (datetime.now() + timedelta(hours=deadline_hours)).isoformat()),
            "deadline_hours": deadline_hours,
            "priority": max(1, min(5, int(priority))),
            "metadata": metadata or {},
            "trigger_count": 0,
            "created_at": _now(),
            "status": "active",
        }
        self.data["intentions"][iid] = intention
        self._save()
        print(f"[ProspectiveMemory] Intention added: '{trigger_keywords[:30]}' → {action}")
        return intention

    def complete_intention(self, iid: str):
        """标记一条意图为已完成。"""
        if iid in self.data["intentions"]:
            entry = self.data["intentions"].pop(iid)
            entry["status"] = "completed"
            entry["completed_at"] = _now()
            self.data["completed"].append(entry)
            self._save()

    def cancel_intention(self, iid: str):
        """取消一条意图。"""
        if iid in self.data["intentions"]:
            entry = self.data["intentions"].pop(iid)
            entry["status"] = "cancelled"
            entry["cancelled_at"] = _now()
            self.data["completed"].append(entry)
            self._save()

    # ── Trigger Checking ───────────────────────────────────────────────────

    def check_triggers(self, context: str) -> list:
        """
        检查当前上下文是否触发任何前瞻意图。

        Args:
            context: 当前上下文字符串

        Returns:
            [{"intention_id", "action", "priority", "match_score"}, ...]
            按 priority × match_score 降序排列
        """
        lc = context.lower()
        triggered = []

        # Check and expire deadlines
        expired = []
        for iid, intent in self.data["intentions"].items():
            if intent["status"] != "active":
                continue

            # Check deadline
            try:
                deadline = datetime.fromisoformat(intent["deadline"])
                if deadline < datetime.now():
                    expired.append(iid)
                    continue
            except (ValueError, TypeError):
                pass

            # Check keyword match
            keywords = intent["trigger_keywords"]
            matches = sum(1 for kw in keywords if kw in lc)
            if matches > 0:
                match_score = matches / len(keywords)
                triggered.append({
                    "intention_id": iid,
                    "action": intent["action"],
                    "priority": intent["priority"],
                    "match_score": round(match_score, 3),
                })
                intent["trigger_count"] = intent.get("trigger_count", 0) + 1

        # Handle expired
        for iid in expired:
            intent = self.data["intentions"].pop(iid)
            intent["status"] = "expired"
            intent["expired_at"] = _now()
            self.data["completed"].append(intent)
            print(f"[ProspectiveMemory] Intention expired: {intent['action']}")

        if triggered or expired:
            self._save()

        # Sort by priority × match_score
        triggered.sort(key=lambda t: t["priority"] * t["match_score"], reverse=True)
        return triggered

    def get_active_intentions(self) -> list:
        """获取所有活跃意图。"""
        return [
            {"id": iid, "trigger": " ".join(i["trigger_keywords"]),
             "action": i["action"], "priority": i["priority"],
             "deadline": i.get("deadline_hours")}
            for iid, i in self.data["intentions"].items()
            if i["status"] == "active"
        ]

    def get_stats(self) -> dict:
        return {
            "active": len(self.data["intentions"]),
            "completed": sum(1 for c in self.data["completed"] if c["status"] == "completed"),
            "expired": sum(1 for c in self.data["completed"] if c["status"] == "expired"),
            "cancelled": sum(1 for c in self.data["completed"] if c["status"] == "cancelled"),
        }


if __name__ == "__main__":
    pm = ProspectiveMemory()
    pm.add_intention("下载 超时 timeout", "try_fix_three_times", deadline_hours=24, priority=4)
    pm.add_intention("格式 不支持 unsupported", "switch_skill", deadline_hours=48, priority=3)

    # Test triggers
    results = pm.check_triggers("P2b 下载卡住了，timeout 错误")
    print(f"\nTriggered: {results}")

    results2 = pm.check_triggers("everything is fine")
    print(f"No trigger: {results2}")

    stats = pm.get_stats()
    print(f"\nStats: {stats}")

    print("\n[ProspectiveMemory] Test passed!")
