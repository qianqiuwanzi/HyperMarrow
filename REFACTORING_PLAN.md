# HyperMarrow 解耦重构方案

## 当前依赖图

```
learning-system (包)
│
├── learning_core/
│   ├── q_learning_agent.py     ← 真实代码（算法本体）
│   ├── rl_decision_helper.py  ← from .q_learning_agent（真实使用）
│   └── config.py               ← from memory_core.config（重导出）
│
├── learning_integration/
│   └── decision_check.py       ← from memory_integration.DC as base（wrapper）
│                                ← from learning_core.QLearningAgent（真实使用）
│
└── examples/ tests/            ← from learning_core.*（消费者）

memory-system (包)
│
├── memory_core/
│   ├── q_learning_agent.py    ← from learning_core.QLearningAgent（FACADE，寄生）
│   ├── rl_decision_helper.py   ← from learning_core.*（FACADE，寄生）
│   ├── vector_memory_db.py
│   ├── working_memory_db.py
│   ├── episodic_memory_db.py
│   └── procedural_memory.py
│
└── memory_integration/
    └── decision_check.py        ← from learning_core.QLearningAgent（真实使用）← 唯一交叉点
```

**耦合环**：
```
memory_integration/dc.py
  → learning_core.q_learning_agent   ← 从 learning-system 取算法
    → (learning-system 用 memory_core.config)   ← 配置依赖 memory-system
```

---

## 重构方案：单向依赖（memory-system 为主，learning-system 为下游）

### 核心原则
> **memory-system 是完整决策系统的宿主，包含所有运行时代码。learning-system 只保留实验性/研究性内容，零运行依赖。**

### 目标架构

```
memory-system (自包含完整系统)
├── memory_core/
│   ├── config.py
│   ├── vector_memory_db.py      ← 向量记忆 + 时间索引
│   ├── working_memory_db.py    ← P1 上下文缓冲
│   ├── episodic_memory_db.py   ← P3 情景记忆
│   ├── procedural_memory.py    ← 程序性记忆
│   ├── q_learning_agent.py     ← ★ 从 learning-system 迁入（算法本体）
│   └── rl_decision_helper.py   ← ★ 从 learning-system 迁入（封装）
│
├── memory_integration/
│   └── decision_check.py        ← from .q_learning_agent（内部导入）
│
└── data/                        ← q_table.json / rl_decision_history.json

learning-system (研究包，无运行时代码)
├── learning_core/
│   └── __init__.py              ← from memory_core.q_learning_agent import QLearningAgent
│                                ← from memory_core.rl_decision_helper import RLDecisionHelper
│
├── learning_integration/         ← 精简：只保留高级封装
│   └── decision_check.py         ← from memory_integration.DC as base（wrapper，thin）
│
├── rl_algorithms/               ← ★ 新增：研究用算法
│   ├── dqn_agent.py             ← DQN（实验代码，不在核心路径）
│   ├── policy_gradient.py
│   └── __init__.py
│
├── benchmarks/                   ← ★ 新增：benchmark 工具
│   └── compare_agents.py
│
└── examples/
```

### 关键变化

| # | 操作 | 影响 |
|---|------|------|
| 1 | `learning-system/learning_core/q_learning_agent.py` → `memory-system/memory_core/q_learning_agent.py` | 迁移算法本体 |
| 2 | `learning-system/learning_core/rl_decision_helper.py` → `memory-system/memory_core/rl_decision_helper.py` | 迁移封装 |
| 3 | 删除 `memory-system/memory_core/q_learning_agent.py`（FACADE） | 消除寄生文件 |
| 4 | 删除 `memory-system/memory_core/rl_decision_helper.py`（FACADE） | 消除寄生文件 |
| 5 | `memory-system/memory_integration/decision_check.py`：改 `from learning_core` → `from memory_core` | 解耦交叉导入 |
| 6 | `learning-system/learning_core/config.py`：改为 `from memory_core.config`（已有） | 保持不变 |
| 7 | `learning-system/learning_core/__init__.py`：改为 `from memory_core.*` | 重导出，改为下游 |
| 8 | `learning-system/learning_integration/decision_check.py`：保留 thin wrapper | 精简 |
| 9 | 新建 `learning-system/rl_algorithms/` | 研究代码（实验） |
| 10 | 更新 `setup.py` 文件中的 import 路径 | 包安装正确 |

### 数据文件归属

```
data/ (memory-system 独有)
├── q_table.json              ← Q-Learning 表（决策用）
├── rl_decision_history.json  ← 决策历史
├── working_memory.json       ← 工作记忆
├── episodes.json             ← 情景记忆
└── procedural_memory.json   ← 程序性规则
```

---

## 测试影响分析

| 文件 | 当前 import | 迁移后 import | 需改动 |
|------|------------|--------------|--------|
| `learning-system/examples/basic_q_learning.py` | `from learning_core.ql...` | `from memory_core.ql...` 或保留在 learning-core 重导出 | 改 1 行 |
| `learning-system/examples/decision_helper.py` | `from learning_core.rl...` | 同上 | 改 1 行 |
| `learning-system/tests/test_all.py` | `from learning_core.*` | `from memory_core.*` | 改 2 行 |
| `memory-system/tests/test_all.py` | `from memory_core.rl...` | `from memory_core.ql...` | 改 1 行 |
| `memory_integration/dc.py` | `from learning_core.ql...` | `from memory_core.ql...` | 改 1 行 |
| `learning_integration/dc.py` | `from memory_integration.DC as base` | 不变 | 无 |

---

## 实施记录（2026-07-02 实施）

| Step | 状态 | 说明 |
|------|------|------|
| 1 | ✅ | 复制 learning-core → memory-core（q_learning_agent.py, rl_decision_helper.py） |
| 2 | ✅ | memory_integration/dc.py：`from learning_core` → `from memory_core` |
| 3 | ✅ | 验证 memory-system 独立导入（QLearningAgent 12935B，RLDecisionHelper 4358B） |
| 4 | ✅ | memory-system tests sys.path 修正 |
| 5 | ✅ | learning-system __init__.py → 重导出 memory_core；examples sys.path 更新 |
| 6 | ✅ | 删除 learning_core/q_learning_agent.py 和 rl_decision_helper.py（仅保留 __init__.py） |
| 7 | ⏭️ | research 目录未创建（当前非必需） |
| 8 | ✅ | 完整验证：13/13 测试通过 ✓ |

### 额外修复（计划外）
- learning_integration/dc.py：`from learning_core.ql...` → `from memory_core.ql...`
- learning-system/tests/test_all.py：sys.path 修正 + 4处 import 更新
- learning-system/__init__.py：新增 ACTIONS/ACTION_MAP 导出

### 已知状态
- `learning-system/learning_core/` 仅保留 `__init__.py` + `config.py`（重导出）
- memory-system/memory_core/ 包含所有运行时代码（QLearningAgent, RLDecisionHelper 等）
- learning-system/learning_integration/dc.py 是 thin wrapper（依赖 memory_integration）
- memory-system/memory_integration/dc.py 无任何 learning-system 导入（已解耦）

---
## 实施顺序（计划原文）

```
Step 1: 复制文件（不删除源）
  cp learning-system/learning_core/q_learning_agent.py → memory-system/memory_core/
  cp learning-system/learning_core/rl_decision_helper.py → memory-system/memory_core/

Step 2: 更新 memory_integration/dc.py import（解除交叉依赖）
  from learning_core.ql... → from memory_core.ql...

Step 3: 验证导入（不运行 ChromaDB）
  python -c "from memory_core.q_learning_agent import QLearningAgent; print('OK')"

Step 4: 更新 memory-system tests
  memory-system/tests/test_all.py: from memory_core.rl... → from memory_core.ql...

Step 5: 更新 learning-system
  learning-system/learning_core/__init__.py: 改为 from memory_core.*
  learning-system/learning_core/config.py: 保持 from memory_core.config（已有）
  learning-system/examples/: 更新 import 路径

Step 6: 删除 FACADE 文件
  rm memory-system/memory_core/q_learning_agent.py
  rm memory-system/memory_core/rl_decision_helper.py

Step 7: 新建 research 目录
  learning-system/rl_algorithms/
  learning-system/benchmarks/

Step 8: 完整验证
  python -c "
    from memory_core import QLearningAgent, RLDecisionHelper, DecisionCheckPoint
    from memory_integration.decision_check import DecisionCheckPoint
    print('memory-system OK')
    from learning_core import QLearningAgent, RLDecisionHelper
    print('learning-system OK')
  "
```

---

## 风险评估

| 风险 | 级别 | 缓解 |
|------|------|------|
| FACADE 删除后旧 import 路径断裂 | ⚠️ 中 | Step 6 放在最后，有充分时间迁移 |
| q_table.json 路径依赖 | ✅ 低 | 已在 memory-system/data/，迁移后路径不变 |
| learning-system 空壳化 | ℹ️ 信息 | 预期行为，新建 rl_algorithms/ 承接 |
| pip install -e 需要重跑 | ✅ 低 | `pip install -e` 重装两个包 |
