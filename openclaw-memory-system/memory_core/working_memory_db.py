"""
Working Memory — P1 Foundational Memory Type.

Maintains a sliding-window context buffer for the current session.
API: update_context(), get_active_context(), set_task(), push_task(), pop_task()
"""
import json
from pathlib import Path
from datetime import datetime
from .config import get_data_dir

DATA_DIR = get_data_dir()
WORKING_MEM_FILE = DATA_DIR / "working_memory.json"
MAX_WORKING_SIZE = 50


class WorkingMemoryDB:
    """
    工作记忆缓冲区 — 维护当前会话的活跃上下文。

    与程序性记忆（长期规则）和情景记忆（历史事件）不同，
    工作记忆只保留最近 N 条上下文，支持"当前任务是什么"类查询。

    数据结构
    --------
    {
      "active_context": { key: value }   # 当前上下文键值对
      "context_stack":  [ {...}, ... ]   # 任务栈（push/pop）
      "recent_items":   [ {...}, ... ]   # 最近 N 条记录（sliding window）
      "current_task":   str | null       # 当前任务描述
      "goal":           str | null        # 当前目标
      "session_id":     str              # 会话ID
      "updated_at":     ISO string
    }
    """

    def __init__(self, path=None):
        if path is None:
            path = WORKING_MEM_FILE
        self.path = Path(path) if not isinstance(path, Path) else path
        self.data = self._load_or_init()
        print(f"[WorkingMemory] Loaded: {len(self.data.get('recent_items', []))} recent, "
              f"task={self.data.get('current_task', 'none')}")

    def _load_or_init(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[WorkingMemory] Load failed, using defaults: {e}")
        return {
            "version": "1.0",
            "session_id": datetime.now().isoformat(),
            "active_context": {},
            "context_stack": [],
            "recent_items": [],
            "current_task": None,
            "goal": None,
            "updated_at": datetime.now().isoformat(),
        }

    def _save(self):
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── Core API ──────────────────────────────────────────────────────────────

    def update_context(self, **kwargs):
        """
        更新当前上下文键值。

        用法:
            wm.update_context(task="P2b下载", phase="P2b", attempts=3)
        """
        self.data.setdefault("active_context", {}).update(kwargs)
        self._add_recent_item({"type": "context_update", "data": kwargs})
        self._save()
        print(f"[WorkingMemory] Context updated: {kwargs}")

    def set_task(self, task: str, goal: str = None):
        """设置当前任务和目标。"""
        self.data["current_task"] = task
        self.data["goal"] = goal
        self._add_recent_item({"type": "task_start", "task": task, "goal": goal})
        self._save()
        print(f"[WorkingMemory] Task set: {task} | goal: {goal}")

    def push_task(self, task: str, context: dict = None):
        """压入子任务到栈（支持嵌套）。"""
        self.data.setdefault("context_stack", []).append({
            "task": task,
            "context": context or {},
            "previous_task": self.data.get("current_task"),
            "pushed_at": datetime.now().isoformat(),
        })
        self.data["current_task"] = task
        self._add_recent_item({"type": "task_push", "task": task})
        self._save()
        print(f"[WorkingMemory] Task pushed: {task} (stack depth={len(self.data['context_stack'])})")

    def pop_task(self) -> str | None:
        """弹出栈顶子任务，返回弹出的任务名，并恢复上一级任务。"""
        stack = self.data.get("context_stack", [])
        if not stack:
            return None
        popped = stack.pop()
        if stack:
            self.data["current_task"] = stack[-1]["task"]
        else:
            self.data["current_task"] = popped.get("previous_task")
        self._add_recent_item({"type": "task_pop", "task": popped["task"]})
        self._save()
        print(f"[WorkingMemory] Task popped: {popped['task']}")
        return popped["task"]

    def get_active_context(self) -> dict:
        """
        获取当前完整活跃上下文。

        Returns:
            {
              "active_context": { ... },
              "current_task": str | null,
              "goal": str | null,
              "session_id": str,
              "updated_at": str,
              "stack_depth": int,
            }
        """
        return {
            "active_context": self.data.get("active_context", {}),
            "current_task": self.data.get("current_task"),
            "goal": self.data.get("goal"),
            "session_id": self.data.get("session_id"),
            "updated_at": self.data.get("updated_at"),
            "stack_depth": len(self.data.get("context_stack", [])),
        }

    def get_context_summary(self) -> str:
        """人类可读的上下文摘要（用于 RL context 注入）。"""
        ctx = self.data.get("active_context", {})
        task = self.data.get("current_task", "无")
        goal = self.data.get("goal", "无")
        stack = self.data.get("context_stack", [])
        parts = [f"task={task}"]
        if goal:
            parts.append(f"goal={goal}")
        if ctx:
            ctx_str = ", ".join(f"{k}={v}" for k, v in ctx.items() if k not in ("task", "goal"))
            if ctx_str:
                parts.append(f"ctx=({ctx_str})")
        if stack:
            parts.append(f"stack_depth={len(stack)}")
        return " | ".join(parts)

    def get_recent(self, n: int = 10) -> list:
        """获取最近 N 条工作记忆记录。"""
        return self.data.get("recent_items", [])[-n:]

    def clear(self):
        """清空工作记忆（开始新会话时调用）。"""
        old_session = self.data.get("session_id")
        # Delete persisted file so _load_or_init creates a fresh state
        if self.path.exists():
            self.path.unlink()
        self.data = self._load_or_init()
        self.data["session_id"] = datetime.now().isoformat()
        self._save()
        print(f"[WorkingMemory] Cleared (old session: {old_session})")

    def _add_recent_item(self, item: dict):
        """追加到 recent_items 并做 sliding window 截断。"""
        item["ts"] = datetime.now().isoformat()
        recent = self.data.setdefault("recent_items", [])
        recent.append(item)
        if len(recent) > MAX_WORKING_SIZE:
            self.data["recent_items"] = recent[-MAX_WORKING_SIZE:]

    def get_stats(self) -> dict:
        """返回统计信息。"""
        return {
            "recent_count": len(self.data.get("recent_items", [])),
            "context_keys": list(self.data.get("active_context", {}).keys()),
            "current_task": self.data.get("current_task"),
            "goal": self.data.get("goal"),
            "stack_depth": len(self.data.get("context_stack", [])),
            "session_id": self.data.get("session_id"),
            "updated_at": self.data.get("updated_at"),
        }
