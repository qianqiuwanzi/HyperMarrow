# OpenClaw 本机验证清单

## 验证前检查

- [ ] `git status` 干净（无意外修改）
- [ ] `data/` 目录已备份
- [ ] `python tests/test_smoke.py` → 12/12
- [ ] `python -c "from hypermarow_mcp import handle_message; print('MCP OK')"` → 无报错

## Phase 1: Bridge 冷启动

```powershell
python -c "
import sys; sys.path.insert(0,'openclaw-memory-system'); sys.path.insert(0,'openclaw-learning-system')
from memory_core.config import setup_hf_mirror; setup_hf_mirror()
from memory_integration.decision_check import create_for_agent, get_agent_registry

dc = create_for_agent('openclaw')
dc2 = create_for_agent('luci')
reg = get_agent_registry()
print(f'Agents: {reg.list_agents()}')
print(f'KG: {dc.knowledge_graph.get_stats()[\"total_entities\"]} entities')
print(f'QL: {dc.ql_agent.get_stats()[\"nonzero_entries\"]}/700')
print(f'PM: {len(dc.procedural_memory.data[\"rules\"])} rules')
print('Bridge startup: OK')
"
```

- [ ] 输出 `Agents: ['openclaw','luci',...]`
- [ ] KG entities > 0
- [ ] QL nonzero > 0
- [ ] PM rules > 0

## Phase 2: check/record 往返

```powershell
python -c "
import sys; sys.path.insert(0,'openclaw-memory-system'); sys.path.insert(0,'openclaw-learning-system')
from memory_core.config import setup_hf_mirror; setup_hf_mirror()
from memory_integration.decision_check import create_for_agent

dc = create_for_agent('openclaw')
actions = ['follow_rule_strictly','try_fix_three_times','write_script','switch_skill','report_user']
contexts = [
    {'task':'download_stuck','phase':'P2b','error':'timeout'},
    {'task':'import_error','phase':'P1','error':'import_error'},
    {'task':'format_unsupported','phase':'P3','error':'format'},
]

for i in range(10):
    action = actions[i % len(actions)]
    ctx = contexts[i % len(contexts)]
    r = dc.check(action=action, context=ctx)
    rec_action = r.get('rl_recommendation',{}).get('recommended_action','?')
    dc.record(action=action, context=ctx, outcome='success' if i%3!=0 else 'failure', reward=0.8 if i%3!=0 else -0.5)
    print(f'{i+1}: check({action}) -> RL={rec_action}, record -> ok')
print('check/record loop: OK')
"
```

- [ ] 10 次循环全部输出 `ok`
- [ ] 无 Exception

## Phase 3: 真实 OpenClaw 任务（20+ 次决策）

在 OpenClaw 正常执行任务时，观察：

- [ ] Bridge 日志每行有 `[HyperMarrow Bridge]` 前缀
- [ ] check() 返回的 `rl_recommendation` 非 None
- [ ] record() 后 Q 表非零条目增加
- [ ] 无 `[HyperMarrow Bridge] Init FAILED`

## Phase 4: 睡眠周期

```powershell
python -c "
import sys; sys.path.insert(0,'openclaw-memory-system'); sys.path.insert(0,'openclaw-learning-system')
from memory_core.config import setup_hf_mirror; setup_hf_mirror()
from memory_integration.decision_check import create_for_agent, get_agent_registry

dc = create_for_agent('openclaw')
reg = get_agent_registry()
for aid in reg.list_agents():
    b = reg.get(aid)
    r = b.consolidator.sleep_cycle(force=True)
    print(f'{aid}: LTP={r.get(\"ltp_count\",0)}, LTD={r.get(\"ltd_pruned\",0)}')
print('Sleep cycle: OK')
"
```

- [ ] LTP/LTD 数值 ≥ 0
- [ ] 无 Exception

## Phase 5: 跨 Agent 迁移

```powershell
python -c "
import sys; sys.path.insert(0,'openclaw-memory-system'); sys.path.insert(0,'openclaw-learning-system')
from memory_integration.decision_check import create_for_agent, get_agent_registry

create_for_agent('openclaw'); create_for_agent('luci')
reg = get_agent_registry()
r = reg.cross_agent_transfer('openclaw','luci')
print(f'Transfer: eps={r.get(\"episodes_transferred\",0)}, q_cells={r.get(\"q_cells_seeded\",0)}')
print('Cross-agent transfer: OK')
"
```

- [ ] 输出包含 `episodes_transferred` 和 `q_cells_seeded`
- [ ] 无 Exception

## 验证后检查

- [ ] `python tests/test_smoke.py` → 12/12（再跑一次）
- [ ] `data/` 目录中新增文件已确认无异常
- [ ] `git diff` 审查所有变更
- [ ] 新文件 `git add`，提交

## 红线（禁止操作）

1. ❌ 禁止手动 `new QLearningAgent()` —— 必须通过 `create_for_agent()`
2. ❌ 禁止在 `memory_core/` 创建新的学习模块 —— 学习模块放 `learning_core/`
3. ❌ 禁止裸 `except: pass` —— 异常必须至少打印日志
4. ❌ 禁止删除 `tests/test_smoke.py`
5. ❌ 禁止创建 `independent_*` 分叉实现
