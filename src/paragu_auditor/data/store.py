"""DuckDB storage layer — replaces in-memory data for persistent storage.

v2: swap in-memory data loading for DuckDB. This is the transition step
towards the full Databricks Delta Lake architecture.

The DuckDB store:
  - Stores CompiledRelease objects as a normalized "contracts" table
  - Stores red flag results
  - Supports SQL queries via DuckDB's native SQL engine
  - Works locally (single file) and scales to ~100k records

v3: replace DuckDB with Databricks Delta tables + Unity Catalog.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd

from .schemas import CompiledRelease
from .jsonld_mapper import load_silver_data

logger = logging.getLogger(__name__)


class DuckDBStore:
    """Persistent storage for procurement contracts using DuckDB.

    Usage:
        store = DuckDBStore("data/paragu_audit.duckdb")
        store.load_synthetic_data()  # Load from JSONL or fixtures
        store.get_contracts(entity="Salud")
        store.compute_red_flags()
    """

    def __init__(self, db_path: str | Path = "data/paragu_audit.duckdb"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self):
        """Create tables if they don't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                ocid VARCHAR PRIMARY KEY,
                tender_id VARCHAR,
                title VARCHAR,
                entity_name VARCHAR,
                procurement_method VARCHAR,
                procurement_method_details VARCHAR,
                amount FLOAT,
                currency VARCHAR DEFAULT 'PYG',
                year INTEGER,
                n_bids INTEGER,
                n_valid_bids INTEGER,
                tender_period_start DATE,
                tender_period_end DATE,
                submission_period_days INTEGER,
                raw_data JSON
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                bid_id VARCHAR PRIMARY KEY,
                ocid VARCHAR,
                bidder_id VARCHAR,
                bidder_name VARCHAR,
                amount FLOAT,
                status VARCHAR
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS awards (
                award_id VARCHAR PRIMARY KEY,
                ocid VARCHAR,
                supplier_id VARCHAR,
                supplier_name VARCHAR,
                amount FLOAT,
                status VARCHAR
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS red_flags (
                ocid VARCHAR,
                flag_id VARCHAR,
                value FLOAT,
                evidence JSON,
                skipped BOOLEAN,
                skip_reason VARCHAR,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ocid, flag_id)
            )
        """)

    def insert_contracts(self, releases: list[CompiledRelease]):
        """Insert compiled releases into the contracts table."""
        for r in releases:
            period = r.tender.calculate_submission_period()
            raw = r.model_dump_json() if hasattr(r, "model_dump_json") else str(r)
            self._conn.execute(
                "INSERT OR REPLACE INTO contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    r.ocid, r.tender.id, r.tender.title,
                    r.tender.procuring_entity_name, r.tender.procurement_method,
                    r.tender.procurement_method_details,
                    r.tender.value.amount if r.tender.value else None,
                    "PYG", r.tender.tender_period_start.year if r.tender.tender_period_start else None,
                    r.tender.n_bids, r.tender.n_valid_bids,
                    r.tender.tender_period_start, r.tender.tender_period_end,
                    period, raw,
                ],
            )
            for b in r.tender.bids:
                self._conn.execute(
                    "INSERT OR REPLACE INTO bids VALUES (?, ?, ?, ?, ?, ?)",
                    [b.id, r.ocid, b.bidder_id, b.bidder_name,
                     b.amount.amount if b.amount else None, b.status],
                )
            for a in r.awards:
                for i, sid in enumerate(a.supplier_ids):
                    name = a.supplier_names[i] if i < len(a.supplier_names) else ""
                    self._conn.execute(
                        "INSERT OR REPLACE INTO awards VALUES (?, ?, ?, ?, ?, ?)",
                        [f"{a.id}-{i}", r.ocid, sid, name,
                         a.value.amount if a.value else None, a.status],
                    )
        self._conn.commit()

    def insert_red_flags(self, results: list):
        """Insert red flag results into the red_flags table."""
        import json
        for r in results:
            self._conn.execute(
                "INSERT OR REPLACE INTO red_flags VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                [r.ocid, r.flag_id, r.value,
                 json.dumps(r.evidence) if r.evidence else None,
                 r.skipped, r.skip_reason],
            )
        self._conn.commit()

    def query(self, sql: str, params: Optional[list] = None) -> pd.DataFrame:
        """Run a raw SQL query and return a DataFrame."""
        if params:
            return self._conn.execute(sql, params).fetchdf()
        return self._conn.execute(sql).fetchdf()

    def get_contracts(
        self,
        entity: Optional[str] = None,
        year: Optional[int] = None,
        method: Optional[str] = None,
        min_amount: Optional[float] = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Search contracts with filters. Returns DataFrame."""
        sql = "SELECT * FROM contracts WHERE 1=1"
        params = []
        if entity:
            sql += " AND LOWER(entity_name) LIKE LOWER(?)"
            params.append(f"%{entity}%")
        if year:
            sql += " AND year = ?"
            params.append(year)
        if method:
            sql += " AND procurement_method = ?"
            params.append(method)
        if min_amount:
            sql += " AND amount >= ?"
            params.append(min_amount)
        sql += " ORDER BY year DESC, tender_period_start DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, params)

    def get_red_flags(
        self,
        flag_id: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Get red flag results with optional filters."""
        sql = """SELECT r.*, c.title, c.entity_name, c.amount, c.year
                 FROM red_flags r
                 LEFT JOIN contracts c ON r.ocid = c.ocid
                 WHERE r.skipped = FALSE AND r.value > 0"""
        params = []
        if flag_id:
            sql += " AND r.flag_id = ?"
            params.append(flag_id)
        if year:
            sql += " AND c.year = ?"
            params.append(year)
        sql += " ORDER BY c.year DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, params)

    def load_synthetic_data(self):
        """Load the synthetic Paraguay dataset for testing/demos."""
        from tests.data.fixtures.synthetic import DEMO_DATASET
        releases = load_silver_data(DEMO_DATASET)
        self.insert_contracts(releases)
        return len(releases)

    def count_contracts(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]

    def close(self):
        self._conn.close()
