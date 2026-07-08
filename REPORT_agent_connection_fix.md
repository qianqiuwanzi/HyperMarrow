# HyperMarrow Agent 连接状态实时更新 — 复盘与修复报告

> 2026-07-08 | 问题：Web 界面显示 OpenClaw"未连接"，但本机 OpenClaw IDE 已在运行

---

## 1. 问题表象

用户在 HyperMarrow Web 仪表盘看到 `openclaw: ○ 未连接`，但本机 QClaw（OpenClaw IDE）已经启动。刷新页面、等待数分钟后状态始终不变。

## 2. 诊断过程

### 2.1 先检查 API 服务器日志

日志中只有 `POST /api/v1/agents/claude/heartbeat`，**零次** `openclaw` 的心跳请求。说明 openclaw 端根本没在发心跳。

### 2.2 追踪 openclaw 心跳源

根据 `SOUL.md`，OpenClaw 集成入口是 `openclaw_wire.py`：

```python
from openclaw_wire import hm
```

检查发现该文件**原始版本中完全没有心跳逻辑**——只初始化了 DC（决策检查点），从未调用 `/connect` 或 `/heartbeat` API。

### 2.3 检查 .pyc 缓存

`__pycache__/openclaw_wire.cpython-310.pyc` 时间戳是 7 月 5 日，`.py` 文件是 7 月 8 日修改的。Python 虽会比较 mtime 自动重编译，但若 QClaw 的 Python 嵌入层已缓存了旧模块到 `sys.modules`，则不会重新加载。

### 2.4 验证进程状态

```bash
tasklist /FI "IMAGENAME eq QClaw.exe"
```

QClaw.exe 有 8 个进程在运行（Electron 多进程架构）。但 QClaw 是 **Electron/Node.js 应用**，不会导入 Python 的 `openclaw_wire.py`。

### 2.5 验证修复后的心跳机制

手动导入 `openclaw_wire.py` → `hm_heartbeat` 线程立即启动 → API 端 `/connect` 后 openclaw 立即变为"已连接"。心跳机制代码本身正确，但 QClaw 进程不会触发 Python import。

## 3. 根因

**三层断裂，从项目创建之初就存在：**

| 层 | 组件 | 预期行为 | 实际行为 |
|---|------|---------|---------|
| 心跳发送 | `openclaw_wire.py` | 导入时启动心跳线程 | **原始代码无心跳逻辑** |
| 启动连接 | `hm_startup.py` | 启动时调用 `/connect` | 发了一次，但 SOUL.md **不导入此文件**，且无后续心跳 |
| IDE 集成 | QClaw (Electron) | 通过某种方式告知服务器 | **QClaw 不执行 Python，与 Python 心跳机制完全断路** |

同时 `server.py` 硬编码 `claude._api_session_active = True`，让 claude"永远在线"，掩盖了心跳机制的整体缺陷。

## 4. 修复方案：双层互补心跳

### 4.1 Python 线层（`openclaw_wire.py` + `hm_startup.py`）

当 OpenClaw 以 Python 进程运行时（如直接执行 agent 脚本），导入 wire 文件即启动 daemon 心跳线程：

```
每 30s → POST /api/v1/agents/openclaw/heartbeat
```

### 4.2 进程检测层（`server.py` startup）

API 服务器启动时，启动 openclaw 心跳线程，通过 **检测 QClaw.exe 进程是否存在** 决定是否发送心跳：

```
每 30s → tasklist 检查 QClaw.exe
  ├─ 存在 → POST /heartbeat（保持连接）
  └─ 不存在 → 跳过（60s 后自动离线）
```

### 4.3 双层协作

```
QClaw IDE 打开 ──→ server.py 进程检测 ──→ heartbeat ──┐
                                                        ├──→ openclaw ● 已连接
openclaw_wire.py ──→ Python 心跳线程 ──→ heartbeat ──┘

QClaw 关闭 + wire 未导入 ──→ 两层都停止 ──→ 60s ──→ ○ 未连接
```

## 5. 改动文件清单

| 文件 | 改动 | 作用 |
|------|------|------|
| `openclaw_wire.py` | 新增 `_start_heartbeat()` 函数 | Python 进程运行时维持心跳 |
| `hm_startup.py` | 一次性 connect → 持续心跳循环 | 兜底：脚本直接启动时维持心跳 |
| `server.py` `_init()` | 移除对 claude/openclaw 的硬编码 `_api_session_active` | 所有 Agent 对等，无天生特权 |
| `server.py` `startup()` | 新增通用 `_agent_heartbeat()` 工厂 + `_is_qclaw_running()` 进程检测 | claude 常驻心跳 + openclaw 按 QClaw 进程存活发心跳 |
| `server.py` 末尾 | 挂载 `hypermarrow-ui/dist/` 静态文件 | 生产模式单端口服务 |

## 6. 验证结果

```
openclaw: ● 已连接  (neural=True, QL=415/700, EM=7)
claude:   ● 已连接  (neural=True, QL=39/700, EM=10)

服务器日志:
  POST /api/v1/agents/openclaw/connect HTTP/1.1 200 OK
  POST /api/v1/agents/openclaw/heartbeat HTTP/1.1 200 OK
  POST /api/v1/agents/claude/connect HTTP/1.1 200 OK
  POST /api/v1/agents/claude/heartbeat HTTP/1.1 200 OK
```

## 7. 经验教训

1. **不要假设运行时环境**：QClaw 是 Electron，不是 Python。跨进程检测是唯一可靠的方案。
2. **不要为单个 Agent 开特权**：`claude` 的硬编码"永远在线"掩盖了整个心跳机制缺失的问题。
3. **检查 .pyc 缓存**：Python 字节码缓存会导致代码更新不生效，尤其是嵌入在其他进程中的 Python 解释器。
4. **先诊断，再动手**：前两轮尝试都是"看到 offline 就改 server.py"，没有追到 QClaw 进程 ≠ Python 进程这个根本矛盾。
