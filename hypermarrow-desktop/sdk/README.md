# HyperMarrow Client SDK

Lightweight Python SDK for the HyperMarrow AI memory & learning system.  
Zero dependencies — uses only Python stdlib.

## Install

```bash
pip install hypermarrow-client
```

## Usage

```python
from hypermarrow import hm

# Archive conversation
hm.intercept("user message", "agent response")

# Query memory before decisions
result = hm.check("action_name", task="current task")

# Record outcome for learning
hm.record("action_name", outcome="success")

# Search historical memory
hm.search("keyword", limit=5)

# System statistics
hm.stats()
```

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `HM_AGENT_ID` | `claude` | Agent identifier |
| `HM_API_URL` | `http://localhost:8741` | API server URL |
