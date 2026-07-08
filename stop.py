#!/usr/bin/env python3
"""
HyperMarrow 藏慧 — 停止脚本

用法:
  python stop.py              # 停止默认端口 8741
  python stop.py --port 9000  # 停止指定端口
  python stop.py --force      # 强制终止
"""

import sys
import socket
import subprocess
import time
from pathlib import Path

_HERE = Path(__file__).parent
_PID_FILE = _HERE / ".hypermarrow.pid"
_DEFAULT_PORT = 8741


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_process_by_port(port: int) -> int | None:
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
    try:
        if sys.platform == "win32":
            flag = ["/F"] if force else []
            subprocess.run(
                ["taskkill"] + flag + ["/PID", str(pid)],
                shell=True, capture_output=True, timeout=10
            )
        else:
            sig = "-9" if force else "-TERM"
            subprocess.run(["kill", sig, str(pid)], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="HyperMarrow 藏慧 — 停止脚本")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--force", action="store_true", help="强制终止")
    args = parser.parse_args()

    if not is_port_in_use(args.port):
        print(f"[Stop] HyperMarrow is not running (port {args.port} is free).")
        if _PID_FILE.exists():
            _PID_FILE.unlink()
            print("[Stop] Removed stale PID file.")
        return

    # Try PID file
    if _PID_FILE.exists():
        try:
            pid = int(_PID_FILE.read_text().strip())
            print(f"[Stop] PID file found: {pid}")
            kill_process(pid, force=args.force)
            time.sleep(1.5)
            if not is_port_in_use(args.port):
                print(f"[Stop] HyperMarrow stopped successfully.")
                _PID_FILE.unlink()
                return
            print("[Stop] PID file method didn't work, trying port scan...")
        except Exception:
            pass

    # Port scan fallback
    pid = find_process_by_port(args.port)
    if pid:
        print(f"[Stop] Found process on port {args.port}: PID {pid}")
        kill_process(pid, force=args.force)
        time.sleep(1.5)
        if not is_port_in_use(args.port):
            print("[Stop] HyperMarrow stopped successfully.")
            if _PID_FILE.exists():
                _PID_FILE.unlink()
            return
        if not args.force:
            print("[Stop] Force killing...")
            kill_process(pid, force=True)
            time.sleep(1)
            if not is_port_in_use(args.port):
                print("[Stop] HyperMarrow force-stopped.")
                if _PID_FILE.exists():
                    _PID_FILE.unlink()
                return

    print(f"[Stop] ERROR: Could not stop HyperMarrow on port {args.port}.")
    print(f"[Stop] Try: python stop.py --force")
    sys.exit(1)


if __name__ == "__main__":
    main()
