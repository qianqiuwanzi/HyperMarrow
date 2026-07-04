# Bridge 接入 OpenClaw 阻塞 — 解决方案

**日期**：2026-07-04  
**阻塞问题**：接入指南给了代码，但没说放哪里  
**推荐方案**：B + A 组合 — MCP 立即可用 + Hook 脚本深度集成

---

## 方案选择

| 方案 | 何时用 | 接入内容 |
|------|--------|----------|
| **[MCP 接入](#方案1-mcp-接入5分钟)** | 立即可用，任何 MCP 客户端 | check/record/search/stats 全部可用 |
| **[Hook 脚本](#方案2-hook-脚本深度集成)** | 需要睡眠调度器、双Agent | 完整 Bridge 功能 |

**两者可以共存。MCP 提供标准协议接入，Hook 脚本提供后台任务。**

---

## 方案1：MCP 接入（5分钟，推荐先做）

### 第1步：创建 `.mcp.json`

在 OpenClaw 的工作目录（或 `D:\OpenClaw\workspace\`）创建：

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

### 第2步：验证

重启 Claude Code，在对话中输入：

> 请调用 hypermarow 的 stats 工具，查看当前记忆系统状态

如果返回 KG 实体数、QL 状态、PM 规则数 → 接入成功。

### 覆盖范围

✅ check / record / search / stats / analogy / transfer / consolidate / skills  
✅ KG / PM / QL / EM / Meta 全部可通过 MCP 读取  
❌ 睡眠调度器（MCP Server 没有后台线程）  
❌ 双 Agent 自动注册（MCP Server 只创建 openclaw）

---

## 方案2：Hook 脚本（深度集成，15分钟）

### 第1步：创建启动入口文件

文件路径：`D:\OpenClaw\workspace\HyperMarrow\hm_startup.py`

```python
"""HyperMarrow Bridge startup — import this in OpenClaw's hook or entry point."""
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

from memory_core.config import setup_hf_mirror
setup_hf_mirror()

from memory_integration.decision_check import create_for_agent

# ── 创建 Agent（带错误容忍）─────────────────────────────────────
DC = None
_HM_READY = False

try:
    DC = create_for_agent("openclaw")
    _DC_luci = create_for_agent("luci")

    # 启用 WorldModel（如果 PyTorch 可用）
    try:
        DC.ql_agent.enable_world_model()
        _DC_luci.ql_agent.enable_world_model()
    except Exception:
        pass

    # 启动睡眠调度器
    from openclaw_memory_system.hypermarow_bridge import _start_sleep_scheduler
    from memory_integration.decision_check import get_agent_registry
    _start_sleep_scheduler(get_agent_registry())

    _HM_READY = True
    print(f"[HyperMarrow] Bridge ready: 2 agents, "
          f"KG={DC.knowledge_graph.get_stats()['total_entities']} entities, "
          f"QL={DC.ql_agent.get_stats()['nonzero_entries']}/700, "
          f"PM={len(DC.procedural_memory.data.get('rules',{}))} rules")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[HyperMarrow] Bridge init FAILED: {e}")
```

### 第2步：确定 OpenClaw 的启动方式，选择对应接入点

#### 情况 A：OpenClaw 通过 Claude Code CLI 启动

在 `D:\OpenClaw\workspace\.claude\settings.json` 中添加 `hooks`：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "command": "python -c \"exec(open(r'D:\\OpenClaw\\workspace\\HyperMarrow\\hm_startup.py').read())\""
      }
    ]
  }
}
```

#### 情况 B：OpenClaw 有 Python 启动脚本

在 OpenClaw 的 Python 启动脚本（如 `start.py`、`main.py`、`__init__.py`）的第一行之后添加：

```python
# ── HyperMarrow Bridge ────────────────────────────────────────
try:
    exec(open(r"D:\OpenClaw\workspace\HyperMarrow\hm_startup.py").read())
except Exception:
    pass  # Bridge failure should not block OpenClaw startup
```

#### 情况 C：不确定入口点在哪

运行以下命令找到入口点：

```powershell
# 查找可能的入口文件
dir /s /b D:\OpenClaw\workspace\*.py | findstr /i "main start init run"
dir /s /b "D:\Program Files\QClaw\*.py" 2>nul | findstr /i "main start"
```

#### 情况 D：通过 `PYTHONSTARTUP` 环境变量

```powershell
# 设置环境变量（每次启动 Python 时自动执行）
setx PYTHONSTARTUP "D:\OpenClaw\workspace\HyperMarrow\hm_startup.py"
```

### 第3步：验证

启动 OpenClaw 后，检查日志中是否出现：

```
[HyperMarrow] Bridge ready: 2 agents, KG=33 entities, QL=407/700, PM=15 rules
[HyperMarrow Bridge] Sleep scheduler started (interval=4h)
```

---

## 最终推荐

```
第一步 (今天, 5分钟):    MCP 接入  → check/record/search/stats 立即可用
第二步 (今天, 15分钟):   Hook 脚本  → 睡眠调度器 + 双Agent + 自动巩固
```

两个方案同时运行，互不冲突。

---

## 验证命令

接入后运行以下验证：

```powershell
cd D:\OpenClaw\workspace\HyperMarrow
python -c "
import sys; sys.path.insert(0,'openclaw-memory-system'); sys.path.insert(0,'openclaw-learning-system')
from memory_core.config import setup_hf_mirror; setup_hf_mirror()
from memory_integration.decision_check import create_for_agent
dc = create_for_agent('openclaw')
r = dc.check(action='try_fix_three_times', context={'task':'verify','phase':'P2b'})
print('check() OK, RL recommends:', r['rl_recommendation']['recommended_action'])
dc.record(action='try_fix_three_times', context={'task':'verify'}, outcome='success', reward=1.0)
print('record() OK')
print('Bridge 功能正常')
"
```
