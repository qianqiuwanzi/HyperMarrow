# HyperMarrow — OpenClaw 记忆与学习系统

**一个可插拔的记忆与学习系统**，为 OpenClaw Agent 提供：
- 语义记忆（Vector DB）
- 程序性记忆（规则分级）
- 强化学习（Q-Learning 决策优化）
- 知识图谱（实体关系）

---

## 🎯 核心特性

| 模块 | 功能 | 状态 |
|------|------|------|
| **VectorMemoryDB** | ChromaDB + Sentence Transformers 语义搜索 | ✅ 稳定 |
| **ProceduralMemory** | 规则分级（Level 1-5），自动晋升 | ✅ 稳定 |
| **QLearningAgent** | Q-Learning 决策优化，buffer 经验回放 | ✅ 稳定 |
| **KnowledgeGraph** | 实体关系图谱，自动提取 | ✅ 稳定（已清理 corrupt 数据）|
| **DecisionCheckPoint** | 集成所有模块的决策的查点 | ✅ 稳定 |
| **Bridge RPC** | JSON-RPC 2.0 接口（stdin/stdout） | ✅ 稳定（4/4 测试通过）|

---

## 🏗️ 架构

```
HyperMarrow/
├── openclaw-memory-system/           # 主包
│   ├── memory_core/                 # 核心记忆模块
│   │   ├── vector_memory_db.py      # 向量数据库（惰性加载）
│   │   ├── procedural_memory.py     # 程序性记忆
│   │   ├── knowledge_graph.py      # 知识图谱
│   │   ├── working_memory_db.py   # 工作记忆（上下文缓冲区）
│   │   ├── episodic_memory_db.py   # 情景记忆（结构化记录）
│   │   └── q_learning_agent.py   # Q-Learning 核心
│   ├── learning_core/              # 独立学习系统
│   │   └── independent_q_agent.py # 独立 Q-Learning（56×5）
│   ├── memory_integration/         # 集成层
│   │   └── decision_check.py      # 决策检查点（DC）
│   ├── openclaw_memory_system/     # OpenClaw 接入层
│   │   ├── hypermarow_bridge.py  # JSON-RPC Bridge（推荐）
│   │   └── hypermarow_http.py    # HTTP Server（备用）
│   └── data/                      # 数据文件（自动创建）
│       ├── procedural_memory.json   # 15 条规则（Level 1-2）
│       ├── q_table.json             # Q-Table (100×7, 407/700 非零)
│       ├── knowledge_graph.json     # 29 实体，25 关系（已清理 corrupt）
│       ├── episodes_*.json         # 情景记忆
│       └── working_memory_*.json   # 工作记忆
├── skills/hypermarow/              # OpenClaw Skill（Wrapper）
│   ├── check.ps1                  # check RPC
│   ├── record.ps1                 # record RPC
│   ├── search.ps1                 # search RPC
│   └── stats.ps1                 # stats RPC
└── data/                          # 全局数据目录（get_data_dir()）
```

---

## 🔌 接入方式（3 种）

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

**PowerShell Wrapper**（`skills/hypermarow/check.ps1`）：
```powershell
$request = '{"jsonrpc":"2.0","method":"check","params":{"context":{"task":"test"},"query":"test"},"id":1}'
$request | python hypermarow_bridge.py
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

## 📥 数据灌入最佳实践

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

**bootstrap_procedural_memory.py**（推荐创建）：
```python
from memory_core.procedural_memory import ProceduralMemory

pm = ProceduralMemory()

pm.add_rule(
    rule_name="遵循用户指令",
    content="用户说'使用 A 技能'，就必须用 A，即使用 B 更好",
    context_patterns=["技能", "用户指令", "权限边界"],
    level=5,
)
# ... 添加其他 14 条规则
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

## 🔧 配置

### HuggingFace 镜像（中国用户）

在 `memory_core/config.py` 中已配置：
```python
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HUGGINGFACE_HUB_CACHE"] = str(workspace / ".cache/huggingface/hub")
```

### 数据目录

默认：`D:\OpenClaw\workspace\data\`

自定义：
```python
from memory_core.config import set_data_dir
set_data_dir("D:/my_custom_data/")
```

### Token 预算（Bridge RPC）

在 `hypermarow_bridge.py` 的 `_build_context_prompt()` 中配置：
```python
TOKEN_BUDGET = {
    "header": 5,
    "rules": 120,      # 程序性规则（Level ≥ 2）
    "rl": 80,          # RL 建议
    "vecdb": 200,      # 向量记忆（top-3）
    "wm": 60,          # 工作记忆
    "kg": 80,          # 知识图谱
    "warnings": 55,    # 警告
}
```

---

## 🚨 故障排除

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

### 问题 4：`context_prompt` 为空

**根因**：`_handle_check()` 的 return 里没有 `context_prompt` 字段。

**修复**：已添加 `context_prompt` 字段（别名 `inject_text`）。

**验证**：
```python
result = _handle_check({"context": {"task": "test"}})
assert len(result["context_prompt"]) > 100
```

---

## 📊 性能基准

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

---

## 🧪 测试

### Bridge RPC 测试（4/4 通过）

```bash
python test_bridge_rpc_simple.py
# 输出写到：D:\OpenClaw\workspace\test_rpc_result.txt
```

**测试用例**：
1. `stats` — PM 统计（问题 1 修复验证）
2. `check` — learning_suggestion 格式（问题 2 修复验证）
3. `record` — KG 无报错（问题 3 修复验证）
4. `context_prompt` — 非空（问题 4 修复验证）

---

## 📝 更新日志

### v2.2.0 (2026-07-03) — Bridge RPC 修复
- ✅ 修复 `_get_stats()` 返回 `PM=0`（添加 fallback 逻辑）
- ✅ 修复 `learning_suggestion` 格式（兼容新旧格式）
- ✅ 修复 KG `Target entity not found`（清理 corrupt 数据）
- ✅ 修复 `context_prompt` 为空（添加字段）
- ✅ Bridge RPC 测试 4/4 通过

### v2.1.0 (2026-07-02) — DecisionCheckPoint 集成
- ✅ DecisionCheckPoint 集成 VectorDB + RL + WorkingMemory
- ✅ Bridge RPC 基础实现（ping/check/record/search/stats）
- ✅ 数据持久化验证（Q-Table, episodes, working memory）

### v2.0.0 (2026-07-01) — 包重构
- ✅ `memory_core` 完全独立（零依赖）
- ✅ `learning_core` 独立化
- ✅ pip install -e 成功

---

## 📚 参考文献

- [Reinforcement Learning in OpenClaw](https://example.com/rl-in-openclaw)（待写）
- [Procedural Memory Design](https://example.com/procedural-memory)（待写）
- [Knowledge Graph for Agent Memory](https://example.com/kg-agent-memory)（待写）

---

## 📄 许可证

MIT License

---

**维护者**：强哥 + 绿鲤鱼与驴（OpenClaw Agent）  
**最后更新**：2026-07-03 22:30 GMT+8
