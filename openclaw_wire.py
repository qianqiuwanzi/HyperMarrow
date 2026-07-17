#!/usr/bin/env python3
"""
OpenClaw ↔ HyperMarrow 一线接线脚本

OpenClaw 只需 import 这一个文件，即可获得：
  1. Interceptor — 每条消息自动触发（实体提取+存档+规则匹配）
  2. MCP 工具 — check/record/search/stats/transfer
  3. CLI — 所有 hypermarrow 命令

用法（OpenClaw 入口文件加一行）:
    from openclaw_wire import hm
    hm.intercept("用户消息", "Agent回复")
    result = hm.check("try_fix_three_times", task="下载失败")
    hm.record("try_fix_three_times", {"task":"下载"}, "success")
"""
import sys, os, threading
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

_DC = None
_REG = None
_INITIALIZED = False


def _init():
    global _DC, _REG, _INITIALIZED
    if _INITIALIZED:
        return
    from memory_integration.decision_check import create_for_agent, get_agent_registry
    _DC = create_for_agent("openclaw")
    _REG = get_agent_registry()
    _INITIALIZED = True
    kg = _DC.knowledge_graph.get_stats()
    ql = _DC.ql_agent.get_stats()
    pm = len(_DC.procedural_memory.data.get("rules", {}))
    print(f"[HyperMarrow] Ready: KG={kg['total_entities']}, QL={ql['nonzero_entries']}/700, "
          f"PM={pm}, EM={_DC.episodic_memory.get_stats()['total_episodes']}")

    # ── Heartbeat thread: keep agent connection alive ─────────────────────
    _start_heartbeat()
    # ── Dream scheduler: periodic memory consolidation (prevents leaks) ────
    _start_dream_scheduler()


def _start_heartbeat():
    """Start a daemon heartbeat thread to keep openclaw agent connected."""
    import urllib.request
    _heartbeat_started = getattr(_start_heartbeat, '_started', False)
    if _heartbeat_started:
        return
    _start_heartbeat._started = True

    def _beat():
        # Send initial connect, then heartbeat every 30s
        url_connect = 'http://localhost:8741/api/v1/agents/openclaw/connect'
        url_beat = 'http://localhost:8741/api/v1/agents/openclaw/heartbeat'
        # Initial connect
        try:
            urllib.request.urlopen(urllib.request.Request(url_connect, method='POST'), timeout=3)
        except Exception:
            pass
        # Periodic heartbeat
        while True:
            try:
                urllib.request.urlopen(urllib.request.Request(url_beat, method='POST'), timeout=3)
            except Exception:
                pass  # API server might not be running
            import time
            time.sleep(30)

    t = threading.Thread(target=_beat, daemon=True, name="hm_heartbeat")
    t.start()


def _start_dream_scheduler():
    """Start a daemon dream scheduler — runs consolidation every 4 hours.
    Prevents unbounded memory growth in long-running SDK processes.
    Mirrors the API server's _dream_scheduler behavior."""
    _dream_started = getattr(_start_dream_scheduler, '_started', False)
    if _dream_started:
        return
    _start_dream_scheduler._started = True

    def _schedule():
        import time as _time
        _time.sleep(300)  # Wait 5 min after startup before first cycle
        while True:
            try:
                _init()
                _DC.consolidator.dream_cycle(force=True)
                print(f"[Dream Scheduler] Cycle completed — memory pruned", flush=True)
            except Exception as e:
                print(f"[Dream Scheduler] Failed: {e}", flush=True)
            _time.sleep(14400)  # Every 4 hours

    t = threading.Thread(target=_schedule, daemon=True, name="hm_dream_scheduler")
    t.start()


class HyperMarrowWire:
    """OpenClaw 一线接入接口"""

    @property
    def dc(self):
        _init(); return _DC

    @property
    def reg(self):
        _init(); return _REG

    def intercept(self, user_message: str, agent_response: str = "",
                  blocking: bool = False) -> dict:
        """
        每条消息后调用。非阻塞（默认）。

        对标 GBrain gbrain_dispatch: 实体提取→KG, 消息存档→EM, 规则匹配→PM。
        """
        from memory_integration.interceptor import hypermarow_intercept
        return hypermarow_intercept(user_message, agent_response,
                                     blocking=blocking)

    def check(self, action: str, **context) -> dict:
        """决策检查 — 等价于 MCP check 工具"""
        _init()
        return _DC.check(action=action, context=context if context else None)

    def record(self, action: str, context: dict = None, outcome: str = "success",
               reward: float = None, note: str = "", async_mode: bool = True):
        """记录决策 — 等价于 MCP record 工具。默认异步。"""
        _init()
        _DC.record(action=action, context=context or {}, outcome=outcome,
                    reward=reward, note=note, async_mode=async_mode)

    def search(self, query: str, limit: int = 5, days: int = 30) -> list:
        """搜索记忆"""
        _init()
        return _DC.episodic_memory.search_episodes(query, n=limit)

    def stats(self) -> dict:
        """全系统统计"""
        _init()
        return {
            "kg": _DC.knowledge_graph.get_stats(),
            "ql": _DC.ql_agent.get_stats(),
            "em": _DC.episodic_memory.get_stats(),
            "pm": len(_DC.procedural_memory.data.get("rules", {})),
            "meta": _DC.metacognition.get_performance_dashboard(),
            "agents": _REG.list_agents(),
        }

    def dream(self) -> dict:
        """触发记忆巩固"""
        _init()
        return _DC.consolidator.dream_cycle(force=True)

# ── Global singleton ─────────────────────────────────────────────────────
hm = HyperMarrowWire()

# ── Auto-init on import ──────────────────────────────────────────────────
_init()


# ── Test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Agents: {hm.reg.list_agents()}")
    print(f"KG: {hm.dc.knowledge_graph.get_stats()['total_entities']} entities")

    # Test intercept
    r = hm.intercept("P2b 下载 timeout，重试3次", blocking=True)
    print(f"Intercept: entities={r['entities_found']}, "
          f"episodes={r['episodes_created']}, rules={r['rules_matched']}")

    # Test check
    result = hm.check("try_fix_three_times", task="download_timeout", phase="P2b")
    rl = result.get("rl_recommendation", {}) or {}
    print(f"Check: RL recommends {rl.get('recommended_action', '?')} "
          f"(conf={rl.get('confidence', 0):.0%})")

    # Test async record
    hm.record("try_fix_three_times", {"task": "wire_test"}, "success",
              async_mode=True)
    print("Record: queued (async)")

    # Test dream
    dr = hm.dream()
    print(f"Dream: status={dr['status']}, phases={list(dr.get('phases',{}).keys())}")

    print("\nOpenClaw wiring: ALL OK")
