# HyperMarrow 藏慧 — 类人记忆与学习系统

> HyperMarrow = Hyper + Memory Brain — 超记忆之脑

`openclaw-memory-system` — 可独立安装的 Python 包，实现类人认知能力：
三层记忆 × 知识图谱 × 强化学习 × 元认知 × 多 Agent 支持

---

## 概述

HyperMarrow 是一个持久化认知架构，让 AI 具备类似人类的记忆和学习能力。
每个 Agent 有**独立的情景记忆**和**强化学习策略**，同时共享**程序性规则**和**知识图谱**。

### 核心特性

| 特性 | 说明 |
|------|------|
| 三层记忆 | 工作记忆（P1）× 向量语义（P2）× 情景记忆（P3） |
| 强化学习 | 100 状态 × 7 动作 Q-Learning，经验回放，决策置信度 |
| 知识图谱 | 实体-关系 BFS 查询，跨记忆类型提取 |
| 元认知 | 置信度校准（ECE）、异常检测、自我反思 |
| 多 Agent | AgentRegistry 支持多 Agent 隔离记忆 + 跨 Agent 知识迁移 |
| 记忆巩固 | LTP 增强 + LTD 衰减 + 情景合并 + Q 回放 |
| 感知通道 | 屏幕 / 语音 / 对话流监控（依赖可选） |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                     多 Agent 层 (AgentRegistry)                  │
│     openclaw DC          │          luci DC                     │
│   [隔离: WM/EM/QL]      │        [隔离: WM/EM/QL]              │
└───────────┬──────────────┴──────────────┬────────────────────────┘
            │                            │
            │     ┌──────────────────────┘
            │     │ shared_layer（所有 Agent 共用）
            ▼     ▼
┌─────────────────────────────────────────────────────────────────┐
│  DecisionCheckPoint — 统一决策编排                               │
│  check(action, context) → record(action, context, outcome)       │
└────────────┬──────────────┬──────────────┬────────────────────────┘
             │              │              │
      ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────────────────────┐
      │ Procedural  │ │  Vector   │ │  Q-Learning Agent          │
      │ Memory      │ │  Memory   │ │  (per-agent Q-table)       │
      │ (共享规则)  │ │ (ChromaDB)│ │                            │
      └──────┬──────┘ └─────┬─────┘ └─────┬─────────────────────┘
             │              │              │
      ┌──────▼──────────────▼──────┐ ┌─────▼─────────────────────┐
      │    感知层 / 知识图谱 / 迁移学习 / 记忆巩固 / 元认知      │
      │    (所有 Agent 共用)                                       │
      └─────────────────────────────┘
```

### 记忆分层策略

| 记忆类型 | 隔离/共享 | 说明 |
|---------|---------|------|
| WorkingMemoryDB | **per-agent** | 当前任务上下文 |
| EpisodicMemoryDB | **per-agent** | 情景经历记录 |
| QLearningAgent | **per-agent** | 独立 Q 表，独立学习历史 |
| MetacognitionMonitor | **per-agent** | 置信度校准、异常检测 |
| ProceduralMemory | **共享** | 5 级规则库，所有 Agent 共用 |
| KnowledgeGraph | **共享** | 实体关系图谱，所有 Agent 贡献 |
| VectorMemoryDB | **共享** | 语义向量，所有 Agent 共享 |
| MemoryConsolidator | **共享** | LTP/LTD 巩固，per-agent EM |
| TransferLearner | **共享** | 跨 Agent 经验迁移 |
| PerceptionOrchestrator | **共享** | 感知协调器 |

---

## 包结构

```
HyperMarrow/
├── openclaw-memory-system/              # 记忆系统包（完整认知架构）
│   ├── memory_core/                     # 核心模块（18个）
│   │   ├── __init__.py                  # 统一导出
│   │   ├── config.py                    # 工作区 / HF镜像配置
│   │   ├── agent_registry.py            # 多Agent注册表
│   │   ├── working_memory_db.py         # P1: 工作记忆
│   │   ├── vector_memory_db.py          # P2: 向量语义记忆 (ChromaDB)
│   │   ├── episodic_memory_db.py        # P3: 情景记忆
│   │   ├── procedural_memory.py         # 程序性记忆 (5级规则)
│   │   ├── q_learning_agent.py          # Q-Learning (100×7, 确定性哈希)
│   │   ├── rl_decision_helper.py        # RL 决策辅助
│   │   ├── knowledge_graph.py           # 知识图谱 (实体-关系)
│   │   ├── perception_channels.py       # 感知通道 (屏幕/语音/对话)
│   │   ├── metacognition_monitor.py     # 元认知监控台
│   │   ├── transfer_learner.py           # 迁移学习
│   │   ├── memory_consolidator.py       # LTP/LTD 记忆巩固
│   │   ├── prospective_memory.py        # 前瞻记忆 (意图-条件触发)
│   │   ├── neural_state.py              # 神经状态编码 (64维嵌入)
│   │   ├── world_model.py               # 世界模型 (P(s'|s,a) + EFE规划)
│   │   ├── meta_learner.py             # 元学习器 (超参自动调节)
│   │   └── episodic_memory.py           # P3 外观类
│   ├── memory_integration/              # 集成模块
│   │   ├── __init__.py
│   │   └── decision_check.py             # DecisionCheckPoint + Agent工厂
│   ├── tests/
│   ├── data/                            # 运行时数据（per-agent 隔离）
│   │   ├── working_memory_openclaw.json
│   │   ├── episodes_openclaw.json
│   │   ├── q_table_openclaw.json
│   │   ├── working_memory_luci.json
│   │   ├── episodes_luci.json
│   │   ├── q_table_luci.json
│   │   └── chromadb/                    # 共享向量数据库
│   └── setup.py
│
└── openclaw-learning-system/            # 学习系统包（重导出）
    ├── learning_core/
    │   └── __init__.py                  # 从 memory_core 重新导出
    ├── learning_integration/
    │   ├── __init__.py
    │   └── decision_check.py
    └── setup.py
```

---

## 核心 API

### DecisionCheckPoint — 统一决策编排

集成全部子系统，提供 `check()` / `record()` API。
支持两种模式：**全局模式**（单用户）和 **Agent 模式**（多 Agent）。

```python
# ── Agent 模式（推荐）────────────────────────────────────────────
from memory_integration.decision_check import (
    create_for_agent, set_current_agent, get_current_dc
)

# 初始化时为每个 Agent 创建独立 DecisionCheckPoint
dc_openclaw = create_for_agent("openclaw")
dc_luci     = create_for_agent("luci")

# 切换当前 Agent 上下文
set_current_agent("luci")

# 决策检查 — 自动使用当前 Agent 的隔离记忆
result = dc_luci.check(
    action="switch_skill",
    context={"task": "P2b下载卡住", "phase": "P2b", "attempts": 3},
)
# result["rl_recommendation"]["recommended_action"]  → RL 推荐动作
# result["procedural_hints"]                         → 匹配规则
# result["related_entities"]                         → KG 关联实体
# result["similar_memories"]                         → 向量相似记忆
# result["warnings"]                                 → 冲突仲裁结果

# 记录结果 — 自动写入 luci 的隔离数据文件
dc_luci.record(
    action="switch_skill",
    context={"task": "P2b下载卡住"},
    outcome="success",
    reward=1.0,
    note="P2b下载重试3次后成功",
)
# 写入: working_memory_luci.json / episodes_luci.json
#       q_table_luci.json / rl_decision_history_luci.json

# ── 全局模式（向后兼容）────────────────────────────────────────
from memory_integration.decision_check import DecisionCheckPoint

cp = DecisionCheckPoint(enable_vector_db=True, enable_rl=True)
result = cp.check("try_fix_three_times", {"task": "download_stuck"})
cp.record("try_fix_three_times", {"task": "download_stuck"}, "success")
```

### AgentRegistry — 多 Agent 管理

每个 Agent 有独立的隔离记忆，共享层实现跨 Agent 知识迁移。

```python
from memory_core.agent_registry import AgentRegistry

reg = AgentRegistry()
bundle = reg.register(
    agent_id="openclaw",
    action_space=[
        "follow_rule_strictly", "use_existing_tool",
        "try_fix_three_times", "report_before_bypass",
        "switch_skill", "request_user_input", "defer_to_rl",
    ],
)

# AgentBundle 的组件:
bundle.working_memory   # 隔离的 WorkingMemoryDB
bundle.episodic_memory  # 隔离的 EpisodicMemoryDB
bundle.ql_agent         # 隔离的 QLearningAgent
bundle.metacognition    # 隔离的 MetacognitionMonitor
bundle.knowledge_graph  # 共享的 KnowledgeGraph（所有Agent共用）
bundle.procedural_memory # 共享的 ProceduralMemory

# 跨 Agent 知识迁移（每10个成功经验自动触发）
bundle.notify_and_share("luci", outcome="success")
```

### P1: WorkingMemoryDB — 工作记忆

```python
wm = bundle.working_memory
wm.set_task("视频生成任务", goal="完成P2b素材下载")
wm.update_context(phase="P2b", attempts=3)
wm.push_task("子任务: 解析链接", context={"url": "..."})
summary = wm.get_context_summary()
popped = wm.pop_task()
```

### P2: VectorMemoryDB — 向量语义记忆（共享）

```python
db = VectorMemoryDB()  # 共享，同一 ChromaDB 实例
db.add_memory("mem_001", "P2b下载卡住需要重试", metadata={"agent": "openclaw"})
results = db.search("下载超时", n_results=5, days_filter=7)
stats = db.get_temporal_stats()
```

### P3: EpisodicMemoryDB — 情景记忆（隔离）

```python
em = bundle.episodic_memory
em.add_episode(
    what="P2b下载卡住，重试3次成功",
    context={"phase": "P2b", "task": "素材下载"},
    outcome="success", emotion="positive",
    tags=["download", "retry"], importance=4,
    lesson="增加超时到30s",
)
lessons = em.get_lessons()
```

### KnowledgeGraph — 知识图谱（共享）

```python
kg = bundle.knowledge_graph
tool = kg.add_entity("daily-video-factory", "tool")
skill = kg.add_entity("cover-generator", "skill")
kg.add_relationship(tool["id"], skill["id"], "uses", weight=0.9)
related = kg.find_related(tool["id"], max_depth=2)
central = kg.get_central_entities(10)
```

### QLearningAgent — 强化学习（隔离）

```python
ql = bundle.ql_agent
ql.add_experience("error_context", "try_fix_three_times", reward=1.0,
                  next_state="fixed", done=False)
action = ql.get_action(ql.state_to_index("error_context"), training=False)
ql.batch_learn(batch_size=32)
stats = ql.get_stats()
```

### MetacognitionMonitor — 元认知（隔离）

```python
mc = bundle.metacognition
mc.record_decision_outcome(0.9, "success", "try_fix", "context_str")
cal = mc.get_calibration_curve()
anomaly = mc.check_anomaly({"confidence": 0.9, "outcome": "failure"})
reflection = mc.evaluate_self_reflection_needed()
```

### MemoryConsolidator — 记忆巩固（共享）

```python
con = bundle.consolidator  # MemoryConsolidator 共享，EM per-agent
result = con.consolidate()  # LTP → LTD → Q replay → Episode merge
```

### ProceduralMemory — 程序性记忆（共享）

```python
pm = bundle.procedural_memory  # 所有 Agent 共用同一规则库
pm.add_rule(
    rule_id="rule_p2b_download",
    rule_name="P2b下载卡住必须重试3次",
    level=4,  # Level 4 = 建议执行
    context_patterns=["P2b", "下载", "卡住", "timeout"],
    success_rate=0.95,
)
rules = pm.list_rules()
```

---

## 数据文件

```
openclaw-memory-system/data/
├── agent_registry.json              # Agent 注册表
├── working_memory_{agent}.json     # P1: per-agent 工作记忆
├── episodes_{agent}.json            # P3: per-agent 情景记忆
├── q_table_{agent}.json             # RL: per-agent Q表 (100×7)
├── rl_decision_history_{agent}.json # RL: per-agent 决策历史
├── procedural_memory.json           # PM: 共享程序性规则
├── knowledge_graph.json             # KG: 共享实体-关系图谱
├── calibration_history_{agent}.json # Meta: per-agent 置信度校准
├── anomaly_log_{agent}.json         # Meta: per-agent 异常记录
├── self_reflections_{agent}.json   # Meta: per-agent 自我反思
├── transfer_profiles.json          # TL: 迁移学习档案
├── consolidation_state.json        # Con: 巩固状态
├── consolidation_archive.json      # Con: 已删除记忆归档
├── conversation_history.json       # Perception: 对话历史
├── meta_cognition.json             # Meta: 元认知总览
└── chromadb/                       # P2: 共享向量数据库
```

---

## 安装方式

### pip install（推荐）

```powershell
pip install -e D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system
pip install -e D:\OpenClaw\workspace\HyperMarrow\openclaw-learning-system
```

### 导入验证

```python
from memory_core import (
    AgentRegistry, ProceduralMemory, WorkingMemoryDB,
    EpisodicMemoryDB, VectorMemoryDB, KnowledgeGraph,
    QLearningAgent, RLDecisionHelper, DecisionCheckPoint,
)
from memory_integration.decision_check import (
    create_for_agent, set_current_agent, get_current_dc,
)
```

---

## 可选依赖

| 功能 | 包 | 用途 |
|------|----|------|
| 屏幕OCR | `pyautogui pytesseract Pillow` | 截图 + 文字提取 |
| 窗口标题 | `pygetwindow` | 活动窗口检测 |
| 语音转录 | `SpeechRecognition pyaudio` | 麦克风录音 + STT |
| GPU加速 | `torch` | NeuralAgent / WorldModel / MetaLearner |

缺失时自动降级，不影响核心功能。

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-07-01 | 初始版本: VectorMemory + ProceduralMemory + Q-Learning |
| 2.0.0 | 2026-07-02 | 重构: +P1 WorkingMemory, +P3 EpisodicMemory, +KG, +Perception, +Metacognition, +TransferLearner, +MemoryConsolidator; 确定性哈希; AgentRegistry 多Agent支持 |
| v2.1.0 | 2026-07-02 | DecisionCheckPoint + AgentRegistry 集成: check()/record() agent_id路由, per-agent 隔离记忆, 共享层复用 |
| v2.2.0 | 2026-07-03 | Bridge RPC 修复: PM=0 fallback, learning_suggestion 格式兼容, KG corrupt 数据清理, context_prompt 字段添加 |

---

## 接入方式（3 种）

### 方式 A：OpenClaw Skill（推荐）

**适用场景**：OpenClaw Agent 直接调用 HyperMarrow。

**配置**：
1. 将 `skills/hypermarow/` 复制到 `D:\OpenClaw\workspace\skills\`
2. OpenClaw 会自动加载 Skill
3. 在 Agent 提示词中添加：
   ```
   在决策前，先调用 hypermarow check RPC，获取规则提示和 RL 建议。
   在执行后，调用 hypermarow record RPC，记录结果。
   ```

**示例**（Agent 主动调用）：
```powershell
# 决策前检查
python -c "
import sys; sys.path.insert(0, 'D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system');
from openclaw_memory_system.hypermarow_bridge import _init_hm, _handle_check;
_init_hm();
result = _handle_check({'context': {'task': 'video_gen', 'phase': 'P2b'}, 'query': '素材下载卡住'});
print(result['context_prompt']);
"
```

---

### 方式 B：JSON-RPC Bridge（子进程）

**适用场景**：跨语言调用（Node.js/TypeScript Plugin）。

**启动 Bridge**：
```bash
python hypermarow_bridge.py
# 等待 stderr 输出 "Ready. PM=15 rules, QL=407/700 Q, ..."
```

**JSON-RPC 请求**（每行一个请求）：
```json
{"jsonrpc": "2.0", "method": "check", "params": {"context": {"task": "test", "phase": "P0"}, "query": "测试"}, "id": 1}
```

**响应**：
```json
{"jsonrpc": "2.0", "result": {"success": true, "context_prompt": "...", "learning_suggestion": {"action": "explore", "confidence": 0.5}}, "id": 1}
```

---

### 方式 C：Python API（直接导入）

**适用场景**：Python 插件或脚本。

```python
import sys
sys.path.insert(0, r"D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system")

from openclaw_memory_system.hypermarow_bridge import _init_hm, _handle_check, _handle_record

# 初始化（一次）
_init_hm()

# 决策前检查
result = _handle_check({
    "context": {"task": "video_gen", "phase": "P2b"},
    "query": "素材下载卡住",
})
print(result["context_prompt"])
print(result["learning_suggestion"])

# 决策后记录
_handle_record({
    "context": {"task": "video_gen", "phase": "P2b"},
    "outcome": "success",
    "notes": "使用了现有脚本，未重新发明轮子",
})
```

---

## 数据灌入最佳实践

### 1. 初始数据（必须）

**程序性记忆**（15 条规则）：
- 文件：`data/procedural_memory.json`
- 最低要求：3 条核心规则（Level ≥ 2）
  - `rule_001`: 遵循用户指令（Level 5）
  - `rule_002`: 使用现有工具（Level 4）
  - `rule_003`: 不重新发明轮子（Level 3）

**Q-Table**（强化学习）：
- 文件：`data/q_table.json`
- 最低要求：33/700 非零（~5% 覆盖率）
- 推荐：407/700 非零（~58% 覆盖率，当前状态）

**知识图谱**：
- 文件：`data/knowledge_graph.json`
- 最低要求：0 个实体（可选）
- 推荐：12-15 个实体（工具、技能、错误类型）

---

### 2. 数据灌入脚本

**bootstrap_rl.py**（已存在）：
```bash
python memory_core/bootstrap_rl.py
# 生成 54 条初始经验，Q-Table 覆盖率从 3% → 15%
```

**bootstrap_knowledge_graph.py**（推荐创建）：
```python
from memory_core.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()

# 添加核心实体
tool = kg.add_entity("daily-video-factory", "tool", {"category": "video"})
skill = kg.add_entity("cover-generator", "skill", {"category": "design"})
error = kg.add_entity("download_stuck", "error_type")

# 添加关系
kg.add_relationship(tool["id"], error["id"], "triggers")
kg.add_relationship(skill["id"], tool["id"], "alternative")
```

---

### 3. 数据验证

**检查数据完整性**：
```python
from openclaw_memory_system.hypermarow_bridge import _init_hm, _get_stats

_init_hm()
stats = _get_stats()
print(f"PM rules: {stats['procedural_memory']['total_rules']}")
print(f"QL nonzero: {stats['q_learning']['nonzero']}/{stats['q_learning']['total']}")
print(f"KG entities: {stats['knowledge_graph']['entities']}")
```

**预期输出**（当前最佳状态）：
```
PM rules: 15
QL nonzero: 407/700
KG entities: 29
```

---

## 故障排除

### 问题 1：`_get_stats()` 返回 `PM=0`

**根因**：`DC.procedural_memory` 为 `None`（初始化顺序问题）。

**修复**：`_get_stats()` 已添加 fallback 逻辑（直接从文件加载 `ProceduralMemory`）。

**验证**：
```python
stats = _get_stats()
assert stats["procedural_memory"]["total_rules"] > 0
```

---

### 问题 2：`learning_suggestion` 格式错误

**根因**：`IndependentQLearningAgent.decide()` 返回 `(action_index, action_name)`，但 Bridge 期望 `(action, confidence)`。

**修复**：`hypermarow_bridge.py` 中添加格式兼容逻辑。

**正确格式**：
```json
{
  "action": "explore",
  "confidence": 0.5,
  "source": "independent_q_agent"
}
```

---

### 问题 3：KG `Target entity not found`

**根因**：`knowledge_graph.json` 里有 corrupt 数据（实体 ID 不是 8 位 hex）。

**修复**：运行清理脚本：
```python
from memory_core.knowledge_graph import KnowledgeGraph
kg = KnowledgeGraph()
# 自动清理（已内置在 __init__ 中）
```

**验证**：
```python
print(len(kg.data["entities"]))  # 应该 = 29（不是 41）
```

---

## 性能基准

**测试环境**：Windows 10, RTX A5500, Python 3.10

| 操作 | 延迟（p50 / p95） | 说明 |
|------|---------------------|------|
| `check()` | 8.60ms / 10.21ms | 包含规则匹配 + RL 建议 |
| `record()` | 49.57ms / 63.25ms | 包含 ChromaDB 写入 + KG 提取 |
| `search()` | 7.15ms / 9.62ms | 向量搜索（模型已加载）|
| **冷启动** | ~23s | Sentence Transformer 加载（首次）|

**优化建议**：
1. 使用惰性加载（`vector_memory_db.py` 已实施）
2. 异步写入（`record()` 中的 ChromaDB 写入可异步化）
3. 预热：在 Agent 启动时任选一个 `search()` 调用，触发模型加载
