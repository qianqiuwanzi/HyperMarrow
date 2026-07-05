# HyperMarrow V2 设计方案

**基于**：GBrain 对比分析 + GBrain 接入方式分析
**日期**：2026-07-05
**状态**：待审核

---

## 一、设计动机

### 当前 V1 状态

HyperMarrow V1 花了 30+ 次提交构建了强大的认知后端（11 子系统、RL、KG、元认知、世界模型），但在**实际使用体验**上有三个致命短板：

| 短板 | 表现 | 根因 |
|------|------|------|
| **OpenClaw 不知道怎么用** | Bridge 接入点不明确，MCP 连接失败 | 外挂式设计，需要显式调用 |
| **人类无法直接交互** | 查看 KG 实体数需要写 Python 脚本 | 无 CLI 工具 |
| **维护依赖 Bridge 存活** | 睡眠调度器是 daemon 线程，Bridge 停止=巩固停止 | 无独立维护入口 |

### GBrain 的启示

GBrain 用更简单的架构（Markdown + CLI + 定时任务）实现了更好的实际体验。核心差距不是功能多寡，而是**设计哲学**：

> GBrain 是 Agent 的"潜意识"——每条消息自动经过，后台静默工作。
> HyperMarrow 是 Agent 的"工具箱"——需要时拿起来用，用完放下。

### V2 目标

**让 HyperMarrow 从"工具箱"变成"潜意识"。** 保留 V1 全部认知能力（RL、KG、元认知、世界模型），增加 3 个接入层使其无缝融入 Agent 工作流。

---

## 二、V2 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                    接入层 (V2 新增)                               │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ hypermarrow CLI  │  │ Interceptor      │  │ MCP Server   │  │
│  │ (独立命令行工具)  │  │ (消息拦截器)     │  │ (外部Agent)  │  │
│  │                  │  │                  │  │              │  │
│  │ stats/search     │  │ 每条OpenClaw消息 │  │ 标准MCP协议  │  │
│  │ dream/agents     │  │ 自动触发:        │  │ check/record │  │
│  │ export/list      │  │ 实体提取→KG      │  │ search/stats │  │
│  │                  │  │ 消息存档→EM      │  │ transfer     │  │
│  │ 独立进程         │  │ 意图检测→PM      │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Dream Cycle      │  │ Bridge (保留)    │                     │
│  │ (独立定时任务)    │  │ (向后兼容)       │                     │
│  │                  │  │                  │                     │
│  │ 9阶段报告        │  │ 睡眠调度器       │                     │
│  │ JSON输出         │  │ 双Agent          │                     │
│  │ 不依赖Bridge     │  │ RPC接口          │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    核心层 (V1 全部保留)                           │
│                                                                  │
│  P1 WorkingMemory  P2 VectorMemory  P3 EpisodicMemory            │
│  ProceduralMemory  KnowledgeGraph    QLearningAgent              │
│  Metacognition     TransferLearner   MemoryConsolidator          │
│  WorldModel        NeuralAgent       MetaLearner                 │
│  AgentRegistry     ProspectiveMemory PerceptionChannels          │
│                                                                  │
│  DecisionCheckPoint — 统一编排                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **接入层是增量，核心层不变** — V1 的 11 子系统零改动
2. **每条消息自动触发** — Interceptor 嵌入 OpenClaw 消息管线
3. **独立可运行** — CLI 和 Dream Cycle 不依赖任何服务
4. **分层接入** — Level 1 (MCP 5分钟) → Level 2 (Interceptor 30分钟) → Level 3 (CLI 按需)

---

## 三、新增组件设计

### 组件 1：`hypermarrow` CLI

**对标**：GBrain 的 `gbrain` 命令

**文件**：`openclaw-memory-system/memory_cli/hypermarrow.py`

**命令清单**：

```bash
# 查看
hypermarrow stats              # 全系统统计 (KG/PM/QL/EM/Meta)
hypermarrow agents             # 列出所有 Agent 及状态
hypermarrow health             # 健康报告 (ECE, 成功率, 连续失败)

# 搜索
hypermarrow search "关键词"     # 搜索情景记忆 + 向量记忆
hypermarrow search "关键词" --agent openclaw --days 7

# 维护
hypermarrow dream              # 手动触发巩固 (9 阶段报告)
hypermarrow dream --json       # JSON 格式输出 (供定时任务)

# 导出
hypermarrow export --format markdown  # 导出可读知识摘要
hypermarrow export --format json     # 导出完整数据快照

# 知识图谱
hypermarrow kg entities         # 列出所有实体
hypermarrow kg central          # 列出核心实体 (度中心性)
hypermarrow kg path A B         # A→B 最短路径
```

**实现**：argparse CLI，调用现有 DecisionCheckPoint API，无需新增后端逻辑。

### 组件 2：`hypermarow_interceptor`

**对标**：GBrain 的 `gbrain_dispatch` 协议

**文件**：`openclaw-memory-system/memory_integration/interceptor.py`

**API**：

```python
def hypermarow_intercept(user_message: str, agent_response: str = "",
                          agent_id: str = "openclaw", blocking: bool = False):
    """
    OpenClaw 每条消息后自动调用。
    
    并行执行 (不阻塞主响应):
      1. 实体提取 → KnowledgeGraph.add_entity
      2. 消息存档 → EpisodicMemory.add_episode
      3. 规则匹配 → ProceduralMemory.check_context
      4. 意图检测 → ProspectiveMemory.check_triggers
    
    Args:
        user_message: 用户消息原文
        agent_response: Agent 回复 (可选)
        agent_id: 当前 Agent ID
        blocking: True=同步执行, False=后台线程 (默认)
    
    Returns:
        {"entities_found": int, "rules_matched": int, "intentions_triggered": int}
    """
```

**关键设计决策**：
- **默认非阻塞**：在后台线程执行，不影响 OpenClaw 响应速度
- **容错**：任何子步骤失败不影响其他步骤
- **轻量**：只做实体提取+存档+匹配，不做 RL 更新 (RL 更新仍在 record() 中)

### 组件 3：独立 Dream Cycle

**对标**：GBrain 的 Dream Cycle (9 阶段定时任务)

**文件**：扩展现有 `memory_consolidator.py`，新增 CLI 入口

**9 阶段**：

| # | 阶段 | 对标 GBrain | 实现 |
|:--:|------|:----------|------|
| 1 | **lint** | lint (结构检查) | 检查 data/ 文件完整性 |
| 2 | **backlinks** | backlinks | KG.infer_relationships() |
| 3 | **sync** | sync | Agent 间状态同步 |
| 4 | **synthesize** | synthesize | merge_similar_episodes() |
| 5 | **extract** | extract | SkillExtractor.extract_skills() |
| 6 | **patterns** | patterns | MetaLearner.adjust() |
| 7 | **embed** | embed | NeuralAgent 编码 + VecDB 索引 |
| 8 | **orphans** | orphans | 检测孤立情景记忆 |
| 9 | **purge** | purge | ltd_decay (艾宾浩斯衰减) |

**JSON 输出格式**：

```json
{
  "status": "ok",
  "timestamp": "2026-07-05T02:00:00",
  "duration_sec": 2.34,
  "phases": {
    "lint": 0,
    "backlinks": 3,
    "sync": 0,
    "synthesize": 1,
    "extract": 2,
    "patterns": 0,
    "embed": 0,
    "orphans": 1,
    "purge": 3
  },
  "agents": ["openclaw", "luci"],
  "warnings": []
}
```

### 组件 4：来源标注强制执行

**对标**：GBrain 的 `[Source: User, YYYY-MM-DD]`

**改动**：`episodic_memory_db.py` 的 `add_episode()` + `decision_check.py` 的 `record()`

```python
# 自动注入 source 字段
episode["_source"] = {
    "agent": self.agent_id if hasattr(self, 'agent_id') else "unknown",
    "channel": "cli" if from_cli else "interceptor" if from_interceptor else "mcp" if from_mcp else "bridge",
    "captured_at": datetime.now().isoformat(),
}
```

### 组件 5：record() 非阻塞化

**对标**：GBrain 的并行执行

**改动**：`decision_check.py` 的 `record()`

```python
def record(self, ..., async_mode: bool = True):
    if async_mode:
        threading.Thread(target=self._record_sync, args=(...), daemon=True).start()
        return {"status": "queued"}
    else:
        return self._record_sync(...)
```

---

## 四、实现路线图

```
Phase 1 (P0, 3 天): CLI + 独立 Dream Cycle
  Day 1: hypermarrow CLI (stats/search/agents/health)
  Day 2: Dream Cycle 9 阶段重构 + JSON 输出
  Day 3: hypermarrow dream + hypermarrow export

Phase 2 (P1, 2 天): Interceptor + 来源标注
  Day 1: hypermarow_interceptor + OpenClaw 接入指南
  Day 2: record() 自动 source 注入 + record() 非阻塞化

Phase 3 (P2, 2 天): 孤立检测 + Markdown 导出
  Day 1: orphans 阶段 + KG 孤立实体检测
  Day 2: hypermarrow export --format markdown
```

**总计**：7 个工作日。核心层零改动。

---

## 五、OpenClaw 接入 (V2 方式)

V2 提供三种接入方式，从简单到深入：

### Level 1：MCP (5 分钟)

```json
// .mcp.json
{"mcpServers": {"hypermarow": {"command": "python", "args": ["..."]}}}
```
即可使用 check/record/search/stats/transfer 5 个工具。

### Level 2：Interceptor (15 分钟)

在 OpenClaw 消息处理管线中加一行：

```python
from hypermarow_memory_system.memory_integration.interceptor import hypermarow_intercept

# OpenClaw 每条消息处理后调用 (非阻塞)
threading.Thread(
    target=hypermarow_intercept,
    args=(user_message, agent_response),
    daemon=True
).start()
```

效果：每条对话自动提取实体、存档情景、匹配规则。

### Level 3：CLI + 定时任务 (30 分钟)

```powershell
# 添加到 Windows Task Scheduler (每天凌晨2点)
hypermarrow dream --json >> dream_log.json
```

效果：独立维护，不依赖 OpenClaw 运行状态。

---

## 六、GBrain 对标总结

| GBrain 能力 | HyperMarrow V1 | HyperMarrow V2 |
|------------|:--:|:--:|
| `gbrain` CLI | ❌ | ✅ `hypermarrow` CLI |
| `gbrain_dispatch` 自动触发 | ❌ | ✅ `hypermarow_interceptor` |
| Dream Cycle 9 阶段 | 部分 (sleep_cycle) | ✅ 完整 9 阶段 + JSON |
| `[Source: User]` 强制标注 | ❌ | ✅ 自动 inject |
| 并行不阻塞 | ❌ | ✅ record() async_mode |
| 定时任务独立运行 | ❌ | ✅ `hypermarrow dream` |
| Markdown 可读性 | ❌ | ✅ `hypermarrow export --md` |
| 孤立内容检测 | ❌ | ✅ orphans 阶段 |
| Q-Learning | ❌ | ✅ (GBrain 完全无) |
| 知识图谱推理 | ❌ | ✅ |
| 元认知自监控 | ❌ | ✅ |
| 多 Agent 协作 | ❌ | ✅ |
| MCP 开放协议 | ❌ | ✅ |

**V2 补齐了 GBrain 的全部体验优势，同时保留了 GBrain 不具备的全部认知能力。**

---

## 七、文件变更清单

### 新增文件

| 文件 | 内容 |
|------|------|
| `memory_cli/hypermarrow.py` | CLI 工具 (stats/search/dream/export/kg/agents) |
| `memory_integration/interceptor.py` | 消息拦截器 (实体提取+存档+匹配) |

### 修改文件

| 文件 | 改动 |
|------|------|
| `memory_consolidator.py` | 9 阶段重构 + JSON 输出 + orphans 阶段 |
| `episodic_memory_db.py` | add_episode() 自动注入 source |
| `decision_check.py` | record() 非阻塞模式 + source 传递 |
| `knowledge_graph.py` | get_orphan_entities() 新方法 |
| `__init__.py` | 导出新组件 |

### 不变文件

所有 V1 核心模块（15 个文件）零改动。

---

*方案结束 — 等待审核*
