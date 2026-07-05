# HyperMarrow vs GBrain — 对比分析与可学习的设计

**日期**：2026-07-05

---

## 一、高层对比

| 维度 | HyperMarrow | GBrain | 谁更好 |
|------|-------------|--------|:--:|
| **定位** | 通用认知架构 (记忆+学习+推理) | 个人知识库系统 | — |
| **哲学** | 模拟人类认知 (P1/P2/P3, LTP/LTD, 元认知) | 实用主义 (Markdown + CLI + Dream Cycle) | 各有千秋 |
| **复杂度** | 40+ 文件, 11 子系统, 神经网络, 主动推理 | CLI + Markdown + 9 阶段维护 | **GBrain 更简单** |
| **存储格式** | JSON (14 个运行时文件) | Markdown 文件 | **GBrain 更可读** |
| **人类可交互** | 无 CLI, 只能通过 API/Bridge | `gbrain` CLI 直接可操作 | **GBrain 更友好** |
| **AI 集成** | Bridge + MCP (双协议) | `gbrain_dispatch` (内嵌协议) | HyperMarrow 更开放 |
| **背景任务** | 睡眠调度器 (daemon 线程) | Dream Cycle (定时任务) | 功能相似 |
| **知识检索** | 向量语义 + KG BFS + 类比推理 (3 通路) | Brain-First Lookup (本地优先) | HyperMarrow 更强 |
| **信号捕获** | PerceptionChannels (可选依赖, 未充分接入) | signal-detector (每条消息触发) | **GBrain 更实用** |
| **来源追踪** | `source` 字段存在但未强制执行 | `[Source: User, YYYY-MM-DD]` 强制标注 | **GBrain 更规范** |
| **测试覆盖** | 12 项冒烟测试 | 无独立测试 (依赖 Dream Cycle 自检) | HyperMarrow 更好 |

---

## 二、GBrain 的 9 个设计优势（HyperMarrow 应该学习）

### 1. CLI 工具 — 人类可直接操作

**GBrain**：
```bash
gbrain search "张三"
gbrain get "people/张三"
gbrain put "ideas/新想法" --content "# 标题\n..."
gbrain list
gbrain dream --json
```

**HyperMarrow**：无 CLI。要查看 KG 实体数只能写 Python 脚本。

**学习**：创建 `hypermarrow` CLI 工具。最简版本：
```bash
hypermarrow stats              # 全系统统计
hypermarrow search "关键词"     # 搜索记忆
hypermarrow dream --json       # 手动触发巩固
hypermarrow agents             # 列出 Agent
```

### 2. Signal Detector — 每条消息自动捕获

**GBrain**：`signal-detector` 在每条用户消息上并行执行，捕获实体、原创想法、时间线事件，**不阻塞主响应**。

**HyperMarrow**：PerceptionChannels 有 ConversationTracker，但：
- 未在 check/record 主循环中自动调用
- 依赖可选外部库（speech_recognition 等）
- 没有"实体检测→自动写入 KG"的流水线

**学习**：在 `check()` 中增加轻量 signal-detector：
```python
# 每条决策自动执行（不阻塞）
threading.Thread(target=self._detect_signals, args=(full_context,)).start()
```
检测：新实体→自动 add_entity, 新想法→自动 add_episode

### 3. Dream Cycle 阶段化报告

**GBrain**：9 个阶段，每阶段有独立的状态码和操作计数：
```json
{"phases": {"lint": 0, "backlinks": 0, "sync": 0, "synthesize": 2, ...}}
```

**HyperMarrow**：sleep_cycle 只返回一个总结果 `{ltp_count, ltd_pruned, ...}`，内部阶段不可见。

**学习**：将 HyperMarrow 的 sleep_cycle 拆分为可独立报告的子阶段，对标 GBrain 的 9 阶段：

| GBrain 阶段 | HyperMarrow 对应 | 当前状态 |
|-------------|-----------------|:--:|
| lint | (无) — 检查数据文件完整性 | ❌ 缺失 |
| backlinks | KG.infer_relationships() | ✅ 已有 |
| sync | (无) — 同步 Agent 间状态 | ❌ 缺失 |
| synthesize | merge_similar_episodes() | ✅ 已有 |
| extract | SkillExtractor.extract_skills() | ✅ 已有 |
| patterns | SkillExtractor (部分) | ⚠️ 部分 |
| embed | NeuralAgent 编码 + VecDB 索引 | ✅ 已有 |
| orphans | (无) — 检测孤立情景记忆 | ❌ 缺失 |
| purge | ltd_decay() | ✅ 已有 |

### 4. Brain-First Lookup — 显式的"本地优先"协议

**GBrain** 的每个查询遵循固定协议：
```
用户提到 X → gbrain search X → 有结果? → 优先用本地 → 再查外部API
```

**HyperMarrow** 的 `check()` 内部做了 PM→RL→KG→VecDB 的查询链，但这个协议是隐式的，没有明确的"本地优先"声明。

**学习**：在 Bridge/MCP 的 `check` 工具返回中增加 `lookup_path` 字段，标明知识来源：
```python
result["lookup_path"] = ["PM: 3 rules matched", "KG: 2 entities related", "RL: agent recommendation"]
```

### 5. 来源标注强制执行

**GBrain**：每个事实必须标注 `[Source: User, 2026-07-05]`。`conventions/quality.md` 中的 Iron Law。

**HyperMarrow**：Episode 有 `source` 字段，但未被强制执行或自动填充。很多 record() 调用不传 source。

**学习**：在 `record()` 中自动填充 source：
```python
episode["source"] = {
    "agent": self.agent_id,
    "channel": "bridge" if from_bridge else "mcp" if from_mcp else "internal",
    "timestamp": datetime.now().isoformat(),
}
```

### 6. 反向链接是强制的

**GBrain**：每个页面必须维护 back-link。Dream Cycle 的 `backlinks` 阶段自动修复缺失链接。

**HyperMarrow**：KG 有 relationships，但没有"每创建一个实体必须建立至少一条关系"的强制规则。`orphans` 阶段完全缺失。

**学习**：在 KG 中添加 `get_orphan_entities()` 方法，在 sleep_cycle 中增加 orphans 阶段。

### 7. Markdown 文件 — 人类可读、Git 友好

**GBrain**：所有知识以 Markdown 文件存储，人类可以直接阅读和编辑。

**HyperMarrow**：全部 JSON。KG 实体关系不可读，Q 表不可读。

**学习**：增加 `hypermarrow export --format markdown` 命令，生成可读的知识摘要：
```markdown
# Knowledge Graph (33 entities, 28 relationships)
## Top Entities
- daily-video-factory (tool): used by cover-generator, executes in P2b
...
```

### 8. 孤立内容检测

**GBrain**：`orphans` 阶段检测并修复无引用的孤立页面。

**HyperMarrow**：LTD decay 按时间和重要性衰减，但不检测"孤立"——即一条情景记忆是否被任何规则、KG 实体或 Q 值引用。一条重要的记忆可能因为孤立而在下次 LTD 中意外删除。

**学习**：LTD 删除前增加孤立检查：被 KG 实体引用或 Q 表高频状态的记忆，即使年龄大也不删除。

### 9. 简单性

**GBrain** 的核心逻辑是：Markdown 文件 + CLI + 定时任务。约 300 行文档可以描述全部设计。

**HyperMarrow** 有 40+ 文件、11 子系统、神经网络、世界模型。学习曲线陡峭，维护负担重。

**学习**：不是要削减功能，而是要提供**分层接入**：
- Level 1 (5分钟): MCP 接入, 5 个工具直接用
- Level 2 (30分钟): Bridge 接入, 完整记忆+学习
- Level 3 (按需): 神经模式、主动推理、世界模型

---

## 三、HyperMarrow 优于 GBrain 的 5 个方面（保持）

| 方面 | HyperMarrow 优势 |
|------|-----------------|
| **强化学习** | Q-Learning + 经验回放 + 神经模式 + 世界模型。GBrain 无学习能力 |
| **知识图谱** | 实体-关系 BFS + 传递推理。GBrain 只有 Markdown 反向链接 |
| **元认知** | ECE 校准 + 异常检测 + 自我反思。GBrain 无自我感知 |
| **多 Agent** | AgentRegistry + 跨 Agent 迁移。GBrain 单用户 |
| **开放协议** | MCP 标准协议，任何 AI 客户端可接入。GBrain 仅 OpenClaw |

---

## 四、优先级行动清单

| 优先级 | 学 GBrain 的什么 | 实现方式 | 估计工作量 |
|:--:|------|----------|:--:|
| **P0** | CLI 工具 | `hypermarow` 命令: stats/search/dream/agents/export | 2 天 |
| **P0** | 来源标注强制执行 | record() 自动填充 source, check() 返回 lookup_path | 0.5 天 |
| **P1** | Dream Cycle 阶段化报告 | sleep_cycle 拆分 9 阶段 + JSON 输出 | 1 天 |
| **P1** | 孤立内容检测 | orphans 阶段: KG.get_orphan_entities() | 0.5 天 |
| **P2** | Markdown 导出 | `hypermarow export --format markdown` | 1 天 |
| **P2** | Signal Detector | check() 中异步实体/想法捕获 | 1 天 |
