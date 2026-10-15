import importlib.util
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("pd", os.path.join(ROOT, "scripts", "prepare_data.py"))
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)

b = pd.bili_buvid()
print("buvid:", b, flush=True)
for bv in ["BV11D4y1q7tL", "BV1oHh86tE7s", "BV15A411s71P"]:
    u, d = pd.bili_resolve(bv, b)
    print(bv, "->", (u or "")[:90], "dur", d, flush=True)
