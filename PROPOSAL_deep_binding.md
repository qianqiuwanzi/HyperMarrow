# 技术提案：HyperMarrow 深度绑定 Agent 记忆与学习系统

> 2026-07-08 | 此文档为技术提案，由 Agent 自行评估是否采纳
>
> ⚠️ **采纳前务必备份原文件** — 涉及的 Agent 配置文件（如 SOUL.md、MEMORY.md）在修改前应做好备份。

---

## 背景

当前 HyperMarrow 以钩子（hook）模式接入 Agent：Agent 调用 `check()` 获取建议，但完全可以选择忽略。HyperMarrow 是"众多输入之一"，不是"权威记忆源"。

## 方案：四级深度绑定

| 级别 | 能力 | 对 Agent 的改变 | 风险 |
|------|------|---------------|------|
| **L1** | 用 `hm.remember()/recall()` 替代 MEMORY.md 读写 | 改读写习惯 | 低 |
| **L2** | 每条消息前自动注入相关记忆到上下文 | 改 prompt 组装 | 低 |
| **L3** | 高风险动作被 `enforce()` 拦截 | 加入检查点 | 中 |
| **L4** | 工具选择由 Q 表 `best_action()` 驱动 | 改决策逻辑 | 高 |

**Agent 可以自由选择启用哪些级别**，不需要一次全部采用。

---

## L1：记忆替代

**当前做法：**
```
Agent 手动编辑 MEMORY.md → 纯文本，易过时，无法跨会话关联
```

**提案做法：**
```python
# 替代 MEMORY.md 写入
def remember(what: str, importance: int = 3):
    hm.record("remember", {"content": what}, "noted", reward=0.5, note=what)
    # HyperMarrow 自动：存入情景记忆 + 提取实体 → KG + 创建/匹配规则 → PM

# 替代 MEMORY.md 读取
def recall(query: str, limit: int = 5) -> str:
    r = hm.search(query, limit)
    return "\n".join(
        f"- [{e.get('when','?')[:10]}] {e.get('what','')[:100]} ({e.get('outcome','?')})"
        for e in r
    )
```

**HyperMarrow 侧无需改动** — `record()` 和 `search()` 接口已就绪。

---

## L2：上下文注入

**提案做法：** 在 Agent 处理消息前，调用以下函数并将返回文本拼接到 system prompt 前：

```python
def build_context(message: str) -> str:
    """
    返回应注入到 Agent 上下文中的记忆块。
    包括：相关规则、RL 建议、关联实体、风险提示。
    """
    result = hm.check("understand", message=message)
    parts = []

    hints = result.get("procedural_hints", [])
    if hints:
        parts.append("相关经验规则:")
        for h in hints[:3]:
            parts.append(f"  - {h['rule_name']} (成功率:{h.get('success_rate',0):.0%}, 级别:{h.get('level',1)})")

    rl = result.get("rl_recommendation") or {}
    if rl.get("confidence", 0) > 0.3:
        parts.append(f"建议动作: {rl['recommended_action']} (置信度:{rl['confidence']:.0%})")

    entities = result.get("related_entities", [])
    if entities:
        names = list(dict.fromkeys(e["related"] for e in entities))[:5]
        parts.append(f"相关知识: {', '.join(names)}")

    return "[HyperMarrow 记忆召回]\n" + "\n".join(parts) if parts else ""

# Agent 在你的 prompt 组装代码中加入:
# context = build_context(user_message)
# full_prompt = f"{system_prompt}\n\n{context}\n\n用户: {user_message}"
```

**HyperMarrow 侧改动：** 无需改动，`check()` 已返回所需全部数据。如需简化，可在 `server.py` 新增一个便捷端点：
```
GET /api/v1/agents/{agent_id}/context?message=...
→ 返回 {context_text: "...", rules: [...], entities: [...]}
```

---

## L3：决策拦截

**提案做法：** 在 Agent 执行"高风险"动作前，插入一个强制检查点：

```python
def enforce(action: str, **context) -> dict:
    """
    返回 {blocked: bool, reason: str, override_suggested: bool, recommended_action: str}
    - blocked=True → 必须停止执行
    - override_suggested=True → 强烈建议改用 recommended_action
    """
    result = hm.check(action, **context)

    # Level 5 规则 → 强制阻止
    for hint in result.get("procedural_hints", []):
        if hint["level"] >= 5:
            if any(kw in hint.get("rule_name", "").lower()
                   for kw in ("skip", "block", "never", "禁止")):
                return {"blocked": True, "reason": f"规则阻止: {hint['rule_name']}"}

    # allowed=False → 阻止
    if not result.get("allowed", True):
        return {"blocked": True, "reason": result.get("suggestion", "")}

    # RL 高置信度 (≥70%) 推荐不同动作 → 建议替换
    rl = result.get("rl_recommendation") or {}
    if rl.get("confidence", 0) > 0.7 and rl.get("recommended_action") != action:
        return {
            "blocked": False,
            "override_suggested": True,
            "recommended_action": rl["recommended_action"],
            "confidence": rl["confidence"],
        }

    return {"blocked": False, "override_suggested": False}

# Agent 使用方式:
# result = enforce("skip_download", phase="P2b")
# if result["blocked"]:
#     return f"Blocked: {result['reason']}"  # 终止执行
# if result["override_suggested"]:
#     action = result["recommended_action"]    # 改用推荐动作
```

**HyperMarrow 侧无需改动。**

---

## L4：Q 值驱动工具选择

**提案做法：** Agent 在不确定该用什么工具/技能时，让 Q 表推荐：

```python
def best_action(task: str = "", phase: str = "", error: str = "") -> dict:
    """
    返回 {source: "rl"|"rule"|"fallback", action: str, confidence: float}
    - source="rl" → Q 表推荐，置信度 >50%
    - source="rule" → 程序性规则命中，成功率 >60%
    - source="fallback" → 无足够经验，Agent 自行判断
    """
    result = hm.check("", task=task, phase=phase, error_type=error)

    rl = result.get("rl_recommendation") or {}
    if rl.get("confidence", 0) > 0.5:
        return {"source": "rl", "action": rl["recommended_action"],
                "confidence": rl["confidence"], "alternatives": rl.get("alternatives", [])}

    hints = result.get("procedural_hints", [])
    if hints and hints[0].get("success_rate", 0) > 0.6:
        return {"source": "rule", "action": hints[0]["rule_name"],
                "confidence": hints[0]["success_rate"]}

    return {"source": "fallback", "reason": "无足够历史经验"}

# Agent 使用方式:
# choice = best_action(task="download", phase="P2b", error="timeout")
# if choice["source"] != "fallback":
#     execute(choice["action"])
# else:
#     # Agent 自己判断
```

**HyperMarrow 侧无需改动。** L4 对历史数据量要求最高，建议在 L1-L3 运行一段时间积累足够经验后再启用。

---

## 建议采纳路径

```
Week 1: L1 + L2（低风险，立即可用）
  → 备份 MEMORY.md → 改用 hm.remember() 写入
  → 在 prompt 组装中注入 build_context()

Week 2: 观察 L1+L2 效果，积累 Q 表经验

Week 3: L3（中风险，需要足够规则积累）
  → 在 3-5 个关键动作上加入 enforce() 检查点

Week 4+: L4（视 Q 表覆盖率决定是否启用）
  → 当 Q 表非零条目 >500 且置信度 >70% 的推荐比例 >30% 时启用
```

## 需要改动的文件

| 文件 | 归属 | 改动内容 |
|------|------|---------|
| `SOUL.md` | Agent 配置 | 新增 `remember()`, `recall()`, `build_context()`, `enforce()`, `best_action()` 函数 |
| `~/.claude/CLAUDE.md` 或项目 `MEMORY.md` | Agent 记忆 | 内容迁移到 HyperMarrow，原文件备份为 `.bak` |
| HyperMarrow `server.py` | 平台 | (可选) 新增 `GET /context` 端点简化 L2 调用 |

## 回滚方式

如深度绑定后效果不理想，恢复原文件备份即可：
```bash
cp SOUL.md.bak SOUL.md
cp MEMORY.md.bak MEMORY.md
```
HyperMarrow 本身不需要任何回滚操作——它只是不再被调用。
