"""Widget tests for the F1 invoice search dialog (headless / offscreen Qt).

Cover the two filters added on top of the existing text + status search: a
seller-company dropdown fed from the coded companies, and an optional issue-date
range that only constrains the query while it is switched on.
"""

from __future__ import annotations

import datetime
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.dialogs.saudi_invoice_dialogs import SaudiInvoiceSearchDialog

_DATE_COL = 3  # «التاريخ والوقت»


_ROWS = [
    {"id": 88, "invoice_number": "INV-88", "seller_name_ar_snapshot": "شركة أ",
     "customer_name_snapshot": "عميل",
     "issue_datetime": datetime.datetime(2026, 10, 11, 21, 5),
     "document_status": "draft", "total_including_vat": 115},
    {"id": 12, "invoice_number": "INV-12", "seller_name_ar_snapshot": "شركة ب",
     "customer_name_snapshot": "عميل ٢", "issue_datetime": None,
     "document_status": "approved", "total_including_vat": 230},
]


class FakeService:
    """Records every search_invoices call so the test can assert the filters."""

    def __init__(self):
        self.calls: list[dict] = []
        self.companies = [
            {"id": 10, "name_ar": "شركة أ", "name_en": "A"},
            {"id": 11, "name_ar": "شركة ب", "name_en": "B"},
        ]
        # Records every inline invoice-number rename; each entry raises if
        # ``rename_error`` is set, so tests can drive the failure path too.
        self.renames: list[dict] = []
        self.rename_error: Exception | None = None
        # Same idea for the inline date edit.
        self.date_changes: list[dict] = []
        self.date_error: Exception | None = None

    def list_companies(self, limit=100):
        return list(self.companies)

    def rename_invoice_number(self, invoice_id, new_number, *, user_id=None):
        self.renames.append(
            {"invoice_id": invoice_id, "new_number": new_number, "user_id": user_id}
        )
        if self.rename_error is not None:
            raise self.rename_error
        return {"header": {"id": invoice_id, "invoice_number": new_number}}

    def change_issue_datetime(self, invoice_id, new_datetime, *, user_id=None):
        self.date_changes.append(
            {"invoice_id": invoice_id, "new_datetime": new_datetime, "user_id": user_id}
        )
        if self.date_error is not None:
            raise self.date_error
        return {"header": {"id": invoice_id, "issue_datetime": new_datetime}}

    def search_invoices(self, keyword="", status=None, limit=300, *,
                        company_id=None, date_from=None, date_to=None,
                        newest_first=True):
        self.calls.append({
            "keyword": keyword, "status": status, "limit": limit,
            "company_id": company_id, "date_from": date_from, "date_to": date_to,
            "newest_first": newest_first,
        })
        return [dict(r) for r in _ROWS]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def dialog(qapp):
    return SaudiInvoiceSearchDialog(FakeService())


@pytest.fixture()
def exported(qapp):
    """A dialog wired to a recording print callback, plus that record."""
    calls: list[tuple] = []
    dlg = SaudiInvoiceSearchDialog(
        FakeService(), print_callback=lambda iid, parent: calls.append((iid, parent))
    )
    return dlg, calls


@pytest.fixture()
def phase1_wired(qapp):
    """A dialog wired to a recording Phase-1 callback, plus that record."""
    calls: list[tuple] = []
    dlg = SaudiInvoiceSearchDialog(
        FakeService(), phase1_callback=lambda iid, parent: calls.append((iid, parent))
    )
    return dlg, calls


@pytest.fixture()
def voucher_wired(qapp):
    """A dialog wired to a recording voucher callback, plus that record."""
    calls: list[tuple] = []
    dlg = SaudiInvoiceSearchDialog(
        FakeService(), voucher_callback=lambda iid, parent: calls.append((iid, parent))
    )
    return dlg, calls


def test_company_combo_lists_all_companies_plus_all_option(dialog):
    combo = dialog.company_combo
    # first entry is the "all companies" sentinel with no id
    assert combo.itemData(0) is None
    assert combo.itemText(0) == "كل الشركات"
    # every coded company follows, in order
    assert combo.count() == 3
    assert combo.itemData(1) == 10
    assert combo.itemData(2) == 11
    assert combo.itemText(1) == "شركة أ"


def test_date_range_is_off_by_default(dialog):
    assert dialog.date_enable.isChecked() is False
    assert dialog.date_from.isEnabled() is False
    assert dialog.date_to.isEnabled() is False
    # the initial auto-search carries no company/date constraint
    first = dialog.service.calls[0]
    assert first["company_id"] is None
    assert first["date_from"] is None and first["date_to"] is None


def test_selecting_a_company_filters_by_its_id(dialog):
    dialog.service.calls.clear()
    dialog.company_combo.setCurrentIndex(2)  # شركة ب -> id 11
    assert dialog.service.calls[-1]["company_id"] == 11


def test_enabling_date_range_passes_from_and_to(dialog):
    dialog.date_from.setDate(dialog.date_from.date().addDays(0))  # keep default
    dialog.service.calls.clear()
    dialog.date_enable.setChecked(True)

    assert dialog.date_from.isEnabled() is True
    assert dialog.date_to.isEnabled() is True
    last = dialog.service.calls[-1]
    assert isinstance(last["date_from"], datetime.date)
    assert isinstance(last["date_to"], datetime.date)
    assert last["date_from"] <= last["date_to"]


def test_date_edits_do_not_query_while_range_is_off(dialog):
    assert dialog.date_enable.isChecked() is False
    dialog.service.calls.clear()
    dialog.date_from.setDate(dialog.date_from.date().addDays(-5))
    # changing a disabled date must not trigger a search
    assert dialog.service.calls == []


# --- the per-row «تصدير» PDF column ---------------------------------------

def test_export_column_is_the_last_column_named_tasdeer(dialog):
    table = dialog.table
    last = table.columnCount() - 1
    assert table.horizontalHeaderItem(last).text() == "تصدير"
    # it does not displace the invoice record carried on column 0 (the whole row
    # dict rides there now, so inline number-edit can validate; id stays reachable)
    assert table.item(0, 0).data(Qt.UserRole)["id"] == 88


def test_every_row_has_a_pdf_link_in_the_export_column(dialog):
    table = dialog.table
    last = table.columnCount() - 1
    assert table.rowCount() == 2
    for r in range(table.rowCount()):
        widget = table.cellWidget(r, last)
        assert widget is not None
        assert "PDF" in widget.text()


def test_clicking_pdf_link_invokes_the_print_callback_with_row_id(exported, qapp):
    dlg, calls = exported
    last = dlg.table.columnCount() - 1
    link = dlg.table.cellWidget(0, last)
    link.clicked.emit()  # simulate the click on the hyperlink
    # The print flow is deferred a tick so the click can unwind first.
    assert calls == []
    qapp.processEvents()
    assert calls == [(88, dlg)]


def test_pdf_link_fires_on_release_not_on_press(qapp):
    # Opening a modal dialog while the press's mouse grab is still held freezes
    # the app once nested a few modal loops deep — so the link must activate on
    # RELEASE (grab already dropped), never on press.
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    from app.ui.dialogs.saudi_invoice_dialogs import _PdfLinkLabel

    link = _PdfLinkLabel("PDF")
    link.resize(60, 30)
    fired = []
    link.clicked.connect(lambda: fired.append(1))

    pos = QPointF(10, 10)
    link.mousePressEvent(
        QMouseEvent(QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    )
    assert fired == []  # press alone must not activate

    link.mouseReleaseEvent(
        QMouseEvent(QEvent.MouseButtonRelease, pos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    )
    assert fired == [1]  # release inside the widget activates exactly once


def test_pdf_link_without_a_callback_does_not_raise(dialog, monkeypatch):
    # No print_callback wired: the link must degrade gracefully, not explode.
    infos = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.information",
        lambda *a, **k: infos.append(a),
    )
    dialog._on_export_clicked(88)
    assert len(infos) == 1


# --- the per-row «مرحلة أولى» Phase-1 column -------------------------------

def _col_index(dialog, key):
    return [k for k, _h in dialog._COLUMNS].index(key)


def test_phase1_column_sits_next_to_the_export_column(dialog):
    from app.ui.dialogs.saudi_invoice_dialogs import _EXPORT_COL_KEY, _PHASE1_COL_KEY

    table = dialog.table
    last = table.columnCount() - 1
    # «تصدير» stays the last column; «مرحلة أولى» is immediately before it.
    assert table.horizontalHeaderItem(last).text() == "تصدير"
    assert table.horizontalHeaderItem(last - 1).text() == "مرحلة أولى"
    assert _col_index(dialog, _EXPORT_COL_KEY) == last
    assert _col_index(dialog, _PHASE1_COL_KEY) == last - 1


def test_every_row_has_a_link_in_the_phase1_column(dialog):
    from app.ui.dialogs.saudi_invoice_dialogs import _PHASE1_COL_KEY

    col = _col_index(dialog, _PHASE1_COL_KEY)
    assert dialog.table.rowCount() == 2
    for r in range(dialog.table.rowCount()):
        widget = dialog.table.cellWidget(r, col)
        assert widget is not None
        assert "PDF" in widget.text()


def test_clicking_phase1_link_invokes_the_phase1_callback_with_row_id(phase1_wired, qapp):
    from app.ui.dialogs.saudi_invoice_dialogs import _PHASE1_COL_KEY

    dlg, calls = phase1_wired
    col = _col_index(dlg, _PHASE1_COL_KEY)
    dlg.table.cellWidget(0, col).clicked.emit()
    # Deferred a tick like the export link, so it can unwind first.
    assert calls == []
    qapp.processEvents()
    assert calls == [(88, dlg)]


def test_phase1_and_export_links_are_independent(exported, qapp):
    # A dialog wired ONLY for Phase-2 export must not fire anything for the
    # Phase-1 link (its callback is None) and vice-versa.
    from app.ui.dialogs.saudi_invoice_dialogs import _PHASE1_COL_KEY

    dlg, calls = exported
    infos = []
    dlg._phase1_callback = None
    import app.ui.dialogs.saudi_invoice_dialogs as mod
    original = mod.QMessageBox.information
    mod.QMessageBox.information = lambda *a, **k: infos.append(a)
    try:
        col = _col_index(dlg, _PHASE1_COL_KEY)
        dlg.table.cellWidget(0, col).clicked.emit()
        qapp.processEvents()
    finally:
        mod.QMessageBox.information = original
    assert calls == []       # the export recorder never fired
    assert len(infos) == 1   # the Phase-1 link reported "service unavailable"


def test_phase1_link_without_a_callback_does_not_raise(dialog, monkeypatch):
    infos = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.information",
        lambda *a, **k: infos.append(a),
    )
    dialog._on_phase1_clicked(88)
    assert len(infos) == 1


# --- the per-row «سندات» receipt-voucher column ----------------------------

def test_voucher_column_sits_before_the_phase1_column(dialog):
    from app.ui.dialogs.saudi_invoice_dialogs import (
        _EXPORT_COL_KEY,
        _PHASE1_COL_KEY,
        _VOUCHER_COL_KEY,
    )

    table = dialog.table
    last = table.columnCount() - 1
    # Visual left→right (last→…): تصدير, مرحلة أولى, سندات.
    assert table.horizontalHeaderItem(last).text() == "تصدير"
    assert table.horizontalHeaderItem(last - 1).text() == "مرحلة أولى"
    assert table.horizontalHeaderItem(last - 2).text() == "سندات"
    assert _col_index(dialog, _EXPORT_COL_KEY) == last
    assert _col_index(dialog, _PHASE1_COL_KEY) == last - 1
    assert _col_index(dialog, _VOUCHER_COL_KEY) == last - 2


def test_every_row_has_a_link_in_the_voucher_column(dialog):
    from app.ui.dialogs.saudi_invoice_dialogs import _VOUCHER_COL_KEY

    col = _col_index(dialog, _VOUCHER_COL_KEY)
    assert dialog.table.rowCount() == 2
    for r in range(dialog.table.rowCount()):
        widget = dialog.table.cellWidget(r, col)
        assert widget is not None
        assert "PDF" in widget.text()


def test_clicking_voucher_link_invokes_the_voucher_callback_with_row_id(voucher_wired, qapp):
    from app.ui.dialogs.saudi_invoice_dialogs import _VOUCHER_COL_KEY

    dlg, calls = voucher_wired
    col = _col_index(dlg, _VOUCHER_COL_KEY)
    dlg.table.cellWidget(0, col).clicked.emit()
    assert calls == []
    qapp.processEvents()
    assert calls == [(88, dlg)]


def test_voucher_link_without_a_callback_does_not_raise(dialog, monkeypatch):
    infos = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.information",
        lambda *a, **k: infos.append(a),
    )
    dialog._on_voucher_clicked(88)
    assert len(infos) == 1


# --- inline «رقم الفاتورة» edit -------------------------------------------

def test_draft_number_cell_is_editable_but_other_cells_are_not(dialog):
    table = dialog.table
    # Row 0 is a draft: its number cell (col 0) accepts editing.
    assert bool(table.item(0, 0).flags() & Qt.ItemIsEditable)
    # No other text column on that row is editable except the date (col 3, see
    # the date tests below); the link columns hold cell widgets, not items, so
    # table.item(...) is None there — skip them.
    for c in range(1, table.columnCount()):
        if c == _DATE_COL:
            continue
        item = table.item(0, c)
        if item is None:
            continue
        assert not (item.flags() & Qt.ItemIsEditable)


def test_approved_number_cell_is_locked(dialog):
    # Row 1 is «مُصدَّرة» (approved): its number must NOT be inline-editable.
    assert not (dialog.table.item(1, 0).flags() & Qt.ItemIsEditable)


def test_editing_a_draft_number_persists_via_the_service(dialog):
    table = dialog.table
    # Simulate the user committing a new number in the cell.
    table.item(0, 0).setText("INV-NEW")
    assert dialog.service.renames == [
        {"invoice_id": 88, "new_number": "INV-NEW", "user_id": None}
    ]
    # The cell and the carried record both reflect the saved value.
    assert table.item(0, 0).text() == "INV-NEW"
    assert table.item(0, 0).data(Qt.UserRole)["invoice_number"] == "INV-NEW"


def test_no_op_edit_does_not_call_the_service(dialog):
    table = dialog.table
    table.item(0, 0).setText("INV-88")  # unchanged value
    assert dialog.service.renames == []


def test_blank_number_is_rejected_and_reverted(dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.warning",
        lambda *a, **k: warnings.append(a),
    )
    table = dialog.table
    table.item(0, 0).setText("   ")
    assert dialog.service.renames == []      # never reached the service
    assert len(warnings) == 1                # the user was told
    assert table.item(0, 0).text() == "INV-88"  # cell reverted


def test_service_rejection_reverts_the_cell(dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.warning",
        lambda *a, **k: warnings.append(a),
    )
    dialog.service.rename_error = ValueError("رقم الفاتورة مستخدم مسبقًا لنفس الشركة.")
    table = dialog.table
    table.item(0, 0).setText("INV-12")  # a duplicate the service refuses
    assert len(dialog.service.renames) == 1  # attempted
    assert len(warnings) == 1                # surfaced the error
    assert table.item(0, 0).text() == "INV-88"  # reverted to the stored value


def test_double_clicking_the_number_column_does_not_open(dialog):
    # The number cell is for editing; opening happens from any other column or
    # the «فتح» button. A double-click on col 0 must not accept the dialog.
    dialog._on_item_double_clicked(dialog.table.item(0, 0))
    assert dialog.selected_id is None


def test_double_clicking_another_column_opens_the_invoice(dialog):
    dialog.table.setCurrentCell(0, 1)
    dialog._on_item_double_clicked(dialog.table.item(0, 1))
    assert dialog.selected_id == 88


# --- inline «التاريخ والوقت» edit (single click) ---------------------------

def test_draft_date_cell_is_editable(dialog):
    assert bool(dialog.table.item(0, _DATE_COL).flags() & Qt.ItemIsEditable)


def test_approved_date_cell_is_locked(dialog):
    assert not (dialog.table.item(1, _DATE_COL).flags() & Qt.ItemIsEditable)


def test_single_click_on_a_draft_date_starts_editing(dialog, monkeypatch):
    edited = []
    monkeypatch.setattr(dialog.table, "editItem", lambda item: edited.append(item))
    item = dialog.table.item(0, _DATE_COL)
    dialog._on_item_clicked(item)
    assert edited == [item]


def test_single_click_on_an_approved_date_does_not_edit(dialog, monkeypatch):
    edited = []
    monkeypatch.setattr(dialog.table, "editItem", lambda item: edited.append(item))
    dialog._on_item_clicked(dialog.table.item(1, _DATE_COL))
    dialog._on_item_clicked(dialog.table.item(0, 1))  # another column
    assert edited == []


def test_date_column_uses_a_datetime_editor(dialog, qapp):
    from PySide6.QtWidgets import QDateTimeEdit, QStyleOptionViewItem

    table = dialog.table
    delegate = table.itemDelegateForColumn(_DATE_COL)
    index = table.model().index(0, _DATE_COL)
    editor = delegate.createEditor(table.viewport(), QStyleOptionViewItem(), index)
    assert isinstance(editor, QDateTimeEdit)
    delegate.setEditorData(editor, index)
    assert editor.dateTime().toPython() == datetime.datetime(2026, 10, 11, 21, 5)


def test_editing_a_draft_date_persists_via_the_service(dialog):
    table = dialog.table
    table.item(0, _DATE_COL).setText("2026-10-09 14:30")
    assert dialog.service.date_changes == [
        {"invoice_id": 88, "new_datetime": datetime.datetime(2026, 10, 9, 14, 30),
         "user_id": None}
    ]
    assert table.item(0, _DATE_COL).text() == "2026-10-09 14:30"
    record = table.item(0, 0).data(Qt.UserRole)
    assert record["issue_datetime"] == datetime.datetime(2026, 10, 9, 14, 30)


def test_unchanged_date_does_not_call_the_service(dialog):
    dialog.table.item(0, _DATE_COL).setText("2026-10-11 21:05")
    assert dialog.service.date_changes == []


def test_invalid_date_text_is_rejected_and_reverted(dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.warning",
        lambda *a, **k: warnings.append(a),
    )
    table = dialog.table
    table.item(0, _DATE_COL).setText("not a date")
    assert dialog.service.date_changes == []
    assert len(warnings) == 1
    assert table.item(0, _DATE_COL).text() == "2026-10-11 21:05"


def test_service_rejection_reverts_the_date(dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(
        "app.ui.dialogs.saudi_invoice_dialogs.QMessageBox.warning",
        lambda *a, **k: warnings.append(a),
    )
    dialog.service.date_error = ValueError("لا يمكن تعديل فاتورة مُصدَّرة.")
    table = dialog.table
    table.item(0, _DATE_COL).setText("2026-10-09 14:30")
    assert len(dialog.service.date_changes) == 1
    assert len(warnings) == 1
    assert table.item(0, _DATE_COL).text() == "2026-10-11 21:05"


def test_double_clicking_the_date_column_does_not_open(dialog):
    dialog._on_item_double_clicked(dialog.table.item(0, _DATE_COL))
    assert dialog.selected_id is None
