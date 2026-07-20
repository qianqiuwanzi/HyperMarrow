# 记忆 API 部署方案报告

## 一、当前安装包源码暴露情况

### 已保护（在 app.asar 内，不可直接读取）

| 内容 | 说明 |
|------|------|
| `dist/main/*.js` | Electron 主进程，TypeScript 编译产物 |
| `dist/preload/*.js` | Preload 桥接，TypeScript 编译产物 |
| `src/renderer/` | 前端 HTML/CSS/JS（可混淆压缩） |
| `node_modules/` | 第三方依赖（二进制/混淆） |

### 已暴露（在 resources/ 目录，可直接阅读）

| 目录/文件 | 文件数 | 暴露内容 |
|-----------|--------|---------|
| `openclaw-memory-system/` | 33 .py + 数据 | 全部记忆系统源码 |
| `openclaw-learning-system/` | 12 .py | 全部学习系统源码 |
| `start.py` | 1 | 启动脚本 |
| `stop.py` | 1 | 停止脚本 |
| `config.yaml` | 1 | 系统配置 |

**暴露总量：45 个 .py 文件，18 个 .json 数据文件，共 114 个文件。**

其中包括：
- 7 大记忆模块核心算法（情景记忆、知识图谱、程序记忆、工作记忆、向量记忆、元认知、巩固器）
- 7 大学习模块核心算法（Q-Learning、World Model、Meta Learner、Transfer Learner 等）
- SDK 集成代码（拦截器、决策检查点）
- CLI 和 HTTP 桥接代码
- 全部配置文件和数据文件

## 二、推荐的解决方案

### 方案：PyInstaller 编译为单一可执行文件

将整个 Python 记忆 API 编译为一个独立的 `.exe` 文件，客户无法反编译出可读源码。

**技术选型：**

```
Python 源码 (.py)  →  PyInstaller  →  dist/hypermarrow-api.exe
```

**优点：**
- 单一 `.exe` 文件，无源码泄露
- 无需客户安装 Python 环境
- 启动速度与 Python 解释器版本一致
- 成熟稳定，社区广泛使用

**缺点：**
- 打包后体积较大（约 300-500MB，包含 Python + 依赖）
- 首次编译耗时长（约 5-10 分钟）
- 每次更新 API 需要重新编译

**实施步骤：**

1. **安装 PyInstaller**
```bash
pip install pyinstaller
```

2. **创建 spec 文件** `hypermarrow-api.spec`
```python
# -*- mode: python -*-
a = Analysis(
    ['start.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('openclaw-memory-system/', 'openclaw-memory-system/'),
        ('openclaw-learning-system/', 'openclaw-learning-system/'),
    ],
    hiddenimports=[
        'uvicorn', 'fastapi', 'chromadb', 'sentence_transformers',
        'numpy', 'torch', 'memory_core', 'memory_api',
        'memory_integration', 'learning_core', 'learning_integration',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='hypermarrow-api',
    debug=False,
    strip=True,
    upx=True,
    console=False,
)
```

3. **构建**
```bash
pyinstaller hypermarrow-api.spec
```

4. **集成到 Electron 安装包**
```yaml
# electron-builder.yml
extraResources:
  - from: ../dist/hypermarrow-api.exe
    to: hypermarrow-api.exe
```

5. **Electron 主进程启动方式改为**
```typescript
apiProcess = spawn(path.join(process.resourcesPath, 'hypermarrow-api.exe'), 
    ['--port', '8741'], { cwd: process.resourcesPath });
```

### 备选方案：Nuitka 编译

Nuitka 将 Python 编译为 C 再编译为机器码，安全级别更高但编译时间很长（30 分钟+）且依赖复杂。

## 三、推荐实施计划

| 阶段 | 任务 | 时间 |
|------|------|------|
| 1 | PyInstaller 编译 hypermarrow-api.exe | 1 天 |
| 2 | 更新 electron-builder 配置 | 0.5 天 |
| 3 | 更新主进程启动逻辑 | 0.5 天 |
| 4 | 测试完整安装流程 | 0.5 天 |
| 5 | 打包上传 | 0.5 天 |
| **总计** | | **3 天** |
