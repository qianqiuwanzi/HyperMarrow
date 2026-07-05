# GBrain → OpenClaw 接入方式分析 — HyperMarrow 应该学什么

**日期**：2026-07-05

---

## 一、两种接入模式的根本差异

### GBrain：内嵌式

```
OpenClaw 每条用户消息
    │
    ├─ 主响应 (正常回复)
    │
    └─ gbrain_dispatch (并行, 不阻塞)
         ├─ signal-detector: 检测实体/想法 → gbrain put
         ├─ brain-ops:       检测已知引用 → gbrain search
         └─ 按需加载 Skill (匹配触发词)
```

**特点**：不需要显式调用。不需要连接协议。不需要启动外部进程。**OpenClaw 每条消息自动触发。**

### HyperMarrow：外挂式

```
OpenClaw 需要时
    │
    ├─ Bridge 模式: 启动 hm_startup.py → 手动 import → 手动调 check/record
    │   问题: 启动点不明确, 易于忘记调用
    │
    └─ MCP 模式: 启动独立进程 → 通过 stdio 协议通信 → 手动调 tool
        问题: 连接不稳定, 协议兼容性修复刚完成
```

**特点**：需要显式调用。需要提前启动。需要维持连接。**目前 OpenClaw 不知道怎么用。**

---

## 二、GBrain 接入的 4 个值得学的设计

### 1. 每条消息自动触发（最重要）

GBrain 的 `gbrain_dispatch` 协议是内嵌在 OpenClaw 消息处理管线中的：

```
OpenClaw 收到用户消息
    → 主逻辑处理
    → 同时触发 gbrain_dispatch (不阻塞主响应)
        → signal-detector 扫描消息中的实体/想法
        → brain-ops 检查是否涉及已知实体
```

**HyperMarrow 应该学**：不要求 OpenClaw 主动调用 `check()`/`record()`。而是提供一个**回调/拦截器**，让 OpenClaw 在处理每条消息时自动经过 HyperMarrow：

```python
# HyperMarrow 提供这个拦截器
def hypermarow_interceptor(user_message: str, agent_response: str):
    """OpenClaw 每条消息后自动调用 (并行, 不阻塞)"""
    dc = get_or_create_dc()
    # 1. 从消息中提取实体 → 写入 KG
    dc.knowledge_graph.extract_entities_from_text(user_message)
    # 2. 记录为情景记忆
    dc.episodic_memory.add_episode(
        what=f"User: {user_message[:80]}",
        context={"role": "user"},
        outcome="partial",
    )
    # 3. 检查是否有匹配的规则/意图
    dc.check(action="follow_rule_strictly", context={"message": user_message})
```

### 2. 并行不阻塞

GBrain 的 signal-detector 在**并行线程**中执行，不阻塞主响应。用户不会因为 GBrain 写入知识库而多等一秒钟。

**HyperMarrow 学到了但没执行**：Bridge 已经有 daemon 线程（睡眠调度器），但 `check()` 和 `record()` 在主线程中同步执行。

**应该改**：`record()` 中的重操作（KG 实体提取、VecDB 写入、Q 表持久化）放到后台线程。

### 3. 独立 CLI 用于调试

GBrain 的 `gbrain` CLI 不依赖 OpenClaw：

```bash
gbrain search "张三"      # 不需要 OpenClaw 运行
gbrain dream --json       # 独立维护
gbrain list               # 查看所有页面
```

**HyperMarrow 没有这个**。调试时必须写 Python 脚本。Bridge 挂了 → 无法访问任何记忆。

**应该学**：`hypermarrow` CLI 独立于 Bridge/MCP，用于快速诊断和人工操作。

### 4. Dream Cycle 是独立定时任务

GBrain 的 Dream Cycle 通过系统定时任务（Windows Task Scheduler / cron）执行，**不依赖 OpenClaw 是否在运行**。

**HyperMarrow 的睡眠调度器**是 Bridge 的一个 daemon 线程。Bridge 停止 → 巩固停止。

**应该学**：提供独立的 `hypermarrow dream` 命令，可由外部定时任务触发，不依赖任何服务运行。

---

## 三、HyperMarrow 新的接入架构（建议）

学习 GBrain 后，HyperMarrow 的接入应该是这样的：

```
┌─────────────────────────────────────────────────────────┐
│                  OpenClaw 消息管线                       │
│                                                         │
│  每条用户消息                                            │
│      │                                                  │
│      ├─ 主响应                                          │
│      │                                                  │
│      └─ hypermarow_interceptor (并行, 不阻塞)            │
│           ├─ 实体提取 → KG.add_entity                    │
│           ├─ 消息存档 → EM.add_episode                   │
│           ├─ 规则匹配 → PM.check_context                  │
│           └─ 意图检测 → ProspectiveMemory.check_triggers │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              独立工具 (不依赖 OpenClaw)                   │
│                                                         │
│  hypermarow stats             查看全系统状态              │
│  hypermarow search "关键词"    搜索记忆                   │
│  hypermarow dream --json      手动触发巩固               │
│  hypermarow export --md       导出可读知识摘要            │
│  hypermarow agents            列出所有 Agent             │
│                                                         │
│  Windows 定时任务: hypermarow dream --json (每天)        │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              MCP Server (外部 Agent 接入)                │
│                                                         │
│  Claude Code / Cursor / 其他 → MCP stdio 协议           │
│  5 个工具: check / record / search / stats / transfer    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 四、优先级行动

| # | 行动 | 对标 GBrain | 工作量 |
|:--:|------|:----------|:--:|
| 1 | **创建 `hypermarrow` CLI** | `gbrain` CLI | 2 天 |
| 2 | **创建 `hypermarow_interceptor`** | `gbrain_dispatch` | 1 天 |
| 3 | **独立 Dream Cycle 触发器** | 定时任务 | 0.5 天 |
| 4 | **record() 非阻塞化** | 并行执行 | 0.5 天 |

其中 #1 和 #2 是最关键的——有了 CLI 和拦截器，HyperMarrow 就从"需要手动调用的外挂"变成"嵌入 OpenClaw 消息流的记忆引擎"。

---

## 五、最关键的一句话

> GBrain 接入方式的核心不是技术方案（CLI、协议、线程），而是**设计哲学**：记忆系统应该是 Agent 的"潜意识"——不需要显式调用，每条消息自动经过，后台静默工作。HyperMarrow 目前是 Agent 的"工具箱"——需要时拿起来用，用完放下。这是根本差距。
