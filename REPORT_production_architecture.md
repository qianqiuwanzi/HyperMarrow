# HyperMarrow 生产环境完整架构设计报告

> 2026-07-08 | 独立于 Claude/OpenClaw 的完整生产部署方案

---

## 一、总体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                        智商藏不住                               │
│                                                                      │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐   │
│  │   Web UI (SPA)      │    │   API Server (FastAPI, :8741)     │   │
│  │   React + Recharts  │◄───│   记忆7模块 + 学习7模块            │   │
│  │   静态文件, 单页面   │    │   WebSocket 实时推送              │   │
│  └──────────────────────┘    └───────────┬──────────────────────┘   │
│                                          │                           │
│  ┌───────────────────────────────────────┴──────────────────────┐   │
│  │                    数据层 (isolated + shared)                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │   │
│  │  │  Per-Agent  │ │  Per-Agent  │ │  Shared (cross-agent)    │ │   │
│  │  │  WM, EM, QL │ │  WM, EM, QL │ │  KG, VecDB, PM           │ │   │
│  │  │  Meta       │ │  Meta       │ │  Consolidator, Transfer   │ │   │
│  │  │  (openclaw) │ │  (claude)   │ │  Perception, MetaLearner  │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
          ▲                              ▲
          │ HTTP /connect /heartbeat     │ HTTP /connect /heartbeat
          │ (每30s)                      │ (每30s)
     ┌────┴─────┐                  ┌────┴─────┐
     │ OpenClaw │                  │  Claude  │
     │ (QClaw)  │                  │ (Claude  │
     │          │                  │  Code)   │
     └──────────┘                  └──────────┘
```

---

## 二、Agent 如何与 HyperMarrow 建立关联

### 2.1 注册（一次性）

HyperMarrow 内置了 4 个已知 Agent 的 action space 定义：

```python
# agent_registry.py
KNOWN_AGENTS = ["openclaw", "claude", "codex", "hermes"]

AGENT_ACTIONS = {
    "openclaw": ["follow_rule_strictly", "use_existing_tool", "try_fix_three_times",
                 "report_user", "write_script", "switch_skill", "skip_phase"],
    "claude":   [...],  # 同上，相同 action space
    "codex":    ["run_terminal", "write_file", "search_code", "ask_user", "delegate_to_claude"],
    "hermes":   ["think", "act", "observe", "plan", "reflect", "learn", "teach", "coordinate"],
}
```

**新 Agent 上线的注册流程：**

1. Agent 第一次被引用时，`server.py` 调用 `create_for_agent("agent_id")`
2. `AgentRegistry.register()` 创建 `AgentBundle` — 分配隔离存储文件
3. 持久化到 `agent_registry.json`
4. 自动注入共享层（KG、VecDB、PM 等）

**安装包场景：** HyperMarrow 编译安装后，Agent 注册信息通过 `agent_registry.json` 持久化。外部 Agent（如 OpenClaw、Claude）首次连接到 HyperMarrow API 时自动完成注册。

### 2.2 连接（运行时）

每个 Agent 通过 HTTP API 宣告存在：

```
POST /api/v1/agents/{agent_id}/connect     → 设置 _api_session_active = True
POST /api/v1/agents/{agent_id}/heartbeat   → 更新 _last_heartbeat 时间戳
POST /api/v1/agents/{agent_id}/disconnect  → 设置 _api_session_active = False
```

**双层心跳保障：**

| 层 | 机制 | 适用场景 |
|---|------|---------|
| **进程检测层** | `server.py` 定期检测宿主进程（如 QClaw.exe） | Electron/IDE 类 Agent |
| **Wire 文件层** | Agent 进程内嵌 `openclaw_wire.py`（类同 claude_wire.py） | Python 运行时 Agent |

```
# 进程检测（server.py startup）
def _is_agent_host_running(agent_id):
    if agent_id == "openclaw":
        return _is_process_running("QClaw.exe")   # Windows: tasklist
    if agent_id == "claude":
        return _is_process_running("claude")       # Linux: pgrep
    # 通用：检查 Agent 配置文件标记的进程名

# Wire 文件（Agent 进程内）
def _start_heartbeat():
    while True:
        POST /api/v1/agents/{agent_id}/heartbeat
        sleep(30)
```

**60 秒超时检测：** 两层心跳任一层活跃即可保持连接。两层都停止后，`agents_list()` API 检测到 `_last_heartbeat` 超过 60 秒未更新，自动标记为离线。

### 2.3 数据隔离

每个 Agent 的数据按 `{type}_{agent_id}.json` 命名空间隔离：

```
data/
├── agent_registry.json          # 全局：Agent 注册表
├── knowledge_graph.json         # 共享：知识图谱
├── procedural_memory.json       # 共享：程序性记忆规则
├── consolidation_state.json     # 共享：巩固状态
├── extracted_skills.json        # 共享：涌现技能
│
├── episodes_openclaw.json       # openclaw 隔离：情景记忆
├── working_memory_openclaw.json # openclaw 隔离：工作记忆
├── q_table_openclaw.json        # openclaw 隔离：Q 表
├── q_table_openclaw.pt          # openclaw 隔离：神经网络权重
│
├── episodes_claude.json         # claude 隔离：情景记忆
├── q_table_claude.json          # claude 隔离：Q 表
├── q_table_claude.pt            # claude 隔离：神经网络权重
│
└── chromadb/                    # 共享：向量数据库
```

**隔离的：** WorkingMemory、EpisodicMemory、QLearningAgent、Metacognition
**共享的：** KnowledgeGraph、VectorMemoryDB、ProceduralMemory、MemoryConsolidator、TransferLearner、Perception

---

## 三、数据如何灌入

### 3.1 三条灌入路径

```
Agent 进程
    │
    ├── hm.intercept(user_msg, agent_response)
    │       │
    │       ├── 实体提取 → KnowledgeGraph.add_entity()
    │       ├── 消息存档 → EpisodicMemory.add_episode()
    │       └── 规则匹配 → ProceduralMemory.check_context()
    │
    ├── hm.check(action, context)
    │       │
    │       ├── Perception.observe_all() → 环境感知
    │       ├── ProceduralMemory → 规则命中 + 冲突仲裁
    │       ├── QLearningAgent → RL 推荐 (Q-table lookup)
    │       ├── VectorMemoryDB → 相似记忆检索
    │       ├── KnowledgeGraph → 关联实体发现
    │       └── Metacognition → 自我反思评估
    │
    └── hm.record(action, context, outcome, reward)
            │
            ├── QLearningAgent.add_experience() → Q 表在线更新
            ├── EpisodicMemory.add_episode() → 情景存档
            ├── ProceduralMemory.record_outcome() → 规则成功率更新
            ├── VectorMemoryDB.add_memory() → 语义向量存储
            ├── KnowledgeGraph → 自动实体关联
            ├── Metacognition.record_decision_outcome() → 校准
            └── 每10条: batch_learn() + 持久化 Q 表
                每20条: consolidate() + skill_extractor
                每50条: meta_learner.adjust()
```

### 3.2 生产环境集成方式

Agent 开发者只需在自己的进程中嵌入 wire 文件：

```python
# openclaw_wire.py / claude_wire.py（HyperMarrow SDK 提供）
from hypermarrow_sdk import HyperMarrowWire

hm = HyperMarrowWire(agent_id="my-agent", api_url="http://localhost:8741")

# 每条对话后
hm.intercept(user_msg, agent_response)

# 决策前
result = hm.check(action="try_fix", context={"task": "download"})

# 决策后
hm.record(action="try_fix", outcome="success", reward=0.8)
```

**安装包提供：**
- `hypermarrow_sdk` Python 包（pip install）
- Wire 文件模板（复制即用）
- REST API 直接调用（非 Python Agent）

---

## 四、记忆和学习能力如何提升

### 4.1 记忆巩固 — Dream Cycle（9 阶段）

```
Dream Cycle (每 20 条 record 或手动触发)
├── Phase 1: lint          清理孤立/损坏的记录
├── Phase 2: backlinks     补充 KG 反向关系
├── Phase 3: sync          同步跨 Agent 知识
├── Phase 4: synth         合成涌现规则
├── Phase 5: extract       提取技能 (SkillExtractor)
├── Phase 6: patterns      发现行为模式
├── Phase 7: embed         更新向量嵌入
├── Phase 8: orphans       回收无引用实体
├── Phase 9: purge         过期记忆清理
├── batch_learn            Q-Learning 批量回放 (32 samples)
├── calibrate              元认知校准 (ECE 调整)
└── extract_rules          程序性记忆规则提炼
```

### 4.2 Q-Learning — 混合神经网络模式

```
Tabular Q-Table (100 states × 7 actions)
    +
Neural Network (PyTorch, 2-layer MLP)
    +
World Model (Active Inference, 前向预测)
    ↓
Hybrid: Q(s,a) = α·Q_tabular + (1-α)·Q_neural
```

**学习循环：**
1. `record()` → 即时 Q 更新（TD-learning）
2. 每 10 条 → `batch_learn(32)` 批量回放
3. 每 50 条 → `meta_learner.adjust()` 自动调参（learning_rate, epsilon, consolidation_frequency）
4. Dream Cycle → 全局巩固

### 4.3 跨 Agent 知识迁移

```
Agent A 积累 10 次成功经验
    ↓
AgentRegistry.notify_and_share("AgentA")
    ↓
    ├── 情景记忆迁移：Agent A 的高价值 episodes → Agent B（标记 transferred）
    ├── Q 表种子：通过状态特征相似度映射，Q 值以 50% 强度注入 Agent B
    └── 校准参考：Agent A 的 metacognition 校准曲线 → Agent B 初始参考
    ↓
Agent B 获得冷启动知识，避免从零开始
```

**交叉动作映射：** 即使 Agent 的动作空间不同，也能迁移。例如 Claude 的 `"write_script"` 映射为 Codex 的 `"write_file"`。

### 4.4 元学习 — 系统自我调节

```
MetaLearner 监控指标:
├── TD error 上升        → 提高 learning_rate
├── World Model loss 下降 → 提高 planning_horizon
├── ECE (校准误差) 偏高  → 提高 exploration_weight
├── 连续失败增多          → 提高 consolidation_frequency
└── 状态空间增长快        → 自动扩展 state 容量上限
```

### 4.5 技能涌现 — SkillExtractor

从情景记忆中自动发现复用模式：

```
episodes 中同 action 成功 ≥ 3 次
    ↓
提取为 "Skill" (技能模板)
    ↓
注入 ProceduralMemory 作为新规则
    ↓
其他 Agent 通过 TransferLearner 自动获得
```

目前已有 80+ 提取的技能。

---

## 五、生产部署方案

### 5.1 安装包结构

```
HyperMarrow/
├── hypermarrow-server/       # API 服务器
│   ├── memory_api/server.py
│   ├── memory_core/          # 7 记忆子系统
│   └── data/                 # 运行时数据目录
├── hypermarrow-ui/           # Web 仪表盘
│   └── dist/                 # 编译后静态文件
├── hypermarrow-sdk/          # Agent SDK (pip install)
│   └── hypermarrow_wire.py   # Agent 集成入口
├── start.py                  # 统一启动脚本
├── stop.py                   # 统一停止脚本
└── config.yaml               # 部署配置
```

### 5.2 config.yaml（设计）

```yaml
server:
  host: "0.0.0.0"
  port: 8741
  
agents:
  # 每个 Agent 的进程检测配置
  openclaw:
    host_process: "QClaw.exe"       # Windows 进程名
    heartbeat_from_server: true     # 服务器代为心跳
  claude:
    host_process: "claude"
    heartbeat_from_server: true
  codex:
    host_process: null              # 无宿主进程检测
    heartbeat_from_server: false    # 纯外部心跳

data:
  dir: "./data"                     # 数据目录
  retention_days: 90                # 数据保留天数
  
learning:
  consolidation_interval: 20        # 每 N 条 record 触发巩固
  transfer_threshold: 10           # 跨 Agent 共享阈值
  dream_cycle_interval_hours: 6    # 睡眠周期间隔
```

### 5.3 启动流程

```bash
# 安装后
hypermarrow start                  # 启动服务
hypermarrow start --port 9000      # 自定义端口
hypermarrow stop                   # 停止服务
hypermarrow status                 # 查看状态

# 或传统方式
python start.py                    # 构建 UI + 启动 API
python stop.py                     # 优雅停止
```

### 5.4 新 Agent 接入步骤

```
1. Agent 开发者安装 SDK:
   pip install hypermarrow-sdk

2. 在 Agent 入口文件加入:
   from hypermarrow_sdk import wire
   hm = wire.connect(agent_id="my-agent", server="http://localhost:8741")

3. 在对话循环中调用:
   hm.intercept(user_msg, response)   # 每条消息
   hm.check(action, context)          # 决策前
   hm.record(action, outcome)         # 决策后

4. HyperMarrow 自动:
   - 注册 Agent → agent_registry.json
   - 创建隔离数据文件
   - 启动心跳监测
   - 注入共享知识层
```

---

## 六、当前状态与待完善

### 已实现 ✅

| 功能 | 状态 |
|------|------|
| 多 Agent 注册与隔离 | ✅ AgentRegistry + 命名空间文件 |
| 连接/心跳/断连 API | ✅ HTTP API + 60s 超时检测 |
| 双层心跳（进程检测 + wire） | ✅ server.py + openclaw_wire.py |
| 7 模块记忆系统 | ✅ WM, VecDB, EM, PM, KG, Perception, Prospective |
| 7 模块学习系统 | ✅ QL, Meta, Consolidation, Transfer, WM, Dream, Skills |
| Dream Cycle 记忆巩固 | ✅ 9 阶段自动执行 |
| 跨 Agent 知识迁移 | ✅ TransferLearner + AgentRegistry |
| 元学习自动调参 | ✅ MetaLearner |
| 技能涌现 | ✅ SkillExtractor (80+ skills) |
| Web 仪表盘 | ✅ React SPA，6 个可视化面板 |
| 生产模式单端口服务 | ✅ FastAPI 挂载静态 UI |
| 统一启停脚本 | ✅ start.py / stop.py |

### 待完善 🔧

1. **SDK 独立打包** — 当前 `openclaw_wire.py` 紧耦合在项目内，需提取为独立 `pip install` 包
2. **Agent 发现机制** — 当前依赖硬编码的进程名检测，应支持 Agent 主动注册时声明宿主进程
3. **config.yaml** — 当前配置硬编码，需引入配置文件驱动
4. **认证/安全** — 当前无认证，生产环境需要 API Key 或 Token
5. **数据备份与恢复** — 记忆数据的持久化和灾难恢复
