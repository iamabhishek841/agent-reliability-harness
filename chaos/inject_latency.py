"""Set artificial latency; values beyond the backend budget become a timeout."""

import argparse

from common import load, save

parser = argparse.ArgumentParser()
parser.add_argument("--system", choices=["legacy_crm", "knowledge_platform"], default="legacy_crm")
parser.add_argument("--seconds", type=float, default=6.0)
args = parser.parse_args()
state = load()
state.setdefault("latency", {})[args.system] = max(0.0, args.seconds)
save(state)
print({"scenario": "latency", "system": args.system, "seconds": args.seconds})

