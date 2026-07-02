# 快速启动指南

## 1. 安装

```bash
# 解压包
unzip openclaw-memory-system-1.0.0.zip
cd openclaw-memory-system-1.0.0

# 安装依赖
pip install -r requirements.txt

# 检查安装
python check_install.py
```

## 2. 初始化向量数据库

```bash
# 首次运行需要下载模型（约400MB）
python -c "
from core.vector_memory_db import VectorMemoryDB
db = VectorMemoryDB('./data/chromadb')
print('Vector DB initialized')
"
```

## 3. 测试系统

```bash
python tests/test_all.py
```

## 4. 集成到你的项目

### 方式 1: 直接导入

```python
import sys
sys.path.insert(0, '/path/to/openclaw-memory-system')

from core.vector_memory_db import VectorMemoryDB
from core.procedural_memory import ProceduralMemory
from integration.decision_check import DecisionCheckPoint

# 初始化
db = VectorMemoryDB("/your/data/path/chromadb")
pm = ProceduralMemory("/your/data/path")
checkpoint = DecisionCheckPoint("/your/data/path")
```

### 方式 2: pip 安装

```bash
# 从本地安装
pip install /path/to/openclaw-memory-system-1.0.0

# 然后直接导入
from openclaw_memory import VectorMemoryDB, ProceduralMemory, DecisionCheckPoint
```

## 5. 添加自定义记忆

```python
from core.vector_memory_db import VectorMemoryDB

db = VectorMemoryDB()

# 添加单条记忆
db.add_memory(
    id="my_rule_001",
    text="遇到网络问题时，先检查代理设置",
    metadata={"category": "debug", "priority": "high"}
)

# 批量添加
memories = [
    {"id": "rule_001", "text": "...", "metadata": {}},
    {"id": "rule_002", "text": "...", "metadata": {}},
]
db.batch_add(memories)
```

## 6. 添加程序性规则

```python
from core.procedural_memory import ProceduralMemory

pm = ProceduralMemory()

pm.add_rule(
    rule_name="检查依赖版本",
    content="遇到模块导入错误时，先检查 requirements.txt 中的版本约束",
    context_patterns=["导入错误", "ImportError", "依赖"],
    level=2  # 1-5, 越高越重要
)
```

## 7. 记录决策经验

```python
from core.rl_decision_helper import RLDecisionHelper

rl = RLDecisionHelper()

# 记录成功经验
rl.record_decision(
    state="video_generation_P2b",
    action="use_existing_tool",
    outcome="success",
    reward=1.0
)

# 记录失败经验
rl.record_decision(
    state="video_generation_P2b",
    action="switch_skill",
    outcome="failure",
    reward=-1.0
)
```

## 8. 使用决策检查点

```python
from integration.decision_check import DecisionCheckPoint

checkpoint = DecisionCheckPoint()

# 在关键决策前调用
result = checkpoint.check({
    "context": "准备切换技能",
    "task": "视频生成",
    "phase": "P2b",
    "action": "switch_skill"
})

# 检查结果
if result['warnings']:
    print("⚠️ 警告:")
    for w in result['warnings']:
        print(f"  - {w}")

if result['rl_recommendation']:
    rec = result['rl_recommendation']
    print(f"RL 建议: {rec['recommended_action']} (置信度: {rec['confidence']:.2f})")
```

## 常见问题

### Q: 模型下载失败？

设置 HuggingFace 镜像：

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_ENDPOINT'] = 'https://hf-mirror.com'
```

### Q: 沙盒安全策略阻止写入？

将缓存目录改到允许的位置：

```python
os.environ['HUGGINGFACE_HUB_CACHE'] = './cache/huggingface/hub'
os.environ['HF_HOME'] = './cache/huggingface'
```

### Q: 如何迁移现有数据？

直接复制 `data/` 目录到新位置，然后初始化时指定新路径：

```python
checkpoint = DecisionCheckPoint(workspace="/new/data/path")
```
