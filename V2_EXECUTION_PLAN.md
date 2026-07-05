# HyperMarrow V2 执行计划

**日期**：2026-07-05
**总工期**：7 个工作日
**核心原则**：V1 核心层零改动，全部新增/修改在接入层

---

## Phase 1：CLI + 独立 Dream Cycle（3 天，P0）

### Day 1：CLI 工具骨架 + 基础命令

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 1.1 | 创建 CLI 入口 | `memory_cli/hypermarrow.py` (新) | `python -m memory_cli.hypermarrow --help` 输出帮助 |
| 1.2 | `hypermarrow stats` | 同上 | KG=33, PM=15, QL=407/700 全部显示 |
| 1.3 | `hypermarrow agents` | 同上 | 列出 openclaw + luci, 各自动作数/健康状态 |
| 1.4 | `hypermarrow health` | 同上 | ECE/成功率/连续失败/健康分 全部显示 |
| 1.5 | `hypermarrow search "关键词"` | 同上 | 返回情景记忆 + 向量记忆结果 |

**Day 1 验收**：
```powershell
hypermarrow stats              # 输出完整系统统计
hypermarrow agents             # 输出 2 个 Agent
hypermarrow search "download"  # 返回匹配结果
```

### Day 2：Dream Cycle 9 阶段重构

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 2.1 | 重构 sleep_cycle → dream_cycle | `memory_consolidator.py` (改) | 9 阶段独立方法 |
| 2.2 | 增加 lint 阶段 | 同上 | 检查 data/ 文件存在且可解析 |
| 2.3 | 增加 sync 阶段 | 同上 | Agent 间状态同步 (调用 AgentRegistry.share_all) |
| 2.4 | 增加 orphans 阶段 | `knowledge_graph.py` (改) | `get_orphan_entities()` 返回无关系的实体 |
| 2.5 | JSON 输出格式 | `memory_consolidator.py` (改) | `{"status":"ok","phases":{...}}` |

**Day 2 验收**：
```python
consolidator.dream_cycle(force=True)
# 返回:
# {"status": "ok", "phases": {"lint": 0, "backlinks": 3, "sync": 0, ...}}
```

### Day 3：CLI dream + export 命令

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 3.1 | `hypermarrow dream` | `memory_cli/hypermarrow.py` | 终端美化输出 9 阶段结果 |
| 3.2 | `hypermarrow dream --json` | 同上 | JSON 输出（供定时任务） |
| 3.3 | `hypermarrow export --format markdown` | 同上 | 生成可读 .md 文件 |
| 3.4 | `hypermarrow kg entities/central/path` | 同上 | KG 查询命令 |

**Day 3 验收**：
```powershell
hypermarrow dream --json > dream_$(date +%Y%m%d).json  # 定时任务可用
hypermarrow export --format markdown > knowledge.md      # 人类可读
hypermarrow kg central                                   # 核心实体 Top 10
```

---

## Phase 2：Interceptor + 来源标注（2 天，P1）

### Day 4：消息拦截器

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 4.1 | 创建拦截器模块 | `memory_integration/interceptor.py` (新) | 导入无报错 |
| 4.2 | `hypermarow_intercept()` | 同上 | 输入消息→提取实体→存档情景 |
| 4.3 | 实体提取逻辑 | 同上 | 从消息中提取已知实体类型关键词→KG.add_entity |
| 4.4 | 消息存档逻辑 | 同上 | EM.add_episode(what=消息摘要) |
| 4.5 | 非阻塞执行 (daemon线程) | 同上 | 调用不阻塞主线程 |

**Day 4 验收**：
```python
from memory_integration.interceptor import hypermarow_intercept
result = hypermarow_intercept("P2b 下载 timeout 了，试试重试")
assert result["entities_found"] >= 1   # P2b + timeout
assert result["episodes_created"] >= 1
```

### Day 5：来源标注 + record() 非阻塞

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 5.1 | add_episode() 自动 inject source | `episodic_memory_db.py` (改) | source={agent,channel,timestamp} |
| 5.2 | record() 传递 source | `decision_check.py` (改) | 所有 record() 自动带 source |
| 5.3 | record() async_mode 参数 | `decision_check.py` (改) | async_mode=True → 返回 {"status":"queued"} |
| 5.4 | 更新 Bridge 使用非阻塞 record | `hypermarow_bridge.py` (改) | Bridge record 调用改为非阻塞 |

**Day 5 验收**：
```python
dc.record(action="test", context={}, outcome="success", async_mode=True)
# 立即返回 {"status": "queued"}
# 1秒后检查 EM: 新 episode 已写入, source 字段存在
```

---

## Phase 3：孤立检测 + Markdown 导出（2 天，P2）

### Day 6：孤立内容检测

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 6.1 | `KG.get_orphan_entities()` | `knowledge_graph.py` (改) | 返回无关系的实体列表 |
| 6.2 | orphans 阶段集成到 dream_cycle | `memory_consolidator.py` (改) | dream_cycle JSON 中 orphans 非零时触发 |
| 6.3 | 孤立检测 CLI | `memory_cli/hypermarrow.py` | `hypermarrow health` 显示孤立数量 |

**Day 6 验收**：
```python
orphans = kg.get_orphan_entities()
# 返回无关系的实体列表
```

### Day 7：Markdown 导出 + 回归测试

| # | 任务 | 文件 | 验收 |
|:--:|------|------|------|
| 7.1 | Markdown 导出逻辑 | `memory_cli/hypermarrow.py` | 生成层级清晰、可读的 md |
| 7.2 | KG 导出 | 同上 | 实体类型分组 + 关系列表 |
| 7.3 | PM 规则导出 | 同上 | 按 Level 分组 |
| 7.4 | 回归测试 | `tests/test_smoke.py` | 12/12 |
| 7.5 | 更新 README | `README.md` | 反映 V2 新能力 |

**Day 7 验收**：
```powershell
hypermarrow export --format markdown
cat hypermarrow_knowledge.md  # 人类完全可读
python tests/test_smoke.py    # 12/12 PASS
```

---

## 总计

| Phase | 天数 | 新增文件 | 修改文件 | 核心层改动 |
|:------|:--:|:------:|:------:|:--:|
| 1: CLI + Dream Cycle | 3 | `memory_cli/hypermarrow.py` | `memory_consolidator.py`, `knowledge_graph.py` | 0 |
| 2: Interceptor + Source | 2 | `memory_integration/interceptor.py` | `episodic_memory_db.py`, `decision_check.py`, `hypermarow_bridge.py` | 0 |
| 3: Orphans + Export | 2 | 0 | `knowledge_graph.py`, `memory_consolidator.py`, `memory_cli/hypermarrow.py`, `README.md` | 0 |
| **合计** | **7** | **2** | **5** | **0** |

## 验收最终清单

```powershell
# CLI
hypermarrow stats              # 全系统统计
hypermarrow agents             # 2 Agent
hypermarrow health             # 健康报告
hypermarrow search "download"  # 搜索记忆
hypermarrow dream --json       # 9 阶段维护
hypermarrow export --md        # 可读导出
hypermarrow kg central         # KG 核心实体

# Interceptor
python -c "
from memory_integration.interceptor import hypermarow_intercept
r = hypermarow_intercept('P2b download timeout, retry 3 times')
assert r['entities_found'] >= 1
assert r['episodes_created'] >= 1
print('Interceptor: OK')
"

# Dream Cycle JSON
python -c "
from memory_integration.decision_check import create_for_agent
dc = create_for_agent('openclaw')
r = dc.consolidator.dream_cycle(force=True)
assert r['status'] == 'ok'
assert len(r['phases']) == 9
print('Dream Cycle: OK')
"

# Async record
python -c "
dc.record(action='test', context={}, outcome='success', async_mode=True)
print('Async record: OK')
"

# 回归
python tests/test_smoke.py     # 12/12 PASS
```
