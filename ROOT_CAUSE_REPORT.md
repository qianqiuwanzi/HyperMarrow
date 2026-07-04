# HyperMarrow Bridge 失败根本原因报告

**日期**：2026-07-04 23:40 GMT+8  
**诊断人**：AI（强哥监督）  
**状态**：✅ 根本原因已找到，Bridge 已恢复正常

---

## 核心问题

**为什么昨天 Bridge 还能接入、输入灌入成功，今天全部失败了？**

---

## 根本原因：`pip install -e` 卸载后 `.egg-link` 被删除，Python 找不到模块

### 时间线对比

| 时间点 | `sys.path` 状态 | 结果 |
|--------|------------------|------|
| **昨天 2026-07-03** | `pip install -e packages/openclaw-memory-system` ✅ 创建了 `.egg-link` 文件 → Python 能通过 `site-packages/` 找到 `memory_integration` 模块 | ✅ Bridge 工作，5/5 RPC 测试通过 |
| **今天 2026-07-04 上午** | 为了重命名 `packages/` → `HyperMarrow/`，先卸载了 pip 包 → `.egg-link` 文件被删除 → `sys.path` 中没有 `openclaw-memory-system/` 路径 | ❌ `ModuleNotFoundError: No module named 'memory_integration'` |
| **今天 2026-07-04 下午（现在）** | 修复了 `hypermarrow_bridge.py` 第23-25行，手动添加路径：`sys.path.insert(0, str(_HYPERMARROW_ROOT / "openclaw-memory-system"))` | ✅ **Bridge 恢复正常！** |

### 技术细节

1. **昨天成功的原因**：
   - `pip install -e packages/openclaw-memory-system` 在 `site-packages/` 创建了 `.egg-link` 文件
   - `.egg-link` 文件内容：`D:\OpenClaw\workspace\packages\openclaw-memory-system`
   - Python 启动时自动读取 `.egg-link`，把 `openclaw-memory-system/` 加入 `sys.path`
   - 因此 `from memory_integration.decision_check import create_for_agent` 能成功

2. **今天失败的原因**：
   - 卸载 pip 包时，`.egg-link` 文件被删除
   - `hypermarrow_bridge.py` 原来的路径设置：`sys.path.insert(0, str(_PACKAGE_ROOT.parent.parent))`
   - 这行代码解析后指向 `D:\OpenClaw\workspace\`（错误！），而不是 `D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system\`
   - 因此 Python 找不到 `memory_integration` 模块

3. **修复方法**：
   - 在 `hypermarrow_bridge.py` 文件开头（第23-25行）手动添加：
     ```python
     _HYPERMARROW_ROOT = Path(r"D:\OpenClaw\workspace\HyperMarrow")
     sys.path.insert(0, str(_HYPERMARROW_ROOT / "openclaw-memory-system"))
     sys.path.insert(0, str(_HYPERMARROW_ROOT / "openclaw-learning-system"))
     ```
   - 这样无论 `pip install -e` 是否安装，Bridge 都能正确找到模块

---

## 验证结果

### 1. 导入测试（✅ 通过）

```powershell
python test_import_fixed.py
```

输出：
```
✅ memory_integration imported successfully
✅ learning_integration imported successfully
✅ DecisionCheckPoint created successfully
  KG entities: 39
  Q-table: 407/700 nonzero
✅ All tests passed!
```

### 2. Bridge JSON-RPC ping 测试（✅ 通过）

```powershell
Get-Content "D:\tmp\jsonrpc_ping.txt" | python hypermarow_bridge.py --mode jsonrpc
```

输出：
```json
{"jsonrpc": "2.0", "id": 1, "result": {"success": true, "pong": true, "ready": true, ...}}
```

### 3. Bridge JSON-RPC check 测试（✅ 通过）

```powershell
Get-Content "D:\tmp\jsonrpc_check.txt" | python hypermarow_bridge.py --mode jsonrpc
```

输出（摘要）：
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "success": true,
    "allowed": true,
    "suggestion": "[PM] Rule '遇到问题先修复3次再报告' is Level 5 — auto-approved",
    "confidence": 0.936,
    "rl_recommendation": {
      "recommended_action": "follow_rule_strictly",
      "confidence": 1.0,
      "q_value": 0.3609
    },
    "warnings": ["[RL] Suggests 'follow_rule_strictly' (Q=0.361, conf=100%) instead of 'write_script'"]
  }
}
```

---

## 当前系统状态

### HyperMarrow 系统

- ✅ 核心模块可导入（`memory_core`、`learning_core`、`memory_integration`）
- ✅ Bridge JSON-RPC 模式正常工作（ping/check 测试通过）
- ✅ 数据文件完整（15 PM 规则、39 KG 实体、407/700 Q 值）
- ✅ `hypermarrow_bridge.py` 路径配置已修复

### 待解决问题

1. **MCP Server 连接失败**：`openclaw mcp probe hypermarrow` 仍然返回 `Connection closed`
   - 原因：`hypermarow_mcp.py` 的 MCP 协议实现可能与 OpenClaw 不兼容
   - 建议：暂时跳过 MCP，直接使用 Bridge JSON-RPC

2. **Skill 未加载**：`openclaw skills list` 没有显示 `hypermarrow`
   - 原因：缺少 `skill.json` 元数据文件
   - 建议：暂时跳过 Skill，直接在主会话中调用 Bridge

3. **`pip install -e` 仍然失败**（SIGKILL）
   - 原因：可能是内存不足或超时
   - 建议：不依赖 `pip install -e`，直接使用 `sys.path.insert()` 方式

---

## 推荐下一步

### 方案1：直接在主会话中调用 Bridge（推荐）

在 OpenClaw 主会话中，使用 `exec` 工具调用 Bridge JSON-RPC：

```python
import subprocess
import json

# 启动 Bridge 子进程
bridge = subprocess.Popen(
    ["python", r"D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system\openclaw_memory_system\hypermarrow_bridge.py", "--mode", "jsonrpc"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 发送 JSON-RPC 请求
request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "check", "params": {"action": "test_action", "task": "test"}})
bridge.stdin.write(request + "\n")
bridge.stdin.flush()

# 读取响应
response_line = bridge.stdout.readline()
result = json.loads(response_line)
print(result)
```

### 方案2：修复 MCP Server 连接问题

调试 `hypermarow_mcp.py` 的 MCP 握手过程，找出为什么 OpenClaw 连接失败。

### 方案3：创建 Skill 元数据文件

创建 `skills/hypermarrow/skill.json`，让 OpenClaw 识别这个 Skill。

---

## 附录：关键文件修改记录

### `hypermarrow_bridge.py` 修改（第23-25行）

**修改前**：
```python
import sys, json, os, time
from pathlib import Path

# ── Working directory: HyperMarrow package root ──────────────────
_BRIDGE_DIR = Path(__file__).parent.resolve()
_PACKAGE_ROOT = _BRIDGE_DIR  # openclaw_memory_system/
sys.path.insert(0, str(_PACKAGE_ROOT.parent.parent))
```

**修改后**：
```python
import sys, json, os, time
from pathlib import Path

# ── Add HyperMarrow packages to sys.path ──────────────────────
_HYPERMARROW_ROOT = Path(r"D:\OpenClaw\workspace\HyperMarrow")
sys.path.insert(0, str(_HYPERMARROW_ROOT / "openclaw-memory-system"))
sys.path.insert(0, str(_HYPERMARROW_ROOT / "openclaw-learning-system"))

# ── Working directory: HyperMarrow package root ──────────────────
_BRIDGE_DIR = Path(__file__).parent.resolve()
_PACKAGE_ROOT = _BRIDGE_DIR  # openclaw_memory_system/
```

---

## 教训总结

1. **不要依赖 `pip install -e`**：开发过程中，`.egg-link` 可能被意外删除，导致导入失败
2. **在脚本开头手动设置 `sys.path`**：更可靠，不依赖外部环境
3. **记录每次修改**：今天的失败本来可以避免，如果有文档记录昨天的成功环境
4. **分离开发环境和生产环境**：开发时直接用 `sys.path.insert()`，生产时才用 `pip install -e`

---

**结论**：问题根源是 `pip install -e` 卸载后 `.egg-link` 被删除，已通过手动添加 `sys.path` 修复。Bridge 现在可以正常工作。
