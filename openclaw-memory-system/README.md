# OpenClaw Memory & Learning System

一个可插拔的记忆与学习系统，支持语义搜索、程序性记忆、强化学习和决策辅助。

## 特性

- **向量数据库**: 基于 ChromaDB + Sentence Transformers 的语义记忆搜索
- **程序性记忆**: 规则分级系统，支持规则晋升和成功率追踪
- **强化学习**: Q-Learning 决策优化，自动学习最优策略
- **决策检查点**: 集成所有系统的智能决策辅助

## 系统要求

- Python 3.10+
- 操作系统: Windows / Linux / macOS
- 依赖: 见 `requirements.txt`

## 快速安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行安装检查
python check_install.py

# 3. 初始化向量数据库
python vector_memory_db.py init

# 4. 测试系统
python test_all.py
```

## 使用方式

### 1. 语义搜索

```python
from vector_memory_db import VectorMemoryDB

db = VectorMemoryDB()
results = db.search("daily-video-factory 错误处理", n_results=3)

for result in results['documents'][0]:
    print(result[:100])
```

### 2. 程序性记忆

```python
from procedural_memory import ProceduralMemory

pm = ProceduralMemory()

# 添加规则
pm.add_rule(
    rule_name="使用技能前检查scripts目录",
    content="在使用任何技能前，必须先检查其 scripts/ 目录",
    context_patterns=["技能", "scripts", "工具"],
    level=1
)

# 检查上下文
rules = pm.check_context("准备使用 daily-video-factory 技能")
for rule in rules:
    print(f"[Level {rule['level']}] {rule['rule_name']}")
```

### 3. 强化学习

```python
from rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper()

# 记录决策
rl.record_decision(
    state="daily-video-factory_P2b",
    action="use_existing_tool",
    outcome="success",
    reward=1.0
)

# 获取推荐
recommendation = rl.get_recommendation({
    "task_type": "video_generation",
    "phase": "P2b"
})
print(recommendation)
```

### 4. 决策检查点

```python
from decision_check import DecisionCheckPoint

checkpoint = DecisionCheckPoint()

# 执行决策检查
result = checkpoint.check({
    "context": "P2b 素材下载卡住",
    "task": "使用 daily-video-factory",
    "phase": "P2b",
    "action": "切换技能"
})

print(f"适用规则: {len(result['procedural_rules'])}")
print(f"RL推荐: {result['rl_recommendation']}")
print(f"警告: {result['warnings']}")
```

## 目录结构

```
openclaw-memory-system/
├── core/                      # 核心模块
│   ├── vector_memory_db.py    # 向量数据库
│   ├── procedural_memory.py   # 程序性记忆
│   ├── q_learning_agent.py    # Q-Learning 核心
│   └── rl_decision_helper.py  # RL 决策辅助
├── integration/               # 集成模块
│   └── decision_check.py      # 决策检查点
├── cli/                       # 命令行工具
│   ├── vector-db.py           # 向量数据库 CLI
│   └── manage_rules.py        # 规则管理 CLI
├── tests/                     # 测试脚本
│   ├── test_vector_search.py
│   ├── test_procedural.py
│   └── test_all.py
├── data/                      # 数据文件
│   ├── procedural_rules.json
│   ├── q_table.json
│   └── chromadb/
├── requirements.txt
├── setup.py
└── README.md
```

## 配置

### HuggingFace 镜像（中国用户）

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = './cache/huggingface/hub'
os.environ['HF_HOME'] = './cache/huggingface'
```

### 自定义数据路径

```python
from decision_check import DecisionCheckPoint

# 指定自定义工作目录
checkpoint = DecisionCheckPoint(workspace="/path/to/your/workspace")
```

## API 参考

### VectorMemoryDB

| 方法 | 说明 |
|------|------|
| `add_memory(id, text, metadata)` | 添加单条记忆 |
| `batch_add(memories)` | 批量添加记忆 |
| `search(query, n_results)` | 语义搜索 |
| `get_similar(memory_id, n_results)` | 查找相似记忆 |
| `delete(memory_id)` | 删除记忆 |

### ProceduralMemory

| 方法 | 说明 |
|------|------|
| `add_rule(rule_name, content, patterns, level)` | 添加规则 |
| `check_context(context)` | 检查上下文匹配规则 |
| `get_recommendation(context)` | 获取推荐规则 |
| `record_usage(rule_id, success)` | 记录规则使用结果 |

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

## 许可证

MIT License
