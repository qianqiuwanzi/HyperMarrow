# HyperMarrow 接入 OpenClaw 本机执行指南

> 生成日期：2026-07-04
> 目标：让本机 OpenClaw 安全接入 HyperMarrow 记忆与学习系统
> 前置阅读：`code_architecture_review_2026-07-04.md`（了解上次犯的错）

---

## 一、pip 安装 vs sys.path：该用哪个？

### 结论：本机 OpenClaw 用 sys.path，不用 pip

| 方式 | 适用场景 | OpenClaw 本机 |
|------|----------|:--:|
| `pip install` | 发布到 PyPI，供外部用户安装 | ❌ 过度，且需每次重装 |
| `pip install -e` | 开发中，修改即时生效 | ✅ 可以，但需要 setup.py 正确 |
| `sys.path.insert` | 单项目本地开发 | ✅ **最推荐** |

### OpenClaw 启动时应该这样：

```python
import sys
from pathlib import Path

_HYM_ROOT = Path(r"D:\OpenClaw\workspace\HyperMarrow")
sys.path.insert(0, str(_HYM_ROOT / "openclaw-memory-system"))
sys.path.insert(0, str(_HYM_ROOT / "openclaw-learning-system"))

# 然后正常导入
from memory_core.config import setup_hf_mirror
setup_hf_mirror()
from memory_integration.decision_check import create_for_agent
dc = create_for_agent("openclaw")
```

### setup.py 怎么处理？

**保留不动**。`setup.py` 中的依赖声明（`openclaw-memory-system` 依赖 `openclaw-learning-system`）对未来发布到 PyPI 是正确的。本地开发不需要它。

---

## 二、Bridge 和 MCP：两种接入方式，互补不是替代

| | Bridge (`hypermarow_bridge.py`) | MCP (`hypermarow_mcp.py`) |
|---|---|---|
| **协议** | 自定义 JSON-RPC | 标准 MCP 协议 (modelcontextprotocol.io) |
| **通信** | stdin/stdout | stdin/stdout |
| **客户端** | **仅 OpenClaw** | **任何 MCP 客户端** (Claude Code, Cursor, Continue, ...) |
| **方法数** | 6 (ping/check/record/search/stats/init) | 8 工具 + 4 资源 + 2 提示 |
| **后台任务** | ✅ 睡眠调度器、双Agent注册、自动知识共享 | ❌ 无后台任务 |
| **启动方式** | OpenClaw 内部 `import` 后调 `_init_hm()` | 独立进程 `python hypermarow_mcp.py` |
| **适用场景** | OpenClaw 专属深度集成 | 外部 Agent 标准接入 |

### 两者如何协作：

```
OpenClaw 进程                      外部 Agent
     │                                  │
     ├─ Bridge (内置)                    ├─ MCP Client
     │   ├─ _init_hm()                  │   └─ stdio → MCP Server
     │   ├─ 双Agent注册                  │       └─ handle_message()
     │   ├─ 睡眠调度器(daemon线程)        │
     │   └─ check() / record()           │
     │                                  │
     └────────── 共享后端 ───────────────┘
              DecisionCheckPoint
              AgentRegistry
              KG / PM / QL / EM / Meta / ...
```

**Bridge 是 OpenClaw 的"内置引擎"，MCP 是"对外开放窗口"。两者可同时运行，共享同一套数据和后端。**

---

## 三、接入 OpenClaw 的执行建议

### 第零步：安全准备（最重要）

```powershell
# 1. 确认当前状态
cd D:\OpenClaw\workspace\HyperMarrow
git status                     # 应该干净，无意外修改
git log --oneline -5           # 确认最后一次提交是 b7a46f9

# 2. 备份数据目录（14个JSON文件是几个月的学习和记忆积累）
cp -r openclaw-memory-system/data/ data_backup_20260704/

# 3. 运行基线测试
python tests/test_smoke.py     # 必须 12/12 PASS
```

### 第一步：Bridge 冷启动验证

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"D:\OpenClaw\workspace\HyperMarrow") / "openclaw-memory-system"))
sys.path.insert(0, str(Path(r"D:\OpenClaw\workspace\HyperMarrow") / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

from memory_integration.decision_check import create_for_agent, get_agent_registry

# 创建两个 Agent
dc_openclaw = create_for_agent("openclaw")
dc_luci = create_for_agent("luci")
reg = get_agent_registry()

# 验证
assert len(reg.list_agents()) >= 2, "Agent 注册失败"
assert dc_openclaw.knowledge_graph is not None, "KG 未连接"
assert dc_openclaw.ql_agent is not None, "QL 未连接"
assert dc_openclaw.procedural_memory is not None, "PM 未连接"

print(f"Agents: {reg.list_agents()}")
print(f"KG: {dc_openclaw.knowledge_graph.get_stats()['total_entities']} entities")
print(f"QL: {dc_openclaw.ql_agent.get_stats()['nonzero_entries']}/700 Q-values")
print(f"PM: {len(dc_openclaw.procedural_memory.data['rules'])} rules")
print("Bridge 冷启动: OK")
```

### 第二步：check/record 往返测试

```python
actions = ['follow_rule_strictly', 'try_fix_three_times', 'write_script', 
           'switch_skill', 'report_user']
contexts = [
    {'task': 'download_stuck', 'phase': 'P2b', 'error': 'timeout'},
    {'task': 'import_error', 'phase': 'P1', 'error': 'import_error'},
    {'task': 'format_unsupported', 'phase': 'P3', 'error': 'format'},
]

for i in range(10):
    action = actions[i % len(actions)]
    ctx = contexts[i % len(contexts)]
    
    r = dc_openclaw.check(action=action, context=ctx)
    rec = r.get('rl_recommendation', {}).get('recommended_action', '?')
    
    dc_openclaw.record(
        action=action, context=ctx,
        outcome='success' if i % 3 != 0 else 'failure',
        reward=0.8 if i % 3 != 0 else -0.5,
    )
    print(f"  [{i+1}] check({action}) → RL recommends {rec}")

print("check/record 往返: OK")
```

### 第三步：真实任务验证（在 OpenClaw 正常执行任务时）

观察要点：
- Bridge 日志是否有 `[HyperMarrow Bridge] Ready` 
- check() 返回的 `rl_recommendation` 不为 None
- record() 后 Q 表非零条目应逐步增加
- 睡眠调度器日志每 4 小时出现一次 `[Sleep] === Nightly cognitive cycle starting ===`

### 第四步：睡眠周期手动触发

```python
reg = get_agent_registry()
for agent_id in reg.list_agents():
    bundle = reg.get(agent_id)
    if bundle and bundle.consolidator:
        result = bundle.consolidator.sleep_cycle(force=True)
        print(f"{agent_id}: LTP={result.get('ltp_count',0)}, LTD={result.get('ltd_pruned',0)}")
```

### 第五步：验证后检查

```powershell
python tests/test_smoke.py          # 再跑一次，必须 12/12
git diff --stat                      # 审查所有变更
```

---

## 四、红线：绝对禁止的操作（上次犯过的错）

| # | 禁止操作 | 原因 | 正确做法 |
|:--:|----------|------|----------|
| 1 | **手动 `new QLearningAgent()`** | 绕过 AgentRegistry，没有共享层，没有持久化路径 | 必须通过 `create_for_agent("agent_id")` |
| 2 | **在 `memory_core/` 创建新学习模块** | 违反架构分层 | 学习模块只放 `learning_core/`，memory_core 只留 shim |
| 3 | **裸 `except: pass`** | 吞没所有错误，调试无法定位 | 至少 `except Exception as e: print(f"[Module] {e}")` |
| 4 | **删除 `tests/test_smoke.py`** | 唯一测试文件，删除后无法回归验证 | 验证前后都要跑一次 |
| 5 | **创建 `independent_*` 分叉** | 产生重复实现，Bridge 格式不兼容 | 有需求就扩展主 `QLearningAgent`，不建分叉 |
| 6 | **修改架构后不同步文档** | 文档与实现矛盾，后来者无法理解 | 同步更新 `README.md`，删除过时 md 文件 |
| 7 | **`data/` 目录不加备份就操作** | Q表、KG、规则是几个月的积累，删除即永久丢失 | 任何操作前先 `cp -r data/ data_backup_$(date)/` |
| 8 | **学习模块的导入路径用相对导入** | `from .neural_state` 在 learning_core 中会失败（neural_state 在 memory_core） | 用 `from memory_core.neural_state import` |

---

## 五、架构速查（避免放错文件）

```
learning_core/          ← 学习系统真身
  q_learning_agent.py    ← QLearningAgent 唯一实现 (582行)
  rl_decision_helper.py  ← RLDecisionHelper 唯一实现 (155行)
  meta_learner.py        ← MetaLearner + SkillExtractor (416行)
  transfer_learner.py    ← TransferLearner 唯一实现 (365行)
  config.py              ← 自包含配置（无 memory_core 依赖）

memory_core/            ← 记忆系统真身 + 学习系统 shim
  q_learning_agent.py    ← 6行 shim (from learning_core import ...)
  rl_decision_helper.py  ← 4行 shim
  meta_learner.py        ← 4行 shim
  transfer_learner.py    ← 4行 shim
  knowledge_graph.py     ← 真身 (755行)
  working_memory_db.py   ← 真身 (267行)
  episodic_memory_db.py  ← 真身 (388行)
  procedural_memory.py   ← 真身 (553行)
  neural_state.py        ← 真身 (394行) — 被 learning_core 导入
  world_model.py         ← 真身 (414行) — 被 learning_core 导入
  agent_registry.py      ← 真身 (485行)
  ... (其余均为真身)
```

**记忆铁律：如果新增一个 .py 文件，先判断它是"记忆"还是"学习"。记忆放 memory_core，学习放 learning_core。跨包导入用绝对路径 `from memory_core.xxx` 或 `from learning_core.xxx`。**

---

## 六、MCP Server 配置（供外部 Agent 接入）

### Claude Code 接入

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "hypermarow": {
      "command": "python",
      "args": [
        "D:/OpenClaw/workspace/HyperMarrow/openclaw-memory-system/openclaw_memory_system/hypermarow_mcp.py"
      ]
    }
  }
}
```

### 可用工具清单

| 工具 | 功能 | 必填参数 |
|------|------|----------|
| `check` | 评估动作（RL+PM+KG+VecDB） | action |
| `record` | 记录决策结果 | action, outcome |
| `search` | 搜索情景+向量记忆 | query |
| `stats` | 全系统统计 | 无 |
| `analogy` | 类比推理 | task |
| `transfer` | 跨Agent知识迁移 | source, target |
| `consolidate` | 触发记忆巩固循环 | 无 |
| `skills` | 列出提取的技能和规则 | 无 |

---

## 七、故障排查

| 症状 | 可能原因 | 解决 |
|------|----------|------|
| `ModuleNotFoundError: No module named 'memory_core'` | sys.path 未设置 | 确认 openclaw-memory-system 在 sys.path |
| `ModuleNotFoundError: No module named 'learning_core.neural_state'` | 相对导入错误 | 检查是否用了 `from .neural_state` 而非 `from memory_core.neural_state` |
| `AgentRegistry: shared=✗` | 共享层未注入 | 通过 `create_for_agent()` 创建，不要手动注册 |
| `mat1 and mat2 shapes cannot be multiplied` | 神经编码维度不匹配 | 状态必须先 `_serialize_state()` 为 34 维向量再传神经网络 |
| `[HyperMarrow Bridge] Init FAILED` | config 或数据文件损坏 | 检查 `data/` 目录，从备份恢复 |
| Q 表全零 | q_table.json 丢失或损坏 | 从备份恢复 `data/q_table.json` |
