# 快速启动指南

## 1. 安装

```bash
# 解压包
unzip openclaw-learning-system-1.0.0.zip
cd openclaw-learning-system-1.0.0

# 安装依赖
pip install -r requirements.txt

# 测试安装
python tests/test_all.py
```

## 2. 基础使用

### Q-Learning Agent

```python
from core.q_learning_agent import QLearningAgent

# 创建 agent
agent = QLearningAgent(state_size=100, action_size=7)

# 选择动作
state = 0  # 状态索引
action = agent.get_action(state)

# 更新 Q 表
agent.update(state, action, reward=1.0, next_state=1)
```

### RL Decision Helper

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper(workspace="./data")

# 获取推荐
recommendation = rl.get_recommendation({
    "task_type": "video_generation",
    "phase": "P2b"
})

print(f"推荐: {recommendation['recommended_action']}")
print(f"置信度: {recommendation['confidence']:.2f}")

# 记录决策
rl.record_decision(
    state="video_generation_P2b",
    action="use_existing_tool",
    outcome="success",
    reward=1.0
)
```

### Decision Checkpoint

```python
from integration.decision_check import DecisionCheckPoint

checkpoint = DecisionCheckPoint(workspace="./data")

# 执行决策检查
result = checkpoint.check({
    "context": "准备切换技能",
    "task": "视频生成",
    "phase": "P2b"
})

# 查看结果
if result['warnings']:
    print("⚠️ 警告:")
    for w in result['warnings']:
        print(f"  - {w}")

if result['rl_recommendation']:
    rec = result['rl_recommendation']
    print(f"RL 建议: {rec['recommended_action']}")
```

## 3. 运行示例

```bash
# Q-Learning 基础示例
python examples/basic_q_learning.py

# Decision Helper 示例
python examples/decision_helper.py
```

## 4. 集成到你的项目

### 方式 1: 直接导入

```python
import sys
sys.path.insert(0, '/path/to/openclaw-learning-system')

from core.q_learning_agent import QLearningAgent
from core.rl_decision_helper import RLDecisionHelper
from integration.decision_check import DecisionCheckPoint

# 初始化
agent = QLearningAgent(state_size=100, action_size=7)
rl = RLDecisionHelper(workspace="/your/data/path")
checkpoint = DecisionCheckPoint(workspace="/your/data/path")
```

### 方式 2: pip 安装

```bash
# 从本地安装
pip install /path/to/openclaw-learning-system-1.0.0

# 然后直接导入
from openclaw_learning import QLearningAgent, RLDecisionHelper, DecisionCheckPoint
```

## 5. 自定义动作空间

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper(workspace="./data")

# 定义新的动作空间
custom_actions = {
    0: "retry_with_cache",
    1: "use_mirror_endpoint",
    2: "ask_user_for_input",
    3: "fallback_to_default"
}

rl.set_action_space(custom_actions)
```

## 6. 性能监控

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper(workspace="./data")

# 分析性能
analysis = rl.analyze_performance()

print(f"总决策数: {analysis['total_decisions']}")
print(f"成功率: {analysis['success_rate']:.1%}")

# 查看每个动作的统计
for action, stats in analysis['action_stats'].items():
    print(f"{action}: {stats['success_rate']:.1%} success")
```

## 7. 持久化

Q 表和决策历史会自动保存到 `data/` 目录：

- `q_table.json` - Q 表数据
- `rl_decision_history.json` - 决策历史

加载时自动恢复。

## 常见问题

### Q: 如何调整学习率？

```python
agent = QLearningAgent(
    state_size=100,
    action_size=7,
    alpha=0.2,   # 学习率 (默认 0.1)
    gamma=0.95,  # 折扣因子 (默认 0.9)
    epsilon=0.15 # 探索率 (默认 0.1)
)
```

### Q: 如何查看 Q 表？

```python
import numpy as np

# 查看 Q 表统计
print(f"Q-table shape: {agent.q_table.shape}")
print(f"Q-values range: [{agent.q_table.min():.3f}, {agent.q_table.max():.3f}]")

# 查看某个状态的 Q 值
state = 0
print(f"Q-values for state {state}: {agent.q_table[state]}")

# 最优动作
best_action = np.argmax(agent.q_table[state])
print(f"Best action: {best_action}")
```

### Q: 如何重置学习？

```python
# 重置 Q 表
agent.q_table = np.zeros((agent.state_size, agent.action_size))

# 清空历史
rl.history = []
```
