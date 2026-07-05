# OpenHuman 值得学的 2 点 — 是否应该在 HyperMarrow 中实现？

**日期**：2026-07-05
**判决**：两项都不需要。理由如下。

---

## 一、Memory Tree 的人类可读性 → 不需要

### OpenHuman 做了什么
记忆存为 Markdown 树在 SQLite 中，镜像为 Obsidian vault，用户可以直接打开编辑。

### 为什么 HyperMarrow 不需要

| 原因 | 说明 |
|------|------|
| **定位不同** | OpenHuman 是桌面应用，用户是普通人。HyperMarrow 是 Python 库，用户是开发者。开发者不需要 Obsidian——他们需要 `hypermarrow stats` 和 `kg central`。 |
| **已有方案** | `hypermarrow export --format markdown` 已经可以导出可读摘要。再加就是过度设计。 |
| **JSON 更适合 ML** | Q 表 (100×7 float)、KG 实体关系、神经嵌入——这些数据 Markdown 无法表达。JSON 是正确选择。 |
| **GBrain 的反例** | GBrain 确实用 Markdown 文件，但 GBrain 没有 RL、没有 KG、没有嵌入。当数据结构复杂到一定程度，Markdown 就装不下了。 |

### 判决

**不做。** `export --md` 已经覆盖了"人类可读"的需求。把 14 个 JSON 文件全改成 Markdown 是架构失控。

---

## 二、TokenJuice 的压缩思维 → 不需要

### OpenHuman 做了什么
工具输出进入模型前压缩 80% Token。同一信息量，少花钱。

### 为什么 HyperMarrow 不需要

| 原因 | 说明 |
|------|------|
| **层不同** | Token 压缩是 **Agent/API 层**的事——模型输入管理。HyperMarrow 是**记忆存储层**——存什么、怎么检索。两层职责不同。 |
| **已有方案** | Interceptor 已经做了：消息存档前截断到 200 字符，`record()` 有 `async_mode` 减少阻塞。这已经够用了。 |
| **OpenHuman 自己也有问题** | TokenJuice 是"治标"——压缩输出让它更便宜，但不解决"为什么要在上下文里塞这么多东西"。HyperMarrow 的 AttentionGate + WorkingMemory 激进修剪是"治本"——只保留相关的。 |
| **用户反馈的真实含义** | 用户说"记忆消耗 Token 浪费"——意思是**不该进记忆的东西进了记忆**。这是检索精准度的问题，不是压缩的问题。P0-2 (lookup_path) 和 P0-3 (相关性排序) 才是正确的解法。 |

### 判决

**不做。** Interceptor 的 200 字截断 + WorkingMemory 的激进修剪已经覆盖。TokenJuice 是 HTTP 响应压缩，HyperMarrow 做的是"不存垃圾"——后者更根本。

---

## 三、真正的启示

OpenHuman 最值得学的不是具体功能，而是两个设计原则——HyperMarrow 已经做到了：

| OpenHuman 原则 | HyperMarrow 对应 |
|---------------|-----------------|
| **"不是向量黑盒"** — 用户应该能看到记忆里有什么 | `hypermarrow stats/search/export` + `lookup_path` |
| **"Thinking continues after you stop typing"** — 潜意识 | DreamCycle 睡眠调度器 + Interceptor 非阻塞捕获 |

---

## 四、一句话总结

> OpenHuman 是给普通人的桌面应用，HyperMarrow 是给开发者的认知引擎。TokenJuice 是 API 层的事，Markdown 存储是简单数据的格式。**把一个 Python 库包装成 Obsidian 插件，把一个记忆引擎降级成 Token 压缩器——都是错位。**
