#!/usr/bin/env python3
"""
智商藏不住 — Crystal Core API
"""
import sys, os, json, asyncio
from pathlib import Path
from datetime import datetime

# 强制设置工作目录和路径
os.chdir(Path(__file__).resolve().parent.parent.parent)
_HERE = Path(__file__).resolve().parent.parent  # openclaw-memory-system/
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "openclaw-learning-system"))

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

app = FastAPI(title="智商藏不住 Crystal Core", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── API Token Authentication Middleware ────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException

class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Bearer Token authentication for /api/v1/agents/* endpoints."""
    async def dispatch(self, request, call_next):
        # Only protect agent mutation endpoints (GET is public)
        if request.url.path.startswith("/api/v1/agents/") and request.method in ("POST", "PUT", "DELETE"):
            from memory_core.config import get_config
            token = get_config().get("server", {}).get("api_token")
            if token:
                auth = request.headers.get("Authorization", "")
                scheme, _, provided = auth.partition(" ")
                if scheme.lower() != "bearer" or provided != token:
                    return JSONResponse(
                        {"status": "error", "message": "Invalid or missing API token"},
                        status_code=401,
                    )
        return await call_next(request)

from fastapi.responses import JSONResponse
app.add_middleware(TokenAuthMiddleware)

_DC = None; _REG = None; _WS = set()

def _get_or_create_claude_dc():
    global _CLAUDE_DC
    if _CLAUDE_DC is None:
        from memory_integration.decision_check import create_for_agent
        _CLAUDE_DC = create_for_agent("claude",
            enable_vector_db=_FEATURES.get("vector_memory", True),
            enable_rl=_FEATURES.get("q_learning", True),
            enable_metacognition=_FEATURES.get("metacognition", True),
            enable_world_model=_FEATURES.get("world_model", True),
            enable_prospective=_FEATURES.get("prospective_memory", True),
        )
    return _CLAUDE_DC

def _init():
    global _DC, _REG, _CLAUDE_DC
    if _DC is None:
        from memory_core.config import setup_hf_mirror, get_config, get_features, is_feature_enabled
        setup_hf_mirror()
        _FEATURES = get_features()

        # ── License-based feature gating (commercial mode) ─────────────────
        if get_config().get("license", {}).get("enabled", False):
            try:
                _HYPERMARROW = Path(__file__).resolve().parent.parent.parent
                sys.path.insert(0, str(_HYPERMARROW.parent))  # workspace/
                sys.path.insert(0, str(_HYPERMARROW.parent / "commercial"))  # workspace/commercial/ for LICENSE_SDK
                from LICENSE_SDK.license_manager import LicenseManager, LicenseStatus
                _lm = LicenseManager()
                _status = _lm.verify()
                if _status in (LicenseStatus.VALID, LicenseStatus.OFFLINE):
                    _licensed = set(_lm.get_features())
                    if "*" not in _licensed:
                        for key in list(_FEATURES.keys()):
                            if key not in _licensed:
                                _FEATURES[key] = False
                else:
                    # License invalid → fallback to basic features only
                    _FEATURES = {k: k in ("working_memory","episodic_memory","procedural_memory","knowledge_graph")
                                 for k in _FEATURES}
                print(f"[API] License: {_status.value}, features={sum(1 for v in _FEATURES.values() if v)}/{len(_FEATURES)}",
                      file=sys.stderr, flush=True)
            except ImportError:
                print("[API] LICENSE_SDK not available — running community edition", file=sys.stderr)
            except Exception as e:
                print(f"[API] License check failed ({e}) — running community edition", file=sys.stderr)

        from memory_integration.decision_check import create_for_agent, get_agent_registry
        # Create system agent for shared subsystems (hidden from agent list until connected)
        _DC = create_for_agent("openclaw",
            enable_vector_db=_FEATURES.get("vector_memory", True),
            enable_rl=_FEATURES.get("q_learning", True),
            enable_metacognition=_FEATURES.get("metacognition", True),
            enable_world_model=False,
            enable_prospective=_FEATURES.get("prospective_memory", True),
        )
        _REG = get_agent_registry()
        _CLAUDE_DC = None
        # Mark system agents as not-yet-connected
        for aid in ["openclaw", "claude"]:
            b = _REG.get(aid)
            if b: b._connected = False
        # Wire DC back to bundle
        for aid, dc in [("openclaw",_DC)]:
            b = _REG.get(aid)
            if b and dc:
                b.decision_checkpoint = dc
                b._connected = False

# ═══════════════════════════════════════════════════════════════════════════════
# 记忆系统 API (7 模块)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/memory/overview")
def memory_overview():
    _init()
    kg = _DC.knowledge_graph.get_stats()
    pm = _DC.procedural_memory.data
    wm = _DC.working_memory.get_active_context()
    em = _DC.episodic_memory.get_stats()
    vm = _DC.vector_db.get_stats() if _DC.vector_db else {}
    return {
        "p1_working_memory": {"task": wm.get("current_task",""), "goal": wm.get("goal",""),
            "stack_depth": wm.get("stack_depth",0), "context_keys": list(wm.get("active_context",{}).keys())},
        "p2_vector_memory": {"total_vectors": vm.get("total_vectors",0), "collection": vm.get("collection_name",""),
            "embedding_dim": vm.get("embedding_dim",0)},
        "p3_episodic_memory": {"total": em["total_episodes"], "with_lessons": em.get("with_lessons",0),
            "avg_importance": em.get("avg_importance",0), "by_outcome": em.get("by_outcome",{}),
            "by_emotion": em.get("by_emotion",{})},
        "procedural_memory": {"total_rules": len(pm.get("rules",{})),
            "by_level": {str(lv): sum(1 for r in pm.get("rules",{}).values() if r.get("level")==lv)
                         for lv in range(1,6)}},
        "knowledge_graph": {"entities": kg["total_entities"], "relationships": kg["total_relationships"],
            "density": kg["density"], "types": kg.get("entity_types",{})},
        "perception": {"screen": _DC.perception.screen.get_stats() if _DC.perception else {},
            "conversation": _DC.perception.conversation.get_stats() if _DC.perception else {}},
        "prospective": _DC.prospective.get_stats() if _DC.prospective else {},
    }

@app.get("/api/v1/kg/graph")
def kg_graph():
    _init()
    ents = _DC.knowledge_graph.data["entities"]; rels = _DC.knowledge_graph.data["relationships"]
    central = _DC.knowledge_graph.get_central_entities(30)
    cids = {c["entity"]["id"] for c in central if c.get("entity")}
    return {"nodes":[{"id":eid,"name":e["name"],"type":e["type"],"degree":len(_DC.knowledge_graph._adjacency.get(eid,[])),"central":eid in cids} for eid,e in ents.items()],
            "edges":[{"source":r["source_id"],"target":r["target_id"],"type":r["relation_type"],"weight":r["weight"]} for r in rels]}

@app.get("/api/v1/em/timeline")
def em_timeline(limit:int=Query(80,le=200)):
    _init()
    return [{"id":e.get("episode_id",""),"what":e.get("what","")[:100],"outcome":e.get("outcome",""),
             "emotion":e.get("emotion",""),"importance":e.get("importance",0),"tags":e.get("tags",[]),
             "when":e.get("when",""),"lesson":e.get("lesson","")[:80]} for e in _DC.episodic_memory.get_recent_episodes(limit)]

@app.get("/api/v1/pm/rules")
def pm_rules():
    _init()
    return [{"id":rid,"name":r["rule_name"],"level":r["level"],"success_rate":r.get("success_rate",0),
             "attempts":r.get("total_attempts",0),"patterns":r.get("context_patterns",[])[:5],
             "last_used":r.get("last_used_at")} for rid,r in _DC.procedural_memory.data.get("rules",{}).items()]

@app.get("/api/v1/vm/stats")
def vm_stats():
    _init()
    if _DC.vector_db:
        return _DC.vector_db.get_temporal_stats()
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# Engine module status (for on-demand download UX)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/engine/features")
def engine_features():
    """Report which engine modules are installed and available."""
    _init()
    features = {
        "vector_memory": False,
        "neural": False,
        "modules": {},
    }

    # Check vector memory engine (chromadb + sentence-transformers)
    if _DC.vector_db is not None:
        try:
            from memory_core.vector_memory_db import VectorMemoryDB
            features["vector_memory"] = VectorMemoryDB.is_available()
        except ImportError:
            features["vector_memory"] = False

    # Check neural engine (torch)
    try:
        import torch
        features["neural"] = True
    except ImportError:
        features["neural"] = False

    # Module metadata for download
    features["modules"] = {
        "vector": {
            "name": "向量记忆引擎",
            "description": "语义搜索和智能记忆",
            "installed": features["vector_memory"],
            "size_mb": 80,
        },
        "neural": {
            "name": "神经引擎",
            "description": "世界模型和深度学习",
            "installed": features["neural"],
            "size_mb": 120,
        },
    }
    return features

# ═══════════════════════════════════════════════════════════════════════════════
# 学习系统 API (7 模块)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/learning/overview")
def learning_overview():
    _init()
    ql = _DC.ql_agent.get_stats()
    meta = _DC.metacognition.get_performance_dashboard()
    con = _DC.consolidator.state
    return {
        "q_learning": {"nonzero": ql["nonzero_entries"], "total": ql["total_entries"],
            "nonzero_pct": ql["nonzero_pct"], "buffer": ql["total_experiences"],
            "mode": ql.get("neural_mode","tabular"), "states": ql.get("distinct_states",0),
            "alpha": ql["alpha"], "gamma": ql["gamma"], "epsilon": ql["epsilon"],
            "collisions": ql.get("collisions_resolved",0)},
        "metacognition": {"health": meta.get("overall_health","?"), "score": meta.get("health_score",0),
            "accuracy": meta.get("recent_accuracy",0), "ece": meta.get("calibration",{}).get("ece",0),
            "decisions": meta.get("total_decisions",0), "failures": meta.get("consecutive_failures",0),
            "anomalies": meta.get("anomalies_recent",0)},
        "consolidation": {"total": con.get("total_consolidations",0), "last_sleep": con.get("last_sleep_at"),
            "ltp_total": con.get("total_ltp",0), "ltd_total": con.get("total_ltd_pruned",0),
            "merged_total": con.get("total_episodes_merged",0)},
        "transfer": _DC.transfer_learner.get_stats() if _DC.transfer_learner else {},
        "world_model": (_DC.ql_agent._world_model.get_stats() if (getattr(_DC.ql_agent,'_world_model',None) and _DC.ql_agent._world_model.wm) else {"train_steps":0,"torch_available":True}) | {"status":"就绪（新数据自动训练）" if ql.get("neural_mode")!="tabular" else "待启用"},
        "meta_learner": {"adjustments": _DC.meta_learner.state.get("total_adjustments", 0) if _DC.meta_learner else 0},
        "neural": ql.get("neural_stats",{}),
    }

@app.get("/api/v1/ql/heatmap")
def ql_heatmap():
    _init()
    q = _DC.ql_agent.q_table
    actions = ["遵规则","用工具","修三次","报用户","写脚本","换技能","跳阶段"]
    rows = [{"state":i,"values":[round(float(q[i,j]),4) for j in range(q.shape[1])],
             "best":int(np.argmax(np.abs(q[i,:])))} for i in range(min(30,q.shape[0])) if any(abs(q[i,j])>0.001 for j in range(q.shape[1]))]
    return {"actions":actions,"rows":rows,"shape":list(q.shape)}

@app.get("/api/v1/meta/calibration")
def meta_calibration():
    _init()
    return _DC.metacognition.get_calibration_curve()

@app.get("/api/v1/meta/anomalies")
def meta_anomalies(limit:int=Query(20,le=50)):
    _init()
    return _DC.metacognition.get_recent_anomalies(limit)

@app.get("/api/v1/dream/status")
def dream_status():
    _init()
    r = _DC.consolidator.dream_cycle(force=False)
    if r is None:
        return {"running":False,"last":_DC.consolidator.state.get("last_sleep_at"),
                "total":_DC.consolidator.state.get("total_consolidations",0)}
    # Filter: only keep integer phase values (strip dict/object entries like calibrate)
    if "phases" in r:
        r["phases"] = {k:v for k,v in r["phases"].items() if isinstance(v,int)}
    return r

@app.get("/api/v1/dream/run")
def dream_run():
    _init()
    r = _DC.consolidator.dream_cycle(force=True)
    if "phases" in r:
        r["phases"] = {k:v for k,v in r["phases"].items() if isinstance(v,int)}
    return r

@app.get("/api/v1/skills/list")
def skills_list():
    _init()
    try:
        from memory_core.meta_learner import SkillExtractor
        se = SkillExtractor()
        return se.data.get("skills",{})
    except: return {}

@app.get("/api/v1/agents")
def agents_list():
    _init()
    r=[]
    now = datetime.now()
    for aid in _REG.list_agents():
        b=_REG.get(aid)
        # Only show agents that have been explicitly connected
        if b and not getattr(b, '_connected', False):
            continue
        if not b:
            continue
        dc = b.decision_checkpoint
        ql=b.ql_agent.get_stats(); em=b.episodic_memory.get_stats()
        meta=b.metacognition.get_performance_dashboard()
        wm=b.working_memory
        wm_ctx=wm.get_active_context()
        # Real status with heartbeat check (stale after 60s without heartbeat)
        neural_active = ql.get("neural_mode","tabular") != "tabular"
        wm_active = ql.get("world_model_stats") is not None
        dc_active = dc is not None and getattr(dc,'_api_session_active',False)
        # Check heartbeat staleness
        if dc_active and hasattr(dc,'_last_heartbeat') and dc._last_heartbeat:
            try:
                last = datetime.fromisoformat(dc._last_heartbeat)
                if (now - last).total_seconds() > 60:
                    dc._api_session_active = False
                    dc_active = False
            except: pass
        if dc_active: status="connected"; status_text="● 已连接"
        elif dc is not None: status="offline"; status_text="○ 未连接"
        else: status="registered"; status_text="— 仅注册"
        r.append({"id":aid,"status":status,"status_text":status_text,
            "actions":b.action_dim,"ql_nonzero":ql["nonzero_entries"],"ql_total":ql["total_entries"],
            "em_episodes":em["total_episodes"],"health":meta.get("overall_health","?"),
            "accuracy":meta.get("recent_accuracy",0),
            "neural_active":neural_active,"wm_active":wm_active,
            "has_em":em["total_episodes"] > 0,"has_wm_task":bool(wm_ctx.get("current_task"))})
    return r

@app.get("/api/v1/search")
def search(q:str=Query(...,min_length=1),limit:int=Query(5,le=20)):
    _init()
    return {"query":q,
        "em":[{"what":e.get("what","")[:80],"outcome":e.get("outcome",""),"importance":e.get("importance",0)} for e in _DC.episodic_memory.search_episodes(q,n=limit)],
        "kg":[{"name":e["name"],"type":e["type"]} for e in _DC.knowledge_graph.search_entities(q,limit=limit)]}

@app.get("/api/v1/interceptor/stats")
def interceptor_stats():
    try:
        from memory_integration.interceptor import get_interceptor_stats
        return get_interceptor_stats()
    except: return {}

@app.get("/api/v1/achievements")
def achievements():
    _init()
    kg = _DC.knowledge_graph.get_stats()
    ql = _DC.ql_agent.get_stats()
    em = _DC.episodic_memory.get_stats()
    con = _DC.consolidator.state
    meta = _DC.metacognition.get_performance_dashboard()
    achievements = []
    em_total = em["total_episodes"]; ql_nz = ql["nonzero_entries"]; kg_ent = kg["total_entities"]; con_total = con.get("total_consolidations",0); meta_acc = meta.get("recent_accuracy",0)
    descs = {"mem":"记录了 " + str(em_total) + " 条情景记忆","ql":"Q表非零条目突破 " + str(ql_nz),"kg":"知识图谱已有 " + str(kg_ent) + " 个实体","dream":"已完成 " + str(con_total) + " 次记忆巩固","acc":"决策准确率 " + str(int(meta_acc*100)) + "%"}
    if em_total >= 10: achievements.append({"id":"mem_10","title":"记忆收藏家","desc":descs["mem"],"icon":"📒","level":1 if em_total<50 else 2 if em_total<100 else 3})
    if ql_nz >= 100: achievements.append({"id":"ql_100","title":"学习达人","desc":descs["ql"],"icon":"🎯","level":1 if ql_nz<300 else 2 if ql_nz<500 else 3})
    if kg_ent >= 3: achievements.append({"id":"kg_3","title":"知识编织者","desc":descs["kg"],"icon":"🕸️","level":1})
    if con_total >= 10: achievements.append({"id":"dream_10","title":"安睡者","desc":descs["dream"],"icon":"🌙","level":1})
    if meta_acc >= 0.7: achievements.append({"id":"acc_70","title":"精准决策者","desc":descs["acc"],"icon":"🎯","level":2})
    return {"achievements":achievements,"total":len(achievements)}

def _resolve_agent_dc(agent_id: str):
    """Resolve a DecisionCheckPoint for any agent via the registry.
    Auto-registers unknown agents on first contact.
    Returns (dc, bundle) or (None, None)."""
    _init()
    bundle = _REG.get(agent_id)
    if not bundle:
        # Auto-register: new agent self-onboarding
        try:
            from memory_integration.decision_check import create_for_agent
            create_for_agent(agent_id)
            bundle = _REG.get(agent_id)
        except Exception as e:
            print(f"[API] Auto-register '{agent_id}' failed: {e}", file=sys.stderr)
            return None, None
    # DC should be wired; if not (legacy bundle), create it now
    dc = bundle.decision_checkpoint if bundle else None
    if dc is None and bundle:
        try:
            from memory_integration.decision_check import create_for_agent
            create_for_agent(agent_id)
            dc = bundle.decision_checkpoint
        except Exception as e:
            print(f"[API] DC create for '{agent_id}' failed: {e}", file=sys.stderr)
    return dc, bundle


@app.post("/api/v1/agents/{agent_id}/connect")
def agent_connect(agent_id: str):
    """Agent 注册连接 — 任意 Agent 均可调用，自动注册"""
    dc, bundle = _resolve_agent_dc(agent_id)
    if bundle:
        bundle._connected = True
        _ensure_heartbeat(agent_id)
    if dc:
        dc._api_session_active = True
        dc._last_heartbeat = datetime.now().isoformat()
        if bundle:
            bundle.decision_checkpoint = dc
        return {"status":"ok","agent":agent_id,"connected":True}
    return {"status":"error","message":f"Agent '{agent_id}' could not be resolved"}

@app.post("/api/v1/agents/{agent_id}/heartbeat")
def agent_heartbeat(agent_id: str):
    """Agent 心跳 — 任意 Agent 维持连接状态"""
    dc, _ = _resolve_agent_dc(agent_id)
    if dc:
        dc._api_session_active = True
        dc._last_heartbeat = datetime.now().isoformat()
        return {"status":"ok","agent":agent_id,"alive":True}
    return {"status":"error","message":f"Agent '{agent_id}' could not be resolved"}

@app.post("/api/v1/agents/{agent_id}/disconnect")
def agent_disconnect(agent_id: str):
    """Agent 断开连接"""
    dc, _ = _resolve_agent_dc(agent_id)
    if dc:
        dc._api_session_active = False
        return {"status":"ok","agent":agent_id,"connected":False}
    return {"status":"error","message":f"Agent '{agent_id}' could not be resolved"}

# ── Agent 数据灌入 API (HTTP mode, non-Python agents) ──────────────────

@app.post("/api/v1/agents/{agent_id}/intercept")
def agent_intercept(agent_id: str, body: dict):
    """数据灌入：对话消息 → 记忆拦截（实体提取 + 存档 + 规则匹配）"""
    _init()
    from memory_integration.interceptor import hypermarow_intercept
    result = hypermarow_intercept(
        body.get("user_message", ""),
        body.get("agent_response", ""),
        blocking=True,
        agent_id=agent_id,
    )
    return {"status": "ok", "agent": agent_id, **result}

@app.post("/api/v1/agents/{agent_id}/check")
def agent_check(agent_id: str, body: dict):
    """决策检查：调用完整 10 步决策流水线"""
    dc, _ = _resolve_agent_dc(agent_id)
    if not dc:
        return {"status": "error", "message": f"Agent '{agent_id}' not found"}
    result = dc.check(
        action=body.get("action", ""),
        context=body.get("context", {}),
        agent_id=agent_id,
    )
    return {"status": "ok", "agent": agent_id, **result}

@app.post("/api/v1/agents/{agent_id}/record")
def agent_record(agent_id: str, body: dict):
    """决策记录：回写所有记忆/学习子系统"""
    dc, _ = _resolve_agent_dc(agent_id)
    if not dc:
        return {"status": "error", "message": f"Agent '{agent_id}' not found"}
    dc.record(
        action=body.get("action", ""),
        context=body.get("context", {}),
        outcome=body.get("outcome", "success"),
        reward=body.get("reward"),
        note=body.get("note", ""),
        agent_id=agent_id,
    )
    return {"status": "ok", "agent": agent_id, "outcome": body.get("outcome", "success")}

@app.get("/api/v1/license/status")
def license_status():
    """License 状态查询 — 供 UI Panel 和 Agent 检查"""
    from memory_core.config import get_config, get_features
    cfg = get_config()
    lic_cfg = cfg.get("license", {})
    features = get_features()

    status_info = {
        "enabled": lic_cfg.get("enabled", False),
        "mode": "commercial" if lic_cfg.get("enabled") else "community",
        "plan": "community",
        "features": {k: v for k, v in features.items()},
        "features_enabled": sum(1 for v in features.values() if v),
        "features_total": len(features),
    }

    if lic_cfg.get("enabled"):
        try:
            _HYPERMARROW = Path(__file__).resolve().parent.parent.parent
            sys.path.insert(0, str(_HYPERMARROW.parent))
            sys.path.insert(0, str(_HYPERMARROW.parent / "commercial"))
            from LICENSE_SDK.license_manager import LicenseManager, LicenseStatus
            lm = LicenseManager()
            status = lm.verify()
            status_info.update({
                "license_status": status.value,
                "plan": lm.license_data.get("permissions", {}).get("plan", "unknown") if lm.license_data else "unknown",
                "expiry": lm.get_expiry_date(),
                "max_devices": lm.get_max_devices(),
                "user": lm.get_user_info(),
            })
        except ImportError:
            status_info["license_status"] = "sdk_not_installed"
        except Exception as e:
            status_info["license_status"] = f"error: {e}"

    return status_info

@app.get("/api/v1/share/card")
def share_card():
    _init()
    kg=_DC.knowledge_graph.get_stats(); ql=_DC.ql_agent.get_stats()
    central=_DC.knowledge_graph.get_central_entities(5)
    meta=_DC.metacognition.get_performance_dashboard()
    return {"title":"智商藏不住 — 我的AI记忆","generated":datetime.now().isoformat(),
        "stats":{"entities":kg["total_entities"],"relationships":kg["total_relationships"],
                 "q_nonzero":ql["nonzero_entries"],"q_total":ql["total_entries"],
                 "health":meta.get("overall_health","?"),"score":meta.get("health_score",0)},
        "top":[{"name":c["entity"]["name"] if c["entity"] else "?","degree":c["degree"]} for c in central]}

# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket 实时推送
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def ws_endpoint(ws:WebSocket):
    await ws.accept(); _WS.add(ws)
    try:
        while True:
            await asyncio.sleep(5); _init()
            ql=_DC.ql_agent.get_stats(); meta=_DC.metacognition.get_performance_dashboard()
            await ws.send_json({"ts":datetime.now().isoformat(),"ql_nonzero":ql["nonzero_entries"],
                "ql_buffer":ql["total_experiences"],"health":meta.get("overall_health","?"),
                "accuracy":meta.get("recent_accuracy",0),"score":meta.get("health_score",0)})
    except: pass
    finally: _WS.discard(ws)

# ═══════════════════════════════════════════════════════════════════════════════
# 用户认证 API
# ═══════════════════════════════════════════════════════════════════════════════

from memory_api.user_auth import generate_code, verify_code, get_user_by_token


@app.post("/api/v1/user/send-code")
def user_send_code(body: dict):
    """发送短信验证码"""
    phone = body.get("phone", "").strip()
    if not phone or len(phone) < 11:
        return {"success": False, "message": "请输入正确的11位手机号"}
    try:
        code, dev_code = generate_code(phone)
        result = {"success": True, "message": "验证码已发送"}
        if dev_code:
            result["dev_code"] = dev_code  # 开发模式返回验证码
        return result
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except RuntimeError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"发送失败: {e}"}


@app.post("/api/v1/user/login")
def user_login(body: dict):
    """手机号+验证码登录"""
    phone = body.get("phone", "").strip()
    code = body.get("code", "").strip()
    if not phone or not code:
        return {"success": False, "message": "请输入手机号和验证码"}
    result = verify_code(phone, code)
    if result["success"]:
        return {
            "success": True,
            "token": result["token"],
            "expires_in": result["expires_in"],
            "user": result["user"],
        }
    return result


@app.get("/api/v1/user/info")
def user_info(token: str = Query("")):
    """查询用户信息"""
    user = get_user_by_token(token)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "message": "未登录或 token 已过期"}


# ═══════════════════════════════════════════════════════════════════════════════
# v2 License API 代理 → https://license.qianshi.cool
# ═══════════════════════════════════════════════════════════════════════════════

import urllib.request as _urllib

_LICENSE_SERVER = "https://license.qianshi.cool"


def _proxy_to_license(path: str, body: dict | None = None):
    """代理请求到 License 服务器"""
    try:
        url = f"{_LICENSE_SERVER}{path}"
        data = json.dumps(body).encode() if body else None
        req = _urllib.Request(url, data=data, headers={"Content-Type": "application/json"})
        if data:
            req.method = "POST"
        resp = _urllib.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "status": 0, "data": {"detail": f"License 服务器连接失败: {e}"}}


@app.get("/api/v2/client/license/status")
def license_status_v2():
    """License 状态（v2 格式，代理到 License 服务器）"""
    return _proxy_to_license("/api/v2/client/license/status")


@app.post("/api/v2/client/pay/create")
def pay_create(body: dict):
    """创建支付订单（代理到 License 服务器）"""
    return _proxy_to_license("/api/v2/client/pay/create", body)


@app.get("/api/v2/client/pay/status/{out_trade_no}")
def pay_status(out_trade_no: str):
    """支付状态查询（代理到 License 服务器）"""
    return _proxy_to_license(f"/api/v2/client/pay/status/{out_trade_no}")


@app.post("/api/v2/client/license/renew")
def license_renew(body: dict):
    """许可续期（代理到 License 服务器）"""
    return _proxy_to_license("/api/v2/client/license/renew", body)


# ── Production mode: serve built UI at / ──────────────────────────────────
# In dev mode (no dist/), UI is served by Vite on port 5173 separately.
_UI_DIST = Path(__file__).resolve().parent.parent.parent / "hypermarrow-ui" / "dist"
if _UI_DIST.exists() and (_UI_DIST / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")

@app.on_event("startup")
async def startup():
    _init()
    import threading, urllib.request, subprocess, time
    from memory_core.config import get_config, get_agent_config

    def _is_process_running(process_name: str) -> bool:
        """Cross-platform process detection (MSYS-safe on Windows)."""
        if not process_name:
            return False
        try:
            if sys.platform == "win32":
                # Use full tasklist + Python filter instead of /FI flag
                # because MSYS (Git Bash) mangles /FI as a Unix path
                r = subprocess.run(
                    ["tasklist"], capture_output=True, text=True, timeout=8
                )
                return process_name.lower() in r.stdout.lower()
            elif sys.platform == "darwin":
                r = subprocess.run(
                    ["pgrep", "-f", process_name], capture_output=True, text=True, timeout=5
                )
                return r.returncode == 0
            else:  # Linux
                r = subprocess.run(
                    ["pgrep", "-f", process_name], capture_output=True, text=True, timeout=5
                )
                return r.returncode == 0
        except Exception:
            return False

    def _is_agent_host_running(agent_id: str) -> bool:
        """Check if agent's host process is running (cross-platform, config-driven)."""
        agent_cfg = get_agent_config()
        proc_cfg = agent_cfg.get("process_detection", {}).get(agent_id, {})
        # sys.platform is "win32" on Windows, but config uses "windows" for readability
        proc_name = (proc_cfg.get(sys.platform) or
                     proc_cfg.get("windows") or  # alias for win32
                     proc_cfg.get("linux") or
                     proc_cfg.get("darwin"))
        return _is_process_running(proc_name) if proc_name else False

    def _agent_heartbeat(agent_id: str, is_alive_check=None):
        """Generic heartbeat loop for any agent."""
        url_connect = f'http://localhost:8741/api/v1/agents/{agent_id}/connect'
        url_beat    = f'http://localhost:8741/api/v1/agents/{agent_id}/heartbeat'
        try:
            urllib.request.urlopen(urllib.request.Request(url_connect, method='POST'), timeout=3)
        except Exception:
            pass
        while True:
            if is_alive_check is None or is_alive_check():
                try:
                    urllib.request.urlopen(urllib.request.Request(url_beat, method='POST'), timeout=3)
                except Exception:
                    pass
            time.sleep(30)

    # ── Heartbeat threads: started on-demand per agent, not hardcoded ──
    _heartbeat_threads = {}
    def _ensure_heartbeat(agent_id: str):
        """Start heartbeat thread for an agent if not already running."""
        if agent_id in _heartbeat_threads:
            return
        t = threading.Thread(
            target=_agent_heartbeat,
            args=(agent_id, lambda: _is_agent_host_running(agent_id)),
            daemon=True, name=f"hm_{agent_id}_heartbeat"
        )
        t.start()
        _heartbeat_threads[agent_id] = t

    # ── Dream Cycle scheduler ────────────────────────────────────────────
    def _dream_scheduler():
        cfg = get_config()
        interval_h = cfg.get("learning", {}).get("dream_cycle_interval_hours", 6)
        time.sleep(120)  # Wait 2 min after startup before first cycle
        while True:
            time.sleep(interval_h * 3600)
            try:
                _init()
                _DC.consolidator.dream_cycle(force=True)
                print(f"[Dream Scheduler] Cycle completed", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[Dream Scheduler] Failed: {e}", file=sys.stderr, flush=True)

    threading.Thread(target=_dream_scheduler, daemon=True, name="dream_scheduler").start()

    print(f"[智商藏不住 API] http://0.0.0.0:8741 — 记忆7模块 + 学习7模块 已就绪")

if __name__=="__main__":
    import uvicorn; uvicorn.run(app,host="0.0.0.0",port=8741)
