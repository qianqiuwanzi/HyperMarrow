#!/usr/bin/env python3
"""
HyperMarrow Bridge Server
=========================
Listens on stdin for JSON-RPC 2.0 requests, calls HyperMarrow DecisionCheckPoint,
and writes JSON-RPC responses to stdout.

Protocol:
  - Input:  one JSON-RPC request per line (newline-delimited)
  - Output: one JSON-RPC response per line
  - Errors: JSON-RPC error response (don't crash the pipe)

Methods:
  ping       → health check
  check      → dc.check() + search
  record     → dc.record()
  search     → vector DB semantic search
  stats      → system statistics
  init       → re-initialize DC (for restart)
"""

import sys, json, os, time
from pathlib import Path

# ── Working directory: HyperMarrow package root ──────────────────
# Bridge is at: openclaw_memory_system/hypermarow_bridge.py
# Package root: openclaw_memory_system/
_BRIDGE_DIR = Path(__file__).parent.resolve()
_PACKAGE_ROOT = _BRIDGE_DIR  # openclaw_memory_system/
sys.path.insert(0, str(_PACKAGE_ROOT.parent.parent))

# ── Ensure UTF-8 ──────────────────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ── Redirect ALL stdout → stderr to prevent module init prints ───────
# from polluting the JSON-RPC response stream.  Keep a reference to
# the real stdout so _send_response() can still write JSON there.
_real_stdout = sys.stdout
sys.stdout = sys.stderr

# ── Observability (lazy import, path set in _init_hm) ─────────────────────
try:
    from metrics import RPCMetrics, get_metrics, LatencyBreakdown
    _metrics = get_metrics()  # global singleton
except ImportError:
    print("[HyperMarrow Bridge] metrics module not found, observability disabled", file=sys.stderr, flush=True)
    _metrics = None

# ── HyperMarrow Imports ───────────────────────────────────────────
print("[HyperMarrow Bridge] Initializing...", file=sys.stderr, flush=True)

_HM_READY = False
DC = None

def _init_hm():
    """Initialize HyperMarrow DecisionCheckPoint."""
    global DC, _HM_READY
    try:
        # Setup HuggingFace mirror
        try:
            from memory_core.config import setup_hf_mirror
            setup_hf_mirror()
        except ImportError:
            pass  # config may not exist

        # Create DC for openclaw agent
        from memory_integration.decision_check import create_for_agent
        DC = create_for_agent("openclaw")
        _HM_READY = True

        # ── Learning system is integrated via DC.ql_agent (full QLearningAgent) ──
        # No separate learning agent needed — DecisionCheckPoint handles RL natively

        # Get stats for startup log
        stats = _get_stats()
        print(
            f"[HyperMarrow Bridge] Ready. "
            f"PM={stats.get('procedural_memory',{}).get('total_rules',0)} rules, "
            f"QL={stats.get('q_learning',{}).get('nonzero',0)}/{stats.get('q_learning',{}).get('total',0)} Q, "
            f"VecDB={stats.get('vector_memory',{}).get('vectors',0)} vectors, "
            f"EM={stats.get('episodic_memory',{}).get('episodes',0)} episodes",
            file=sys.stderr, flush=True
        )

    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"[HyperMarrow Bridge] Init FAILED: {e}", file=sys.stderr, flush=True)
        _HM_READY = False


def _dummy_metrics():
    """Fallback if metrics import failed."""
    class _Dummy:
        def record(self, *a, **kw): pass
        def summary(self): return {}
        def health_check(self): return {"status": "DISABLED"}
    return _Dummy()

if _metrics is None:
    _metrics = _dummy_metrics()
def _get_stats() -> dict:
    """Get current system statistics."""
    if not _HM_READY or DC is None:
        return {"ready": False}

    import numpy as np

    pm_stats = {}
    # Try DC.procedural_memory first
    if DC is not None and DC.procedural_memory is not None:
        try:
            rules = DC.procedural_memory.list_rules()
            pm_stats = {
                "total_rules": len(rules),
                "levels": sorted(set(r.get("level", 1) for r in rules)),
            }
        except Exception as e:
            pm_stats = {"error": str(type(e).__name__)}
    else:
        # Fallback: load ProceduralMemory directly from data dir
        try:
            from memory_core.procedural_memory import ProceduralMemory
            pm = ProceduralMemory()
            rules = pm.list_rules()
            pm_stats = {
                "total_rules": len(rules),
                "levels": sorted(set(r.get("level", 1) for r in rules)),
                "source": "fallback_direct_load"
            }
        except Exception as e:
            pm_stats = {"error": f"fallback failed: {type(e).__name__}: {e}"}

    ql_stats = {}
    if DC.ql_agent:
        try:
            qt = DC.ql_agent.q_table
            nonzero = int(np.count_nonzero(qt))
            ql_stats = {
                "nonzero": nonzero,
                "total": int(qt.size),
                "pct": f"{100*nonzero/max(qt.size,1):.1f}%",
                "buffer_size": len(DC.ql_agent.experience_buffer),
            }
        except Exception as e:
            ql_stats = {"error": str(type(e).__name__)}

    vec_count = 0
    if DC.vector_db:
        try:
            s = DC.vector_db.get_stats()
            vec_count = s.get("total_vectors", 0)
        except Exception:
            pass

    em_count = 0
    try:
        episodes = DC.episodic_memory.data.get("episodes", [])
        em_count = len(episodes)
    except Exception:
        pass

    wm_count = 0
    try:
        entries = DC.working_memory.data.get("entries", [])
        wm_count = len(entries)
    except Exception:
        pass

    kg_count = 0
    if DC.knowledge_graph:
        try:
            kg_count = len(DC.knowledge_graph.data.get("entities", {}))
        except Exception:
            pass

    # ── Observability: RPC metrics + health check ───────────────────
    try:
        rpc_summary = _metrics.summary()
        health = _metrics.health_check()
    except Exception:
        rpc_summary = {}
        health = {"status": "UNKNOWN"}

    return {
        "ready": True,
        "agent_id": DC._agent_id if DC else "none",
        "procedural_memory": pm_stats,
        "q_learning": ql_stats,
        "vector_memory": {"vectors": vec_count},
        "episodic_memory": {"episodes": em_count},
        "working_memory": {"entries": wm_count},
        "knowledge_graph": {"entities": kg_count},
        # ── New: observability ────────────────────────────────────────
        "metrics": rpc_summary,
        "health": health,
        "timestamp": time.time(),
    }



_init_hm()


# ── Token counter helpers ─────────────────────────────────────────────────
import re as _re

def _count_tokens(text: str) -> int:
    """Character-based token estimation. Chinese=1, English words=0.4, other=0.25."""
    if not text:
        return 0
    chinese = len(_re.findall(r'[\u4e00-\u9fff\uff00-\uffef]', text))
    english = len(_re.findall(r'[a-zA-Z]+', text))
    ascii_other = len(_re.findall(r'[a-zA-Z0-9.,!?;:\s]', text)) - sum(len(w) for w in _re.findall(r'[a-zA-Z]+', text))
    return max(1, round(chinese * 1.0 + english * 0.4 + ascii_other * 0.25))


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Binary-search truncate text to max_tokens."""
    if max_tokens <= 0 or not text:
        return ""
    if _count_tokens(text) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if _count_tokens(text[:mid]) <= max_tokens:
            lo = mid
        else:
            hi = mid
    return text[:lo]


# ── Core Functions ───────────────────────────────────────────────────────────────

def _build_context_prompt(context: dict, max_chars: int = 1800, max_tokens: int = 600) -> str:
    """
    Build a system-prompt-ready context summary from HyperMarrow check result.

    Sources (in priority order):
    1. ProceduralMemory — matched rules (Level ≥ 2)
    2. RL Q-Learning    — current state recommended action
    3. VectorMemoryDB   — similar past decisions (top-3, quality-filtered)
    4. WorkingMemory    — current task context summary
    5. KnowledgeGraph   — related entities

    Token budget: Each source has a max allocation; exceeded sources are
    truncated with priority ordering.

    Args:
        context: DC.check() result dict
        max_chars: Character limit (soft, for display)
        max_tokens: Hard token budget (default 600 ≈ ~2400 chars)

    Returns:
        Markdown-formatted context string
    """
    # Token budget per source (total = 600 tokens)
    TOKEN_BUDGET = {"header": 5, "rules": 120, "rl": 80, "vecdb": 200,
                     "wm": 60, "kg": 80, "warnings": 55}
    total_budget = max_tokens - 10  # reserve for overhead

    # Source priority (higher = more important, cut last)
    SOURCE_PRIORITY = ["header", "warnings", "rl", "rules", "wm", "kg", "vecdb"]

    parts = []  # [(name, text, tokens), ...]

    # 0. Header (fixed)
    parts.append(("header", "[HyperMarrow Memory]", _count_tokens("[HyperMarrow Memory]")))

    # 1. Procedural rules — quality filter: only Level ≥ 2
    pm_hints = context.get("procedural_hints", [])
    filtered_rules = [h for h in pm_hints if h.get("level", 1) >= 2]
    rules_lines = []
    if filtered_rules:
        rules_lines.append("**Relevant Rules:**")
        for h in filtered_rules[:4]:
            level = h.get("level", 1)
            name = h.get("rule_name", "unknown")
            sr = h.get("success_rate", 0)
            stars = "⭐" * min(level, 5)
            rules_lines.append(f"- {stars} *{name}* (success: {sr:.0%})")
    rules_text = "\n".join(rules_lines) if rules_lines else None
    if rules_text:
        parts.append(("rules", rules_text, _count_tokens(rules_text)))

    # 2. RL recommendation
    rl = context.get("rl_recommendation", {})
    rl_lines = []
    if rl.get("recommended_action"):
        conf = rl.get("confidence", 0)
        q_val = rl.get("q_value", 0)
        rec = rl.get("recommended_action")
        rl_lines.append(f"**RL Policy:** `{rec}` (Q={q_val:.3f}, conf={conf:.0%})")
        if conf < 0.25:
            rl_lines.append("⚠️ Low confidence. Verify carefully.")
    rl_text = "\n".join(rl_lines) if rl_lines else None
    if rl_text:
        parts.append(("rl", rl_text, _count_tokens(rl_text)))

    # 3. Vector DB — quality filter: similarity ≥ 0.5
    vec_results = context.get("vector_results", [])
    similar_memories = context.get("similar_memories", [])
    all_similar = vec_results + [
        {"preview": m if isinstance(m, str) else m.get("preview", ""),
         "score": m.get("score", 0) if isinstance(m, dict) else 0}
        for m in similar_memories
    ]
    # Quality filter: similarity > 0.4 (score < 0.6)
    filtered_sim = [v for v in all_similar
                    if v.get("preview") and (1 - float(v.get("score", 1))) > 0.4]
    seen = set()
    vecdb_lines = []
    if filtered_sim:
        vecdb_lines.append("**Similar Past Decisions:**")
        for v in filtered_sim[:4]:
            preview = v.get("preview", "")
            if not preview or preview in seen:
                continue
            seen.add(preview)
            score = v.get("score", 0)
            sim = 1 - float(score) if score is not None else 0.5
            vecdb_lines.append(f"- [match={sim:.0%}] {preview[:150]}")
    vecdb_text = "\n".join(vecdb_lines) if vecdb_lines else None
    if vecdb_text:
        parts.append(("vecdb", vecdb_text, _count_tokens(vecdb_text)))

    # 4. Working memory summary
    wm = context.get("working_memory_summary", "")
    wm_text = f"**Current Context:** {wm}" if wm else None
    if wm_text:
        parts.append(("wm", wm_text, _count_tokens(wm_text)))

    # 5. Knowledge graph
    entities = context.get("related_entities", [])
    kg_lines = []
    if entities:
        kg_lines.append("**Related Knowledge:**")
        for e in entities[:5]:
            src = e.get("source", "")
            rel = e.get("related", "")
            typ = e.get("type", "")
            if src and rel:
                kg_lines.append(f"- {src} → {rel} ({typ})")
    kg_text = "\n".join(kg_lines) if kg_lines else None
    if kg_text:
        parts.append(("kg", kg_text, _count_tokens(kg_text)))

    # 6. Warnings
    warnings = context.get("warnings", [])
    warn_lines = []
    for w in warnings[:3]:
        if isinstance(w, str) and (w.startswith("[PM]") or w.startswith("[RL]")
                                  or w.startswith("[ARB]") or w.startswith("[KG]")):
            warn_lines.append(w)
    warn_text = "\n".join(warn_lines) if warn_lines else None
    if warn_text:
        parts.append(("warnings", warn_text, _count_tokens(warn_text)))

    # ── Token budget allocation ────────────────────────────────────────
    result_parts = []
    used_tokens = 0

    # Sort by priority (low priority first for truncation)
    priority_map = {name: i for i, name in enumerate(SOURCE_PRIORITY)}
    sorted_parts = sorted(parts, key=lambda x: priority_map.get(x[0], 99))

    remaining = total_budget
    for name, text, tokens in sorted_parts:
        if tokens <= remaining:
            result_parts.append((name, text, tokens))
            remaining -= tokens
        else:
            # Truncate this part to fit
            truncated = _truncate_to_tokens(text, remaining)
            if truncated:
                result_parts.append((name, truncated, _count_tokens(truncated)))
            break

    # Sort back to display order
    result_parts.sort(key=lambda x: SOURCE_PRIORITY.index(x[0]) if x[0] in SOURCE_PRIORITY else 99)

    # Join
    result = "\n".join(text for _, text, _ in result_parts)
    total_used = sum(t for _, _, t in result_parts)

    if len(result) > max_chars:
        result = result[:max_chars] + f"\n... [+{len(result)-max_chars} chars]"

    return result



def _handle_check(params: dict) -> dict:
    """Process a check() RPC call."""
    if not _HM_READY or DC is None:
        return {"success": False, "error": "HyperMarrow not initialized"}

    session_key = params.get("session_key", "unknown")
    action = params.get("action", "agent_think")
    raw_context = params.get("context", {})

    ctx_for_check = {
        "session_key": session_key,
        "channel": raw_context.get("channelId", raw_context.get("channel", "webchat")),
        "provider": raw_context.get("provider", "webchat"),
        "trigger": raw_context.get("trigger", ""),
        "agent_id": raw_context.get("agentId", "openclaw"),
        "raw": raw_context,
    }

    try:
        check_result = DC.check(action=action, context=ctx_for_check)
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": f"dc.check() failed: {e}"}

    # ── Learning System: RL suggestion from full QLearningAgent ──
    learning_suggestion = None
    if DC.ql_agent is not None:
        try:
            state_idx = DC.ql_agent.state_to_index(ctx_for_check)
            action_idx = DC.ql_agent.get_action(state_idx, training=False)
            from memory_core.q_learning_agent import ACTIONS as _ACT
            action_name = _ACT[action_idx] if action_idx < len(_ACT) else "unknown"
            # Get Q-values for confidence
            q_vals = DC.ql_agent.q_table[state_idx, :]
            max_q = float(np.max(np.abs(q_vals))) if hasattr(np, 'max') else 1.0
            confidence = float(q_vals[action_idx]) / (max_q + 1e-6) if max_q > 0 else 0.0
            confidence = max(0.0, min(1.0, confidence))
            learning_suggestion = {
                "action": action_name,
                "confidence": round(confidence, 3),
                "source": "ql_agent"
            }
        except Exception as e:
            print(f"[Learning] RL suggestion failed: {e}", file=sys.stderr, flush=True)

    # Build injection text
    inject_text = _build_context_prompt(check_result)

    # Build context_prompt (for direct use by LLM)
    context_prompt = inject_text  # alias for clarity

    return {
        "success": True,
        "allowed": check_result.get("allowed", True),
        "suggestion": check_result.get("suggestion"),
        "confidence": check_result.get("confidence", 0.5),
        "inject_text": inject_text,
        "context_prompt": context_prompt,
        "warnings": check_result.get("warnings", []),
        "rule": check_result.get("rule"),
        "rl_recommendation": check_result.get("rl_recommendation"),
        "learning_suggestion": learning_suggestion,
        "similar_memories": check_result.get("similar_memories", [])[:5],
        "metadata": {
            "agent_id": DC._agent_id,
            "source": "hypermarow_bridge",
            "session_key": session_key,
        }
    }


def _handle_record(params: dict) -> dict:
    """Process a record() RPC call."""
    if not _HM_READY or DC is None:
        return {"success": False, "error": "HyperMarrow not initialized"}

    session_key = params.get("session_key", "unknown")
    action = params.get("action", "")
    raw_context = params.get("context", {})
    outcome = params.get("outcome", "partial")
    reward = params.get("reward")
    note = params.get("note", "")

    ctx_for_record = {
        "session_key": session_key,
        "channel": raw_context.get("channelId", raw_context.get("channel", "webchat")),
        "raw": raw_context,
    }

    try:
        DC.record(
            action=action,
            context=ctx_for_record,
            outcome=outcome,
            reward=reward,
            note=note,
        )
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": f"dc.record() failed: {e}"}

    # ── Learning System: RL already recorded via DC.record() ──────

    # Return updated stats
    import numpy as np
    ql_stats = {}
    if DC.ql_agent:
        qt = DC.ql_agent.q_table
        ql_stats = {
            "nonzero": int(np.count_nonzero(qt)),
            "total": int(qt.size),
            "buffer": len(DC.ql_agent.experience_buffer),
        }

    em_count = 0
    try:
        em_count = len(DC.episodic_memory.data.get("episodes", []))
    except Exception:
        pass

    return {
        "success": True,
        "outcome_recorded": outcome,
        "ql_stats": ql_stats,
        "em_count": em_count,
    }


def _handle_search(params: dict) -> dict:
    """Process a semantic search RPC call."""
    if not _HM_READY or DC is None:
        return {"success": False, "error": "HyperMarrow not initialized"}

    query = params.get("query", "")
    n_results = params.get("n_results", 5)

    if not query:
        return {"success": True, "results": []}

    results = []
    if DC.vector_db:
        try:
            search_results = DC.vector_db.search(query, n_results=n_results)
            if search_results.get("ids") and search_results["ids"][0]:
                for i, mem_id in enumerate(search_results["ids"][0]):
                    dist = None
                    if search_results.get("distances"):
                        try:
                            dist = float(search_results["distances"][0][i])
                        except (IndexError, TypeError):
                            pass
                    doc = ""
                    if search_results.get("documents"):
                        try:
                            doc = str(search_results["documents"][0][i] or "")
                        except (IndexError, TypeError):
                            pass
                    results.append({
                        "id": mem_id,
                        "score": dist,
                        "similarity": round(1 - dist, 4) if dist is not None else None,
                        "preview": doc[:200],
                    })
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": True, "query": query, "results": results}


# ── JSON-RPC Server (stdin/stdout) ─────────────────────────────────

def _send_response(response: dict):
    """Write a JSON-RPC response to stdout."""
    line = json.dumps(response, ensure_ascii=False)
    _real_stdout.write(line + "\n")
    _real_stdout.flush()


def _send_error(request_id, code: int, message: str):
    """Write a JSON-RPC error to stdout."""
    _send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    })


def serve():
    """Main stdin/stdout JSON-RPC loop."""
    print("[HyperMarrow Bridge] Started, listening on stdin...", 
          file=sys.stderr, flush=True)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                # EOF: stdin closed — graceful exit
                print("[HyperMarrow Bridge] stdin closed, exiting.", 
                      file=sys.stderr, flush=True)
                break

            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            # Route with metrics tracking
            error = False
            t0 = time.perf_counter()
            try:
                if method == "ping":
                    result = {"success": True, "pong": True, "ready": _HM_READY}
                elif method == "check":
                    with LatencyBreakdown() as lb:
                        result = _handle_check(params)
                        lb.split("dc_check")
                        # Extract sub-timing if available
                        if isinstance(result, dict) and "_latency_ms" in result:
                            result["_latency_breakdown"] = {"_total_ms": result.pop("_latency_ms")}
                elif method == "record":
                    result = _handle_record(params)
                elif method == "search":
                    result = _handle_search(params)
                elif method == "stats":
                    result = _get_stats()
                elif method == "init":
                    _init_hm()
                    result = {"success": True, "ready": _HM_READY}
                else:
                    _send_error(request_id, -32601, f"Unknown method: {method}")
                    continue
            except Exception as e:
                error = True
                result = {"success": False, "error": str(e)}
            finally:
                latency_ms = (time.perf_counter() - t0) * 1000
                _metrics.record(method, latency_ms, error=error)
                # Attach metrics to result for diagnostics
                if isinstance(result, dict):
                    result["_metrics"] = {
                        "method": method,
                        "latency_ms": round(latency_ms, 2),
                        "error": error,
                    }

            _send_response({"jsonrpc": "2.0", "id": request_id, "result": result})

        except json.JSONDecodeError as e:
            print(f"[HyperMarrow Bridge] JSON error: {e} | input: {line[:100]}",
                  file=sys.stderr, flush=True)
            _send_error(request_id=None, code=-32700, message=f"Invalid JSON: {e}")

        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            req_id = request.get("id") if 'request' in dir() else None
            _send_error(req_id, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    serve()
