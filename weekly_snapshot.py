# -*- coding: utf-8 -*-
"""
HyperMarrow 每周记忆/学习能力快照采集脚本
- 采集所有可量化的记忆子系统 + 学习子系统指标
- 输出 JSON 快照（带 ISO 时间戳），保存到 snapshots/ 目录
- 若上一周快照存在，则自动计算增量并生成对比报告

用法:
  python weekly_snapshot.py            # 采集快照 + 对比上周
  python weekly_snapshot.py --force    # 强制重新采集（忽略当天已存在快照）
"""
import sys, os, json, argparse
from pathlib import Path
from datetime import datetime, timedelta

HM = r"D:\OpenClaw\workspace\HyperMarrow"
sys.path.insert(0, HM)
sys.path.insert(0, os.path.join(HM, "openclaw-memory-system"))
sys.path.insert(0, os.path.join(HM, "openclaw-learning-system"))

SNAP_DIR = Path(HM) / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)


def _safe_stats(obj, *alt_methods):
    """安全取统计：依次尝试给定方法名，失败返回 {}。"""
    for m in alt_methods:
        fn = getattr(obj, m, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                continue
    return {}


def build_snapshot(agent_id="openclaw"):
    from memory_integration.decision_check import create_for_agent
    from memory_core.config import setup_hf_mirror
    setup_hf_mirror()

    dc = create_for_agent(agent_id)

    # ── 记忆能力指标（Memory）──────────────────────────────────────
    kg = _safe_stats(dc.knowledge_graph, "get_stats")
    em = _safe_stats(dc.episodic_memory, "get_stats")
    wm = _safe_stats(dc.working_memory, "get_stats")
    meta = _safe_stats(dc.metacognition, "get_stats")
    con = _safe_stats(dc.consolidator, "get_stats")
    vec = _safe_stats(dc.vector_db, "get_stats") if dc.vector_db else {}
    pm = _safe_stats(dc.procedural_memory, "get_automation_summary", "get_stats")
    se = _safe_stats(dc.skill_extractor, "get_stats")
    pros = _safe_stats(dc.prospective, "get_stats")
    trans = _safe_stats(dc.transfer_learner, "get_stats")

    # ── 学习能力指标（Learning）────────────────────────────────────
    ql = _safe_stats(dc.ql_agent, "get_stats") if dc.ql_agent else {}
    mlearner = _safe_stats(dc.meta_learner, "get_stats")

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "agent_id": agent_id,
        "memory": {
            "knowledge_graph": kg,
            "episodic_memory": em,
            "working_memory": wm,
            "metacognition": meta,
            "consolidator": con,
            "vector_db": vec,
            "procedural_memory": pm,
            "skill_extractor": se,
            "prospective": pros,
            "transfer_learner": trans,
        },
        "learning": {
            "q_learning": ql,
            "meta_learner": mlearner,
        },
    }
    return snapshot


def save_snapshot(snap, label=None):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = SNAP_DIR / f"snapshot_{ts}.json"
    fname.write_text(json.dumps(snap, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return fname


def find_prev_snapshot():
    """找最近一个 '< 今天' 的快照（即上一周或更早）。"""
    files = sorted(SNAP_DIR.glob("snapshot_*.json"), key=lambda p: p.name)
    if not files:
        return None
    today = datetime.now().date()
    prev = None
    for f in files:
        # snapshot_YYYYMMDD_HHMMSS.json
        try:
            d = datetime.strptime(f.name[9:17], "%Y%m%d").date()
        except Exception:
            continue
        if d < today:
            prev = f
        else:
            break
    return prev


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def diff_metrics(a, b, prefix=""):
    """递归对比两个 dict，返回 {path: (old, new, delta)}，只在数值型变化时记录。"""
    out = {}
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            na = a.get(k)
            nb = b.get(k)
            out.update(diff_metrics(na, nb, f"{prefix}.{k}" if prefix else k))
    else:
        va = _num(a)
        vb = _num(b)
        if va is not None and vb is not None:
            out[prefix] = (va, vb, round(vb - va, 4))
    return out


def summarize(curd, prevd):
    """生成可读性对比报告（仅保留记忆/学习关键维度）。"""
    cur_m = curd["memory"]; prev_m = prevd["memory"]
    cur_l = curd["learning"]; prev_l = prevd["learning"]

    lines = []
    lines.append(f"📅 复盘周期: {prevd['timestamp']}  →  {curd['timestamp']}")
    lines.append("")

    # 记忆能力
    lines.append("🧠 记忆能力 (Memory)")
    lines.append("-" * 48)
    def line(name, cur, prev, pct=False, higher_better=True):
        if cur is None or prev is None:
            return
        delta = cur - prev
        if pct:
            s = f"{cur:.1%} (上周 {prev:.1%}, Δ{delta:+.1%})"
        else:
            s = f"{cur} (上周 {prev}, Δ{delta:+.0f})"
        arrow = "▲" if (delta > 0) == higher_better else ("▼" if delta != 0 else "—")
        verdict = "进步" if (delta > 0) == higher_better and delta != 0 else ("退步" if delta != 0 else "持平")
        lines.append(f"  {name:<22} {s:<34} {arrow} {verdict}")

    kg_c = cur_m["knowledge_graph"]; kg_p = prev_m["knowledge_graph"]
    line("知识图谱实体数", kg_c.get("total_entities"), kg_p.get("total_entities"))
    line("知识图谱关系数", kg_c.get("total_relationships"), kg_p.get("total_relationships"))
    line("图谱密度", _num(kg_c.get("density")), _num(kg_p.get("density")), pct=True)

    em_c = cur_m["episodic_memory"]; em_p = prev_m["episodic_memory"]
    line("情景记忆总数", em_c.get("total_episodes"), em_p.get("total_episodes"))
    line("成功经验数", em_c.get("by_outcome", {}).get("success"), em_p.get("by_outcome", {}).get("success"))
    line("失败经验数", em_c.get("by_outcome", {}).get("failure"), em_p.get("by_outcome", {}).get("failure"), higher_better=False)
    line("平均重要度", _num(em_c.get("avg_importance")), _num(em_p.get("avg_importance")))

    vec_c = cur_m.get("vector_db") or {}; vec_p = prev_m.get("vector_db") or {}
    cvec = vec_c.get("total_vectors") if isinstance(vec_c, dict) else None
    pvec = vec_p.get("total_vectors") if isinstance(vec_p, dict) else None
    line("语义向量数", cvec, pvec)

    se_c = cur_m.get("skill_extractor") or {}; se_p = prev_m.get("skill_extractor") or {}
    cse = se_c.get("total_skills") if isinstance(se_c, dict) else None
    pse = se_p.get("total_skills") if isinstance(se_p, dict) else None
    line("提取技能数", cse, pse)

    pm_c = cur_m.get("procedural_memory") or {}; pm_p = prev_m.get("procedural_memory") or {}
    line("程序记忆规则数", pm_c.get("total_rules"), pm_p.get("total_rules"))

    con_c = cur_m.get("consolidator") or {}; con_p = prev_m.get("consolidator") or {}
    ccon = con_c.get("total_consolidations") if isinstance(con_c, dict) else None
    pcon = con_p.get("total_consolidations") if isinstance(con_p, dict) else None
    line("记忆巩固次数", ccon, pcon)

    # 学习能力
    lines.append("")
    lines.append("🎓 学习能力 (Learning)")
    lines.append("-" * 48)
    q_c = cur_l["q_learning"]; q_p = prev_l["q_learning"]
    line("Q表非零项", q_c.get("nonzero_entries"), q_p.get("nonzero_entries"))
    line("Q表非零率", _num(q_c.get("nonzero_pct")) and q_c["nonzero_pct"]/100,
                          _num(q_p.get("nonzero_pct")) and q_p["nonzero_pct"]/100, pct=True)
    line("累计学习经验", q_c.get("total_experiences"), q_p.get("total_experiences"))
    line("Q值总和", _num(q_c.get("q_sum")), _num(q_p.get("q_sum")))
    line("探索率epsilon", _num(q_c.get("epsilon")), _num(q_p.get("epsilon")), higher_better=False)

    ml_c = cur_l.get("meta_learner") or {}; ml_p = prev_l.get("meta_learner") or {}
    cml = ml_c.get("total_adjustments") if isinstance(ml_c, dict) else None
    pml = ml_p.get("total_adjustments") if isinstance(ml_p, dict) else None
    line("元学习调整次数", cml, pml)

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="强制采集")
    args = ap.parse_args()

    snap = build_snapshot()
    fname = save_snapshot(snap)
    print(f"[snapshot] saved -> {fname.name}")

    prev = find_prev_snapshot()
    if prev is None:
        print("[compare] 没有上一周快照，本周为基线。下周一起可自动对比。")
        return

    prevd = json.loads(prev.read_text(encoding="utf-8"))
    report = summarize(snap, prevd)
    print("\n" + report)

    # 同时存一份对比报告
    rep_path = SNAP_DIR / f"compare_{datetime.now().strftime('%Y%m%d')}.md"
    rep_path.write_text(report, encoding="utf-8")
    print(f"\n[report] saved -> {rep_path.name}")


if __name__ == "__main__":
    main()
