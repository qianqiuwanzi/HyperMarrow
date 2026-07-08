#!/usr/bin/env python3
"""
HyperMarrow 藏慧 — 统一启动脚本

用法:
  python start.py              # 生产模式：构建 UI + 启动 API (端口 8741)
  python start.py --dev        # 开发模式：启动 API，UI 另用 Vite
  python start.py --port 9000  # 自定义端口
  python start.py --no-build   # 跳过 UI 构建（dist/ 已存在）

生产模式下，访问 http://localhost:8741 即可使用完整系统。
"""

import sys
import os
import socket
import subprocess
import time
import json
import argparse
from pathlib import Path

_HERE = Path(__file__).parent
_UI_DIR = _HERE / "hypermarrow-ui"
_PID_FILE = _HERE / ".hypermarrow.pid"
_DEFAULT_PORT = 8741


# ═══════════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_process_by_port(port: int) -> int | None:
    """Return PID of the process listening on the port, or None."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    return int(parts[-1])
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                return int(result.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill a process by PID. Returns True on success."""
    try:
        if sys.platform == "win32":
            flag = "/F" if force else ""
            subprocess.run(["taskkill", "/PID", str(pid), flag] if flag else ["taskkill", "/PID", str(pid)],
                           shell=True, capture_output=True, timeout=10)
        else:
            sig = "-9" if force else "-TERM"
            subprocess.run(["kill", sig, str(pid)], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def write_pid(pid: int):
    _PID_FILE.write_text(str(pid))


def read_pid() -> int | None:
    if _PID_FILE.exists():
        try:
            return int(_PID_FILE.read_text().strip())
        except Exception:
            pass
    return None


def remove_pid():
    if _PID_FILE.exists():
        _PID_FILE.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
# Build UI
# ═══════════════════════════════════════════════════════════════════════════════

def build_ui() -> bool:
    """Build the React UI into dist/. Returns True on success."""
    if not _UI_DIR.exists():
        print("[Start] UI directory not found, skipping build.")
        return False

    # Check node_modules
    if not (_UI_DIR / "node_modules").exists():
        print("[Start] Installing UI dependencies (npm install)...")
        result = subprocess.run(
            ["npm", "install"], cwd=str(_UI_DIR),
            shell=True, capture_output=False, timeout=120
        )
        if result.returncode != 0:
            print("[Start] ERROR: npm install failed")
            return False

    print("[Start] Building UI (npm run build)...")
    result = subprocess.run(
        ["npm", "run", "build"], cwd=str(_UI_DIR),
        shell=True, capture_output=False, timeout=120
    )
    if result.returncode != 0:
        print("[Start] ERROR: npm run build failed")
        return False

    dist_dir = _UI_DIR / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        print(f"[Start] UI built successfully → {dist_dir}")
        return True
    else:
        print("[Start] ERROR: dist/ not found after build")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Start server
# ═══════════════════════════════════════════════════════════════════════════════

def start_server(port: int, host: str = "0.0.0.0") -> int | None:
    """Start the HyperMarrow API server. Returns PID."""
    sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
    sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

    from memory_api.server import app
    import uvicorn

    server_proc = subprocess.Popen(
        [sys.executable, "-c",
         f"import uvicorn; from memory_api.server import app; "
         f"uvicorn.run(app, host='{host}', port={port}, log_level='info')"],
        cwd=str(_HERE),
        env={**os.environ, "PYTHONPATH": str(_HERE)},
    )
    return server_proc.pid


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="HyperMarrow 藏慧 — 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start.py                  # 生产模式，构建 UI + 启动
  python start.py --dev            # 开发模式，仅 API，UI 用 npm run dev
  python start.py --port 9000      # 自定义端口
  python start.py --no-build       # 跳过构建（dist/ 已就绪）
  python stop.py                   # 停止服务
        """,
    )
    parser.add_argument("--dev", action="store_true",
                        help="开发模式：只启动 API，UI 用 Vite 单独启动")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT,
                        help=f"API 端口（默认 {_DEFAULT_PORT}）")
    parser.add_argument("--host", default="0.0.0.0",
                        help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--no-build", action="store_true",
                        help="跳过 UI 构建")
    parser.add_argument("--stop", action="store_true",
                        help="停止正在运行的服务")

    args = parser.parse_args()

    # ── Stop mode ──────────────────────────────────────────────────────────────
    if args.stop:
        stop_service(args.port)
        return

    # ── Check if already running ───────────────────────────────────────────────
    if is_port_in_use(args.port):
        pid = find_process_by_port(args.port)
        print(f"[Start] Port {args.port} is already in use (PID {pid}).")
        print(f"[Start] HyperMarrow is already running → http://localhost:{args.port}")
        print(f"[Start] To restart:  python stop.py && python start.py")
        sys.exit(1)

    existing_pid = read_pid()
    if existing_pid:
        print(f"[Start] Found stale PID file (PID {existing_pid}). Cleaning up.")
        remove_pid()

    # ── Build UI (production mode) ────────────────────────────────────────────
    ui_url = f"http://localhost:5173 (Vite dev server)"
    if not args.dev and not args.no_build:
        if build_ui():
            ui_url = f"http://localhost:{args.port}"
        else:
            print("[Start] UI build failed. Falling back: start API only.")
            print("[Start] Run 'cd hypermarrow-ui && npm run dev' for UI.")
    elif args.dev:
        print("[Start] Dev mode: UI not served by API. Run 'npm run dev' in hypermarrow-ui/.")

    # ── Start API server ──────────────────────────────────────────────────────
    print(f"[Start] Starting HyperMarrow API on http://{args.host}:{args.port} ...")
    sys.path.insert(0, str(_HERE / "openclaw-memory-system"))
    sys.path.insert(0, str(_HERE / "openclaw-learning-system"))

    import uvicorn
    from memory_api.server import app

    # Write PID before starting (uvicorn.run blocks)
    write_pid(os.getpid())

    print(f"[Start] ─────────────────────────────────────────────")
    print(f"[Start]   HyperMarrow 藏慧")
    print(f"[Start]   API:  http://localhost:{args.port}/docs")
    print(f"[Start]   UI:   {ui_url}")
    print(f"[Start]   停止: python stop.py")
    print(f"[Start] ─────────────────────────────────────────────")

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\n[Start] Shutting down...")
    finally:
        remove_pid()
        print("[Start] Stopped.")


def stop_service(port: int = _DEFAULT_PORT):
    """Stop a running HyperMarrow service."""
    print(f"[Stop] Looking for HyperMarrow on port {port}...")

    # Try PID file first
    pid = read_pid()
    if pid:
        print(f"[Stop] Found PID file: {pid}")
        if kill_process(pid):
            time.sleep(1)
            if not is_port_in_use(port):
                print(f"[Stop] Process {pid} stopped (via PID file).")
                remove_pid()
                return
        print(f"[Stop] PID file method failed, trying port scan...")

    # Fallback: scan by port
    pid = find_process_by_port(port)
    if pid:
        print(f"[Stop] Found process on port {port}: PID {pid}")
        if kill_process(pid):
            time.sleep(1)
            if not is_port_in_use(port):
                print(f"[Stop] Process {pid} stopped.")
                remove_pid()
                return
        # Force kill
        print(f"[Stop] Force killing PID {pid}...")
        kill_process(pid, force=True)
        time.sleep(1)
        if not is_port_in_use(port):
            print(f"[Stop] Process {pid} force-stopped.")
            remove_pid()
            return

    if not is_port_in_use(port):
        print(f"[Stop] HyperMarrow is not running (port {port} is free).")
        remove_pid()
    else:
        print(f"[Stop] ERROR: Could not stop the process on port {port}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
