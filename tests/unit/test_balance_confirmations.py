"""Tests for the Balance Confirmations stack (مصادقة على الرصيد).

* the ``balance_confirmations`` TableSpec, schema block and registrations
  (sidebar, permissions);
* the service: joined list query, the statement balance query (one company or
  «كل الشركات»), and the save special-case (automatic number, balance always
  recomputed — never taken from the form);
* the screen: the three-step layout, the «كل الشركات» company choice, the live
  balance preview and the print data;
* the printed letter.

No real database: a fake connection/service records calls and returns canned
rows. Qt runs headless (offscreen).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from decimal import Decimal

import pytest

from app.services.review_data_service import ALL_COMPANIES_LABEL, ReviewDataService, TABLE_SPECS

SPEC = TABLE_SPECS["balance_confirmations"]


# --------------------------------------------------------------------------- #
# Spec, schema and registrations
# --------------------------------------------------------------------------- #
def test_spec_fields():
    assert SPEC.table_name == "balance_confirmations"
    assert SPEC.primary_key == "id"
    fields = {f.name: f for f in SPEC.fields}
    assert fields["confirmation_number"].required is False   # empty = automatic
    assert fields["confirmation_date"].required is True
    assert fields["customer_id"].required is True
    assert fields["company_id"].required is False            # NULL = كل الشركات
    assert fields["description"].required is False
    for name in ("total_debit", "total_credit", "balance"):
        assert fields[name].readonly is True
    for name in ("customer_name", "company_name"):
        assert fields[name].virtual and fields[name].hidden_on_form
    assert SPEC.list_columns == (
        "confirmation_number", "customer_name", "company_name", "confirmation_date", "balance",
    )


def test_full_schema_creates_the_table_idempotently():
    from app.database import schema_bootstrap

    sql = schema_bootstrap.full_schema_sql()
    assert "CREATE TABLE IF NOT EXISTS public.balance_confirmations (" in sql
    assert "CREATE SEQUENCE IF NOT EXISTS public.balance_confirmation_number_seq" in sql
    assert "'BC-'" in sql
    # company_id is nullable (كل الشركات); the back-fill keeps it that way.
    assert "    company_id integer,\n" in sql
    assert "balance_confirmations" in schema_bootstrap.missing_columns_sql(sql)


def test_registered_in_sidebar_and_permissions():
    from app.services.permission_registry import collect_targets
    from app.ui.main_window import HIDDEN_NAV_KEYS, MODULES

    keys = {key: label for key, label, _cls in MODULES}
    assert keys["balance_confirmations"] == "مصادقة على الرصيد"
    assert "balance_confirmations" not in HIDDEN_NAV_KEYS
    codes = {t["target_code"] for t in collect_targets()}
    assert "balance_confirmations" in codes


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #
def _render(query) -> str:
    try:
        return query.as_string(None)
    except Exception:  # pragma: no cover - plain strings
        return str(query)


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list[tuple] = []
        self.closed = False

    def execute(self, query, params=None):
        self.calls.append((_render(query), params))
        return _Cursor(self.rows)


def _service_with(conn) -> ReviewDataService:
    service = ReviewDataService()
    service._connection = conn
    return service


def test_list_joins_customers_and_companies():
    conn = _FakeConn([])
    _service_with(conn).list_records(SPEC, "النقيب")
    sql, params = conn.calls[0]
    assert "FROM balance_confirmations bc" in sql
    assert "LEFT JOIN customers c ON c.customer_id = bc.customer_id" in sql
    assert "LEFT JOIN companies co ON co.id = bc.company_id" in sql
    assert f"COALESCE(co.name_ar, '{ALL_COMPANIES_LABEL}')" in sql
    assert sql.count("ILIKE") == 4
    assert params == ["%النقيب%"] * 4 + [500]


def test_customer_balance_for_one_company():
    conn = _FakeConn([{"total_debit": Decimal("1265"), "total_credit": Decimal("515")}])
    totals = _service_with(conn).customer_balance(1, 7, "2026-10-20")
    assert totals == {
        "total_debit": Decimal("1265.00"),
        "total_credit": Decimal("515.00"),
        "balance": Decimal("750.00"),
    }
    sql, params = conn.calls[0]
    # Same movements as the customer statement: invoices (debit), cash invoices'
    # settlements + receipt vouchers (credit), up to and including the date.
    assert "FROM sales_invoices si" in sql
    assert "lower(si.payment_type) = 'cash'" in sql
    assert "FROM receipt_vouchers rv" in sql
    assert "si.issue_datetime < (%(d)s::date + INTERVAL '1 day')" in sql
    assert "rv.voucher_date <= %(d)s::date" in sql
    assert params == {"c": 1, "co": 7, "d": "2026-10-20"}


def test_customer_balance_for_all_companies_passes_null_company():
    conn = _FakeConn([{"total_debit": 0, "total_credit": Decimal("40")}])
    totals = _service_with(conn).customer_balance(1, None, "2026-10-20")
    assert conn.calls[0][1]["co"] is None
    assert totals["balance"] == Decimal("-40.00")   # we owe the customer


def test_customer_balance_without_customer_skips_the_query():
    conn = _FakeConn([])
    assert _service_with(conn).customer_balance(None, None, "2026-10-20")["balance"] == 0
    assert conn.calls == []


def _payload(**overrides):
    payload = {
        "confirmation_number": "",
        "confirmation_date": "2026-10-20",
        "customer_id": 1,
        "company_id": None,
        "description": "",
    }
    payload.update(overrides)
    return payload


def test_save_recomputes_balance_and_lets_db_number_it():
    conn = _FakeConn([{"id": 1, "total_debit": Decimal("100"), "total_credit": Decimal("30")}])
    service = _service_with(conn)
    # A forged balance on the form is ignored.
    service.save_record(SPEC, _payload(balance="999999", total_debit="1"), None)
    insert_sql, params = conn.calls[-1]
    assert "INSERT INTO" in insert_sql
    assert "confirmation_number" not in insert_sql
    assert Decimal("70.00") in params and "999999" not in params
    assert Decimal("100.00") in params and Decimal("30.00") in params


def test_save_requires_a_customer():
    service = _service_with(_FakeConn([{"id": 1}]))
    with pytest.raises(ValueError) as excinfo:
        service.save_record(SPEC, _payload(customer_id=None), None)
    assert "اسم العميل" in str(excinfo.value)


def test_register_manual_number_only_for_bc_numbers():
    conn = _FakeConn([])
    service = _service_with(conn)
    service.register_manual_balance_confirmation_number("X-5")
    assert conn.calls == []
    service.register_manual_balance_confirmation_number("BC-012")
    sql, params = conn.calls[0]
    assert "setval('balance_confirmation_number_seq'" in sql
    assert params == {"n": 12}


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
class _FakeUiService:
    def __init__(self):
        self.balance_calls: list[tuple] = []
        self.save_calls: list[tuple] = []

    def list_records(self, spec, keyword: str = "", limit: int = 500):
        return []

    def list_customers_for_selection(self):
        return [{"customer_id": 1, "customer_name": "شركة النقيب للإنارة الحديثة", "phone_number": ""}]

    def list_companies_for_selection(self):
        return [{"id": 10, "name_ar": "شركة الأولى"}, {"id": 11, "name_ar": "شركة الثانية"}]

    def get_company_details(self, company_id):
        return {"id": company_id, "name_ar": "شركة الأولى"}

    def customer_balance(self, customer_id, company_id, as_of):
        self.balance_calls.append((customer_id, company_id, as_of))
        return {"total_debit": Decimal("186420.00"), "total_credit": Decimal("137670.00"),
                "balance": Decimal("48750.00")}

    def peek_next_balance_confirmation_number(self):
        return "BC-007"

    def register_manual_balance_confirmation_number(self, number):
        pass

    def value_exists(self, spec, column, value, exclude_id=None):
        return False

    def save_record(self, spec, payload, record_id):
        self.save_calls.append((dict(payload), record_id))
        return 5

    def get_record(self, spec, record_id):
        return {"id": 5, "confirmation_number": "BC-007", "confirmation_date": "2026-10-20",
                "customer_id": 1, "company_id": 10, "total_debit": Decimal("186420.00"),
                "total_credit": Decimal("137670.00"), "balance": Decimal("48750.00"),
                "description": "ربع ثالث"}


class _FakeMessageBox:
    infos: list[tuple] = []

    @staticmethod
    def information(parent, title, text, *args, **kwargs):
        _FakeMessageBox.infos.append((title, text))

    warning = critical = information


@pytest.fixture
def qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def screen(qt_app, monkeypatch):
    import app.ui.screens.balance_confirmations_screen as mod
    import app.ui.screens.base_crud_screen as base

    monkeypatch.setattr(mod, "QMessageBox", _FakeMessageBox)
    monkeypatch.setattr(base, "QMessageBox", _FakeMessageBox)
    return mod.BalanceConfirmationsScreen(_FakeUiService())


def test_three_steps_and_editors(screen):
    assert set(screen.step_panels) == {"customer", "balance", "save"}
    assert set(screen.inputs) == {
        "confirmation_number", "confirmation_date", "company_id", "customer_id", "description",
    }
    # «كل الشركات» first (NULL), then the companies.
    assert screen.company_combo.itemText(0) == ALL_COMPANIES_LABEL
    assert screen.company_combo.itemData(0) is None
    assert screen.company_combo.findData(11) == 2


def test_new_record_shows_live_balance_for_the_picked_company(screen):
    screen.new_record()
    assert screen.inputs["confirmation_number"].placeholderText() == "تلقائي: BC-007"
    screen.inputs["confirmation_date"].setText("2026-10-20")
    screen.company_combo.setCurrentIndex(1)
    screen.customer_combo.setCurrentIndex(1)
    assert screen.service.balance_calls[-1] == (1, 10, "2026-10-20")
    assert screen.balance_value.text() == "48,750.00"
    assert screen.debit_value.text() == "186,420.00"
    assert screen.direction_chip.text().startswith("عليكم")


def test_save_sends_ids_and_reloads_the_stored_record(screen):
    screen.new_record()
    screen.inputs["confirmation_date"].setText("2026-10-20")
    screen.customer_combo.setCurrentIndex(1)   # all companies stays selected
    screen.save_record()
    payload, record_id = screen.service.save_calls[-1]
    assert record_id is None
    assert payload["customer_id"] == 1 and payload["company_id"] is None
    assert "balance" not in payload            # the service computes it
    assert screen.inputs["confirmation_number"].text() == "BC-007"


def test_print_data_carries_the_letter_fields(screen):
    screen._fill_form(screen.service.get_record(SPEC, 5))
    data = screen._collect_print_data()
    assert data["number"] == "BC-007"
    assert data["customer"] == "شركة النقيب للإنارة الحديثة"
    assert data["balance"] == Decimal("48750.00")
    assert data["seller"]["name"] == "شركة الأولى"


def test_print_with_no_customer_shows_a_hint(screen):
    screen.new_record()
    _FakeMessageBox.infos = []
    screen.print_confirmation()
    assert _FakeMessageBox.infos and "اختر" in _FakeMessageBox.infos[0][1]


# --------------------------------------------------------------------------- #
# Printed letter
# --------------------------------------------------------------------------- #
def test_letter_states_balance_direction_and_reply_slip(qt_app):
    from app.ui.screens.balance_confirmation_print import build_balance_confirmation_html

    page = build_balance_confirmation_html({
        "number": "BC-007", "date": "2026-10-20", "customer": "شركة النقيب للإنارة الحديثة",
        "balance": Decimal("48750.00"), "description": "", "seller": {"name": "شركة الأولى"},
    })
    assert "مصادقة على صحة الرصيد" in page
    assert "2026/10/20" in page and 'data-hijri="2026-10-20"' in page
    assert "48,750.00" in page and "عليكم" in page
    assert "السادة / شركة الأولى" in page
    assert "15 يوم" in page and "التوقيع" in page

    credit = build_balance_confirmation_html({
        "number": "BC-008", "date": "2026-10-20", "customer": "عميل",
        "balance": Decimal("-40"), "seller": None,
    })
    assert "40.00" in credit and "لكم" in credit and "-40" not in credit
