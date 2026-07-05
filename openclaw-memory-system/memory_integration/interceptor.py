"""
HyperMarrow Interceptor — 消息拦截器

对标 GBrain 的 gbrain_dispatch 协议。
每条 OpenClaw 消息自动触发：实体提取 → 消息存档 → 规则匹配 → 意图检测。
默认在后台 daemon 线程执行，不阻塞主响应。
"""
import sys, os
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Path setup: MUST run before any memory_core imports ──────────────────────
_HERE = Path(__file__).parent.parent  # openclaw-memory-system/
_LEARNING = _HERE.parent / "openclaw-learning-system"
for _p in [str(_HERE), str(_LEARNING)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_DC = None
_REG = None


def _ensure_dc(agent_id: str = "openclaw"):
    global _DC, _REG
    if _DC is None:
        from memory_integration.decision_check import create_for_agent, get_agent_registry
        _DC = create_for_agent(agent_id)
        _REG = get_agent_registry()
    return _DC


def hypermarow_intercept(user_message: str,
                          agent_response: str = "",
                          agent_id: str = "openclaw",
                          inherit_from: str = None,
                          inherit_level: str = "rules",
                          blocking: bool = False) -> dict:
    """
    OpenClaw 每条消息后自动调用。

    对标 GBrain 的 gbrain_dispatch:
      - signal-detector: 从消息中检测实体/想法 → KG
      - brain-ops: 消息存档 → EM
      - rule matching: 上下文匹配 → PM
      - intention detection: 意图匹配 → ProspectiveMemory

    Args:
        user_message: 用户消息原文
        agent_response: Agent 回复 (可选)
        agent_id: 当前 Agent ID
        inherit_from: 父 Agent ID — 子代理继承其 PM 规则和 KG 实体
        inherit_level: "rules" | "full" | "none" — 继承级别
        blocking: True=同步执行, False=后台线程 (默认)

    Returns:
        {"entities_found": int, "episodes_created": int,
         "rules_matched": int, "intentions_triggered": int,
         "inherited_from": str or None}
    """
    if blocking:
        return _intercept_sync(user_message, agent_response, agent_id,
                                inherit_from, inherit_level)
    else:
        result_holder = {}
        t = threading.Thread(
            target=lambda: result_holder.update(
                _intercept_sync(user_message, agent_response, agent_id,
                                inherit_from, inherit_level)),
            daemon=True, name=f"hm_intercept"
        )
        t.start()
        return {"status": "queued", "thread": t.name}


def _intercept_sync(user_message: str, agent_response: str,
                     agent_id: str, inherit_from: str = None,
                     inherit_level: str = "rules") -> dict:
    """Synchronous interceptor logic."""
    dc = _ensure_dc(agent_id)
    result = {"entities_found": 0, "episodes_created": 0,
              "rules_matched": 0, "intentions_triggered": 0,
              "inherited_from": None}

    combined_text = user_message
    if agent_response:
        combined_text += " " + agent_response[:200]

    # ── P0-1: Child agent memory inheritance ──────────────────────────────
    if inherit_from and inherit_level != "none":
        try:
            parent_dc = _ensure_dc(inherit_from)
            inherited_count = 0

            # Inherit PM rules: match parent's rules against current context
            if inherit_level in ("rules", "full"):
                parent_rules = parent_dc.procedural_memory.check_context(combined_text)
                if parent_rules:
                    wm = dc.working_memory
                    rule_names = [r["rule_name"] for r in parent_rules[:5]]
                    wm.update_context(inherited_rules=", ".join(rule_names))
                    inherited_count += len(rule_names)

            # Inherit KG entities: copy parent's matching entities
            if inherit_level == "full":
                parent_entities = parent_dc.knowledge_graph.extract_entities_from_text(
                    combined_text)
                for ent in parent_entities[:3]:
                    dc.knowledge_graph.add_entity(
                        ent["name"], ent["type"], ent.get("properties", {}))
                    inherited_count += 1

            result["inherited_from"] = inherit_from
            if inherited_count > 0:
                print(f"[Interceptor] Inherited {inherited_count} items from '{inherit_from}' "
                      f"(level={inherit_level})", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[Interceptor] Inheritance failed: {e}", file=sys.stderr, flush=True)

    try:
        # 1. Entity extraction → KG
        kg = dc.knowledge_graph
        entities = kg.extract_entities_from_text(combined_text)
        result["entities_found"] = len(entities)

        # 2. Message archival → EM
        what = user_message[:100]
        if len(user_message) > 100:
            what += "..."
        ep = dc.episodic_memory.add_episode(
            what=f"[Intercept] {what}",
            context={
                "user_message": user_message[:200],
                "agent_response": agent_response[:200] if agent_response else "",
                "agent_id": agent_id,
            },
            outcome="partial",
            emotion="neutral",
            tags=["intercept", agent_id],
            importance=2,
        )
        if ep:
            result["episodes_created"] = 1

        # 3. Rule matching → PM
        pm_matches = dc.procedural_memory.check_context(combined_text)
        result["rules_matched"] = len(pm_matches)

        # 4. Intention detection → ProspectiveMemory
        if hasattr(dc, 'prospective') and dc.prospective:
            triggers = dc.prospective.check_triggers(combined_text)
            result["intentions_triggered"] = len(triggers)

    except Exception as e:
        print(f"[Interceptor] Error: {e}", file=sys.stderr, flush=True)

    return result


def get_interceptor_stats() -> dict:
    """返回拦截器运行统计。"""
    return {
        "dc_initialized": _DC is not None,
        "agent_count": len(_REG.list_agents()) if _REG else 0,
    }


# ── Simple test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from memory_core.config import setup_hf_mirror
    setup_hf_mirror()

    r = hypermarow_intercept(
        "P2b 下载 timeout 了，试试重试3次吧",
        blocking=True
    )
    print(f"Intercept result: {r}")
    assert r["entities_found"] >= 1, f"Expected entities, got {r}"
    assert r["episodes_created"] >= 1
    print("Interceptor test passed!")
