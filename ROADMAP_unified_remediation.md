# HyperMarrow 统一改造路线图

> 2026-07-08 | 综合 HyperMarrow 原生改造 + commercial 6 断层修复

---

## 总体逻辑

两条线合并为 4 个 Phase，按依赖关系排序。每个 Phase 同时推进 HyperMarrow 和 commercial，不各自为战。

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
(地基)      (商业化)    (开放)      (加固)
  │            │           │           │
  config      license    API/SDK      auth/cron
  build       feature     registry     license UI
  paths       heartbeat   intercept    cross-platform
```

---

## Phase 1：统一地基（config + build + 路径）

**解决的问题：**
- commercial 断层 1（打包入口不对）
- commercial 断层 5（路径配置不一致）
- HyperMarrow P1（无配置驱动）

### 1.1 新增 `config.yaml`

```yaml
# HyperMarrow/config.yaml — 统一配置，替代所有硬编码

server:
  host: "0.0.0.0"
  port: 8741

paths:
  workspace: "./workspace"
  data: "./data"
  ui_dist: "./hypermarrow-ui/dist"

agents:
  heartbeat_interval: 30          # 秒
  stale_timeout: 60               # 秒
  process_detection:              # 进程检测（跨平台）
    openclaw:
      windows: "QClaw.exe"
      linux: "openclaw"
      darwin: "QClaw"

license:
  enabled: false                  # false = 社区版（全功能）
  server_url: "https://license.openclaw.ai"
  public_key_path: "./license_key.pub"
  verify_interval: 86400          # 24h
  offline_days: 7

learning:
  consolidation_interval: 20      # 每 N 条 record 触发巩固
  transfer_threshold: 10         # 跨 Agent 共享阈值
  dream_cycle_interval_hours: 6
  batch_learn_size: 32

features:                         # 社区版默认全开
  working_memory: true
  episodic_memory: true
  procedural_memory: true
  knowledge_graph: true
  vector_memory: true
  q_learning: true
  metacognition: true
  prospective_memory: true
  world_model: true
  cross_agent_transfer: true
```

### 1.2 重写 `memory_core/config.py`

```python
# 从 config.yaml 读取，环境变量覆盖，保持向后兼容
import yaml
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

_config = None
def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config
```

### 1.3 修复 `packaging/build_all.py`

```python
# commercial/packaging/build_hypermarrow.py — 正确的打包入口
# 打包 HyperMarrow API server + LICENSE_SDK + UI static files

python -m nuitka --standalone --onefile \
    --include-package=memory_core,memory_integration,memory_api \
    --include-package=learning_core,learning_integration \
    --include-package=LICENSE_SDK \
    --include-data-dir=../hypermarrow-ui/dist=hypermarrow-ui/dist \
    --include-data-dir=../data=data \
    --include-data-file=../config.yaml=config.yaml \
    --output-dir=./dist \
    --output-filename=hypermarrow-server \
    start_server.py
```

### 1.4 交付物

| 文件 | 状态 |
|------|------|
| `HyperMarrow/config.yaml` | 新增 |
| `HyperMarrow/memory_core/config.py` | 重写 |
| `commercial/packaging/build_hypermarrow.py` | 重写 |
| `commercial/packaging/build_installer.py` | 新增（NSIS 安装包） |

---

## Phase 2：商业化落地（License 集成 + 功能开关）

**解决的问题：**
- commercial 断层 2（功能开关未接入）
- commercial 断层 3（两套心跳未统一）
- commercial 断层 4（Agent 注册无设备限制）

### 2.1 `server.py` 接入 License Feature Gate

```python
# server.py _init() — 按 license 控制子系统
def _init():
    global _DC, _REG, _CLAUDE_DC
    if _DC is not None:
        return

    config = get_config()
    features = config.get("features", {})

    # 商业化模式：从 license 文件读取功能开关
    if config.get("license", {}).get("enabled", False):
        from LICENSE_SDK.license_manager import LicenseManager
        lm = LicenseManager()
        if lm.verify().is_valid():
            licensed = set(lm.get_features())
            for key in features:
                if key not in licensed and "*" not in licensed:
                    features[key] = False
        else:
            # License 无效 → 仅基础功能
            features = {k: False for k in features}
            features["working_memory"] = True
            features["episodic_memory"] = True
            features["procedural_memory"] = True
            features["knowledge_graph"] = True

    # 按 feature flags 初始化子系统
    _DC = create_for_agent("openclaw",
        enable_vector_db=features.get("vector_memory", True),
        enable_rl=features.get("q_learning", True),
        enable_metacognition=features.get("metacognition", True),
        enable_world_model=features.get("world_model", True),
    )
    # ...
```

### 2.2 统一心跳

将 License 在线验证嵌入 HyperMarrow 的 agent heartbeat：

```python
# server.py agent_heartbeat — 融合 license 验证
@app.post("/api/v1/agents/{agent_id}/heartbeat")
def agent_heartbeat(agent_id: str):
    _init()
    # ... 现有心跳逻辑 ...

    # 附带 license 状态（如已启用商业化模式）
    config = get_config()
    if config.get("license", {}).get("enabled", False):
        from LICENSE_SDK.license_manager import LicenseManager, LicenseStatus
        lm = LicenseManager()
        license_ok = lm.verify() in (LicenseStatus.VALID, LicenseStatus.OFFLINE)
        if not license_ok:
            # License 失效 → 降级功能
            _disable_pro_features()

    return {"status": "ok", "agent": agent_id, "alive": True}
```

### 2.3 Agent 注册接入设备限制

```python
# agent_registry.py register() — 检查 license 设备数
def register(self, agent_id: str, action_space: list, ...):
    config = get_config()
    if config.get("license", {}).get("enabled", False):
        from LICENSE_SDK.license_manager import LicenseManager
        lm = LicenseManager()
        max_devices = lm.get_max_devices()
        if max_devices > 0:
            current = len(self._agents)
            if current >= max_devices:
                raise RuntimeError(
                    f"License 设备数已达上限 ({max_devices})"
                )
    # ... 正常注册逻辑 ...
```

### 2.4 交付物

| 文件 | 改动 |
|------|------|
| `server.py` `_init()` | 新增 License feature gate |
| `server.py` `agent_heartbeat()` | 融合 License 验证 |
| `memory_core/agent_registry.py` `register()` | 新增设备数检查 |
| `memory_core/decision_check.py` `create_for_agent()` | 新增子系统开关参数 |

---

## Phase 3：开放 API（Agent 自助接入 + SDK 独立化）

**解决的问题：**
- HyperMarrow P0（agent_connect 硬编码 → 注册表查找）
- HyperMarrow P0（新增 HTTP API: intercept/check/record）
- HyperMarrow P1（提取 SDK 为独立 pip 包）

### 3.1 `agent_connect/heartbeat/disconnect` 通用化

```python
# server.py — 从硬编码改为注册表查找
@app.post("/api/v1/agents/{agent_id}/connect")
def agent_connect(agent_id: str, request: Request = None):
    _init()
    bundle = _REG.get(agent_id)
    if not bundle:
        # 自动注册新 Agent
        action_space = None
        if request:
            body = await request.json()
            action_space = body.get("action_space")
        bundle = create_for_agent(agent_id, action_space=action_space)

    dc = bundle.decision_checkpoint
    dc._api_session_active = True
    dc._last_heartbeat = datetime.now().isoformat()
    return {"status": "ok", "agent": agent_id, "connected": True}
```

### 3.2 新增 HTTP API：intercept / check / record

```python
# server.py — 新增 3 个 Agent 操作 API

@app.post("/api/v1/agents/{agent_id}/intercept")
def agent_intercept(agent_id: str, body: dict):
    """Agent 发送对话消息 → 服务器端执行记忆拦截"""
    _init()
    bundle = _REG.get(agent_id)
    if not bundle:
        bundle = create_for_agent(agent_id)
    dc = bundle.decision_checkpoint

    from memory_integration.interceptor import hypermarow_intercept
    result = hypermarow_intercept(
        body["user_message"],
        body.get("agent_response", ""),
        blocking=True
    )
    return {"status": "ok", **result}

@app.post("/api/v1/agents/{agent_id}/check")
def agent_check(agent_id: str, body: dict):
    """Agent 决策前检查"""
    # ... 类似结构，调用 dc.check() ...

@app.post("/api/v1/agents/{agent_id}/record")
def agent_record(agent_id: str, body: dict):
    """Agent 决策后记录"""
    # ... 类似结构，调用 dc.record() ...
```

### 3.3 提取 `hypermarrow-sdk` 为独立 pip 包

```
hypermarrow-sdk/                    # pip install hypermarrow-sdk
├── setup.py
├── hypermarrow/
│   ├── __init__.py
│   ├── wire.py                     # 原 openclaw_wire.py，通用化
│   ├── client.py                   # HTTP API 客户端（非 Python Agent 用）
│   └── heartbeat.py               # 心跳线程
└── README.md
```

Agent 开发者接入：
```python
# Python Agent — 本地嵌入模式
from hypermarrow import HyperMarrowWire
hm = HyperMarrowWire(agent_id="my-agent", server="http://localhost:8741")

# 非 Python Agent — HTTP API 模式
curl -X POST http://localhost:8741/api/v1/agents/my-agent/intercept \
  -H "Content-Type: application/json" \
  -d '{"user_message": "...", "agent_response": "..."}'
```

### 3.4 交付物

| 文件 | 改动 |
|------|------|
| `server.py` `agent_connect/heartbeat/disconnect` | 重写为注册表驱动 |
| `server.py` | 新增 `/intercept`, `/check`, `/record` 端点 |
| `hypermarrow-sdk/` | 新建独立 pip 包 |
| `openclaw_wire.py` | 重构为 SDK 的别名（向后兼容） |

---

## Phase 4：生产加固（安全 + 定时任务 + UI 补齐）

**解决的问题：**
- HyperMarrow P2（API 认证）
- HyperMarrow P2（定时 Dream Cycle）
- HyperMarrow P1（跨平台进程检测）
- commercial 断层 6（Web UI License 面板）

### 4.1 API 认证

```python
# server.py — Token 认证中间件
from fastapi import Header, HTTPException

def verify_api_token(authorization: str = Header(None)):
    config = get_config()
    required_token = config.get("server", {}).get("api_token")
    if not required_token:
        return  # 未配置 token，跳过认证

    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != required_token:
        raise HTTPException(403, "Invalid API token")

# 应用到所有 /api/v1/agents/* 端点
```

### 4.2 定时 Dream Cycle

```python
# server.py startup — 添加定时巩固线程
def _dream_scheduler():
    import time
    config = get_config()
    interval_hours = config.get("learning", {}).get("dream_cycle_interval_hours", 6)
    while True:
        time.sleep(interval_hours * 3600)
        try:
            _init()
            _DC.consolidator.dream_cycle(force=True)
            print(f"[Dream Scheduler] Cycle completed", file=sys.stderr)
        except Exception as e:
            print(f"[Dream Scheduler] Failed: {e}", file=sys.stderr)

threading.Thread(target=_dream_scheduler, daemon=True, name="dream_scheduler").start()
```

### 4.3 跨平台进程检测

```python
# server.py — 从 config.yaml 读取各平台进程名
def _is_agent_host_running(agent_id: str) -> bool:
    config = get_config()
    proc_config = config.get("agents", {}).get("process_detection", {}).get(agent_id, {})
    proc_name = proc_config.get(sys.platform)
    if not proc_name:
        return False

    if sys.platform == "win32":
        result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {proc_name}"],
                                capture_output=True, text=True)
        return proc_name in result.stdout
    else:
        result = subprocess.run(["pgrep", "-f", proc_name], capture_output=True)
        return result.returncode == 0
```

### 4.4 Web UI License 面板

```jsx
// hypermarrow-ui/src/pages/License.tsx — 新增页面
export default function LicensePage() {
  const [license, setLicense] = useState(null)

  useEffect(() => {
    fetch('/api/v1/license/status').then(r => r.json()).then(setLicense)
  }, [])

  return (
    <div className="license-panel">
      <StatusBadge status={license?.status} />
      <InfoRow label="计划" value={license?.plan} />
      <InfoRow label="到期" value={license?.expiry} />
      <InfoRow label="设备" value={`${license?.devices_used}/${license?.max_devices}`} />
      <FeatureList features={license?.features} />
    </div>
  )
}
```

### 4.5 交付物

| 文件 | 改动 |
|------|------|
| `server.py` | 新增 Token 认证中间件 |
| `server.py` `startup()` | 新增定时 Dream Cycle |
| `server.py` | 跨平台进程检测 |
| `hypermarrow-ui/src/pages/License.tsx` | 新增 License 状态页 |
| `hypermarrow-ui/src/App.tsx` | 添加 License Tab |

---

## 完整依赖图

```
Phase 1 (地基)
├── config.yaml ─────────────────────────────────────────────┐
├── config.py 重写 ──────────────────────────────────────┐   │
├── build_hypermarrow.py ────────────────────────────┐   │   │
│                                                     │   │   │
Phase 2 (商业化)                                       │   │   │
├── server.py feature gate ─── depends on: config ────┼───┼───┤
├── 统一心跳 ───────────────── depends on: config ────┼───┼───┤
├── 设备限制 ───────────────── depends on: config ────┼───┤   │
│                                                     │   │   │
Phase 3 (开放)                                         │   │   │
├── agent_connect 通用化 ───── depends on: Phase 2 ───┼───┼───┤
├── HTTP intercept/check/record ──────────────────────┼───┼───┤
├── hypermarrow-sdk pip ─────── depends on: Phase 3.1 ┘   │   │
│                                                         │   │
Phase 4 (加固)                                             │   │
├── API 认证 ─────────────────── depends on: Phase 3 ─────┼───┤
├── 定时 Dream Cycle ──────────── depends on: config ─────┼───┤
├── 跨平台进程检测 ────────────── depends on: config ─────┤   │
└── UI License 面板 ───────────── depends on: Phase 2 ────┘   │
                                                             │
                         全部依赖 Phase 1 ────────────────────┘
```

---

## 工作量估算

| Phase | 内容 | 改动文件 | 预估 |
|-------|------|---------|------|
| 1 | config + build + 路径统一 | 3 新增 + 2 重写 | 中 |
| 2 | License 集成 + 功能开关 | 4 修改 | 中 |
| 3 | API 通用化 + SDK 独立 | 2 重写 + 3 新增 | 大 |
| 4 | 安全 + 定时 + UI 面板 | 4 修改 + 1 新增 | 小 |

**建议从 Phase 1 开始**，按依赖顺序逐 Phase 推进。Phase 1 完成后，后续所有改动都有统一的配置基座。
