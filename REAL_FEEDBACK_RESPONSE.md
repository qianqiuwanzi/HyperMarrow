# 真实用户反馈 — HyperMarrow 方案报告

**数据来源**：182 条真实用户反馈（GitHub Issues / Reddit / Twitter）  
**日期**：2026-07-05

---

## 一、用户最痛的 5 个问题 vs HyperMarrow 现状

| # | 用户痛点 | 提及 | HyperMarrow | 判决 |
|:--:|----------|:--:|-------------|:--:|
| 1 | 跨会话记忆不连续 | 32 | EpisodicMemory + Q-table + KG + PM 全持久化 JSON | ✅ 已解决 |
| 2 | 上下文压缩丢失记忆 | 17 | 这不是记忆系统的问题，是 Agent 上下文窗口管理 | ❌ 不归我们 |
| 3 | 子代理无法访问父记忆 | 15 | AgentRegistry + create_for_agent 已支持，Interceptor 未接线 | ⚠️ 该做 |
| 4 | 已存储的记忆被忽略 | 14 | check() 走 PM→RL→KG→VecDB 链，但"记忆优先"不显式 | ⚠️ 该做 |
| 5 | 记忆检索不精准 | 12 | KG + VecDB + AnalogicalReasoner 三通路，相关性排序弱 | ⚠️ 该做 |

---

## 二、13 项需求逐条判决

### ✅ 已解决（HyperMarrow 领先竞品）

| # | 需求 | HyperMarrow 实现 | 竞品状态 |
|:--:|------|-----------------|:--:|
| 7 | 记忆衰减/遗忘 | Ebbinghaus LTD (`R(t)=R0×e^(-t/τ)`) + 检索延长半衰期 | **所有竞品无** |
| 10 | 记忆优先级 | EpisodicMemory importance (1-5) + 情感调制 LTP | **所有竞品无** |
| 12 | 记忆只存不学 | Q-Learning (408/700 Q值) + SkillExtractor + MetaLearner | **所有竞品无** |
| 1 | 跨会话持久化 | EM + Q-table + KG + PM 全持久化 JSON | Claude 有但弱(CLAUDE.md), Codex 无 |
| 8 | 记忆膨胀控制 | LTD Ebbinghaus 衰减 + merge_similar_episodes + 归档 | 所有竞品无 |

### ⚠️ 该做（HyperMarrow 有能力覆盖但未完成）

| # | 需求 | 差距 | 方案 |
|:--:|------|------|------|
| 3 | 子代理记忆继承 | AgentRegistry 已有框架, Interceptor 未接线 | `hm.intercept()` 增加 `inherit_from` 参数 |
| 4 | 存储记忆被忽略 | "记忆优先"协议隐式, 无显式 lookup_path | check() 返回 `lookup_path` 字段 |
| 5 | 检索精准度 | 按时间排序而非相关性 | KG 检索增加相关度评分, 词频×时效×重要性 |
| 13 | 性能随数量下降 | JSON 全量读写, 1000+ 条后变慢 | 非紧急但已知 |

### ❌ 不应做（不是记忆系统的职责）

| # | 需求 | 原因 |
|:--:|------|------|
| 2 | 上下文压缩丢失记忆 | OpenClaw/Claude Code 的上下文窗口管理 |
| 6 | Token 消耗浪费 | API 层问题, 记忆系统不管理 Token |
| 9 | 多设备同步 | 文件同步问题, 不在记忆系统职责 |
| 11 | 可视化编辑 | CLI 已有 `stats/search/export`, Web UI 是独立项目 |

---

## 三、P0 实施方案（3 项，1.5 天）

### P0-1：子代理记忆继承（对标需求 #3，15 次提及）

**用户原话**："296 个子代理会话，0 个持久化了项目记忆"

**方案**：在 `hm.intercept()` 增加 `inherit_from` 参数：

```python
# 父代理创建子代理时
hm.intercept(user_message, agent_response, 
             inherit_from="openclaw",    # 继承 openclaw 的 PM 规则
             inherit_level="rules")      # rules | full | none
```

**实现**：`interceptor.py` 增加 `_inject_inherited_context()`，将父 Agent 的 PM 规则和 KG 实体注入子 Agent 的 WM。

**工作量**：0.5 天

### P0-2：显式"记忆优先"协议（对标需求 #4，14 次提及）

**用户原话**："MEMORY.md 指令在快速处理时被跳过"

**方案**：`hm.check()` 返回结果中增加 `lookup_path` 字段：

```python
result = hm.check("try_fix", task="download_timeout")
# result["lookup_path"] = [
#     "PM: 2 rules matched (L5 '重试3次', L2 '切换技能')",
#     "KG: 3 entities found (timeout, P2b, download)",
#     "RL: Q=0.357 for 'try_fix_three_times'",
#     "EM: 1 similar episode (2026-07-04, outcome=success)"
# ]
```

**实现**：`decision_check.py` 的 `check()` 返回增加 `lookup_path` 字段，Interceptor 在每次拦截时显式标注知识来源。

**工作量**：0.5 天

### P0-3：检索相关性排序（对标需求 #5，12 次提及）

**用户原话**："检索到的记忆按时间排序，而不是按相关性"

**方案**：KG 检索增加综合评分 = 词频匹配度 × 时效衰减 × 重要性权重：

```python
def _relevance_score(entity, query, now):
    tf = _token_overlap(entity.name, query)       # 词频匹配 0-1
    recency = _ebbinghaus(entity.updated_at, now)  # 时效衰减 0-1
    importance = entity.get("weight", 0.5)         # 重要性 0-1
    return tf * 0.5 + recency * 0.3 + importance * 0.2
```

**实现**：`knowledge_graph.py` 的 `search_entities()` 增加 `sort_by="relevance"` 参数。

**工作量**：0.5 天

---

## 四、竞品通病 — HyperMarrow 的三个核心优势（保持）

| 竞品通病 | HyperMarrow 优势 |
|----------|-----------------|
| 记忆 = 平面 KV 存储 | KnowledgeGraph（实体-关系-实体）— **唯一具备结构化记忆** |
| 只存不学 | Q-Learning + DreamCycle + SkillExtractor — **唯一具备完整学习闭环** |
| 没有遗忘机制 | Ebbinghaus LTD + 情感调制 + 检索延长半衰期 — **唯一具备生物遗忘曲线** |

这三个优势是 HyperMarrow 的壁垒，所有竞品都不具备。保持。

---

## 五、一句话总结

> 182 条真实用户反馈中，13 项核心需求有 5 项 HyperMarrow 已领先解决（衰减、优先级、学习、持久化、膨胀控制），3 项该做（子代理继承、记忆优先协议、相关性排序），1.5 天搞定。5 项不应做（上下文压缩、Token 优化、多设备同步、可视化 UI、性能优化）——那不是记忆系统的职责。**用户最痛的不是"功能不够多"，是"已有的功能不可见"。**
