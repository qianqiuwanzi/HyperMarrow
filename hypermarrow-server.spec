# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['start_server.py'],
    pathex=['D:\\OpenClaw\\workspace\\commercial'],
    binaries=[],
    datas=[('config.yaml', '.'), ('openclaw-memory-system/data', 'openclaw-memory-system/data'), ('hypermarrow-ui/dist', 'hypermarrow-ui/dist')],
    hiddenimports=['LICENSE_SDK', 'LICENSE_SDK.config', 'LICENSE_SDK.license_manager', 'LICENSE_SDK.fingerprint', 'LICENSE_SDK.crypto_utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'PIL', 'cv2', 'numba', 'llvmlite', 'soundfile', 'sounddevice', 'imageio', 'imageio_ffmpeg', 'gradio', 'sympy', 'altair', 'av', 'diffusers', 'yt_dlp', 'timm', 'tensorflow'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='hypermarrow-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
