"""Fast, dependency-light repository verification for environments without Docker."""

import compileall
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "docker-compose.yml",
    ".env.example",
    "backend/app/main.py",
    "backend/app/agents/graph.py",
    "backend/app/integrations/legacy_crm.py",
    "db/legacy_crm/schema.sql",
    "db/legacy_crm/seed_data.py",
    "db/knowledge_platform/schema.sql",
    "db/knowledge_platform/ingest.py",
    "eval/test_cases.jsonl",
    "frontend/streamlit_app.py",
    "observability/prometheus.yml",
    "observability/grafana/dashboards/agent_overview.json",
    ".github/workflows/ci.yml",
    "README.md",
]


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    cases = [json.loads(line) for line in (ROOT / "eval/test_cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    policies = list((ROOT / "db/knowledge_platform/policy_docs").glob("*.md"))
    failure_logs = list((ROOT / "eval/failure_log").glob("20*.md"))
    dashboard = json.loads((ROOT / "observability/grafana/dashboards/agent_overview.json").read_text(encoding="utf-8"))
    compiled = compileall.compile_dir(str(ROOT / "backend"), quiet=1) and compileall.compile_dir(str(ROOT / "eval"), quiet=1) and compileall.compile_dir(str(ROOT / "chaos"), quiet=1) and compileall.compile_dir(str(ROOT / "frontend"), quiet=1)
    checks = {
        "required_files": not missing,
        "test_case_count_25_to_30": 25 <= len(cases) <= 30,
        "policy_document_count_10_to_15": 10 <= len(policies) <= 15,
        "three_failure_logs": len(failure_logs) >= 3,
        "grafana_has_panels": len(dashboard.get("panels", [])) >= 6,
        "python_compiles": compiled,
        "no_committed_env": not (ROOT / ".env").exists(),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    if missing:
        print("Missing:", ", ".join(missing))
    print(json.dumps({"test_cases": len(cases), "policy_docs": len(policies), "failure_logs": len(failure_logs), "grafana_panels": len(dashboard.get("panels", []))}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

