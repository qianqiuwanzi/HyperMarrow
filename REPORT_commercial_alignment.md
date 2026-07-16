# HyperMarrow 商业化架构对齐报告

> 2026-07-08 | commercial/ 设计 vs HyperMarrow 源码 — 差距分析与同步方案

---

## 一、总体评估：架构方向正确，但断层明显

商业方案的设计思路是对的——License SDK → 授权服务器 → 打包分发 → 销售。但与 HyperMarrow 源码之间存在 **6 个关键断层**，若不修复，商业化项目无法直接对接 HyperMarrow。

### 架构对比

```
商业化设计文档中的结构:           实际 HyperMarrow 源码结构:
commercial/                      HyperMarrow/
├── LICENSE_SDK/    ✅ 已实现     ├── openclaw-memory-system/   ← 记忆系统
├── license_server/ ✅ 已实现     ├── openclaw-learning-system/ ← 学习系统
├── packaging/      ✅ 已实现     ├── hypermarrow-ui/           ← Web UI
├── sales/          ✅ 已实现     ├── openclaw_wire.py          ← Agent 集成
├── memory-system/  ❌ 不存在     ├── start.py / stop.py        ← 启停
└── learning-system/ ❌ 不存在    └── server.py (memory_api/)   ← API
```

**商业化设计假设的 `memory-system/` 和 `learning-system/` 目录在 commercial 项目中并不存在**——它们指向的是 HyperMarrow 源码。但打包脚本 (`build_all.py`) 试图打包一个不存在的结构。

---

## 二、六大断层详解

### 断层 1：打包入口与 HyperMarrow 不匹配

**设计：** Nuitka 编译 `memory-system/__main__.py` → 单文件 `.exe`
**实际：** HyperMarrow 是 FastAPI 服务器 + React SPA，入口是 `start_server.py`/`start.py`

**后果：** 打包脚本运行时找不到源码，编译失败。

**修复方向：**
```python
# packaging/build_hypermarrow.py  — 正确的打包入口
# 打包 HyperMarrow API server
python -m nuitka --standalone --onefile \
    --include-package=memory_core,memory_integration,memory_api \
    --include-package=learning_core,learning_integration \
    --include-data-dir=../hypermarrow-ui/dist=static \
    start_server.py
```

### 断层 2：License 功能开关未接入 HyperMarrow

**设计：** SDK Config 定义了功能分级：
```python
DEFAULT_FEATURES  = ["basic_memory", "semantic_search", "importance_marking", "procedural_memory"]
PRO_FEATURES      = [... + "rl_decision", "meta_cognition", "prospective_memory", ...]
ENTERPRISE_FEATURES = ["*"]
```

**实际：** HyperMarrow 的 7+7 个子系统全量启用，**没有任何功能开关**。`server.py` 启动时无条件初始化所有模块。

**后果：** Free 版用户也能使用 Pro 功能。商业化无法落地。

**修复方向：** 在 `server.py` `_init()` 中加入 feature gate：
```python
# server.py — 接入 License 功能控制
from license_sdk import LicenseManager
_lm = LicenseManager()

ENABLED_SUBSYSTEMS = {
    "vector_memory":     "semantic_search" in _lm.get_features(),
    "rl_decision":       "rl_decision" in _lm.get_features(),
    "meta_cognition":    "meta_cognition" in _lm.get_features(),
    "prospective_memory": "prospective_memory" in _lm.get_features(),
    "world_model":       "advanced_planning" in _lm.get_features(),
}
```

### 断层 3：两套心跳系统未统一

| | HyperMarrow 心跳 | License 心跳 |
|---|---|---|
| 端口 | 8741 | 8000 |
| 用途 | Agent 连接状态 | License 在线验证 |
| 间隔 | 30s | 3600s |
| 端点 | `/api/v1/agents/{id}/heartbeat` | `/api/v1/heartbeat` |

**后果：** 两个独立的心跳周期不协调。License 过期后 HyperMarrow 不会自动响应。

**修复方向：** 统一心跳端点。HyperMarrow 的 agent heartbeat 应携带 license 状态：
```python
# server.py agent_heartbeat — 融合 license 验证
@app.post("/api/v1/agents/{agent_id}/heartbeat")
def agent_heartbeat(agent_id: str):
    # ... 更新连接状态 ...
    # 附带 license 状态检查
    license_valid = LicenseManager().verify() == LicenseStatus.VALID
    return {"status": "ok", "agent": agent_id, "alive": True,
            "license_valid": license_valid}
```

### 断层 4：Agent 注册与 License 计费未对齐

**设计：** License 限制 `max_devices`（最大安装数），每个设备绑定一个硬件指纹。
**实际：** HyperMarrow 的 Agent 注册 (`AgentRegistry`) 按 Agent ID 计数，无设备限制。

**后果：** 一个 License 可以在无限设备上注册无限 Agent。无法实现"Pro 版 3 台设备"的定价逻辑。

**修复方向：** Agent 注册时同步检查 License 设备数：
```python
# agent_registry.py register() — 接入设备限制
def register(self, agent_id: str, action_space: list, ...):
    lm = LicenseManager()
    if lm.get_max_devices() > 0:
        current = len(self.list_agents())
        if current >= lm.get_max_devices():
            raise LicenseLimitExceeded(
                f"License allows {lm.get_max_devices()} agents, "
                f"currently have {current}"
            )
    ...
```

### 断层 5：数据目录和 License 文件路径不一致

| 文件 | 商业化设计路径 | HyperMarrow 实际路径 |
|------|--------------|-------------------|
| 数据目录 | 未明确定义 | `workspace/HyperMarrow/openclaw-memory-system/data/` |
| License 文件 | `APPDATA/openclaw-memory/license.json` | 不存在 |
| 配置文件 | 无 | `memory_core/config.py` 硬编码 |

**修复方向：** 统一数据目录，添加 `config.yaml` 驱动：
```yaml
# config.yaml
paths:
  data: "./data"
  license: "./license.json"
server:
  port: 8741
license:
  server_url: "https://license.openclaw.ai"
  verify_interval: 86400
```

### 断层 6：商业设计缺少 Web UI 和 API 文档

**设计：** 聚焦于 SDK + License Server + 打包，未考虑 Web 仪表盘。
**实际：** HyperMarrow 有完整的 React SPA（6 面板可视化）和 Swagger API 文档。

**修复方向：** 商业化版本中，Web UI 应包含 License 状态面板：
```
仪表盘新增 Tab: "License"
├── 授权状态 (有效/过期/未激活)
├── 计划 (Free/Pro/Enterprise)
├── 剩余天数
├── 设备数 (已用/最大)
└── 功能清单 (已启用/未启用)
```

---

## 三、同步方案

### 3.1 目录结构（对齐后）

```
HyperMarrow/                          # 统一项目根
├── openclaw-memory-system/          # 记忆系统（源码）
├── openclaw-learning-system/        # 学习系统（源码）
├── hypermarrow-ui/                  # Web UI（源码）
├── openclaw_wire.py                 # Agent SDK（源码）
├── start.py / stop.py              # 启停脚本
│
├── commercial/                      # 商业化工具（与源码平级）
│   ├── LICENSE_SDK/                 # License 验证（嵌入产品）
│   ├── license_server/              # 授权服务器（独立部署）
│   ├── packaging/
│   │   ├── build_hypermarrow.py     # ← 修复：正确的打包入口
│   │   └── build_installer.py      # ← 新增：安装包制作
│   ├── sales/                       # 销售材料
│   └── config.yaml                  # ← 新增：统一配置
│
└── dist/                            # 构建输出
    ├── hypermarrow-server.exe       # Nuitka 编译
    └── hypermarrow-installer.exe    # NSIS/InnoSetup 安装包
```

### 3.2 改动优先级

| 优先级 | 断层 | 改动 | 影响范围 |
|--------|------|------|---------|
| **P0** | 1 | 重写 `packaging/build_all.py`，对接 `start_server.py` | 打包 |
| **P0** | 2 | `server.py` 接入 License feature gate | 功能开关 |
| **P1** | 5 | 新增 `config.yaml`，统一路径和端口配置 | 配置 |
| **P1** | 3 | 融合 HyperMarrow heartbeat 和 License heartbeat | 心跳 |
| **P2** | 4 | Agent 注册接入设备数限制 | 计费 |
| **P2** | 6 | Web UI 新增 License 状态面板 | 前端 |

### 3.3 安装包最终形态

用户购买后的体验：

```
1. 下载 hypermarrow-installer.exe (~50MB)
2. 双击安装 → 选择目录 → 完成
3. 桌面出现 "智商藏不住" 快捷方式
4. 双击启动 → 右下角系统托盘出现图标
5. 首次启动弹出激活窗口：
   ┌─────────────────────────────────┐
   │  智商藏不住 — 激活        │
   │                                 │
   │  License Key: [_______________] │
   │  硬件指纹:    a972da284c20...   │
   │                                 │
   │  [在线激活]  [离线导入]         │
   │                                 │
   │  没有 License? [购买 Pro →]    │
   └─────────────────────────────────┘
6. 激活成功 → 浏览器自动打开 http://localhost:8741
7. 系统托盘常驻，右键菜单：打开/状态/关于/退出
```

### 3.4 定价方案与 HyperMarrow 功能映射

| 功能 | Free | Pro (¥99/月) | Enterprise |
|------|:---:|:---:|:---:|
| 工作记忆 (WM) | ✅ | ✅ | ✅ |
| 情景记忆 (EM) | 1000条 | 无限 | 无限 |
| 程序性记忆 (PM) | ✅ | ✅ | ✅ |
| 知识图谱 (KG) | ✅ | ✅ | ✅ |
| 向量搜索 (VecDB) | ❌ | ✅ | ✅ |
| Q-Learning 决策 | ❌ | ✅ | ✅ |
| 元认知 (Meta) | ❌ | ✅ | ✅ |
| 前瞻记忆 (Prospective) | ❌ | ✅ | ✅ |
| World Model 规划 | ❌ | ❌ | ✅ |
| 跨 Agent 迁移 | ❌ | ❌ | ✅ |
| Agent 数量 | 1 | 3 | 无限 |
| Web 仪表盘 | 基础 | 完整 | 完整 |
| API 文档 | ✅ | ✅ | ✅ |
| 技术支持 | 社区 | 邮件 24h | 专属 1h |
| 私有化部署 | ❌ | ❌ | ✅ |
