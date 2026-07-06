# HyperMarrow 藏慧 — 类人记忆与学习系统

> HyperMarrow = Hyper + Memory Brain — 超记忆之脑

`openclaw-memory-system` — 可独立安装的 Python 包，实现类人认知能力：
三层记忆 × 知识图谱 × 强化学习 × 元认知 × 多 Agent 支持 × Web 可视化

---

## 本机 QClaw / OpenClaw 接入方式（当前实例）

> 本机（即运行这份文档的 OpenClaw Agent）采用**一线接线**方式：只需在 `SOUL.md` 中 `import` 一个文件，并在对话生命周期里调用三个钩子函数，无需 MCP、无需额外进程。

### 接线原理

```
SOUL.md ──import──> openclaw_wire.hm ──> DecisionCheckPoint(agent="openclaw")
                                    ├─ intercept()  每条消息后自动记
                                    ├─ check()     决策前给建议
                                    └─ record()    决策后回写
```

`openclaw_wire.py` 是官方提供的**单文件接线层**：它在被 `import` 时自动完成初始化（注册 Agent `openclaw`、挂好记忆/学习/知识图谱子系统），并对外只暴露一个全局单例 `hm`，把拦截器、决策检查、记忆记录、巩固全部收敛到这一个对象上。

### 步骤一：在 `SOUL.md` 中注册（已内置）

`SOUL.md` 末尾已加入以下代码，Agent 每次启动即自动加载 HyperMarrow：

```python
import sys
from pathlib import Path

# 添加 HyperMarrow 到 sys.path
_HYPERMARROW = Path(r"D:\\OpenClaw\\workspace\\HyperMarrow")
sys.path.insert(0, str(_HYPERMARROW / "openclaw-memory-system"))
sys.path.insert(0, str(_HYPERMARROW / "openclaw-learning-system"))

from openclaw_wire import hm

# 每条消息后自动触发（后台线程，非阻塞）
def on_message(user_message: str, agent_response: str = ""):
    hm.intercept(user_message, agent_response)

# 决策前检查 → 返回规则命中 / 关联实体 / RL 推荐
def check_action(action: str, **ctx):
    return hm.check(action, **ctx)

# 决策后记录 → 回写情景记忆、更新 Q 表、必要时提炼规则
def record_action(action: str, ctx: dict, outcome: str, reward: float = None):
    hm.record(action, ctx, outcome, reward)
```

### 步骤二：对话中的使用约定

| 时机 | 调用 | 作用 |
|------|------|------|
| 每条消息后 | `on_message(user_msg, agent_reply)` | 自动提取实体→知识图谱、存档→情景记忆、匹配规则→程序性记忆 |
| 决策前 | `check_action("try_fix_three_times", task="下载超时")` | 返回命中的规则、关联实体、相似案例与 RL 推荐动作 |
| 决策后 | `record_action("try_fix_three_times", ctx, "success")` | 把结果写回记忆，更新 Q 表（异步，不阻塞回复） |
| 定期（每晚 23:00） | `hm.dream()` | 触发 12 阶段「睡眠巩固」：批学习经验、提炼规则、校准判断 |

### 步骤三：记忆巩固定时任务

每晚由 OpenClaw 的 cron 任务「HyperMarrow Dream Cycle」自动调用 `hm.dream()`（也可手动执行 `HyperMarrow/scripts/run_dream_cycle.py` 立即触发）。巩固结果写入 `logs/`，可在 Web Dashboard 查看运行历史。

### 验证

```python
from openclaw_wire import hm
print(hm.stats())   # 显示 KG / QL / PM / EM 统计
# 示例输出: KG=3, QL=408/700, PM=15, EM=6
```

---

## Claude 接入 HyperMarrow（最佳实践）

### 方式一：Python 直连（推荐，零配置）

```python
# Claude 会话中直接执行：
import sys
sys.path.insert(0, r"D:\OpenClaw\workspace\HyperMarrow\openclaw-memory-system")
sys.path.insert(0, r"D:\OpenClaw\workspace\HyperMarrow\openclaw-learning-system")

from openclaw_wire import hm

# 每条消息后自动触发（非阻塞）
hm.intercept(user_message, agent_response)

# 决策时调用
result = hm.check("try_fix_three_times", task="下载超时", phase="P2b")
print(result["rl_recommendation"]["recommended_action"])
print(result["lookup_path"])

# 记录结果（默认异步）
hm.record("try_fix_three_times", {"task":"下载"}, "success")
```

### 方式二：MCP Server（外部 Agent 接入）

```json
// .mcp.json 或 claude_desktop_config.json
{
  "mcpServers": {
    "hypermarrow": {
      "command": "python",
      "args": ["D:/OpenClaw/workspace/HyperMarrow/start_server.py"]
    }
  }
}
```

### 方式三：Web Dashboard

```powershell
python D:\OpenClaw\workspace\HyperMarrow\start_server.py   # API :8741
cd D:\OpenClaw\workspace\HyperMarrow\hypermarrow-ui && npm run dev  # UI :5173
```

### 方式四：CLI 命令行

```powershell
python -m memory_cli.hypermarrow stats        # 全系统统计
python -m memory_cli.hypermarrow search "关键词" # 搜索记忆
python -m memory_cli.hypermarrow dream --json  # 触发巩固
python -m memory_cli.hypermarrow export --md   # 导出知识
```

### 已验证的功能（7/7 PASS）

| 功能 | 状态 | 说明 |
|------|:--:|------|
| Agent 创建 | ✅ | openclaw + luci 双 Agent，隔离记忆+共享知识 |
| KnowledgeGraph | ✅ | 33+ 实体，28+ 关系，BFS 查询 |
| Q-Learning | ✅ | 415/700 非零，经验回放，自适应 ε |
| ProceduralMemory | ✅ | 15 条规则，5 级自动化，语义匹配 |
| check()/record() | ✅ | 统一决策编排，lookup_path 追踪 |
| 跨 Agent 迁移 | ✅ | 情景迁移 + Q 表种子化 |
| DreamCycle | ✅ | 9 阶段巩固，JSON 输出 |

---

## 概述

我们搜集了 **182 条来自真实用户的反馈**（GitHub Issues、Reddit 讨论、Twitter 吐槽），覆盖 OpenClaw、Claude Code、Codex、Hermes 四大主流框架。结论很一致：

> **用户最痛的不是"功能不够多"，而是"已有的功能不可见、不可信、不可用"。**

下面是用户吐槽最集中的 6 个问题（按提及次数排序）：

| 排名 | 用户痛点 | 提及次数 | 真实声音 |
|:--:|----------|:--:|----------|
| 1 | **每次对话都像失忆** | 32 | "每次会话都是一张白纸，每次都要重新交代背景" |
| 2 | **压缩一下，记忆就没了** | 17 | "59 次压缩后，我被迫自己搭一套记忆系统" |
| 3 | **子代理读不到父代理的记忆** | 15 | "296 个子代理会话，0 个真正存下了项目记忆" |
| 4 | **明明记了，却不被采用** | 14 | "MEMORY.md 的指令在快速处理时被直接跳过" |
| 5 | **想找的记忆找不到** | 12 | "搜出来的记忆按时间排，不是按相关性排" |
| 6 | **记是记了，但越来越笨重** | 11 | "开记忆后每次回复多等 2-3 秒，token 还被白白吃掉" |

更扎心的是一句总结性吐槽（Reddit，高赞）：

> "这就是个 **key-value 便利贴**，不是记忆。没有衰减、没有权重、没有和当前任务的相关性过滤。"

**市面上的记忆系统，普遍有三个通病：**
- 📝 把记忆当成"堆历史"——只存不学，不会从经验里提炼规律
- 🔲 把记忆当成"平面键值对"——没有结构，搜不到关联
- 💀 把记忆当成"永不删除的档案"——只增不减，越用越臃肿

HyperMarrow 就是为治好这三个通病而生的。

---

## 二、HyperMarrow 能解决什么问题？

### 问题 1：跨会话记忆不连续 → **「情景记忆 + 知识沉淀」**
- 每次对话结束后，关键信息（做了什么、结果如何、学到了什么）自动写入**情景记忆**和**程序性规则库**
- 下次对话开始，相关记忆自动召回，不再"从零开始"
- 子代理创建时可一键**继承父代理的规则与知识**，不再各记各的

### 问题 2：记了却不被采用 → **「记忆优先」决策协议**
- 每次做决策前，系统先走一条 **"规则 → 知识 → 经验 → 相似案例"** 的查找链
- 并显式标注**知识来源路径**（哪条规则命中、哪个经验相似），让 AI 没法"假装没看见"
- 高置信度规则（如"遵循用户指令""使用现有工具"）默认强制执行

### 问题 3：想找的记忆找不到 → **「结构化知识图谱 + 相关性排序」**
- 记忆不是平铺的列表，而是**实体—关系—实体**组成的知识图谱（例如：技能 A「使用」工具 B，「触发」错误类型 C）
- 检索时按 **词频匹配 × 时效衰减 × 重要性权重** 综合排序，而不是简单按时间排
- 同时支持向量语义检索，能找到"意思相近"的历史记忆

### 问题 4：只存不学 → **「强化学习 + 睡眠巩固」完整闭环**
- 用 **Q-Learning** 从每次决策的结果中学习：什么情况下该用哪个动作
- 每晚自动跑一次 **「睡眠巩固」（Dream Cycle）**：批学习经验、提炼新规则、校准置信度
- 越用越聪明，而不是越用越像"复读机"

### 问题 5：记了却越来越臃肿 → **「会遗忘的记忆」**
- 引入**艾宾浩斯遗忘曲线**式的衰减机制：久不使用的记忆自动降级
- 频繁被检索的记忆反而"延长半衰期"，越重要越牢固
- 相似情景自动合并，过期记忆归档，上下文不再膨胀

---

## 三、给用户带来什么？

| 给用户的价值 | 具体体验 |
|--------------|----------|
| 🧠 **省心** | 不用每次重复交代背景，AI 记得你上次说了什么、偏好是什么 |
| 🎯 **靠谱** | 决策有依据、有来源，不会"忘了"你定下的规矩 |
| 📈 **越用越顺手** | 常用操作被固化成规则，重复错误不再犯第二次 |
| 🔍 **找得到** | 要的历史记忆能按相关性精准召回，而不是淹没在时间流里 |
| 🪶 **轻量** | 记忆会自我管理、自动遗忘，不拖慢响应、不浪费 token |
| 🔒 **可控** | 重要记忆可标记"不遗忘"，学习过程可查看、可校准 |

**一句话总结：**

> HyperMarrow 让 AI 从"每次重来的工具"，变成"越处越默契的搭档"——它记得你、学着帮你、还不给你添乱。

---

## 四、和竞品比，HyperMarrow 强在哪？

我们对标了四大主流框架的真实反馈，得出三个**竞品全都不具备、HyperMarrow 独有的壁垒**：

| 竞品通病 | HyperMarrow 的优势 |
|----------|-------------------|
| 📝 记忆 = 平面 KV 存储（Claude Code / ChatGPT / OpenClaw 皆然） | 🕸️ **结构化知识图谱**（实体—关系—实体），唯一具备结构化记忆 |
| 🔁 只存不学（所有竞品） | 🎯 **Q-Learning + 睡眠巩固 + 规则提取**，唯一具备完整学习闭环 |
| 💀 没有遗忘机制（所有竞品） | 🌙 **生物式遗忘曲线 + 情感调制**，唯一具备"会忘"的记忆 |

> 注：上下文压缩丢失、Token 浪费、多设备同步、记忆编辑 UI 等，属于上游（模型层 / 同步层 / 界面层）职责，不在记忆系统范围内——HyperMarrow 专注把"记"和"学"这一件事做到极致。

---

## 五、核心能力一览

| 能力 | 一句话说明 |
|------|-----------|
| 📒 **情景记忆** | 像相册一样记录每次经历：做了什么、结果如何、学到什么 |
| 📝 **程序性记忆** | 像经验笔记一样沉淀规则：什么情况该怎么做，带置信度 |
| 🕸️ **知识图谱** | 像思维导图一样连接实体与关系，支撑关联推理 |
| 🎯 **强化学习** | 像经验值系统一样，从每次成败里学"该选哪条路" |
| 🌙 **睡眠巩固** | 像人睡觉整理记忆一样，夜间批处理经验、提炼规则、校准判断 |
| 🧠 **工作记忆** | 像便签纸一样承载当前任务上下文，用完即清，不膨胀 |

---

## 六、怎么用？（接入方式）

HyperMarrow 以 **OpenClaw Skill** 或 **Python 包** 两种方式接入，集成后会在每次对话自动：
1. **拦截**用户消息 → 自动召回相关记忆、提取知识、给出决策建议
2. **决策前检查** → 返回命中的规则、关联实体、相似案例与 RL 推荐动作
3. **决策后记录** → 把结果写回情景记忆，更新 Q 表，必要时提炼新规则

> 想看形象化的界面设计与原型，见仓库内 `memory_visualization_design.md` 与 `memory_visualization_prototype.html`。

---

## 七、数据来源

本 README 的"用户痛点"与"需求判决"均来自 **182 条真实用户反馈**：
- OpenClaw GitHub Issues：17 条
- Claude Code GitHub Issues：122 条
- Reddit（r/ClaudeAI、r/LocalLLaMA、r/AIAgents）：23 条
- Hermes / Codex Issues + Twitter：20 条

原始数据见 `memory/feedback_*.json`，完整分析见 `REAL_FEEDBACK_RESPONSE.md` 与 `memory/2026-07-05_agent_memory_learning_real_feedback.md`。

---

*HyperMarrow — 让 AI 记得住、学得快、用得对。*
