#!/usr/bin/env python3
"""
HyperMarrow HTTP Bridge
=======================
A lightweight HTTP server that exposes HyperMarrow memory system via REST API.
This replaces the JSON-RPC bridge for environments where subprocess stdio
communication is not available (e.g., when loaded as an OpenClaw plugin).

Endpoints:
  GET  /health          → health check
  GET  /stats           → system stats
  POST /check            → decision check
  POST /search           → vector search
  POST /record           → record outcome
  POST /memory/search    → semantic memory search
  POST /memory/stats    → memory stats

Run: python hypermarow_http.py [--port PORT]
"""

import sys, os, json, argparse, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Add parent package to path
_bridge_dir = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_bridge_dir)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from memory_integration.decision_check import DecisionCheckPoint
from memory_core.vector_memory_db import VectorMemoryDB
from memory_core.episodic_memory_db import EpisodicMemoryDB

PORT = 18765
HOST = "127.0.0.1"

# Global instances (lazy init)
_bridge = None
_dcp = None
_vdb = None
_edb = None

def get_bridge():
    global _bridge
    if _bridge is None:
        from hypermarow_bridge import HyperMarrowBridge
        _bridge = HyperMarrowBridge()
        _bridge.start()
    return _bridge

def get_dcp():
    global _dcp
    if _dcp is None:
        _dcp = DecisionCheckPoint(agent_id="openclaw-http")
    return _dcp

def get_vdb():
    global _vdb
    if _vdb is None:
        _vdb = VectorMemoryDB()
    return _vdb

def get_edb():
    global _edb
    if _edb is None:
        _edb = EpisodicMemoryDB()
    return _edb

def json_response(handler, data, status=200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode("utf-8"))

def read_body(handler):
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length == 0:
        return {}
    body = handler.rfile.read(content_length)
    return json.loads(body.decode("utf-8"))

class HyperMarrowHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stdout.write(f"[HyperMarrow HTTP] {args[0]}\n")
        sys.stdout.flush()

    def do_GET(self):
        if self.path == "/health":
            json_response(self, {"status": "ok", "service": "hypermarow-http"})
        elif self.path == "/stats":
            try:
                result = get_bridge().send_rpc({"method": "stats", "id": 99})
                json_response(self, result)
            except Exception as e:
                json_response(self, {"error": str(e)}, 500)
        elif self.path == "/":
            json_response(self, {
                "service": "HyperMarrow HTTP Bridge",
                "version": "1.0.0",
                "endpoints": ["/health", "/stats", "/check", "/search", "/record", "/memory/search", "/memory/stats"]
            })
        else:
            json_response(self, {"error": "not found"}, 404)

    def do_POST(self):
        body = read_body(self)
        method = body.get("method", self.path.lstrip("/"))
        m_id = body.get("id", 1)

        try:
            if method == "check" or self.path == "/check":
                result = get_dcp().check(
                    context=body.get("context", {}),
                    agent_id=body.get("agent_id", "openclaw-http")
                )
                json_response(self, result)

            elif method == "search" or self.path == "/search":
                result = get_bridge().send_rpc({
                    "method": "search",
                    "id": m_id,
                    "params": {"query": body.get("query", "")}
                })
                json_response(self, result)

            elif method == "record" or self.path == "/record":
                result = get_dcp().record(
                    action=body.get("action", ""),
                    outcome=body.get("outcome", "unknown"),
                    context=body.get("context", {}),
                    reward=body.get("reward", 0.0)
                )
                json_response(self, result)

            elif method == "memory/search" or self.path == "/memory/search":
                vdb = get_vdb()
                results = vdb.search(body.get("query", ""), top_k=body.get("top_k", 5))
                json_response(self, {
                    "success": True,
                    "query": body.get("query", ""),
                    "results": [{"text": r["text"][:200], "score": r["score"]} for r in results]
                })

            elif method == "memory/stats" or self.path == "/memory/stats":
                vdb = get_vdb()
                stats = vdb.get_stats() if hasattr(vdb, "get_stats") else {}
                json_response(self, {
                    "success": True,
                    "stats": stats,
                    "bridge_ready": get_bridge().process.poll() is None
                })

            else:
                json_response(self, {"error": f"unknown method: {method}"}, 400)

        except Exception as e:
            import traceback
            traceback.print_exc()
            json_response(self, {"error": str(e)}, 500)

def run_server(port, bg=False):
    server = HTTPServer((HOST, port), HyperMarrowHTTPHandler)
    if bg:
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    print(f"[HyperMarrow HTTP] Server running on http://{HOST}:{port}")
    print("[HyperMarrow HTTP] Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HyperMarrow HTTP] Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HyperMarrow HTTP Bridge")
    parser.add_argument("--port", type=int, default=PORT, help=f"HTTP port (default: {PORT})")
    parser.add_argument("--bg", action="store_true", help="Run in background thread")
    args = parser.parse_args()
    run_server(args.port, bg=args.bg)
