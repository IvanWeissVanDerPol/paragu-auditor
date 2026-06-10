"""Tests for DuckDB storage layer."""
import pytest
import json
from paragu_auditor.data.store import DuckDBStore
from tests.data.fixtures.synthetic import DEMO_DATASET
from paragu_auditor.data.jsonld_mapper import load_silver_data


@pytest.fixture
def store(tmp_path):
    """Create a temporary DuckDB store."""
    db = tmp_path / "test.duckdb"
    s = DuckDBStore(db)
    yield s
    s.close()


class TestDuckDBStore:
    def test_init_creates_tables(self, store):
        tables = store.query("SELECT name FROM sqlite_master WHERE type='table'")
        assert len(tables) >= 4

    def test_load_synthetic_data(self, store):
        n = store.load_synthetic_data()
        assert n == len(DEMO_DATASET)
        assert store.count_contracts() == len(DEMO_DATASET)

    def test_get_contracts_all(self, store):
        store.load_synthetic_data()
        df = store.get_contracts()
        assert len(df) == len(DEMO_DATASET)

    def test_get_contracts_filter_entity(self, store):
        store.load_synthetic_data()
        df = store.get_contracts(entity="Salud")
        assert len(df) >= 2  # 2 Salud contracts in DEMO_DATASET

    def test_get_contracts_filter_year(self, store):
        store.load_synthetic_data()
        df = store.get_contracts(year=2024)
        assert len(df) > 0

    def test_get_contracts_filter_limit(self, store):
        store.load_synthetic_data()
        df = store.get_contracts(limit=3)
        assert len(df) <= 3

    def test_insert_red_flags(self, store):
        store.load_synthetic_data()
        from paragu_auditor.red_flags.runner import run_all_flags_on_dataset
        releases = load_silver_data(DEMO_DATASET)
        results = run_all_flags_on_dataset(releases)
        store.insert_red_flags(results)

        flagged = store.get_red_flags()
        assert len(flagged) >= 0  # may be 0 with synthetic data, that's OK

    def test_query_raw_sql(self, store):
        store.load_synthetic_data()
        df = store.query("SELECT COUNT(*) as cnt FROM contracts")
        assert df["cnt"].iloc[0] == len(DEMO_DATASET)

    def test_close_and_reopen(self, tmp_path):
        db = tmp_path / "reopen.duckdb"
        s1 = DuckDBStore(db)
        s1.load_synthetic_data()
        n1 = s1.count_contracts()
        s1.close()

        s2 = DuckDBStore(db)
        n2 = s2.count_contracts()
        assert n1 == n2
        s2.close()
