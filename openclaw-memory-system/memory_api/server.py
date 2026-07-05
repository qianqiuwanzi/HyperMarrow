#!/usr/bin/env python3
"""
HyperMarrow Crystal Core API — FastAPI backend for Web visualization.

Start:  uvicorn memory_api.server:app --host 0.0.0.0 --port 8741
"""
import sys, json, asyncio
from pathlib import Path
from datetime import datetime

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "openclaw-learning-system"))

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np

app = FastAPI(title="HyperMarrow Crystal Core", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_DC = None
_REG = None
_WS_CLIENTS = set()

def _init():
    global _DC, _REG
    if _DC is None:
        from memory_core.config import setup_hf_mirror; setup_hf_mirror()
        from memory_integration.decision_check import create_for_agent, get_agent_registry
        _DC = create_for_agent("openclaw")
        _REG = get_agent_registry()


# ── REST Endpoints ────────────────────────────────────────────────────────

@app.get("/api/v1/stats")
def api_stats():
    _init()
    kg = _DC.knowledge_graph.get_stats()
    ql = _DC.ql_agent.get_stats()
    em = _DC.episodic_memory.get_stats()
    meta = _DC.metacognition.get_performance_dashboard()
    pm = _DC.procedural_memory.data
    return {
        "kg": {"entities": kg["total_entities"], "relationships": kg["total_relationships"],
               "density": kg["density"], "types": kg.get("entity_types", {})},
        "ql": {"nonzero": ql["nonzero_entries"], "total": ql["total_entries"],
               "nonzero_pct": ql["nonzero_pct"], "buffer": ql["total_experiences"],
               "mode": ql.get("neural_mode", "tabular"), "states": ql.get("distinct_states", 0)},
        "em": {"episodes": em["total_episodes"], "with_lessons": em.get("with_lessons", 0),
               "avg_importance": em.get("avg_importance", 0)},
        "pm": {"rules": len(pm.get("rules", {}))},
        "meta": {"health": meta.get("overall_health", "?"), "score": meta.get("health_score", 0),
                 "accuracy": meta.get("recent_accuracy", 0), "ece": meta.get("calibration", {}).get("ece", 0),
                 "decisions": meta.get("total_decisions", 0), "failures": meta.get("consecutive_failures", 0)},
        "agents": _REG.list_agents(),
    }


@app.get("/api/v1/kg/graph")
def api_kg_graph():
    _init()
    entities = _DC.knowledge_graph.data["entities"]
    relationships = _DC.knowledge_graph.data["relationships"]
    central = _DC.knowledge_graph.get_central_entities(20)
    central_ids = {c["entity"]["id"] for c in central if c.get("entity")}

    nodes = []
    for eid, ent in entities.items():
        deg = len(_DC.knowledge_graph._adjacency.get(eid, []))
        nodes.append({"id": eid, "name": ent["name"], "type": ent["type"],
                      "degree": deg, "central": eid in central_ids})

    edges = []
    for r in relationships:
        edges.append({"source": r["source_id"], "target": r["target_id"],
                      "type": r["relation_type"], "weight": r["weight"]})
    return {"nodes": nodes, "edges": edges}


@app.get("/api/v1/ql/heatmap")
def api_ql_heatmap():
    _init()
    q_table = _DC.ql_agent.q_table
    actions = ["follow_rule", "use_tool", "try_fix", "report", "write_script", "switch", "skip"]
    rows = []
    for i in range(min(20, q_table.shape[0])):
        row_vals = [round(float(q_table[i, j]), 4) for j in range(q_table.shape[1])]
        if any(abs(v) > 0.001 for v in row_vals):
            rows.append({"state": i, "values": row_vals,
                         "best_action": int(np.argmax(np.abs(q_table[i, :])))})
    return {"actions": actions, "rows": rows, "shape": list(q_table.shape)}


@app.get("/api/v1/em/timeline")
def api_em_timeline(limit: int = Query(50, ge=1, le=200)):
    _init()
    episodes = _DC.episodic_memory.get_recent_episodes(limit)
    return [{"id": ep.get("episode_id", ""), "what": ep.get("what", "")[:100],
             "outcome": ep.get("outcome", ""), "emotion": ep.get("emotion", ""),
             "importance": ep.get("importance", 0), "tags": ep.get("tags", []),
             "when": ep.get("when", ""), "lesson": ep.get("lesson", "")[:80]}
            for ep in episodes]


@app.get("/api/v1/pm/rules")
def api_pm_rules():
    _init()
    rules = _DC.procedural_memory.data.get("rules", {})
    return [{"id": rid, "name": r["rule_name"], "level": r["level"],
             "success_rate": r.get("success_rate", 0),
             "attempts": r.get("total_attempts", 0),
             "patterns": r.get("context_patterns", [])[:5]}
            for rid, r in rules.items()]


@app.get("/api/v1/meta/dashboard")
def api_meta_dashboard():
    _init()
    return _DC.metacognition.get_performance_dashboard()


@app.get("/api/v1/dream/status")
def api_dream_status():
    _init()
    r = _DC.consolidator.dream_cycle(force=False)
    if r is None:
        state = _DC.consolidator.state
        return {"last_sleep": state.get("last_sleep_at"),
                "total": state.get("total_consolidations", 0), "running": False}
    return r


@app.get("/api/v1/agents")
def api_agents():
    _init()
    result = []
    for aid in _REG.list_agents():
        b = _REG.get(aid)
        if not b: continue
        ql = b.ql_agent.get_stats()
        em = b.episodic_memory.get_stats()
        meta = b.metacognition.get_performance_dashboard()
        result.append({"id": aid, "actions": b.action_dim,
                       "ql_nonzero": ql["nonzero_entries"], "ql_total": ql["total_entries"],
                       "em_episodes": em["total_episodes"],
                       "health": meta.get("overall_health", "?"),
                       "accuracy": meta.get("recent_accuracy", 0)})
    return result


@app.get("/api/v1/search")
def api_search(q: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=20)):
    _init()
    em = _DC.episodic_memory.search_episodes(q, n=limit)
    kg = _DC.knowledge_graph.search_entities(q, limit=limit)
    return {"query": q, "em": [{"what": e.get("what","")[:80], "outcome": e.get("outcome",""),
                                 "importance": e.get("importance",0)} for e in em],
            "kg": [{"name": e["name"], "type": e["type"]} for e in kg]}


@app.get("/api/v1/share/card")
def api_share_card():
    """Generate share card data (frontend renders to PNG)."""
    _init()
    kg = _DC.knowledge_graph.get_stats()
    ql = _DC.ql_agent.get_stats()
    central = _DC.knowledge_graph.get_central_entities(5)
    return {
        "title": "My HyperMarrow AI Memory",
        "generated": datetime.now().isoformat(),
        "stats": {
            "entities": kg["total_entities"], "relationships": kg["total_relationships"],
            "q_nonzero": ql["nonzero_entries"], "q_total": ql["total_entries"],
        },
        "top_entities": [{"name": c["entity"]["name"] if c["entity"] else "?",
                          "degree": c["degree"]} for c in central],
    }


# ── WebSocket ──────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _WS_CLIENTS.add(ws)
    try:
        while True:
            await asyncio.sleep(5)
            _init()
            ql = _DC.ql_agent.get_stats()
            meta = _DC.metacognition.get_performance_dashboard()
            await ws.send_json({
                "ts": datetime.now().isoformat(),
                "ql_nonzero": ql["nonzero_entries"],
                "ql_buffer": ql["total_experiences"],
                "health": meta.get("overall_health", "?"),
                "accuracy": meta.get("recent_accuracy", 0),
            })
    except: pass
    finally: _WS_CLIENTS.discard(ws)


# ── Startup ────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    _init()
    print(f"[API] HyperMarrow Crystal Core ready — http://0.0.0.0:8741")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8741, log_level="info")
