# HyperMarrow SDK 智商藏不住 Agent SDK

Agent 集成开发包，提供两种接入模式：

## 1. 本地嵌入模式（Python Agent）

```python
from hypermarrow import HyperMarrowWire

hm = HyperMarrowWire(
    agent_id="my-agent",
    server="http://localhost:8741",
    hypermarrow_path="D:/OpenClaw/workspace/HyperMarrow",
)

hm.intercept("用户消息", "Agent回复")   # 每条消息后
result = hm.check("try_fix_three_times", task="下载失败")  # 决策前
hm.record("try_fix_three_times", {"task": "下载"}, "success")  # 决策后（异步）
```

## 2. HTTP Client 模式（任意语言）

```python
from hypermarrow import HyperMarrowClient

client = HyperMarrowClient(agent_id="go-agent", server="http://localhost:8741")
client.connect()  # 自助注册
client.intercept("user msg", "response")
client.check("try_fix", {"task": "download"})
client.record("try_fix", {"task": "download"}, "success", 0.8)
```

详见主项目 README.md。
