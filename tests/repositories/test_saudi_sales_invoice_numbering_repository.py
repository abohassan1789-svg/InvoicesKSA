"""Unit tests for the Saudi sales-invoice numbering repository boundary.

Numbering is per-company and 1-based: each seller restarts from 1, the next
number is MAX(existing for that company) + 1, and uniqueness is scoped to the
seller company rather than the whole table.
"""

from __future__ import annotations

import pytest

from app.repositories.saudi_sales_invoice_repository import SaudiSalesInvoiceRepository


class RecordingDatabase:
    def __init__(self, result=None):
        self.result = result
        self.fetch_one_calls: list[tuple[str, list]] = []

    def fetch_one(self, sql, params=None):
        self.fetch_one_calls.append((str(sql), list(params or [])))
        return self.result


def _repo(db=None):
    repo = object.__new__(SaudiSalesInvoiceRepository)
    repo.db = db or RecordingDatabase()
    repo._url = "unused"
    return repo


# ---------------------------------------------------------------------------
# next_invoice_number: per-company MAX + 1, 1-based, legacy block ignored
# ---------------------------------------------------------------------------
def test_next_number_is_company_scoped_max_plus_one():
    db = RecordingDatabase({"n": 6})
    repo = _repo(db)

    assert repo.next_invoice_number(3) == "6"

    sql, params = db.fetch_one_calls[-1]
    assert "seller_company_id = %s" in sql
    assert "MAX(" in sql
    # company id first, legacy-block threshold second
    assert params[0] == 3


def test_next_number_starts_at_one_for_a_company_with_no_invoices():
    # COALESCE(MAX(...), 0) + 1 → the DB returns 1 for an empty company.
    db = RecordingDatabase({"n": 1})
    repo = _repo(db)

    assert repo.next_invoice_number(99) == "1"


def test_next_number_query_ignores_the_legacy_shared_block():
    db = RecordingDatabase({"n": 1})
    repo = _repo(db)

    repo.next_invoice_number(1)

    sql, params = db.fetch_one_calls[-1]
    # Legacy numbers (>= 50001) are filtered out so a company still carrying them
    # starts its fresh sequence from 1.
    assert "< %s" in sql
    assert 50_001 in params


def test_next_number_defaults_to_one_when_query_returns_nothing():
    db = RecordingDatabase(None)
    repo = _repo(db)

    assert repo.next_invoice_number(1) == "1"


# ---------------------------------------------------------------------------
# invoice_number_exists: uniqueness scoped to the seller company
# ---------------------------------------------------------------------------
def test_duplicate_lookup_is_scoped_to_the_seller_company():
    db = RecordingDatabase({"exists": 1})
    repo = _repo(db)

    assert repo.invoice_number_exists("1", seller_company_id=4) is True

    sql, params = db.fetch_one_calls[-1]
    assert "seller_company_id = %s" in sql
    assert params == ["1", 4]


def test_duplicate_lookup_without_company_falls_back_to_table_wide():
    db = RecordingDatabase(None)
    repo = _repo(db)

    assert repo.invoice_number_exists("1") is False

    sql, params = db.fetch_one_calls[-1]
    assert "seller_company_id" not in sql
    assert params == ["1"]


def test_duplicate_lookup_can_exclude_current_invoice():
    db = RecordingDatabase(None)
    repo = _repo(db)

    assert repo.invoice_number_exists("1", exclude_id=7, seller_company_id=4) is False

    sql, params = db.fetch_one_calls[-1]
    assert "id <> %s" in sql
    assert params == ["1", 4, 7]


def test_legacy_sequence_helpers_are_gone():
    repo = _repo()
    # The global reservation / sequence-sync machinery was removed with the
    # switch to per-company numbering.
    assert not hasattr(repo, "reserve_invoice_number")
    assert not hasattr(repo, "_sync_invoice_number_sequence")
