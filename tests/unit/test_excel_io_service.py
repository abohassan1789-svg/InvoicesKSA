"""Tests for the reusable Excel template import/export engine.

Covers the five requested behaviours: template column generation, missing-column
validation, invalid-row validation, duplicate prevention and saving valid rows
only. All tests use a fake data service, so no database is required.
"""

from __future__ import annotations

import datetime

import pytest
from openpyxl import load_workbook

from app.services.excel_io_service import (
    ExcelTemplateService,
    ExcelWorkbookError,
    io_spec_for,
)


class FakeDataService:
    """Minimal stand-in for ReviewDataService used by the Excel engine."""

    def __init__(self, existing=None, customers=None, statuses=None):
        # existing: {table_name: [row dicts]} for duplicate signatures.
        self.existing = existing or {}
        self.customers = customers or {}  # phone -> customer_id
        self.statuses = statuses or {}  # name -> case_status_id
        self.saved: list[tuple] = []  # (table_key, payload)

    def fetch_column_values(self, table_name, columns):
        return self.existing.get(table_name, [])

    def find_customer_by_phone(self, phone):
        cid = self.customers.get(str(phone).strip())
        return {"customer_id": cid} if cid is not None else None

    def find_case_status_by_name(self, name):
        sid = self.statuses.get(str(name).strip())
        return {"case_status_id": sid} if sid is not None else None

    def save_record(self, spec, payload, record_id):
        self.saved.append((spec.key, payload))
        return 1


# --- 1. Template column generation -----------------------------------------


def test_template_exports_the_on_screen_customer_fields_only():
    """The template carries exactly the customer fields shown on the screen form,
    in field order — not the search grid's 5 columns, and NOT the form-hidden
    columns (installment duration/remaining/amount and the legacy extra area).

    The customer_id primary key is present (it is shown on the form) but is
    auto-assigned on import (see the id_field handling)."""
    io_spec = io_spec_for("customers")
    assert io_spec.headers == [
        "كود العميل",
        "اسم العميل",
        "الهاتف",
        "كود المنطقة",
        "رقم المنطقة",
        "المبنى",
        "الوحدة",
        "الدور",
        "الرقم الضريبي",
        "السجل التجاري",
        "العنوان",
    ]


def test_template_exports_every_company_column_not_just_the_grid():
    """Companies too: all real columns, not the 3-column search grid."""
    io_spec = io_spec_for("companies")
    assert io_spec.headers == [
        "كود الشركة",
        "اسم الشركة (عربي)",
        "اسم الشركة (إنجليزي)",
        "السجل التجاري",
        "الرقم الضريبي",
        "العنوان (عربي)",
        "العنوان (إنجليزي)",
    ]


def test_daily_followup_template_stays_pinned_to_its_resolver_columns():
    """The daily follow-up import resolves phone/status names, so its template is
    a curated set (pinned), NOT the table's raw customer_id/case_status_id columns."""
    io_spec = io_spec_for("daily_followups")
    assert io_spec.headers == [
        "كود المتابعة",
        "إسم العميل",
        "رقم التليفون",
        "تاريخ المتابعة",
        "الحالة",
        "ملاحظات",
    ]


def test_export_template_writes_headers_and_freezes_top_row(tmp_path):
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("employees")
    out = tmp_path / "employees_template.xlsx"

    service.export_template(io_spec, out)

    workbook = load_workbook(out)
    worksheet = workbook.active
    header = [cell.value for cell in worksheet[1]]
    assert header == io_spec.headers
    assert worksheet[1][0].font.bold is True
    assert worksheet.freeze_panes == "A2"
    # Template is empty apart from the header row.
    assert worksheet.max_row == 1


def test_customer_template_omits_form_hidden_columns():
    """Form-hidden customer fields never reach the template (nor the import)."""
    io_spec = io_spec_for("customers")
    keys = [column.key for column in io_spec.columns]
    for hidden in (
        "installment_duration_years",
        "remaining_installments",
        "installment_amount",
        "legacy_area_number_2",
    ):
        assert hidden not in keys


# --- 2. Column matching is by name: extra/missing/reordered columns tolerated -


def test_import_matches_columns_by_name_ignoring_extra_and_order():
    """A file may carry unknown extra columns, in any order — they are ignored,
    and the recognized columns are read by header name (so an older customer
    export with the retired installment columns still imports)."""
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("customers")
    header = ["اسم العميل", "الهاتف", "مدة الأقساط", "رقم منطقة إضافي", "كود العميل"]
    data_rows = [["Ahmed", "0100000009", "5", "99", "1001"]]

    aligned = service._align_rows_to_template(io_spec, header, data_rows)
    rows = service.build_import_rows(io_spec, aligned)

    assert len(rows) == 1 and rows[0].is_valid
    assert rows[0].payload["customer_name"] == "Ahmed"
    assert rows[0].payload["phone_number"] == "0100000009"


def test_import_missing_column_fails_only_that_row_not_the_whole_file():
    """A required column absent from the file does not reject the file; the row
    is just marked invalid (empty required field), so other rows can still save."""
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("customers")
    header = ["اسم العميل", "العنوان"]  # الهاتف (required) is missing
    data_rows = [["Ahmed", "Cairo"]]

    aligned = service._align_rows_to_template(io_spec, header, data_rows)
    rows = service.build_import_rows(io_spec, aligned)

    assert len(rows) == 1 and not rows[0].is_valid
    assert any("الهاتف" in e for e in rows[0].errors)


def test_import_rejects_file_with_no_recognizable_column():
    """Only guard left: a file that shares no column with the screen is rejected."""
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("customers")

    with pytest.raises(ExcelWorkbookError):
        service._align_rows_to_template(io_spec, ["A", "B", "C"], [["1", "2", "3"]])


# --- 3. Invalid row validation ---------------------------------------------


def test_missing_required_field_marks_row_invalid():
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("customers")
    # Col order now starts id, name, phone, ... (the full table). Name (col 2) is
    # blank so the row is invalid; phone (col 3) is present.
    rows = service.build_import_rows(io_spec, [["", "", "0100000001", "5", "12"]])

    assert len(rows) == 1
    assert not rows[0].is_valid
    assert any("اسم العميل" in e for e in rows[0].errors)


def test_invalid_date_and_unknown_foreign_key_marked_invalid():
    data = FakeDataService(customers={"0100known": 1001}, statuses={"مهتم": 3})
    service = ExcelTemplateService(data)
    io_spec = io_spec_for("daily_followups")
    # cols: id, customer_name, customer_phone, follow_up_date, case_status_name, notes
    rows = service.build_import_rows(
        io_spec,
        [
            ["", "Ali", "0100known", "2026-13-40", "مهتم", "n"],  # bad date
            ["", "Sara", "0100unknown", "2026-07-06", "مهتم", "n"],  # bad phone
        ],
    )

    assert not rows[0].is_valid and any("تاريخ" in e for e in rows[0].errors)
    assert not rows[1].is_valid and any("رقم التليفون" in e or "غير معروفة" in e for e in rows[1].errors)


def test_valid_daily_followup_row_resolves_foreign_keys():
    data = FakeDataService(customers={"0100known": 1001}, statuses={"مهتم": 3})
    service = ExcelTemplateService(data)
    io_spec = io_spec_for("daily_followups")

    rows = service.build_import_rows(
        io_spec, [["", "Ali", "0100known", "2026-07-06", "مهتم", "note"]]
    )

    assert rows[0].is_valid
    assert rows[0].payload["customer_id"] == 1001
    assert rows[0].payload["case_status_id"] == 3
    assert rows[0].payload["follow_up_date"] == datetime.date(2026, 7, 6)
    assert rows[0].payload["notes"] == "note"


# --- 4. Duplicate prevention -----------------------------------------------


def test_duplicate_against_existing_database_row():
    data = FakeDataService(existing={"customers": [{"phone_number": "0100000001"}]})
    service = ExcelTemplateService(data)
    io_spec = io_spec_for("customers")

    rows = service.build_import_rows(io_spec, [["", "Ahmed", "0100000001", "5", "1"]])

    assert not rows[0].is_valid
    assert any("مكرر" in e for e in rows[0].errors)


def test_duplicate_within_the_same_file():
    service = ExcelTemplateService(FakeDataService())
    io_spec = io_spec_for("places")
    # places cols: place_id, place_number
    rows = service.build_import_rows(io_spec, [["", "A1"], ["", "A1"]])

    assert rows[0].is_valid
    assert not rows[1].is_valid
    assert any("مكرر" in e for e in rows[1].errors)


# --- 5. Save valid rows only ------------------------------------------------


def test_save_valid_rows_only_persists_valid_rows():
    data = FakeDataService()
    service = ExcelTemplateService(data)
    io_spec = io_spec_for("case_statuses")
    # case_statuses cols: case_status_id, case_status_name
    rows = service.build_import_rows(
        io_spec,
        [
            ["", "جديد"],  # valid
            ["", ""],  # invalid: missing required name
            ["", "مغلق"],  # valid
        ],
    )

    saved, failures = service.save_valid_rows(io_spec, rows)

    assert saved == 2
    assert failures == []
    saved_names = [payload.get("case_status_name") for _key, payload in data.saved]
    assert saved_names == ["جديد", "مغلق"]
