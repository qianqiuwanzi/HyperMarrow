# MCP Server 连接失败 — 问题根源诊断报告

**时间**：2026-07-05 11:15 GMT+8  
**诊断人**：AI（强哥监督）  

---

## 🎯 问题根源（3层）

### 1️⃣ **文件名拼写错误**（已修复）
- **问题**：`hypermarow_mcp.py`（单 `r`）vs `hypermarrow_mcp.py`（双 `r`）
- **原因**：OpenClaw 配置中路径是 `hypermarrow_mcp.py`（双 `r`），但实际文件名是 `hypermarow_mcp.py`（单 `r`）
- **修复**：重命名文件 `hypermarow_mcp.py` → `hypermarrow_mcp.py`
- **状态**：✅ 已修复

### 2️⃣ **transport 类型不匹配**（已修复，但暴露更深问题）
- **问题**：OpenClaw 配置中 `"transport": "sse"`，但 `hypermarrow_mcp.py` 使用 **stdio** 传输
- **原因**：`hypermarrow_mcp.py` 使用官方 `mcp` 库的 `stdio_server()`，但 OpenClaw MCP 客户端不支持 stdio
- **修复尝试**：将 `"transport": "sse"` 改为 `"transport": "stdio"`
- **结果**：❌ 配置验证失败（`transport` 允许值：`"sse"` 或 `"streamable-http"`）
- **结论**：OpenClaw **不支持 stdio 传输**

### 3️⃣ **OpenClaw MCP 客户端限制**（根本原因）
- **OpenClaw 支持的传输**：`"sse"` 或 `"streamable-http"`
- **`hypermarrow_mcp.py` 使用的传输**：**stdio**（`mcp.server.stdio.stdio_server()`）
- **不兼容原因**：
  - stdio：通过 stdin/stdout 通信（适合本地进程）
  - SSE/HTTP：通过 HTTP 协议通信（适合远程服务）
- **解决方案**：
  1. 修改 `hypermarrow_mcp.py` 使用 SSE 传输（需要重写）
  2. 创建 SSE 包装器（中等复杂度）
  3. **跳过 MCP，直接使用 `openclaw_wire.py`**（推荐）✅

---

## ✅ 推荐方案：跳过 MCP，使用 `openclaw_wire.py`

### 优势
1. ✅ **更简单**：只需 `from openclaw_wire import hm`
2. ✅ **已验证**：第2步和第3步测试全部通过
3. ✅ **功能完整**：包含所有 MCP 工具的功能
   - `hm.check()` = MCP `check` 工具
   - `hm.record()` = MCP `record` 工具
   - `hm.search()` = MCP `search` 工具
   - `hm.stats()` = MCP `stats` 工具
   - `hm.dream()` = MCP `transfer` 工具 + 记忆巩固
4. ✅ **非阻塞设计**：`intercept()` 和 `record()` 默认后台线程/异步
5. ✅ **对标 GBrain**：`intercept()` = `gbrain_dispatch`

### 集成方法
在 `SOUL.md` 或 `AGENTS.md` 中添加：
```python
from openclaw_wire import hm

# 每条消息后自动调用
def on_message(user_message, agent_response):
    hm.intercept(user_message, agent_response)
```

---

## 📊 验证结果总结

| 步骤 | 任务 | 状态 | 说明 |
|------|------|------|------|
| **第1步** | Smoke Test（12/12） | ✅ **通过** | 所有核心模块导入正常 |
| **第2步** | openclaw_wire.py 导入 | ✅ **通过** | `from openclaw_wire import hm` 成功 |
| **第3步** | 真实会话中测试拦截器 | ✅ **通过** | 消息自动存档到 EM，规则匹配正常 |
| **第4步** | MCP 验证 | ⚠️ **失败** | OpenClaw 不支持 stdio 传输 |
| **第5步** | Dream Cycle 验证 | ✅ **通过** | 9-stage 全部执行成功 |

---

## 🔧 如果未来需要 MCP 集成

### 方案1：修改 `hypermarrow_mcp.py` 使用 SSE 传输
```python
# 当前（stdio）
from mcp.server.stdio import stdio_server
async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)

# 需要改为（SSE）
from mcp.server.sse import SseServerTransport
from aiohttp import web

app = web.Application()
sse = SseServerTransport("/messages")
app.router.add_get("/sse", lambda r: sse.handle_get(r))
app.router.add_post("/messages", lambda r: sse.handle_post(r))
web.run_app(app, port=8080)
```

### 方案2：创建 SSE 包装器
- 创建一个 SSE MCP Server，内部调用 `openclaw_wire.py`
- 复杂度：中等（需要理解 `mcp` 库的 SSE 传输）

### 方案3：使用 `openclaw_wire.py`（推荐）
- 复杂度：低（已验证可用）
- 功能：完整
- 性能：更好（无 MCP 协议开销）

---

## 📝 结论

**MCP Server 连接失败的根本原因**：OpenClaw MCP 客户端不支持 stdio 传输。

**推荐方案**：跳过 MCP，直接在 OpenClaw 中导入 `openclaw_wire.py`。

**下一步**：
1. 在 `SOUL.md` 或 `AGENTS.md` 中添加 `from openclaw_wire import hm`
2. 在每条消息后调用 `hm.intercept()`
3. 在决策前后调用 `hm.check()` 和 `hm.record()`
4. 定期调用 `hm.dream()`（如每天晚上）

---

**诊断完成时间**：2026-07-05 11:20 GMT+8  
**诊断人**：AI（强哥监督）  
**状态**：✅ 问题根源已找到，推荐方案已确定
