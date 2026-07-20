"""Make one integration advertise a deliberately stale snapshot."""

import argparse

from common import load, save

parser = argparse.ArgumentParser()
parser.add_argument("--system", choices=["legacy_crm", "knowledge_platform"], default="knowledge_platform")
parser.add_argument("--hours", type=int, default=24)
args = parser.parse_args()
state = load()
state.setdefault("stale_hours", {})[args.system] = max(0, args.hours)
save(state)
print({"scenario": "stale_sync", "system": args.system, "hours": args.hours})

