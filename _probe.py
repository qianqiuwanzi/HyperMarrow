import sys, json
sys.path.insert(0, r"D:\OpenClaw\workspace\HyperMarrow")
try:
    from hypermarrow import HyperMarrowWire
    hm = HyperMarrowWire(agent_id="openclaw", hypermarrow_path=r"D:\OpenClaw\workspace\HyperMarrow")
    stats = hm.stats()
    print("OK")
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=str)[:4000])
except Exception as e:
    print("ERR:", repr(e))
    import traceback
    traceback.print_exc()
