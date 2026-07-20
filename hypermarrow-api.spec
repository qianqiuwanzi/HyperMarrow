# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for HyperMarrow memory API server (one-directory mode)."""

from PyInstaller.building.api import EXE, COLLECT

_HERE = SPECPATH = os.path.dirname(SPEC)

# ── Collect data files ─────────────────────────────────────────────
datas = [
    ('config.yaml', '.'),
    ('openclaw-memory-system/data', 'openclaw-memory-system/data'),
]

# ── Hidden imports ─────────────────────────────────────────────────
hiddenimports = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'fastapi', 'starlette', 'pydantic',
    'chromadb', 'chromadb.config', 'chromadb.db',
    'sentence_transformers', 'sentence_transformers.models',
    'transformers', 'transformers.models',
    'numpy', 'numpy.core', 'numpy.linalg',
    'torch', 'torch.nn', 'torch.optim',
    'memory_core', 'memory_core.config', 'memory_core.knowledge_graph',
    'memory_core.episodic_memory_db', 'memory_core.working_memory_db',
    'memory_core.vector_memory_db', 'memory_core.procedural_memory',
    'memory_core.memory_consolidator', 'memory_core.metacognition_monitor',
    'memory_core.agent_registry', 'memory_core.meta_learner',
    'memory_api', 'memory_api.server', 'memory_api.user_auth',
    'memory_integration', 'memory_integration.decision_check',
    'memory_integration.interceptor',
    'learning_core', 'learning_core.config', 'learning_core.q_learning_agent',
    'learning_core.meta_learner',
    'learning_integration', 'learning_integration.decision_check',
]

a = Analysis(
    ['start.py'],
    pathex=[_HERE, os.path.join(_HERE, 'openclaw-memory-system'), os.path.join(_HERE, 'openclaw-learning-system')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'PIL', 'cv2', 'numba', 'llvmlite',
        'soundfile', 'sounddevice', 'imageio', 'imageio_ffmpeg',
        'gradio', 'sympy', 'altair', 'av', 'diffusers',
        'yt_dlp', 'timm', 'tensorflow',
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'wx', 'traitlets', 'ipykernel', 'jupyter',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hypermarrow-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='hypermarrow-api',
)
