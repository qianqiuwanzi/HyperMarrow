#!/usr/bin/env python3
"""
HyperMarrow CLI — 独立命令行工具

对标 GBrain 的 `gbrain` 命令。不依赖 Bridge/MCP 运行。

Usage:
    hypermarrow stats                   全系统统计
    hypermarrow agents                  列出所有 Agent
    hypermarrow health                  健康报告
    hypermarrow search <query>          搜索记忆
    hypermarrow dream [--json]          触发记忆巩固
    hypermarrow export [--format md|json]  导出知识
    hypermarrow kg entities             列出 KG 实体
    hypermarrow kg central              核心实体
    hypermarrow kg path <A> <B>         A→B 最短路径
"""
import sys, os, json, argparse
from pathlib import Path
from datetime import datetime

_HERE = Path(__file__).parent.parent  # openclaw-memory-system/
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

_DC = None
_REG = None

def _init():
    global _DC, _REG
    if _DC is None:
        from memory_integration.decision_check import create_for_agent, get_agent_registry
        _DC = create_for_agent("openclaw")
        _REG = get_agent_registry()

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_stats(args):
    _init()
    kg = _DC.knowledge_graph.get_stats()
    pm = _DC.procedural_memory.data
    ql = _DC.ql_agent.get_stats()
    em = _DC.episodic_memory.get_stats()
    meta = _DC.metacognition.get_performance_dashboard()
    wm = _DC.working_memory.get_active_context()

    print("=" * 55)
    print("  HyperMarrow System Stats")
    print("=" * 55)
    print(f"  Knowledge Graph:     {kg['total_entities']} entities, "
          f"{kg['total_relationships']} relationships")
    print(f"    Types: {kg.get('entity_types', {})}")
    print(f"    Density: {kg.get('density', 0)}")
    print()
    print(f"  Procedural Memory:   {len(pm.get('rules', {}))} rules")
    levels = {}
    for r in pm.get("rules", {}).values():
        lv = r.get("level", 0)
        levels[lv] = levels.get(lv, 0) + 1
    print(f"    By level: {dict(sorted(levels.items(), reverse=True))}")
    print()
    print(f"  Q-Learning:          {ql['nonzero_entries']}/{ql['total_entries']} "
          f"non-zero ({ql['nonzero_pct']}%)")
    print(f"    Buffer: {ql['total_experiences']} experiences")
    print(f"    Mode: {ql.get('neural_mode', 'tabular')}, "
          f"states: {ql.get('distinct_states', 0)}")
    if ql.get('neural_stats'):
        ns = ql['neural_stats']
        print(f"    Neural: {ns.get('train_steps', 0)} steps, "
              f"loss={ns.get('recent_loss', 'N/A')}")
    print()
    print(f"  Episodic Memory:     {em['total_episodes']} episodes")
    print(f"    With lessons: {em.get('with_lessons', 0)}")
    print(f"    Avg importance: {em.get('avg_importance', 0)}")
    print()
    print(f"  Working Memory:      task={wm.get('current_task', 'none')}, "
          f"stack_depth={wm.get('stack_depth', 0)}")
    print()
    print(f"  Metacognition:       {meta.get('total_decisions', 0)} decisions")
    print(f"    Health: {meta.get('overall_health', '?')} "
          f"(score={meta.get('health_score', 0)}), "
          f"acc={meta.get('recent_accuracy', 0):.0%}")
    print(f"    ECE: {meta.get('calibration', {}).get('ece', 0):.3f}")
    agents = _REG.list_agents()
    print(f"\n  Agents:              {len(agents)} registered ({', '.join(agents)})")


def cmd_agents(args):
    _init()
    print("=" * 55)
    print("  Registered Agents")
    print("=" * 55)
    for aid in _REG.list_agents():
        bundle = _REG.get(aid)
        if not bundle:
            print(f"  {aid}: (bundle missing)")
            continue
        ql = bundle.ql_agent.get_stats()
        em = bundle.episodic_memory.get_stats()
        meta = bundle.metacognition.get_performance_dashboard()
        shared = "✓" if bundle.knowledge_graph else "✗"
        print(f"\n  [{aid}]  actions={bundle.action_dim}, shared={shared}")
        print(f"    QL: {ql['nonzero_entries']}/{ql['total_entries']} Q, "
              f"{ql['total_experiences']} exp")
        print(f"    EM: {em['total_episodes']} episodes")
        print(f"    Meta: health={meta.get('overall_health', '?')}, "
              f"decisions={meta.get('total_decisions', 0)}")


def cmd_health(args):
    _init()
    meta = _DC.metacognition.get_performance_dashboard()
    kg = _DC.knowledge_graph.get_stats()
    em = _DC.episodic_memory.get_stats()

    print("=" * 55)
    print("  Health Report")
    print("=" * 55)
    print(f"  Overall:    {meta.get('overall_health', '?')} "
          f"(score={meta.get('health_score', 0)}/100)")
    print(f"  Accuracy:   {meta.get('recent_accuracy', 0):.0%} (recent)")
    print(f"  ECE:        {meta.get('calibration', {}).get('ece', 0):.3f} "
          f"(<0.1=good, >0.2=needs review)")
    print(f"  Failures:   {meta.get('consecutive_failures', 0)} consecutive")
    print(f"  Anomalies:  {meta.get('anomalies_recent', 0)} recent")
    ref = meta.get('reflections_needed', False)
    print(f"  Reflection: {'NEEDED ⚠' if ref else 'not needed'}")

    # Orphan check
    orphans = []
    if hasattr(_DC.knowledge_graph, 'get_orphan_entities'):
        orphans = _DC.knowledge_graph.get_orphan_entities()
    print(f"  KG Orphans: {len(orphans)} entities (no relationships)")

    # Data file check
    data_dir = _HERE / "data"
    files = list(data_dir.glob("*.json")) if data_dir.exists() else []
    print(f"  Data files: {len(files)} JSON files in data/")
    for f in sorted(files):
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name}: {size_kb:.1f} KB")


def cmd_search(args):
    _init()
    query = args.query
    limit = args.limit or 5
    days = args.days or 30

    print(f"Search: '{query}' (limit={limit}, days={days})")
    print("-" * 40)

    # Episodic search
    em_results = _DC.episodic_memory.search_episodes(query, n=limit)
    if em_results:
        print(f"\n[Episodic Memory] {len(em_results)} results:")
        for i, ep in enumerate(em_results):
            print(f"  {i+1}. [{ep.get('outcome','?')}] {ep.get('what','')[:100]}")
            print(f"     importance={ep.get('importance',0)}, "
                  f"emotion={ep.get('emotion','?')}, "
                  f"tags={ep.get('tags',[])}")
    else:
        print("\n[Episodic Memory] no results")

    # Vector search
    if _DC.enable_vector_db and _DC.vector_db:
        try:
            from sentence_transformers import SentenceTransformer
            vec = _DC.vector_db.search(query, n_results=limit, days_filter=days)
            if vec and vec.get("documents") and vec["documents"][0]:
                print(f"\n[Vector Memory] {len(vec['documents'][0])} results:")
                for i, doc in enumerate(vec["documents"][0]):
                    meta = vec["metadatas"][0][i] if vec.get("metadatas") else {}
                    print(f"  {i+1}. {doc[:100]}...")
                    if meta:
                        print(f"     source={meta.get('source','?')}, "
                              f"created={meta.get('created_at','?')[:19]}")
        except Exception as e:
            print(f"\n[Vector Memory] search failed: {e}")

    # KG search
    kg_results = _DC.knowledge_graph.search_entities(query, limit=limit)
    if kg_results:
        print(f"\n[Knowledge Graph] {len(kg_results)} entities:")
        for e in kg_results:
            print(f"  [{e.get('type','?')}] {e.get('name','?')}")


def cmd_dream(args):
    _init()
    as_json = args.json

    if as_json:
        results = {}
        for aid in _REG.list_agents():
            bundle = _REG.get(aid)
            if bundle and bundle.consolidator:
                r = bundle.consolidator.dream_cycle(force=True)
                results[aid] = r
        output = {
            "status": "ok" if all(r.get("status") == "ok" for r in results.values()) else "partial",
            "timestamp": datetime.now().isoformat(),
            "agents": results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("=" * 55)
        print("  Dream Cycle")
        print("=" * 55)
        for aid in _REG.list_agents():
            bundle = _REG.get(aid)
            if not bundle or not bundle.consolidator:
                continue
            print(f"\n  [{aid}]")
            r = bundle.consolidator.dream_cycle(force=True)
            if isinstance(r, dict) and "phases" in r:
                for phase, count in r["phases"].items():
                    icon = "✓" if count == 0 else "●"
                    print(f"    {icon} {phase}: {count}")
                print(f"    duration: {r.get('duration_sec', 0):.2f}s")
            else:
                print(f"    LTP={r.get('ltp_count',0)}, LTD={r.get('ltd_pruned',0)}, "
                      f"merged={r.get('episodes_merged',0)}")
        _REG.share_all()
        print(f"\n  Cross-agent sharing: complete")


def cmd_activate(args):
    """一键激活高级认知：WorldModel + NeuralAgent"""
    _init()
    from memory_integration.decision_check import create_for_agent
    # Ensure all registered agents have a DC
    for aid in _REG.list_agents():
        try: create_for_agent(aid)
        except: pass
    print("正在激活高级认知能力...")
    for aid in _REG.list_agents():
        bundle = _REG.get(aid)
        if not bundle: continue
        ql = bundle.ql_agent
        # Switch to hybrid mode: neural encoding + tabular Q-table
        if ql.neural_mode == 'tabular':
            from learning_core.q_learning_agent import QLearningAgent
            # Create new hybrid-mode agent with same state space
            new_ql = QLearningAgent(state_space_size=ql.state_space_size,
                                     action_space_size=ql.action_space_size,
                                     neural_mode='hybrid')
            # Copy Q-table from old agent
            new_ql.q_table = ql.q_table.copy()
            new_ql._state_map = ql._state_map.copy()
            new_ql._state_counter = ql._state_counter
            new_ql.experience_buffer = ql.experience_buffer[:]
            # Enable world model
            new_ql.enable_world_model()
            # Train on existing experience
            buf = ql.experience_buffer
            trained = 0
            for exp in buf[-50:]:
                new_ql.add_experience(exp['state'], exp['action'], exp['reward'],
                                      exp['next_state'], exp.get('done', False))
                trained += 1
            # Replace the agent's QL in both bundle and DC
            bundle.ql_agent = new_ql
            if bundle.decision_checkpoint:
                bundle.decision_checkpoint.ql_agent = new_ql
            try:
                from memory_integration.decision_check import _agent_dc_map
                if aid in _agent_dc_map:
                    _agent_dc_map[aid].ql_agent = new_ql
            except: pass
            # Persist: save Q-table + neural weights so API restart picks them up
            from memory_core.config import get_data_dir
            new_ql.q_table_path = str(get_data_dir() / f"q_table_{aid}.json")
            new_ql.save_q_table(new_ql.q_table_path)
            ns = new_ql.get_stats()
            print(f"  {aid}: 神经={ns.get('neural_stats',{}).get('train_steps',0)}步, "
                  f"世界模型={ns.get('world_model_stats',{}).get('world_model',{}).get('train_steps',0) if ns.get('world_model_stats') else 0}步")
        else:
            ql.enable_world_model()
            print(f"  {aid}: 已激活 (已是 {ql.neural_mode} 模式)")
    print("高级认知激活完成。重启 API 后刷新 http://localhost:5173 查看仪表板")

def cmd_export(args):
    _init()
    fmt = args.format or "markdown"

    if fmt == "json":
        data = {
            "kg": _DC.knowledge_graph.get_stats(),
            "ql": _DC.ql_agent.get_stats(),
            "em": _DC.episodic_memory.get_stats(),
            "pm": {
                "total": len(_DC.procedural_memory.data.get("rules", {})),
                "rules": [
                    {"name": r["rule_name"], "level": r["level"],
                     "success_rate": r.get("success_rate", 0)}
                    for r in list(_DC.procedural_memory.data.get("rules", {}).values())[:20]
                ],
            },
            "exported_at": datetime.now().isoformat(),
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        kg = _DC.knowledge_graph.get_stats()
        pm = _DC.procedural_memory.data
        ql = _DC.ql_agent.get_stats()
        em = _DC.episodic_memory.get_stats()

        print(f"# HyperMarrow Knowledge Export")
        print(f"*Exported: {datetime.now().isoformat()}*")
        print()
        print(f"## Knowledge Graph ({kg['total_entities']} entities, "
              f"{kg['total_relationships']} relationships)")
        print()
        by_type = kg.get("entity_types", {})
        for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            print(f"### {etype} ({count})")
        print()
        central = _DC.knowledge_graph.get_central_entities(10)
        print("## Top Central Entities")
        for c in central:
            ent = c.get("entity", {})
            if ent:
                print(f"- **{ent.get('name','?')}** [{ent.get('type','?')}] "
                      f"(degree={c.get('degree',0)}, centrality={c.get('centrality',0)})")
        print()
        print(f"## Procedural Memory ({len(pm.get('rules', {}))} rules)")
        for rid, rule in list(pm.get("rules", {}).items())[:15]:
            print(f"- **[{rule['level']}] {rule['rule_name']}** "
                  f"(sr={rule.get('success_rate',0):.0%}, "
                  f"n={rule.get('total_attempts',0)})")
        print()
        print(f"## Q-Learning ({ql['nonzero_entries']}/{ql['total_entries']} non-zero)")
        print(f"- Mode: {ql.get('neural_mode', '?')}, "
              f"states: {ql.get('distinct_states', 0)}")
        print(f"- Buffer: {ql['total_experiences']} experiences")
        print()
        print(f"## Episodic Memory ({em['total_episodes']} episodes)")
        recent = _DC.episodic_memory.get_recent_episodes(5)
        for ep in recent:
            print(f"- [{ep['outcome']}] {ep.get('what','')[:80]} "
                  f"({ep.get('emotion','?')}, imp={ep.get('importance',0)})")


def cmd_kg(args):
    _init()
    kg = _DC.knowledge_graph

    if args.kg_action == "entities":
        entities = list(kg.data["entities"].values())
        by_type = {}
        for e in entities:
            by_type.setdefault(e["type"], []).append(e["name"])
        for t, names in sorted(by_type.items()):
            print(f"\n[{t}] ({len(names)})")
            for n in names[:20]:
                print(f"  {n}")
            if len(names) > 20:
                print(f"  ... and {len(names)-20} more")

    elif args.kg_action == "central":
        central = kg.get_central_entities(args.limit or 10)
        print(f"Top {len(central)} Central Entities:")
        for i, c in enumerate(central):
            ent = c.get("entity", {})
            if ent:
                print(f"  {i+1}. [{ent.get('type','?')}] {ent.get('name','?')} "
                      f"(degree={c.get('degree',0)})")

    elif args.kg_action == "path":
        if not args.source or not args.target:
            print("Error: --source and --target required for path")
            return
        src = kg.find_entity(args.source)
        tgt = kg.find_entity(args.target)
        if not src:
            print(f"Entity not found: {args.source}")
            print("Try: hypermarrow kg entities (to see all entities)")
            return
        if not tgt:
            print(f"Entity not found: {args.target}")
            print("Try: hypermarrow kg entities (to see all entities)")
            return
        path = kg.shortest_path(src["id"], tgt["id"])
        if path:
            print(f"Path: {src['name']} → {tgt['name']} ({len(path)//2} hops):")
            for item in path:
                if "relation_type" in item:
                    print(f"  --[{item['relation_type']}]--> ", end="")
                else:
                    print(f"[{item.get('type','?')}] {item.get('name','?')}")
        else:
            print(f"No path found between '{src['name']}' and '{tgt['name']}'")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="hypermarrow",
        description="HyperMarrow Memory & Learning System CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("stats", help="Full system statistics")
    sub.add_parser("agents", help="List all registered agents")
    sub.add_parser("health", help="System health report")

    p_search = sub.add_parser("search", help="Search memory")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.add_argument("--days", type=int, default=30)

    p_dream = sub.add_parser("dream", help="Trigger memory consolidation")
    p_dream.add_argument("--json", action="store_true", help="JSON output")

    p_export = sub.add_parser("export", help="Export knowledge")
    p_export.add_argument("--format", choices=["markdown", "json"], default="markdown")

    sub.add_parser("activate", help="One-click activate advanced cognition (WorldModel + Neural)")

    p_kg = sub.add_parser("kg", help="Knowledge Graph queries")
    p_kg_sub = p_kg.add_subparsers(dest="kg_action")
    p_kg_sub.add_parser("entities", help="List all entities by type")
    p_kg_central = p_kg_sub.add_parser("central", help="Most central entities")
    p_kg_central.add_argument("--limit", type=int, default=10)
    p_kg_path = p_kg_sub.add_parser("path", help="Shortest path between entities")
    p_kg_path.add_argument("source", help="Source entity name")
    p_kg_path.add_argument("target", help="Target entity name")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmds = {"stats": cmd_stats, "agents": cmd_agents, "health": cmd_health,
            "search": cmd_search, "dream": cmd_dream, "export": cmd_export,
            "activate": cmd_activate, "kg": cmd_kg}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
