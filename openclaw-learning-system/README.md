# OpenClaw Learning System

一个可插拔的强化学习决策系统，支持 Q-Learning、决策优化和经验积累。

## 特性

- **Q-Learning 核心**: 经典强化学习算法，支持自定义状态/动作空间
- **决策辅助**: 智能推荐最优决策，提供置信度和理由
- **经验积累**: 自动记录决策历史，持续优化策略
- **可视化分析**: 决策性能分析、Q 表可视化

## 系统要求

- Python 3.10+
- 依赖: numpy

## 快速安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 测试系统
python tests/test_all.py
```

## 使用方式

### 1. 基础 Q-Learning

```python
from core.q_learning_agent import QLearningAgent

# 创建 agent (100 状态, 7 动作)
agent = QLearningAgent(state_size=100, action_size=7)

# 获取状态
state = agent.get_state({"task": "video_generation", "phase": "P2b"})

# 选择动作
action = agent.get_action(state)

# 更新 Q 表
agent.update(state, action, reward=1.0, next_state=state)
```

### 2. 决策辅助系统

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper(workspace="./data")

# 记录决策
rl.record_decision(
    state="video_generation_P2b",
    action="use_existing_tool",
    outcome="success",
    reward=1.0
)

# 获取推荐
recommendation = rl.get_recommendation({
    "task_type": "video_generation",
    "phase": "P2b",
    "error_history": True
})

print(f"推荐动作: {recommendation['recommended_action']}")
print(f"置信度: {recommendation['confidence']:.2f}")
print(f"理由: {recommendation['reasoning']}")
```

### 3. 与程序性记忆集成

```python
from integration.decision_check import DecisionCheckPoint

checkpoint = DecisionCheckPoint(workspace="./data")

# 执行决策检查
result = checkpoint.check({
    "context": "P2b 下载卡住",
    "task": "使用 daily-video-factory",
    "phase": "P2b"
})

print(f"适用规则: {result['procedural_rules']}")
print(f"RL 推荐: {result['rl_recommendation']}")
print(f"警告: {result['warnings']}")
```

## 动作空间

| ID | 动作 | 说明 |
|----|------|------|
| 0 | follow_rule_strictly | 严格遵循规则 |
| 1 | try_fix_first | 先尝试修复 |
| 2 | ask_user | 询问用户 |
| 3 | use_existing_tool | 使用现有工具 |
| 4 | create_new_tool | 创建新工具 |
| 5 | switch_skill | 切换技能 |
| 6 | skip_phase | 跳过阶段 |

## 状态空间

状态由以下特征组合而成：

- `task_type`: 任务类型
- `current_phase`: 当前阶段
- `has_error_history`: 是否有错误历史
- `similar_cases_count`: 相似案例数量
- `time_pressure`: 时间压力
- `context_complexity`: 上下文复杂度

## API 参考

### QLearningAgent

| 方法 | 说明 |
|------|------|
| `get_state(context)` | 将上下文转换为状态索引 |
| `get_action(state)` | 选择最优动作 |
| `update(state, action, reward, next_state)` | 更新 Q 表 |
| `save_q_table()` | 保存 Q 表到文件 |
| `load_q_table()` | 从文件加载 Q 表 |

### RLDecisionHelper

| 方法 | 说明 |
|------|------|
| `record_decision(state, action, outcome, reward)` | 记录决策 |
| `get_recommendation(context)` | 获取推荐动作 |
| `analyze_performance()` | 分析决策性能 |
| `get_state_key(context)` | 生成状态键 |

### DecisionCheckPoint

| 方法 | 说明 |
|------|------|
| `check(context)` | 执行决策检查 |
| `record(context, action, outcome)` | 记录决策结果 |
| `status()` | 获取系统状态 |

## 配置

### 自定义学习参数

```python
from core.q_learning_agent import QLearningAgent

agent = QLearningAgent(
    state_size=200,    # 状态空间大小
    action_size=10,    # 动作空间大小
    alpha=0.2,         # 学习率
    gamma=0.95,        # 折扣因子
    epsilon=0.15       # 探索率
)
```

### 自定义动作空间

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper(workspace="./data")

# 添加自定义动作
rl.add_custom_action("retry_with_different_params", reward_penalty=0.1)
```

## 数据文件

```
data/
├── q_table.json              # Q 表数据
├── rl_decision_history.json  # 决策历史
└── rl_config.json            # RL 配置
```

## 许可证

MIT License
