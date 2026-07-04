# MCP + Skill 问题修复方案

**日期**：2026-07-04  
**状态**：MCP 已修复，Skill 暂不需要

---

## 问题1：MCP Server 连接失败 → 已修复

### 根因
`hypermarow_mcp.py` 原来是一个手写的 JSON-RPC stdin/stdout 循环，不兼容 MCP 协议的标准 stdio transport。OpenClaw 的 MCP 客户端发送标准 MCP 初始化握手时，手写循环无法正确响应 → 连接关闭。

### 修复
重写为使用官方 `mcp` 库 (v1.28.1) 的 `mcp.server.stdio` API：

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("hypermarow")
# ... 注册 tools ...
async with stdio_server() as (read_stream, write_stream):
    await server.run(read_stream, write_stream, ...)
```

### 验证步骤

```powershell
# 1. 确认 mcp 库已安装
pip show mcp    # 应显示 v1.28.1

# 2. 测试 MCP Server 能否正常导入
cd D:\OpenClaw\workspace\HyperMarrow
python -c "from openclaw_memory_system.hypermarow_mcp import tool_stats; print(tool_stats()[:100])"

# 3. 如果上面正常，运行 OpenClaw MCP probe
openclaw mcp probe hypermarrow
```

### 如果仍然失败

两个备选方案：

**备选A：直接用 Python 调用（不走 MCP）**
在 OpenClaw 会话中直接执行 Python，跳过 MCP 协议层：
```python
exec(open(r"D:\OpenClaw\workspace\HyperMarrow\hm_startup.py").read())
dc = __import__('sys').modules.get('__main__').DC  # 或直接导入
result = dc.check(action="try_fix_three_times", context={"task":"test"})
print(result["rl_recommendation"])
```

**备选B：通过 Bridge JSON-RPC**
Bridge 已有成熟的 stdin/stdout JSON-RPC，直接用它：
```python
# OpenClaw 启动时：
import subprocess
bridge = subprocess.Popen(
    ["python", r"D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system\openclaw_memory_system\hypermarow_bridge.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)
```

---

## 问题2：Skill 未加载 → 暂不需要

MCP 接入成功后，OpenClaw 可以直接调用 5 个工具（check/record/search/stats/transfer），不需要 Skill。

如果仍然需要 Skill：
- OpenClaw Skill 目录可能需要 `skill.json` 元数据文件
- Skill 位置可能是 `C:\Users\Administrator\.qclaw\skills\` 而非 `D:\OpenClaw\workspace\skills\`
- 参考 `D:\Program Files\QClaw\v0.2.31.600\resources\openclaw\docs\skills.md` 获取正确格式
