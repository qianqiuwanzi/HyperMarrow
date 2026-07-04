#!/usr/bin/env python3
"""
HyperMarrow MCP Server — stdio transport using official mcp library.

Requires: pip install mcp
Start:    python hypermarow_mcp.py
Config:   openclaw.json → mcp.servers.hypermarrow
"""
import sys, os, json, traceback
from pathlib import Path

_HERE = Path(__file__).parent.parent  # openclaw-memory-system/
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

from memory_integration.decision_check import create_for_agent, get_agent_registry

# ── Init on first use ─────────────────────────────────────────────────────────
DC = None
_REG = None

def _ensure_init():
    global DC, _REG
    if DC is None:
        DC = create_for_agent("openclaw")
        _REG = get_agent_registry()
        print(f"[HyperMarrow MCP] ready — "
              f"KG={DC.knowledge_graph.get_stats()['total_entities']} entities, "
              f"QL={DC.ql_agent.get_stats()['nonzero_entries']}/700, "
              f"PM={len(DC.procedural_memory.data.get('rules',{}))} rules",
              file=sys.stderr, flush=True)

# ── Tool implementations ──────────────────────────────────────────────────────

def tool_check(action: str, task: str = "", phase: str = "",
               error: str = "", attempts: int = 0) -> str:
    _ensure_init()
    ctx = {}
    if task: ctx["task"] = task
    if phase: ctx["phase"] = phase
    if error: ctx["error_type"] = error
    if attempts: ctx["attempts"] = attempts
    result = DC.check(action=action, context=ctx if ctx else None)
    rl = result.get("rl_recommendation", {}) or {}
    lines = [
        f"Decision Check for '{action}':",
        f"  Allowed: {result.get('allowed', True)}",
        f"  RL Recommends: {rl.get('recommended_action', 'N/A')} "
        f"(conf={rl.get('confidence', 0):.0%}, Q={rl.get('q_value', 0):.3f})",
        f"  Procedural Hints: {len(result.get('procedural_hints', []))}",
        f"  Related KG Entities: {len(result.get('related_entities', []))}",
        f"  Warnings: {len(result.get('warnings', []))}",
    ]
    for w in result.get("warnings", []):
        lines.append(f"    ⚠ {w}")
    return "\n".join(lines)

def tool_record(action: str, outcome: str, task: str = "",
                phase: str = "", reward: float = None, note: str = "") -> str:
    _ensure_init()
    ctx = {}
    if task: ctx["task"] = task
    if phase: ctx["phase"] = phase
    if reward is None:
        reward = 1.0 if outcome == "success" else (-1.0 if outcome == "failure" else 0.0)
    DC.record(action=action, context=ctx if ctx else {}, outcome=outcome,
              reward=reward, note=note or "")
    return f"Recorded: {action} → {outcome} (reward={reward})"

def tool_search(query: str, days: int = 30, limit: int = 5) -> str:
    _ensure_init()
    em_results = DC.episodic_memory.search_episodes(query, n=limit)
    lines = [f"Search: '{query}' (last {days}d):"]
    for i, ep in enumerate(em_results):
        lines.append(f"  {i+1}. [{ep.get('outcome','?')}] "
                     f"{ep.get('what','')[:80]} (imp={ep.get('importance',0)})")
    if DC.enable_vector_db and DC.vector_db:
        try:
            vec = DC.vector_db.search(query, n_results=limit, days_filter=days)
            if vec and vec.get("documents"):
                for docs in vec["documents"][:1]:
                    for doc in docs[:3]:
                        lines.append(f"  [VecDB] {doc[:100]}...")
        except: pass
    if not em_results:
        lines.append("  (no results)")
    return "\n".join(lines)

def tool_stats() -> str:
    _ensure_init()
    kg = DC.knowledge_graph.get_stats()
    pm = DC.procedural_memory.data
    ql = DC.ql_agent.get_stats()
    em = DC.episodic_memory.get_stats()
    meta = DC.metacognition.get_performance_dashboard()
    return (
        f"HyperMarrow Stats:\n"
        f"  Knowledge Graph: {kg.get('total_entities',0)} entities, "
        f"{kg.get('total_relationships',0)} rels\n"
        f"  Procedural Memory: {len(pm.get('rules',{}))} rules\n"
        f"  Q-Learning: {ql.get('nonzero_entries',0)}/{ql.get('total_entries',0)} "
        f"nonzero, buffer={ql.get('total_experiences',0)}, "
        f"mode={ql.get('neural_mode','?')}\n"
        f"  Episodic Memory: {em.get('total_episodes',0)} episodes\n"
        f"  Metacognition: health={meta.get('overall_health','?')}, "
        f"acc={meta.get('recent_accuracy',0):.0%}, "
        f"ECE={meta.get('calibration',{}).get('ece',0):.3f}"
    )

def tool_transfer(source: str = "openclaw", target: str = "luci") -> str:
    _ensure_init()
    result = _REG.cross_agent_transfer(source, target)
    return (f"Cross-transfer {source}→{target}:\n"
            f"  Episodes: {result.get('episodes_transferred',0)}\n"
            f"  Q-cells: {result.get('q_cells_seeded',0)}")

# ── MCP Server ────────────────────────────────────────────────────────────────

def _run_stdio():
    """Run MCP server via stdio using the official mcp library."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import asyncio

    server = Server("hypermarow")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name="check", description="Evaluate an action against all memory subsystems (RL+PM+KG). Returns recommendation with confidence and warnings.",
                 inputSchema={"type":"object","properties":{
                     "action":{"type":"string","description":"Action to evaluate"},
                     "task":{"type":"string","description":"Task description"},
                     "phase":{"type":"string","description":"Current phase"},
                     "error":{"type":"string","description":"Error type"},
                     "attempts":{"type":"integer","description":"Attempt count"}},
                     "required":["action"]}),
            Tool(name="record", description="Record a decision outcome. Updates PM success rate, episodic memory, Q-table, metacognition.",
                 inputSchema={"type":"object","properties":{
                     "action":{"type":"string"},
                     "outcome":{"type":"string","enum":["success","failure","partial"]},
                     "task":{"type":"string"},
                     "phase":{"type":"string"},
                     "reward":{"type":"number"},
                     "note":{"type":"string"}},
                     "required":["action","outcome"]}),
            Tool(name="search", description="Search episodic and vector memory for similar past experiences.",
                 inputSchema={"type":"object","properties":{
                     "query":{"type":"string"},
                     "days":{"type":"integer","default":30},
                     "limit":{"type":"integer","default":5}},
                     "required":["query"]}),
            Tool(name="stats", description="Get system-wide statistics across all memory and learning subsystems.",
                 inputSchema={"type":"object","properties":{}}),
            Tool(name="transfer", description="Transfer learned knowledge between agents.",
                 inputSchema={"type":"object","properties":{
                     "source":{"type":"string","default":"openclaw"},
                     "target":{"type":"string","default":"luci"}},
                     "required":[]}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "check":
                text = tool_check(**{k:v for k,v in arguments.items() if k in ("action","task","phase","error","attempts")})
            elif name == "record":
                text = tool_record(**{k:v for k,v in arguments.items() if k in ("action","outcome","task","phase","reward","note")})
            elif name == "search":
                text = tool_search(**{k:v for k,v in arguments.items() if k in ("query","days","limit")})
            elif name == "stats":
                text = tool_stats()
            elif name == "transfer":
                text = tool_transfer(**{k:v for k,v in arguments.items() if k in ("source","target")})
            else:
                text = f"Unknown tool: {name}"
            return [TextContent(type="text", text=text)]
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return [TextContent(type="text", text=f"Error: {e}")]

    async def main_async():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream,
                           server.create_initialization_options())

    asyncio.run(main_async())


def _run_fallback():
    """Fallback: raw JSON-RPC stdio loop (when mcp library unavailable)."""
    print("[HyperMarrow MCP] Running in fallback JSON-RPC mode", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
            method = msg.get("method", "")
            rpc_id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                resp = {"jsonrpc":"2.0","id":rpc_id,"result":{
                    "protocolVersion":"2024-11-05",
                    "serverInfo":{"name":"hypermarow","version":"2.0.0"},
                    "capabilities":{"tools":{}}}}
            elif method == "tools/list":
                resp = {"jsonrpc":"2.0","id":rpc_id,"result":{"tools":[
                    {"name":"check","description":"Evaluate action"},
                    {"name":"record","description":"Record outcome"},
                    {"name":"search","description":"Search memory"},
                    {"name":"stats","description":"System stats"},
                    {"name":"transfer","description":"Cross-agent transfer"},
                ]}}
            elif method == "tools/call":
                name = params.get("name","")
                args = params.get("arguments",{})
                if name == "check": text = tool_check(**{k:v for k,v in args.items() if k in ("action","task","phase","error","attempts")})
                elif name == "record": text = tool_record(**{k:v for k,v in args.items() if k in ("action","outcome","task","phase","reward","note")})
                elif name == "search": text = tool_search(**{k:v for k,v in args.items() if k in ("query","days","limit")})
                elif name == "stats": text = tool_stats()
                elif name == "transfer": text = tool_transfer(**{k:v for k,v in args.items() if k in ("source","target")})
                else: text = f"Unknown: {name}"
                resp = {"jsonrpc":"2.0","id":rpc_id,"result":{"content":[{"type":"text","text":text}]}}
            elif method == "notifications/initialized":
                continue
            else:
                resp = {"jsonrpc":"2.0","id":rpc_id,"error":{"code":-32601,"message":f"Unknown: {method}"}}

            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    try:
        _run_stdio()
    except ImportError:
        _run_fallback()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        _run_fallback()
