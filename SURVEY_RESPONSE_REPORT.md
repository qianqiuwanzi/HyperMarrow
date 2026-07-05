# 智能体记忆学习系统公共需求 — HyperMarrow 方案报告

**基于**：`2026-07-05_agent_memory_learning_survey.md`  
**日期**：2026-07-05

---

## 一、总判：9 项需求，4 项已解决，2 项该做，3 项不应做

| # | 公共需求 | HyperMarrow 状态 | 判决 |
|:--:|----------|:---------------:|:--:|
| P0-1 | 上下文窗口管理 | WorkingMemory + AttentionGate + sliding window | ✅ 已解决 |
| P0-2 | 跨会话持久化记忆 | EpisodicMemory + Q-table + KG + PM + VecDB | ✅ 已解决 |
| P0-3 | 记忆检索精准度 | KG(结构化) + VecDB(语义) + AnalogicalReasoner(类比) | ✅ 已解决 |
| P1-4 | 缓存策略优化 | — | ❌ **不应做** |
| P1-5 | 上下文污染防护 | AgentRegistry 隔离 → 缺输入校验 | ⚠️ **该做** |
| P1-6 | 代码/上下文回滚 | — | ❌ **不应做** |
| P2-7 | 工作流标准化 | — | ❌ **不应做** |
| P2-8 | 并行执行支持 | — | ❌ 不应做 (已由 OpenClaw 解决) |
| P2-9 | 学习系统可控 | Metacognition 监控 → 缺控制 | ⚠️ **该做** |

---

## 二、该做的 2 项（HyperMarrow 应实现）

### 需求 P1-5：上下文污染防护

**问题**：OpenClaw 报告恶意记忆文件可影响所有 Session，Session 间数据泄露风险。

**HyperMarrow 现状**：AgentRegistry 已实现 per-agent 隔离（WM/EM/QL/Meta 各自独立文件），但缺少输入校验——任何内容都可以写入记忆。

**方案**：在 `interceptor.py` 和 `record()` 中增加输入清洗：

```python
# 输入校验层
def _sanitize_input(text: str, max_len: int = 2000) -> str:
    """防止恶意/过大的内容污染记忆系统"""
    if len(text) > max_len:
        text = text[:max_len] + "..."
    # 过滤明显的注入攻击模式
    forbidden = ["<script>", "DROP TABLE", "rm -rf", "System Prompt:"]
    for pattern in forbidden:
        if pattern.lower() in text.lower():
            text = text.replace(pattern, "[FILTERED]")
    return text
```

**工作量**：0.5 天。新增 `memory_core/input_guard.py`，在 interceptor 和 record 入口调用。

### 需求 P2-9：学习系统可控

**问题**：Hermes 报告闭环学习系统可能导致不可预测的行为变化。

**HyperMarrow 现状**：MetacognitionMonitor 监控 ECE/准确率/异常，但只监控不控制。用户无法干预 Q 表更新、LTP 方向、技能提取。

**方案**：在 `hm` 接口中增加 3 个控制方法：

```python
hm.freeze_learning()     # 冻结 Q 表更新 (生产环境安全模式)
hm.rollback_q("2026-07-01")  # Q 表回滚到指定日期的快照
hm.override_rule("rule_id", level=1)  # 手动降级/升级规则
```

**工作量**：1 天。在 `QLearningAgent` 增加 `freeze`/`rollback`，在 `hm` 暴露控制接口。

---

## 三、不应做的 3 项（不属于 HyperMarrow 职责）

### 需求 P1-4：缓存策略优化

**问题**：Claude Code 有两个缓存 Bug 导致 API 成本无声推高 10-20 倍。

**为什么不应做**：这是 Claude Code 的 **API 层**问题（Bun 运行时计费标识符替换逻辑），与记忆系统无关。HyperMarrow 不控制 API 调用、不管理 Token 计数、不参与 Prompt Caching 配置。

**如果 OpenClaw 需要**：在 OpenClaw 的 API 调用层解决，不在 HyperMarrow。

### 需求 P1-6：代码/上下文回滚

**问题**：Codex 生成错误代码后无法快速恢复到稳定状态。

**为什么不应做**：这是 **代码执行引擎**的职责（Git revert、文件版本管理），不是记忆系统该做的。HyperMarrow 记录"发生了什么决策"，不管理"代码文件版本"。

**HyperMarrow 可以辅助**：`record()` 记录每次代码修改的上下文，search 可以查询"上次这个文件是怎么改的"——这已经实现了。

### 需求 P2-7：工作流标准化

**问题**：Codex 缺乏需求→设计→实现→测试的标准化流程。

**为什么不应做**：工作流是 **Agent 的执行层**（Skill、Tool 编排），不是记忆系统。HyperMarrow 提供记忆支持，不定义 Agent 怎么工作。

---

## 四、已解决的 4 项（HyperMarrow 已覆盖）

### P0-1：上下文窗口管理 ✅

| 需求 | HyperMarrow 实现 |
|------|-----------------|
| 自动压缩历史对话 | WorkingMemory sliding window (MAX=50) + Ebbinghaus LTD decay |
| 智能修剪工具结果 | AttentionGate.filter() 按目标相关性过滤 |
| 精准控制 Token 消耗 | `token_counter.py` tiktoken-based 计数 |

### P0-2：跨会话持久化记忆 ✅

| 需求 | HyperMarrow 实现 |
|------|-----------------|
| 项目级记忆 | ProceduralMemory (15 规则, 5 级自动化) |
| 用户偏好记忆 | EpisodicMemory (76+ episodes, 持久化 JSON) |
| 历史决策记录 | rl_decision_history.json + Q-table (408/700 非零) |

### P0-3：记忆检索精准度 ✅

| 需求 | HyperMarrow 实现 |
|------|-----------------|
| 结构化 > 语义相似 | KG(实体-关系 BFS + 传递推理) + VecDB(语义搜索) 双通路 |
| 自动提取关键信息 | SkillExtractor (从 EM 中自动提取 context→action 模式) |
| 去重与压缩 | merge_similar_episodes() + LTD Ebbinghaus decay |

### P2-8：并行执行支持 ✅

OpenClaw 的 sessions_spawn 已支持子代理并行，HyperMarrow 通过 AgentRegistry 提供 per-agent 隔离记忆——每个子代理有独立的 WM/EM/QL。

---

## 五、实施路线

### 本期（本周）

| # | 任务 | 工作量 |
|:--:|------|:--:|
| 1 | **输入校验层** (`input_guard.py`) | 0.5 天 |
| 2 | **学习控制接口** (`hm.freeze/rollback/override`) | 1 天 |

### 下期（按需）

| # | 任务 | 触发条件 |
|:--:|------|----------|
| 3 | 多模态记忆 (图片/音频) | 当 OpenClaw 实际需要处理图片/音频输入时 |
| 4 | Web UI 管理界面 | 当需要可视化管理 Agent/规则/技能时 |

---

## 六、一句话总结

> 9 项公共需求中，4 项 HyperMarrow 已经解决了（上下文管理、持久化记忆、精准检索、并行隔离）。2 项该做（输入校验、学习控制），1.5 天搞定。3 项不应做——缓存优化是 API 层的事，代码回滚是 Git 的事，工作流标准化是 Agent 编排的事，都不是记忆系统的职责。
