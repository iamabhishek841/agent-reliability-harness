import importlib.util
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_seed_module():
    path = ROOT / "db" / "legacy_crm" / "seed_data.py"
    spec = importlib.util.spec_from_file_location("seed_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_seed_shape_is_reproducible_and_messy():
    module = load_seed_module()
    first = module.build_records(datetime(2026, 1, 1, tzinfo=UTC))
    second = module.build_records(datetime(2026, 1, 1, tzinfo=UTC))
    assert first == second
    customers, orders, refunds = first
    assert len(customers) == 122
    assert len(orders) == 140
    assert len(refunds) == 45
    assert 5 <= sum(order[1] is None for order in orders) <= 8
    assert sum(refund[0].startswith("ORPHAN-") for refund in refunds) >= 4


def test_policy_corpus_has_twelve_documents():
    documents = list((ROOT / "db" / "knowledge_platform" / "policy_docs").glob("*.md"))
    assert len(documents) == 12
    assert all(path.read_text(encoding="utf-8").startswith("# ") for path in documents)

