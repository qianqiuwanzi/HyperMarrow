# 智商藏不住 — 类人记忆与学习系统

> HyperMarrow = Hyper + Memory Brain — 超记忆之脑

`openclaw-memory-system` + `openclaw-learning-system` — 可独立安装的 Python 包，实现类人认知能力：
三层记忆 × 知识图谱 × 强化学习 × 元认知 × 多 Agent 支持 × Web 可视化 × 商业化 License

---

## 快速启动

```bash
# 生产模式（单端口，API + UI 一体）
python start.py                  # → http://localhost:8741

# 开发模式（API + Vite 热更新分离）
python start.py --dev            # API :8741 + npm run dev → UI :5173

# 停止
python stop.py
```

**Windows 双击**: `start.bat` / `stop.bat`

---

## 配置

所有配置集中在项目根目录 `config.yaml`，替代了原有的硬编码方式：

```yaml
server:
  port: 8741
  api_token: null        # 生产环境设置 Bearer Token

features:                # 功能开关（社区版默认全开）
  q_learning: true
  vector_memory: true
  world_model: true
  # ...

license:
  enabled: false         # false = 社区版, true = 商业版
  server_url: "https://license.openclaw.ai"
```

环境变量可覆盖配置：`HYPERMARROW_SERVER_PORT=9000 python start.py`

---

## Agent 接入方式

### 方式一：SDK 接入（推荐，Python Agent）

```bash
pip install hypermarrow-sdk    # 或直接使用 hypermarrow-sdk/ 目录
```

```python
from hypermarrow import HyperMarrowWire

hm = HyperMarrowWire(agent_id="my-agent", server="http://localhost:8741")

# 每条消息后自动触发
hm.intercept(user_message, agent_response)

# 决策前检查 → 返回规则命中 / 关联实体 / RL 推荐
result = hm.check("try_fix_three_times", task="下载超时")

# 决策后记录 → 异步写入所有子系统
hm.record("try_fix_three_times", {"task": "下载"}, "success")
```

### 方式二：HTTP API（任何语言）

```bash
# 注册连接
curl -X POST http://localhost:8741/api/v1/agents/my-agent/connect

# 数据灌入
curl -X POST http://localhost:8741/api/v1/agents/my-agent/intercept \
  -H "Content-Type: application/json" \
  -d '{"user_message": "...", "agent_response": "..."}'

# 决策检查
curl -X POST http://localhost:8741/api/v1/agents/my-agent/check \
  -H "Content-Type: application/json" \
  -d '{"action": "try_fix_three_times", "context": {"task": "download"}}'

# 决策记录
curl -X POST http://localhost:8741/api/v1/agents/my-agent/record \
  -H "Content-Type: application/json" \
  -d '{"action": "try_fix", "outcome": "success", "reward": 0.8}'
```

### 方式三：SOUL.md 一线接线（OpenClaw 原生）

```python
from openclaw_wire import hm
# 自动启动心跳、初始化所有子系统
```

### Agent 连接状态

| 机制 | 说明 |
|------|------|
| **自助注册** | 任意 Agent 首次调用 `/connect` 即自动注册，分配隔离数据文件 |
| **双层心跳** | 服务器进程检测 + Agent SDK 心跳线程，每 30s 维持连接 |
| **60s 超时** | 两层心跳均停止后，60 秒自动标记为离线 |
| **跨平台进程检测** | Windows/Linux/macOS 自动检测宿主进程 |

---

## API 参考

### Agent 连接

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents/{id}/connect` | POST | 注册并连接 Agent |
| `/api/v1/agents/{id}/heartbeat` | POST | 心跳维持 |
| `/api/v1/agents/{id}/disconnect` | POST | 断开连接 |

### 数据灌入

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents/{id}/intercept` | POST | 对话消息 → 记忆拦截 |
| `/api/v1/agents/{id}/check` | POST | 决策前 10 步流水线检查 |
| `/api/v1/agents/{id}/record` | POST | 决策后回写所有子系统 |

### 监控查询

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents` | GET | 所有 Agent 状态（含心跳） |
| `/api/v1/memory/overview` | GET | 7 模块记忆统计 |
| `/api/v1/learning/overview` | GET | 7 模块学习统计 |
| `/api/v1/license/status` | GET | License 状态 |
| `/api/v1/kg/graph` | GET | 知识图谱节点+边 |
| `/api/v1/dream/run` | GET | 手动触发 Dream Cycle |
| `/ws` | WS | 实时推送（5s 间隔） |
| `/docs` | GET | Swagger API 文档 |

### 认证

生产环境在 `config.yaml` 中设置 `server.api_token`，Agent 请求需带 `Authorization: Bearer <token>`。社区版无需认证。

---

## 已验证的功能

| 功能 | 状态 | 说明 |
|------|:--:|------|
| Config 驱动 | ✅ | `config.yaml` + 环境变量覆盖，替代所有硬编码 |
| Agent 自助注册 | ✅ | 任意 Agent 首次 `/connect` 自动注册，无需改源码 |
| 双层心跳 | ✅ | 进程检测 + SDK 线程，60s 超时自动离线 |
| 跨平台进程检测 | ✅ | Windows (tasklist) / Linux (pgrep) / macOS |
| SDK | ✅ | `hypermarrow-sdk` pip 包，本地嵌入 + HTTP 客户端 |
| KnowledgeGraph | ✅ | 实体—关系—实体，BFS 查询 |
| Q-Learning | ✅ | Hybrid 模式 (tabular + neural)，415/700 非零 |
| ProceduralMemory | ✅ | 15 条规则，5 级自动化，语义匹配 |
| DreamCycle | ✅ | 12 阶段巩固，定时自动执行 |
| 跨 Agent 迁移 | ✅ | 情景迁移 + Q 表种子化 + 校准参考 |
| 功能开关 | ✅ | 按 License 分级控制子系统启用 |
| License API | ✅ | `/api/v1/license/status`，支撑商业版功能分级 |
| API 认证 | ✅ | Bearer Token 中间件，社区版默认关闭 |
| Web UI | ✅ | React SPA，6 面板 + License 状态 |
| 生产模式单端口 | ✅ | API 直接挂载 UI 静态文件 |

---

## 架构概览

```
Agent (Python/Node/Go/任意)
    │  HTTP /connect /heartbeat /intercept /check /record
    ▼
┌──────────────────────────────────────────┐
│         HyperMarrow API Server (:8741)    │
│  ┌─────────────────────────────────────┐ │
│  │        DecisionCheckPoint           │ │
│  │  intercept → check → record 流水线  │ │
│  └──────────────┬──────────────────────┘ │
│     ┌───────────┴───────────┐            │
│     │  Per-Agent (isolated) │  Shared    │
│     │  WM, EM, QL, Meta     │  KG, PM    │
│     │   (文件级隔离)         │  VecDB     │
│     └───────────────────────┘            │
│     Consolidator │ Transfer │ MetaLearn  │
│            Dream Cycle (12-stage)        │
└──────────────────────────────────────────┘
     │
     ▼
  Web UI (:8741) — 仪表盘 + API 文档
```

### 记忆系统 (7 模块)
P1 工作记忆 · P2 向量记忆 · P3 情景记忆 · 程序性记忆 · 知识图谱 · 感知通道 · 前瞻记忆

### 学习系统 (7 模块)
Q-Learning · 元认知 · 记忆巩固 · 迁移学习 · World Model · 元学习 · 神经网络状态

---

## 商业化

`config.yaml` 中设置 `license.enabled: true` 切换到商业版：

| 功能 | Free | Pro | Enterprise |
|------|:---:|:---:|:---:|
| 工作/情景/程序性记忆 | ✅ | ✅ | ✅ |
| 知识图谱 | ✅ | ✅ | ✅ |
| 向量搜索 | ❌ | ✅ | ✅ |
| Q-Learning 决策 | ❌ | ✅ | ✅ |
| 元认知 | ❌ | ✅ | ✅ |
| World Model | ❌ | ❌ | ✅ |
| 跨 Agent 迁移 | ❌ | ❌ | ✅ |
| Agent 数量 | 1 | 3 | 无限 |

商业化工具链见 `../commercial/` 目录（LICENSE_SDK + license_server + packaging + sales）。

---

## 项目文件

| 文件/目录 | 用途 |
|-----------|------|
| `config.yaml` | 统一配置（端口、功能开关、License、学习参数） |
| `start.py` / `stop.py` | 统一启停脚本 |
| `openclaw-memory-system/` | 记忆系统核心 |
| `openclaw-learning-system/` | 学习系统核心 |
| `hypermarrow-ui/` | React Web 仪表盘 |
| `hypermarrow-sdk/` | Agent SDK（pip install） |
| `openclaw_wire.py` | OpenClaw 一线接线（向后兼容） |
| `REPORT_production_architecture.md` | 生产架构完整设计 |
| `REPORT_commercial_alignment.md` | 商业化对齐分析 |
| `ROADMAP_unified_remediation.md` | 统一改造路线图 |
| `REPORT_agent_connection_fix.md` | Agent 连接修复复盘 |

---

*HyperMarrow — 让 AI 记得住、学得快、用得对。*
