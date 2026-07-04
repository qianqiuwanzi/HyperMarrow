#!/usr/bin/env python3
"""
HyperMarrow MCP Server — Model Context Protocol interface.

Exposes the full memory & learning system to any MCP-compatible client
(Claude Code, Cursor, Continue, etc.) via stdio JSON-RPC.

Protocol: https://modelcontextprotocol.io

Start:  python hypermarow_mcp.py
Config: Add to claude_desktop_config.json or .mcp.json
"""
import sys, os, json, traceback
from pathlib import Path
from datetime import datetime

# ── Path setup ───────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.parent  # openclaw-memory-system/
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "openclaw-learning-system"))

# ── Init HyperMarrow ─────────────────────────────────────────────────────────
DC = None
_HM_READY = False


def _init_hm():
    global DC, _HM_READY
    try:
        from memory_core.config import setup_hf_mirror
        setup_hf_mirror()

        from memory_integration.decision_check import create_for_agent
        DC = create_for_agent("openclaw")
        _HM_READY = True
        _log(f"HyperMarrow MCP ready — {_get_agent_count()} agents, "
             f"{_get_entity_count()} KG entities, {_get_rule_count()} PM rules")
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        _log(f"Init FAILED: {e}")
        _HM_READY = False


def _get_agent_count():
    try:
        from memory_integration.decision_check import get_agent_registry
        return len(get_agent_registry().list_agents())
    except: return 1


def _get_entity_count():
    try:
        return DC.knowledge_graph.get_stats()["total_entities"] if DC else 0
    except: return 0


def _get_rule_count():
    try:
        return len(DC.procedural_memory.data.get("rules", {})) if DC else 0
    except: return 0


def _log(msg):
    print(f"[HyperMarrow MCP] {msg}", file=sys.stderr, flush=True)


# ── MCP Message Handler ──────────────────────────────────────────────────────

def _rpc_ok(rpc_id, result):
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _rpc_err(rpc_id, code, message):
    return {"jsonrpc": "2.0", "id": rpc_id,
            "error": {"code": code, "message": message}}


def handle_message(msg: dict) -> dict:
    """Route an MCP JSON-RPC message to the appropriate handler."""
    method = msg.get("method", "")
    rpc_id = msg.get("id")
    params = msg.get("params", {})

    try:
        if method == "initialize":
            return _rpc_ok(rpc_id, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "hypermarow-mcp", "version": "2.0.0"},
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            })

        elif method == "tools/list":
            return _rpc_ok(rpc_id, {"tools": _list_tools()})

        elif method == "tools/call":
            return _rpc_ok(rpc_id, _call_tool(params.get("name", ""), params.get("arguments", {})))

        elif method == "resources/list":
            return _rpc_ok(rpc_id, {"resources": _list_resources()})

        elif method == "resources/read":
            return _rpc_ok(rpc_id, _read_resource(params.get("uri", "")))

        elif method == "prompts/list":
            return _rpc_ok(rpc_id, {"prompts": _list_prompts()})

        elif method == "prompts/get":
            return _rpc_ok(rpc_id, _get_prompt(params.get("name", ""), params.get("arguments", {})))

        elif method == "notifications/initialized":
            return None  # No response for notifications

        else:
            return _rpc_err(rpc_id, -32601, f"Method not found: {method}")

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return _rpc_err(rpc_id, -32603, str(e))


# ── Tools ────────────────────────────────────────────────────────────────────

def _list_tools():
    return [
        {
            "name": "check",
            "description": "Check if an action should be executed, consulting all memory subsystems (procedural rules, RL, knowledge graph). Returns recommendation with confidence and warnings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Action to evaluate (e.g. try_fix_three_times, switch_skill, write_script)"},
                    "task": {"type": "string", "description": "Task description"},
                    "phase": {"type": "string", "description": "Current phase (P0-P5)"},
                    "error": {"type": "string", "description": "Error type if any (timeout, import_error, etc.)"},
                    "attempts": {"type": "integer", "description": "Number of attempts so far"},
                },
                "required": ["action"],
            },
        },
        {
            "name": "record",
            "description": "Record a decision outcome. Updates all subsystems: procedural memory success rate, episodic memory, RL Q-table, metacognition calibration.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "Action that was taken"},
                    "task": {"type": "string", "description": "Task description"},
                    "phase": {"type": "string", "description": "Current phase"},
                    "outcome": {"type": "string", "enum": ["success", "failure", "partial"]},
                    "reward": {"type": "number", "description": "Reward value (-1 to 1)"},
                    "note": {"type": "string", "description": "Optional note"},
                },
                "required": ["action", "outcome"],
            },
        },
        {
            "name": "search",
            "description": "Search episodic memory and vector memory for similar past experiences.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "days": {"type": "integer", "description": "How many days back to search (default 30)"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "stats",
            "description": "Get system-wide statistics: agent performance, Q-table state, knowledge graph size, memory health.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "analogy",
            "description": "Find the most similar past situations to the current context using embedding similarity + knowledge graph matching.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Current task description"},
                    "phase": {"type": "string", "description": "Current phase"},
                    "error": {"type": "string", "description": "Error type if any"},
                },
                "required": ["task"],
            },
        },
        {
            "name": "transfer",
            "description": "Transfer learned knowledge from one agent to another (cross-agent Q-table seeding + episodic pattern sharing).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source agent ID (e.g. openclaw)"},
                    "target": {"type": "string", "description": "Target agent ID (e.g. luci)"},
                },
                "required": ["source", "target"],
            },
        },
        {
            "name": "consolidate",
            "description": "Run a full memory consolidation cycle: LTP strengthening + LTD decay + episode merging + Q-buffer replay + skill extraction.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "skills",
            "description": "List all extracted skills and auto-generated procedural rules.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def _call_tool(name: str, args: dict) -> dict:
    if not _HM_READY:
        _init_hm()
    if not _HM_READY:
        return {"content": [{"type": "text", "text": "Error: HyperMarrow not initialized"}]}

    if name == "check":
        return _tool_check(args)
    elif name == "record":
        return _tool_record(args)
    elif name == "search":
        return _tool_search(args)
    elif name == "stats":
        return _tool_stats(args)
    elif name == "analogy":
        return _tool_analogy(args)
    elif name == "transfer":
        return _tool_transfer(args)
    elif name == "consolidate":
        return _tool_consolidate(args)
    elif name == "skills":
        return _tool_skills(args)
    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}


def _tool_check(args: dict) -> dict:
    context = {}
    if "task" in args: context["task"] = args["task"]
    if "phase" in args: context["phase"] = args["phase"]
    if "error" in args: context["error_type"] = args["error"]
    if "attempts" in args: context["attempts"] = args["attempts"]

    result = DC.check(action=args["action"], context=context if context else None)

    rl = result.get("rl_recommendation", {}) or {}
    text = (
        f"Decision Check for '{args['action']}':\n"
        f"  Allowed: {result.get('allowed', True)}\n"
        f"  RL Recommends: {rl.get('recommended_action', 'N/A')} "
        f"(confidence={rl.get('confidence', 0):.0%}, Q={rl.get('q_value', 0):.3f})\n"
        f"  Procedural Hints: {len(result.get('procedural_hints', []))}\n"
        f"  Related KG Entities: {len(result.get('related_entities', []))}\n"
        f"  Warnings: {len(result.get('warnings', []))}"
    )
    for w in result.get("warnings", []):
        text += f"\n    ⚠ {w}"

    return {"content": [{"type": "text", "text": text}],
            "structured": result}


def _tool_record(args: dict) -> dict:
    context = {}
    if "task" in args: context["task"] = args["task"]
    if "phase" in args: context["phase"] = args["phase"]

    outcome = args.get("outcome", "success")
    reward = args.get("reward", 1.0 if outcome == "success" else -1.0)

    DC.record(
        action=args["action"], context=context if context else {},
        outcome=outcome, reward=reward,
        note=args.get("note", ""),
    )

    return {"content": [{"type": "text",
            "text": f"Recorded: {args['action']} → {outcome} (reward={reward})"}]}


def _tool_search(args: dict) -> dict:
    days = args.get("days", 30)
    limit = args.get("limit", 5)
    query = args["query"]

    # Search episodic memory
    em_results = DC.episodic_memory.search_episodes(query, n=limit)
    text = f"Search results for '{query}' (last {days}d):\n"
    for i, ep in enumerate(em_results):
        text += (f"  {i+1}. [{ep.get('outcome','?')}] {ep.get('what','')[:80]} "
                 f"(importance={ep.get('importance',0)}, tags={ep.get('tags',[])})\n")

    # Search vector memory
    if DC.enable_vector_db and DC.vector_db:
        try:
            vec_results = DC.vector_db.search(query, n_results=limit, days_filter=days)
            if vec_results and vec_results.get("documents"):
                for docs in vec_results["documents"]:
                    for doc in docs[:3]:
                        text += f"  [VecDB] {doc[:100]}...\n"
        except: pass

    return {"content": [{"type": "text", "text": text}]}


def _tool_stats(args: dict) -> dict:
    kg = DC.knowledge_graph.get_stats() if DC.knowledge_graph else {}
    pm = DC.procedural_memory.data if DC.procedural_memory else {}
    ql = DC.ql_agent.get_stats() if DC.ql_agent else {}
    em = DC.episodic_memory.get_stats() if DC.episodic_memory else {}
    meta = DC.metacognition.get_performance_dashboard() if DC.metacognition else {}

    text = (
        f"HyperMarrow System Stats:\n"
        f"  Knowledge Graph: {kg.get('total_entities',0)} entities, "
        f"{kg.get('total_relationships',0)} relationships\n"
        f"  Procedural Memory: {len(pm.get('rules',{}))} rules\n"
        f"  Q-Learning: {ql.get('nonzero_entries',0)}/{ql.get('total_entries',0)} "
        f"non-zero, buffer={ql.get('total_experiences',0)}\n"
        f"  Episodic Memory: {em.get('total_episodes',0)} episodes\n"
        f"  Metacognition: health={meta.get('overall_health','?')}, "
        f"accuracy={meta.get('recent_accuracy',0):.0%}, "
        f"ECE={meta.get('calibration',{}).get('ece',0):.3f}\n"
        f"  Neural: {ql.get('neural_mode','tabular')}, "
        f"distinct_states={ql.get('distinct_states',0)}"
    )
    return {"content": [{"type": "text", "text": text}]}


def _tool_analogy(args: dict) -> dict:
    try:
        from memory_core import AnalogicalReasoner
        ar = AnalogicalReasoner(
            neural_agent=DC.ql_agent._neural_agent if DC.ql_agent else None,
            knowledge_graph=DC.knowledge_graph,
            procedural_memory=DC.procedural_memory,
        )
        result = ar.reason(args)
        text = f"Analogical Reasoning:\n  {result['recommendation']}\n"
        if result["analogies"]:
            text += "Similar past experiences:\n"
            for a in result["analogies"][:3]:
                text += (f"  - [{a['outcome']}] {a['what'][:80]} "
                         f"(similarity={a['similarity']:.0%})\n")
        if result["matching_rules"]:
            text += "Matching procedural rules:\n"
            for r in result["matching_rules"][:3]:
                text += f"  - [{r['rule']}] L{r['level']} ({r['success_rate']:.0%})\n"
        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Analogy failed: {e}"}]}


def _tool_transfer(args: dict) -> dict:
    source = args.get("source", "openclaw")
    target = args.get("target", "luci")
    try:
        from memory_integration.decision_check import get_agent_registry
        reg = get_agent_registry()
        result = reg.cross_agent_transfer(source, target)
        text = (f"Cross-agent transfer {source}→{target}:\n"
                f"  Episodes transferred: {result.get('episodes_transferred', 0)}\n"
                f"  Q-table cells seeded: {result.get('q_cells_seeded', 0)}\n"
                f"  Calibration references: {result.get('calibration_references', 0)}")
        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Transfer failed: {e}"}]}


def _tool_consolidate(args: dict) -> dict:
    try:
        from memory_integration.decision_check import get_agent_registry
        from memory_core.meta_learner import SkillExtractor
        reg = get_agent_registry()
        text = "Consolidation results:\n"
        for agent_id in reg.list_agents():
            bundle = reg.get(agent_id)
            if not bundle or not bundle.consolidator:
                continue
            result = bundle.consolidator.consolidate()
            text += (f"  {agent_id}: LTP={result.get('ltp_count',0)}, "
                     f"LTD={result.get('ltd_pruned',0)}, "
                     f"merged={result.get('episodes_merged',0)}, "
                     f"Q_replay={result.get('q_replayed',0)}\n")
            # Skill extraction
            try:
                se = SkillExtractor(episodic_memory=bundle.episodic_memory,
                                     knowledge_graph=bundle.knowledge_graph)
                extracted = se.extract_skills(min_successes=2)
                if extracted > 0:
                    fed = se.feed_procedural(bundle.procedural_memory)
                    text += f"    Skills: extracted={extracted}, fed to PM={fed}\n"
            except: pass
        # Cross-agent share
        reg.share_all()
        text += "  Cross-agent sharing: complete"
        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Consolidation failed: {e}"}]}


def _tool_skills(args: dict) -> dict:
    try:
        from memory_core.meta_learner import SkillExtractor
        se = SkillExtractor()
        skills = se.data.get("skills", {})
        text = f"Extracted Skills ({len(skills)}):\n"
        for sid, skill in list(skills.items())[:20]:
            text += (f"  [{skill['action']}] patterns={skill.get('context_patterns',[])[:3]} "
                     f"n={skill.get('success_count',0)}, sr={skill.get('success_rate',0):.0%}\n")
        # Also show procedural rules
        pm = DC.procedural_memory if DC else None
        if pm:
            rules = pm.data.get("rules", {})
            auto_rules = [r for r in rules.values() if "[Auto]" in r.get("rule_name","")]
            text += f"\nAuto-generated Procedural Rules ({len(auto_rules)}):\n"
            for r in auto_rules[:10]:
                text += (f"  {r['rule_name']} (L{r['level']}, "
                         f"sr={r.get('success_rate',0):.0%})\n")
        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Skills query failed: {e}"}]}


# ── Resources ────────────────────────────────────────────────────────────────

def _list_resources():
    return [
        {"uri": "hypermarow://knowledge-graph/entities",
         "name": "Knowledge Graph Entities",
         "description": "All entities in the knowledge graph with types and properties",
         "mimeType": "application/json"},
        {"uri": "hypermarow://procedural-memory/rules",
         "name": "Procedural Memory Rules",
         "description": "All automation rules with levels and success rates",
         "mimeType": "application/json"},
        {"uri": "hypermarow://episodic-memory/recent",
         "name": "Recent Episodic Memories",
         "description": "Last 20 episodic records with outcomes and emotions",
         "mimeType": "application/json"},
        {"uri": "hypermarow://q-table/state",
         "name": "Q-Table Summary",
         "description": "Q-table statistics: shape, nonzero entries, value distribution",
         "mimeType": "application/json"},
    ]


def _read_resource(uri: str) -> dict:
    if not _HM_READY:
        _init_hm()

    if uri == "hypermarow://knowledge-graph/entities":
        stats = DC.knowledge_graph.get_stats()
        central = DC.knowledge_graph.get_central_entities(10)
        data = {
            "total": stats["total_entities"],
            "relationships": stats["total_relationships"],
            "types": stats.get("entity_types", {}),
            "top_central": [{"name": c["entity"]["name"] if c["entity"] else "?",
                             "degree": c["degree"]} for c in central],
        }
        return {"contents": [{"uri": uri, "mimeType": "application/json",
                "text": json.dumps(data, ensure_ascii=False, indent=2)}]}

    elif uri == "hypermarow://procedural-memory/rules":
        rules = DC.procedural_memory.data.get("rules", {})
        summary = [{"name": r["rule_name"], "level": r["level"],
                     "success_rate": r["success_rate"],
                     "patterns": r.get("context_patterns", [])[:5]}
                   for r in list(rules.values())[:20]]
        return {"contents": [{"uri": uri, "mimeType": "application/json",
                "text": json.dumps({"total": len(rules), "rules": summary},
                                   ensure_ascii=False, indent=2)}]}

    elif uri == "hypermarow://episodic-memory/recent":
        episodes = DC.episodic_memory.get_recent_episodes(20)
        summary = [{"what": e["what"][:100], "outcome": e["outcome"],
                     "emotion": e["emotion"], "importance": e["importance"],
                     "tags": e.get("tags", []), "when": e.get("when", "")}
                   for e in episodes]
        return {"contents": [{"uri": uri, "mimeType": "application/json",
                "text": json.dumps({"total": len(episodes), "episodes": summary},
                                   ensure_ascii=False, indent=2)}]}

    elif uri == "hypermarow://q-table/state":
        ql = DC.ql_agent.get_stats()
        import numpy as np
        q_flat = DC.ql_agent.q_table.flatten()
        data = {
            "shape": list(DC.ql_agent.q_table.shape),
            "nonzero": ql["nonzero_entries"],
            "total": ql["total_entries"],
            "q_mean": round(float(np.mean(q_flat)), 4),
            "q_std": round(float(np.std(q_flat)), 4),
            "q_min": round(float(np.min(q_flat)), 4),
            "q_max": round(float(np.max(q_flat)), 4),
            "buffer_size": ql["total_experiences"],
            "distinct_states": ql.get("distinct_states", 0),
            "neural_mode": ql.get("neural_mode", "tabular"),
        }
        return {"contents": [{"uri": uri, "mimeType": "application/json",
                "text": json.dumps(data, ensure_ascii=False, indent=2)}]}

    return {"contents": [{"uri": uri, "text": f"Resource not found: {uri}"}]}


# ── Prompts ──────────────────────────────────────────────────────────────────

def _list_prompts():
    return [
        {"name": "decide",
         "description": "Generate a decision prompt for the current context, pulling in relevant memories and rules",
         "arguments": [
             {"name": "action", "description": "Action being considered", "required": True},
             {"name": "task", "description": "Current task", "required": True},
         ]},
        {"name": "reflect",
         "description": "Generate a reflection prompt to review recent decisions and identify patterns",
         "arguments": []},
    ]


def _get_prompt(name: str, args: dict) -> dict:
    if not _HM_READY:
        _init_hm()

    if name == "decide":
        action = args.get("action", "")
        task = args.get("task", "")

        # Gather context
        check_result = DC.check(action=action, context={"task": task}) if action else {}
        rl = check_result.get("rl_recommendation", {}) or {}

        rules_text = ""
        for hint in check_result.get("procedural_hints", [])[:3]:
            rules_text += f"- [{hint['rule_name']}] L{hint['level']} ({hint.get('success_rate',0):.0%})\n"

        recent = DC.episodic_memory.get_recent_episodes(3)
        episodes_text = ""
        for ep in recent:
            episodes_text += f"- [{ep['outcome']}] {ep['what'][:80]}\n"

        prompt = (
            f"You are considering the action '{action}' for task '{task}'.\n\n"
            f"SYSTEM RECOMMENDATION:\n"
            f"  RL suggests: {rl.get('recommended_action','N/A')} "
            f"(confidence={rl.get('confidence',0):.0%})\n\n"
            f"MATCHING RULES:\n{rules_text or '(none)'}\n"
            f"RECENT EXPERIENCES:\n{episodes_text or '(none)'}\n"
            f"Based on this context, what should the next action be?"
        )
        return {"messages": [{"role": "user", "content": {"type": "text", "text": prompt}}]}

    elif name == "reflect":
        meta = DC.metacognition.get_performance_dashboard()
        kg = DC.knowledge_graph.get_stats()
        prompt = (
            f"Reflect on recent HyperMarrow performance:\n\n"
            f"  Decision accuracy: {meta.get('recent_accuracy',0):.0%}\n"
            f"  Calibration ECE: {meta.get('calibration',{}).get('ece',0):.3f}\n"
            f"  Overall health: {meta.get('overall_health','?')}\n"
            f"  Knowledge graph: {kg.get('total_entities',0)} entities\n"
            f"  Consecutive failures: {meta.get('consecutive_failures',0)}\n\n"
            f"What patterns do you see? What should be adjusted?"
        )
        return {"messages": [{"role": "user", "content": {"type": "text", "text": prompt}}]}

    return {"messages": [{"role": "user", "content": {"type": "text",
            "text": f"Prompt not found: {name}"}}]}


# ── Main Loop ────────────────────────────────────────────────────────────────

def main():
    """MCP Server main loop — reads JSON-RPC from stdin, writes to stdout."""
    _log("Starting MCP server...")
    _init_hm()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            response = handle_message(msg)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            _log(f"Invalid JSON: {line[:100]}")
        except Exception:
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
