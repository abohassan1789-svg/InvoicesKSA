"""Tests for the Supply Contracts stack (عقود التوريد).

* the ``supply_contracts`` TableSpec, schema block and registrations
  (sidebar, permissions);
* the service: the save special-case (automatic number) and the manual-number
  sequence bump;
* the screen: the four field groups (no scroll, no preview), «طباعة الختم»,
  pre-filling a party from «الشركات» / «العملاء», the saved payload and the
  print data;
* the printed contract: the fixed clauses with the typed blanks, in the
  original layout and the five extra ones, with or without the stamp.

No real database: a fake connection/service records calls and returns canned
rows. Qt runs headless (offscreen).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.services.review_data_service import ReviewDataService, TABLE_SPECS

SPEC = TABLE_SPECS["supply_contracts"]


# --------------------------------------------------------------------------- #
# Spec, schema and registrations
# --------------------------------------------------------------------------- #
def test_spec_fields():
    assert SPEC.table_name == "supply_contracts"
    fields = {f.name: f for f in SPEC.fields}
    assert fields["contract_number"].required is False      # empty = automatic
    for name in ("contract_date", "first_party_name", "second_party_name"):
        assert fields[name].required is True
    assert fields["contract_day"].virtual and fields["contract_day"].readonly
    for name in ("first_party_company_id", "second_party_customer_id"):
        assert fields[name].hidden_on_form and not fields[name].virtual
    groups = list(dict.fromkeys(f.group for f in SPEC.fields if f.group))
    assert groups == ["البيانات الأساسية", "الطرف الأول", "الطرف الثاني", "التوريد والسداد"]


def test_full_schema_creates_the_table_idempotently():
    from app.database import schema_bootstrap

    sql = schema_bootstrap.full_schema_sql()
    assert "CREATE TABLE IF NOT EXISTS public.supply_contracts (" in sql
    assert "CREATE SEQUENCE IF NOT EXISTS public.supply_contract_number_seq" in sql
    assert "'CT-'" in sql
    assert "supply_contracts" in schema_bootstrap.missing_columns_sql(sql)
    # Every non-virtual field is a column of the table.
    block = sql.split("CREATE TABLE IF NOT EXISTS public.supply_contracts (")[1].split(");")[0]
    for field in SPEC.fields:
        if not field.virtual:
            assert f"    {field.name} " in block, field.name
    assert "    show_stamp boolean DEFAULT true NOT NULL,\n" in block


def test_show_stamp_is_coerced_to_a_boolean():
    service = ReviewDataService()
    field = {f.name: f for f in SPEC.fields}["show_stamp"]
    assert service._coerce_value(field, False) is False
    assert service._coerce_value(field, "true") is True
    assert service._coerce_value(field, "0") is False


def test_registered_in_sidebar_and_permissions():
    from app.services.permission_registry import collect_targets
    from app.ui.main_window import HIDDEN_NAV_KEYS, MODULES

    keys = {key: label for key, label, _cls in MODULES}
    assert keys["supply_contracts"] == "عقود التوريد"
    assert "supply_contracts" not in HIDDEN_NAV_KEYS
    assert "supply_contracts" in {t["target_code"] for t in collect_targets()}


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


def test_save_lets_db_number_the_contract():
    conn = _FakeConn([{"id": 1}])
    _service_with(conn).save_record(SPEC, {
        "contract_number": "", "contract_date": "2026-10-20",
        "first_party_name": "شركة زيادة البركة التجارية", "second_party_name": "شركة الضيافة",
        "payment_days_after_first_supply": "60",
    }, None)
    insert_sql, params = conn.calls[-1]
    assert "INSERT INTO" in insert_sql
    assert "contract_number" not in insert_sql
    assert 60 in params


def test_save_requires_both_parties():
    service = _service_with(_FakeConn([{"id": 1}]))
    with pytest.raises(ValueError) as excinfo:
        service.save_record(SPEC, {"contract_date": "2026-10-20", "first_party_name": "أ",
                                   "second_party_name": ""}, None)
    assert "الطرف الثاني" in str(excinfo.value)


def test_manual_number_bumps_the_sequence_only_for_ct_numbers():
    conn = _FakeConn([])
    service = _service_with(conn)
    service.register_manual_supply_contract_number("BC-5")
    assert conn.calls == []
    service.register_manual_supply_contract_number("CT-0042")
    sql, params = conn.calls[0]
    assert "setval('supply_contract_number_seq'" in sql
    assert params == {"n": 42}


def test_peek_next_number_formats_four_digits():
    conn = _FakeConn([{"last_value": 7, "is_called": True}])
    assert _service_with(conn).peek_next_supply_contract_number() == "CT-0008"


# --------------------------------------------------------------------------- #
# Screen
# --------------------------------------------------------------------------- #
_STORED = {
    "id": 3, "contract_number": "CT-0012", "contract_date": "2026-10-20",
    "first_party_company_id": 10, "first_party_name": "شركة زيادة البركة التجارية",
    "first_party_cr": "7009631370", "first_party_cr_city": "جدة", "first_party_address": "جدة",
    "first_party_rep_name": "سعيد عبدالله الغامدي", "first_party_rep_nationality": "سعودي",
    "first_party_rep_id": "1034567890", "first_party_rep_title": "المدير العام",
    "second_party_customer_id": None, "second_party_name": "شركة الضيافة الراقية للإعاشة",
    "second_party_cr": "4030298765", "second_party_cr_city": "جدة",
    "second_party_branches": "مكة المكرمة", "second_party_address": "جدة",
    "second_party_rep_name": "محمد أحمد عبدالرحمن", "second_party_rep_nationality": "مصري",
    "second_party_rep_id": "2456789013", "second_party_rep_title": "المدير العام",
    "supply_sites": "مدينة جدة، ومدينة مكة المكرمة",
    "payment_days_after_first_supply": 60, "payment_days_after_statement": 10,
    "bank_name": "مصرف الراجحي", "bank_account": "SA0380000000608010167519",
}


class _FakeUiService:
    def __init__(self):
        self.save_calls: list[tuple] = []

    def list_records(self, spec, keyword: str = "", limit: int = 500):
        return []

    def list_customers_for_selection(self):
        return [{"customer_id": 1, "customer_name": "مطاعم ركن الطازج", "phone_number": ""}]

    def list_companies_for_selection(self):
        return [{"id": 10, "name_ar": "شركة زيادة البركة التجارية"}]

    def get_company_details(self, company_id):
        return {"id": company_id, "name_ar": "شركة زيادة البركة التجارية",
                "commercial_registration": "7009631370", "address_ar": "جدة - حي الصفا"}

    def get_record(self, spec, record_id):
        if spec.key == "customers":
            return {"customer_id": 1, "customer_name": "مطاعم ركن الطازج", "cr": "4030111222",
                    "address": "مكة المكرمة"}
        return dict(_STORED)

    def peek_next_supply_contract_number(self):
        return "CT-0013"

    def register_manual_supply_contract_number(self, number):
        pass

    def value_exists(self, spec, column, value, exclude_id=None):
        return False

    def save_record(self, spec, payload, record_id):
        self.save_calls.append((dict(payload), record_id))
        return 3


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
    import app.ui.screens.base_crud_screen as base
    import app.ui.screens.supply_contracts_screen as mod

    monkeypatch.setattr(mod, "QMessageBox", _FakeMessageBox)
    monkeypatch.setattr(base, "QMessageBox", _FakeMessageBox)
    return mod.SupplyContractsScreen(_FakeUiService())


def test_form_has_every_blank_without_scroll_or_preview(screen):
    from PySide6.QtWidgets import QScrollArea, QTextBrowser

    expected = {f.name for f in SPEC.fields if not f.hidden_on_form}
    assert set(screen.inputs) == expected
    assert set(screen.group_boxes) == {
        "البيانات الأساسية", "التوريد والسداد", "الطرف الأول", "الطرف الثاني",
    }
    assert not screen.findChildren(QScrollArea)
    assert not screen.findChildren(QTextBrowser)


def test_new_record_defaults_and_day_name(screen):
    screen.new_record()
    assert screen.inputs["contract_number"].placeholderText() == "تلقائي: CT-0013"
    screen.inputs["contract_date"].setText("2026-10-20")
    assert screen.inputs["contract_day"].text() == "الثلاثاء"
    assert screen.inputs["first_party_rep_title"].text() == "المدير العام"


def test_stamp_checkbox_follows_mode_and_record(screen):
    screen.new_record()
    assert screen.stamp_checkbox.isChecked() and screen.stamp_checkbox.isEnabled()
    screen._fill_form(dict(_STORED, show_stamp=False))
    assert not screen.stamp_checkbox.isChecked()
    screen.set_mode("view")
    assert not screen.stamp_checkbox.isEnabled()


def test_picking_a_company_and_customer_prefills_the_parties(screen):
    screen.new_record()
    combo = screen.first_party_combo
    combo.setCurrentIndex(combo.findData(10))
    screen._prefill_first_party()
    assert screen.inputs["first_party_cr"].text() == "7009631370"
    assert screen.inputs["first_party_address"].text() == "جدة - حي الصفا"
    combo = screen.second_party_combo
    combo.setCurrentIndex(combo.findData(1))
    screen._prefill_second_party()
    assert screen.inputs["second_party_cr"].text() == "4030111222"
    assert screen.inputs["second_party_address"].text() == "مكة المكرمة"


def test_save_sends_names_and_party_ids(screen):
    screen.new_record()
    screen.inputs["contract_date"].setText("2026-10-20")
    screen.first_party_combo.setCurrentIndex(screen.first_party_combo.findData(10))
    screen.second_party_combo.setEditText("عميل غير مسجل")   # typed, not in the list
    screen.inputs["payment_days_after_first_supply"].setText("60")
    screen.stamp_checkbox.setChecked(False)
    screen.save_record()
    payload, record_id = screen.service.save_calls[-1]
    assert record_id is None
    assert payload["first_party_name"] == "شركة زيادة البركة التجارية"
    assert payload["first_party_company_id"] == 10
    assert payload["second_party_name"] == "عميل غير مسجل"
    assert payload["second_party_customer_id"] is None
    assert payload["payment_days_after_first_supply"] == "60"
    assert "contract_day" not in payload
    assert payload["show_stamp"] is False
    assert screen.inputs["contract_number"].text() == "CT-0012"   # reloaded


def test_saved_contract_fills_the_form_and_print_data(screen):
    screen._fill_form(dict(_STORED))
    assert screen.first_party_combo.currentText() == "شركة زيادة البركة التجارية"
    assert screen.second_party_combo.currentText() == "شركة الضيافة الراقية للإعاشة"
    data = screen.collect_print_data()
    assert data["contract_number"] == "CT-0012"
    assert data["payment_days_after_statement"] == "10"
    assert data["first_party_company"]["id"] == 10
    assert data["show_stamp"] is True


def test_print_without_parties_shows_a_hint(screen):
    screen.new_record()
    _FakeMessageBox.infos = []
    screen.print_contract()
    assert _FakeMessageBox.infos and "الطرفين" in _FakeMessageBox.infos[0][1]


# --------------------------------------------------------------------------- #
# Printed contract
# --------------------------------------------------------------------------- #
def test_contract_prints_fixed_clauses_and_typed_blanks(qt_app):
    from app.ui.screens.supply_contract_print import build_supply_contract_html

    page = build_supply_contract_html(dict(_STORED))
    assert "عقد توريد خضار وفواكه" in page
    assert "أنه في يوم <span class=\"v\">الثلاثاء</span>" in page
    assert "20 / 10 / 2026" in page
    for value in ("7009631370", "سعيد عبدالله الغامدي", "مكة المكرمة", "مصرف الراجحي",
                  "SA0380000000608010167519"):
        assert value in page
    assert "بعد <span class=\"v\">60</span> يوم من تاريخ أول توريد" in page
    assert "خلال <span class=\"v\">10</span> أيام" in page
    for clause in ("ثانياً: الشروط العامة", "خامساً: الجزاءات", "قبل الموعد بـ 30 يوماً",
                   "سادساً: نسخ العقد", "سابعاً: فض النزاع"):
        assert clause in page


def test_empty_blanks_print_as_dots(qt_app):
    from app.ui.screens.supply_contract_print import build_supply_contract_html

    page = build_supply_contract_html({"first_party_name": "أ", "second_party_name": "ب"})
    assert "لدى بنك ............" in page
    assert 'class="v">أ<' in page


def test_day_and_date_helpers():
    from app.ui.screens.supply_contract_print import contract_date_text, contract_day_name

    assert contract_day_name("2026-10-23") == "الجمعة"
    assert contract_day_name("") == ""
    assert contract_date_text("2026-10-05") == "05 / 10 / 2026"


_STAMP = {"id": 10, "name_ar": "شركة زيادة البركة التجارية", "stamp": b"\x89PNG-stamp",
          "stamp_mime": "image/png"}


def _all_builders():
    from app.ui.screens.supply_contract_print import supply_contract_builders

    return supply_contract_builders()


def test_picker_offers_the_original_and_the_five_picked_layouts():
    from app.ui.screens.supply_contract_print import SUPPLY_CONTRACT_TEMPLATE_OPTIONS

    assert SUPPLY_CONTRACT_TEMPLATE_OPTIONS == (
        "النموذج الأساسي", "الترويسة الخضراء", "الكحلي والذهبي", "العنابي الرسمي",
        "الخضار والفواكه", "البطاقات",
    )
    assert set(_all_builders()) == {1, 2, 3, 4, 5, 6}


@pytest.mark.parametrize("choice", [1, 2, 3, 4, 5, 6])
def test_every_layout_prints_the_same_contract(qt_app, choice):
    page = _all_builders()[choice](dict(_STORED, first_party_company=_STAMP))
    for text in ("عقد توريد خضار وفواكه", "شركة الضيافة الراقية للإعاشة", "7009631370",
                 "مصرف الراجحي", "سنة كاملة", "قبل الموعد بـ 30 يوماً", "سابعاً: فض النزاع",
                 "التوقيع:"):
        assert text in page, (choice, text)
    assert "data:image/png;base64," in page        # the stamp


@pytest.mark.parametrize("choice", [1, 2, 3, 4, 5, 6])
def test_unticked_stamp_is_left_out(qt_app, choice):
    page = _all_builders()[choice](dict(_STORED, first_party_company=_STAMP, show_stamp=False))
    assert "data:image/png;base64," not in page
    assert "الختم:" in page


def test_letterhead_layouts_name_the_first_party_and_number(qt_app):
    for choice in (2, 3, 4, 5):
        page = _all_builders()[choice](dict(_STORED))
        assert page.count("شركة زيادة البركة التجارية") >= 2   # letterhead + parties
        assert "CT-0012" in page


def test_print_asks_for_a_layout_and_uses_it(screen, monkeypatch):
    import app.ui.screens.supply_contract_print as printing

    shown = []

    class _Dialog:
        def __init__(self, data, parent=None, html_builder=None):
            shown.append((data, html_builder))

        def exec(self):
            return 0

    sentinel = lambda data: "<html></html>"  # noqa: E731
    monkeypatch.setattr(printing, "choose_supply_contract_builder", lambda parent: sentinel)
    monkeypatch.setattr(printing, "SupplyContractPreviewDialog", _Dialog)
    screen._fill_form(dict(_STORED))
    screen.print_contract()
    assert shown and shown[0][1] is sentinel
    assert shown[0][0]["contract_number"] == "CT-0012"
