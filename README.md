# OpenClaw 记忆与学习系统包

## 概述

本目录包含两个可独立安装的 Python 包：

| 包名 | 功能 | 依赖 |
|------|------|------|
| `openclaw-memory-system` | 记忆系统（语义搜索 + 程序性记忆） | chromadb, sentence-transformers, numpy |
| `openclaw-learning-system` | 学习系统（Q-Learning + 决策辅助） | numpy |

## 包结构

```
packages/
├── .pythonpath                    # PYTHONPATH 配置文件
│
├── openclaw-memory-system/        # 记忆系统包
│   ├── memory_core/               # 核心模块
│   │   ├── __init__.py
│   │   ├── vector_memory_db.py    # 向量数据库
│   │   ├── procedural_memory.py   # 程序性记忆
│   │   ├── q_learning_agent.py   # Q-Learning
│   │   └── rl_decision_helper.py  # RL 决策辅助
│   ├── memory_integration/        # 集成模块
│   │   ├── __init__.py
│   │   └── decision_check.py      # 决策检查点
│   ├── memory_cli/                # CLI 模块
│   │   └── vector_db.py
│   ├── tests/
│   ├── examples/
│   ├── data/                      # 数据目录
│   ├── setup.py
│   └── README.md
│
└── openclaw-learning-system/     # 学习系统包
    ├── learning_core/             # 核心模块
    │   ├── __init__.py
    │   ├── q_learning_agent.py
    │   └── rl_decision_helper.py
    ├── learning_integration/      # 集成模块
    │   ├── __init__.py
    │   └── decision_check.py
    ├── tests/
    ├── examples/
    ├── data/
    ├── setup.py
    └── README.md
```

## 安装方式

### 方式 1：使用 PYTHONPATH（推荐，无需 pip）

```powershell
# 1. 运行设置脚本
python D:\OpenClaw\workspace\use_packages.py

# 2. 在你的代码中导入
python -c "from memory_core.vector_memory_db import VectorMemoryDB"
```

或者手动设置：
```powershell
# 添加到系统环境变量 PYTHONPATH
# 或在代码中：
import sys
sys.path.insert(0, r"D:\OpenClaw\workspace\packages\openclaw-memory-system")
sys.path.insert(0, r"D:\OpenClaw\workspace\packages\openclaw-learning-system")
```

### 方式 2：pip install（沙盒环境可能受限）

```powershell
pip install -e D:\OpenClaw\workspace\packages\openclaw-memory-system
pip install -e D:\OpenClaw\workspace\packages\openclaw-learning-system
```

## 使用示例

### 记忆系统

```python
from memory_core.vector_memory_db import VectorMemoryDB
from memory_core.procedural_memory import ProceduralMemory

# 向量数据库
db = VectorMemoryDB(workspace="D:/OpenClaw/workspace")
results = db.search("查询内容")

# 程序性记忆
memory = ProceduralMemory(workspace="D:/OpenClaw/workspace")
rules = memory.check_rules("当前上下文")
```

### 学习系统

```python
from learning_core.q_learning_agent import QLearningAgent
from learning_core.rl_decision_helper import RLDecisionHelper

# Q-Learning Agent
agent = QLearningAgent(state_size=100, action_size=7)
action = agent.get_action(state)

# 决策辅助
rl = RLDecisionHelper(workspace="./data")
recommendation = rl.get_recommendation({
    "task_type": "video_generation",
    "phase": "P2b"
})
```

### 决策检查点

```python
from memory_integration.decision_check import DecisionCheckPoint

checkpoint = DecisionCheckPoint(workspace="D:/OpenClaw/workspace")
result = checkpoint.check(
    context="准备切换技能",
    task_type="视频生成",
    phase="P2b"
)

if result['warnings']:
    print("警告:", result['warnings'])
print("推荐动作:", result['rl_recommendation']['recommended_action'])
```

## 数据存储

数据存储在包目录的 `data/` 子目录下：

```
openclaw-memory-system/data/
├── procedural_memory.json        # 程序性记忆规则
├── q_table.json                  # Q-Learning Q表
├── rl_decision_history.json      # RL 决策历史
└── chromadb/                     # 向量数据库文件
```

## 与 scripts/ 的关系

| 目录 | 用途 |
|------|------|
| `scripts/` | 当前 OpenClaw 实际调用的模块 |
| `packages/` | 独立封装的版本，可复用到其他 Agent |

`scripts/__init__.py` 会自动加载 `packages/.pythonpath` 中的路径，实现单一源码管理。

## 常见问题

### Q: 导入时报 "No module named"

确保 PYTHONPATH 包含正确的父目录：

```python
import sys
sys.path.insert(0, "D:/OpenClaw/workspace/packages/openclaw-memory-system")
sys.path.insert(0, "D:/OpenClaw/workspace/packages/openclaw-learning-system")
```

### Q: 如何更新包

直接修改 `packages/` 目录下的文件即可。重新导入模块时更改会自动生效。

### Q: 如何完全卸载

删除 PYTHONPATH 中的路径，或运行：
```powershell
pip uninstall openclaw-memory-system openclaw-learning-system
```
