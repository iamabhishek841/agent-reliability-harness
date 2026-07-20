"""Simulate a 403/access revocation for a selected integration."""

import argparse

from common import load, save

parser = argparse.ArgumentParser()
parser.add_argument("--system", choices=["legacy_crm", "knowledge_platform"], default="legacy_crm")
parser.add_argument("--restore", action="store_true")
args = parser.parse_args()
state = load()
revoked = set(state.get("revoked", []))
revoked.discard(args.system) if args.restore else revoked.add(args.system)
state["revoked"] = sorted(revoked)
save(state)
print({"scenario": "access", "system": args.system, "revoked": not args.restore})

