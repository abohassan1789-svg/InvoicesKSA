"""Supply Contracts screen (عقود التوريد).

The contract's blanks laid out to fit without a vertical scroll (the user
dropped the side-by-side live preview on 2026-10-20): the usual green header
and CRUD toolbar, then

* البيانات الأساسية (with «طباعة الختم») beside التوريد والسداد;
* الطرف الأول beside الطرف الثاني;
* the list of saved contracts underneath (also F1).

The contract itself is seen in «طباعة العقد», which asks for one of the six
print layouts and opens the preview / PDF / print window.

The first party's name is a dropdown of «الشركات» and the second party's of
«العملاء»: picking one pre-fills the commercial register and the address, but
every value stays editable and is stored as typed (a name not in the list is
fine). The ids of the company / customer that pre-filled them are saved too.
"""

from __future__ import annotations

import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.review_data_service import ReviewDataService, TABLE_SPECS
from app.ui.common.theme import GREEN, TEXT, _button_style
from app.ui.dialogs.record_lookup_dialog import RecordLookupDialog
from app.ui.screens.base_crud_screen import BaseCrudScreen
from app.ui.screens.supply_contract_print import contract_day_name

# Typed on a new contract; every one stays editable.
NEW_CONTRACT_DEFAULTS = {
    "first_party_rep_title": "المدير العام",
    "second_party_rep_title": "المدير العام",
}

# Form rows, top to bottom: (group, fields per row, width share) side by side.
FORM_ROWS: tuple[tuple[tuple[str, int, int], ...], ...] = (
    (("البيانات الأساسية", 2, 2), ("التوريد والسداد", 3, 3)),
    (("الطرف الأول", 2, 1), ("الطرف الثاني", 2, 1)),
)


class SupplyContractsScreen(BaseCrudScreen):
    SPEC_KEY = "supply_contracts"

    SEARCH_PLACEHOLDER = "البحث برقم العقد أو اسم الطرف الأول أو الثاني أو التاريخ"

    def __init__(self, service: ReviewDataService, parent: QWidget | None = None) -> None:
        super().__init__(service, TABLE_SPECS[self.SPEC_KEY], parent)
        self.lookup_shortcut = QShortcut(QKeySequence("F1"), self)
        self.lookup_shortcut.activated.connect(self.open_contract_lookup)

    # --- layout ----------------------------------------------------------------
    def _install_extra_toolbar_buttons(self, layout) -> None:
        self.print_button = QPushButton("طباعة العقد")
        self.lookup_button = QPushButton("F1 بحث")
        for button, bg, hover in (
            (self.print_button, "#4338CA", "#3730A3"),
            (self.lookup_button, "#0E7490", "#155E75"),
        ):
            button.setFixedHeight(38)
            button.setStyleSheet(_button_style(bg, hover))
            layout.addWidget(button)
        self.print_button.clicked.connect(self.print_contract)
        self.lookup_button.clicked.connect(self.open_contract_lookup)

    def _build_content(self):
        content = QVBoxLayout()
        content.setSpacing(4)
        # Kept for BaseCrudScreen (new_record / _fill_form write to it) but not
        # laid out: رقم العقد already shows the current contract, and the row
        # it would take is what keeps the form scroll-free.
        self.summary_label = QLabel("سجل جديد")

        visible = [f for f in self.spec.fields if not f.hidden_on_form]
        self.group_boxes = {}
        for row in FORM_ROWS:
            line = QHBoxLayout()
            line.setSpacing(10)
            for group, columns, share in row:
                fields = [f for f in visible if f.group == group]
                box = self._build_field_group(group, fields, columns)
                grid = box.layout()
                grid.setContentsMargins(14, 16, 14, 10)
                grid.setVerticalSpacing(6)
                self.group_boxes[group] = box
                line.addWidget(box, share)
            content.addLayout(line)
        self._add_stamp_checkbox(self.group_boxes["البيانات الأساسية"])
        content.addWidget(self._build_list_panel(), 1)
        return content

    def _add_stamp_checkbox(self, box) -> None:
        """«طباعة الختم» in the free cell after اليوم."""
        self.stamp_checkbox = QCheckBox("طباعة الختم")
        self.stamp_checkbox.setChecked(True)
        self.stamp_checkbox.setToolTip("طباعة ختم شركة الطرف الأول تحت «الختم» في العقد")
        self.stamp_checkbox.setStyleSheet(
            f"QCheckBox {{ font-size:14px; font-weight:900; color:{TEXT}; spacing:8px; }}"
            f"QCheckBox::indicator {{ width:18px; height:18px; }}"
            f"QCheckBox::indicator:checked {{ background:{GREEN}; border:1px solid {GREEN}; border-radius:4px; }}"
            "QCheckBox::indicator:unchecked { background:#FFFFFF; border:1px solid #94A3B8; border-radius:4px; }"
        )
        grid = box.layout()
        grid.addWidget(self.stamp_checkbox, grid.rowCount() - 1, 2, 1, 2)

    # --- editors ---------------------------------------------------------------
    def _make_editor(self, field):
        if field.name == "first_party_name":
            combo = self._make_party_combo()
            self._fill_company_options(combo)
            combo.activated.connect(lambda _i: self._prefill_first_party())
            self.first_party_combo = combo
            return combo
        if field.name == "second_party_name":
            combo = self._make_party_combo()
            self._fill_combo(combo, self._customer_options(), "customer_id", "customer_name",
                             skip_blank_labels=True)
            combo.activated.connect(lambda _i: self._prefill_second_party())
            self.second_party_combo = combo
            return combo
        editor = super()._make_editor(field)
        if isinstance(editor, QLineEdit):
            editor.setLayoutDirection(Qt.RightToLeft)
            editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if field.name == "contract_date":
                editor.textChanged.connect(self._update_day)
        return editor

    def _make_party_combo(self) -> QComboBox:
        """Editable name combo: pick a known party or type any other name."""
        combo = self._make_combo(read_only_edit=False)
        combo.setLayoutDirection(Qt.RightToLeft)
        combo.lineEdit().setLayoutDirection(Qt.RightToLeft)
        combo.lineEdit().setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        combo.setInsertPolicy(QComboBox.NoInsert)
        if combo.completer() is not None:
            combo.completer().setCompletionMode(QCompleter.PopupCompletion)
            combo.completer().setFilterMode(Qt.MatchContains)
        return combo

    def _fill_company_options(self, combo: QComboBox) -> None:
        try:
            companies = self.service.list_companies_for_selection()
        except Exception:
            companies = []
        self._fill_combo(combo, companies, "id", "name_ar", skip_blank_labels=True)

    @staticmethod
    def _party_id(combo: QComboBox) -> Any | None:
        """The id behind the typed name, or None for a name not in the list."""
        text = combo.currentText().strip()
        if not text:
            return None
        index = combo.findText(text, Qt.MatchExactly)
        return combo.itemData(index) if index > 0 else None

    def _editor_value(self, editor):  # type: ignore[override]
        if editor is getattr(self, "first_party_combo", None) or editor is getattr(self, "second_party_combo", None):
            return editor.currentText().strip()
        return super()._editor_value(editor)

    def _set_editor_value(self, editor, value) -> None:  # type: ignore[override]
        if editor is not None and editor in (getattr(self, "first_party_combo", None),
                                             getattr(self, "second_party_combo", None)):
            editor.blockSignals(True)
            try:
                text = "" if value is None else str(value)
                index = editor.findText(text, Qt.MatchExactly) if text else 0
                editor.setCurrentIndex(max(0, index))
                editor.setEditText(text)
                editor.lineEdit().setCursorPosition(0)
            finally:
                editor.blockSignals(False)
            return
        super()._set_editor_value(editor, value)

    def _collect_payload(self) -> dict[str, Any]:  # type: ignore[override]
        payload = super()._collect_payload()
        payload.pop("contract_day", None)
        payload["first_party_company_id"] = self._party_id(self.first_party_combo)
        payload["second_party_customer_id"] = self._party_id(self.second_party_combo)
        payload["show_stamp"] = self.stamp_checkbox.isChecked()
        return payload

    # --- pre-fill from the company / customer ----------------------------------
    def _prefill_first_party(self) -> None:
        if self.mode not in {"new", "edit"}:
            return
        company_id = self._party_id(self.first_party_combo)
        if company_id is None:
            return
        try:
            company = self.service.get_company_details(company_id) or {}
        except Exception as exc:
            self._show_error("تعذر تحميل بيانات الشركة", exc)
            return
        self._prefill({
            "first_party_cr": company.get("commercial_registration"),
            "first_party_address": company.get("address_ar"),
        })

    def _prefill_second_party(self) -> None:
        if self.mode not in {"new", "edit"}:
            return
        customer_id = self._party_id(self.second_party_combo)
        if customer_id is None:
            return
        try:
            customer = self.service.get_record(TABLE_SPECS["customers"], customer_id) or {}
        except Exception as exc:
            self._show_error("تعذر تحميل بيانات العميل", exc)
            return
        self._prefill({
            "second_party_cr": customer.get("cr"),
            "second_party_address": customer.get("address"),
        })

    def _prefill(self, values: dict[str, Any]) -> None:
        """Copy the known values in; a blank in the source never wipes a typed one."""
        for name, value in values.items():
            if value not in (None, ""):
                self._set_editor_value(self.inputs.get(name), value)

    # --- derived values -------------------------------------------------------
    def _update_day(self, *_args) -> None:
        day_editor = self.inputs.get("contract_day")
        date_editor = self.inputs.get("contract_date")
        if day_editor is not None and date_editor is not None:
            day_editor.setText(contract_day_name(date_editor.text()))

    def contract_data(self) -> dict[str, Any]:
        """Every blank of the contract as currently shown on the form."""
        data = {name: self._editor_value(editor) for name, editor in self.inputs.items()}
        data.pop("contract_day", None)
        return {key: ("" if value is None else str(value).strip()) for key, value in data.items()}

    # --- CRUD hooks ------------------------------------------------------------
    def _fill_form(self, record: dict[str, Any]) -> None:
        super()._fill_form(record)
        self._update_day()
        self.stamp_checkbox.setChecked(record.get("show_stamp") is not False)
        self.summary_label.setText(f"العقد الحالي: {record.get('contract_number') or ''}")

    def _clear_form(self) -> None:
        super()._clear_form()
        self.stamp_checkbox.setChecked(True)

    def set_mode(self, mode: str) -> None:  # type: ignore[override]
        super().set_mode(mode)
        checkbox = getattr(self, "stamp_checkbox", None)
        if checkbox is not None:
            checkbox.setEnabled(mode in {"new", "edit"})

    def refresh_screen(self) -> None:  # type: ignore[override]
        for combo, refill in (
            (self.first_party_combo, self._fill_company_options),
            (self.second_party_combo, lambda c: self._fill_combo(
                c, self._customer_options(force_refresh=True), "customer_id", "customer_name",
                skip_blank_labels=True)),
        ):
            text = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
            refill(combo)
            self._set_editor_value(combo, text)
        super().refresh_screen()

    def new_record(self) -> None:  # type: ignore[override]
        super().new_record()
        self._set_editor_value(self.inputs.get("contract_date"), datetime.date.today().strftime("%Y-%m-%d"))
        for name, value in NEW_CONTRACT_DEFAULTS.items():
            self._set_editor_value(self.inputs.get(name), value)
        number_editor = self.inputs.get("contract_number")
        if number_editor is not None:
            try:
                hint = f"تلقائي: {self.service.peek_next_supply_contract_number()}"
            except Exception:
                hint = "تلقائي (CT-...)"
            number_editor.setPlaceholderText(hint)

    def save_record(self) -> None:  # type: ignore[override]
        exclude_id = None if self.mode == "new" else self.current_id
        number_editor = self.inputs.get("contract_number")
        number = (number_editor.text() if number_editor is not None else "").strip()
        if number:
            try:
                if self.service.value_exists(self.spec, "contract_number", number, exclude_id=exclude_id):
                    QMessageBox.warning(self, "قيمة مكررة", "رقم العقد مستخدم من قبل لعقد آخر.")
                    return
            except Exception:
                pass  # the UNIQUE index stays the final guard
        super().save_record()
        if self.mode != "view" or self.current_id is None:
            return  # the save failed; the base screen already said why
        if number:
            try:
                self.service.register_manual_supply_contract_number(number)
            except Exception:
                pass
        # Show what was stored, including the automatic CT-<n>.
        try:
            record = self.service.get_record(self.spec, self.current_id)
        except Exception:
            record = None
        if record:
            self._fill_form(record)

    def open_contract_lookup(self) -> None:
        if self.mode in {"new", "edit"}:
            return
        dialog = RecordLookupDialog(self.service, self.spec, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_id is not None:
            record = self.service.get_record(self.spec, dialog.selected_id)
            if record:
                self.current_id = dialog.selected_id
                self._fill_form(record)
                self.set_mode("view")
                self._select_row_by_id(self.current_id)

    # --- print -----------------------------------------------------------------
    def collect_print_data(self) -> dict[str, Any] | None:
        data: dict[str, Any] = dict(self.contract_data())
        if not data.get("first_party_name") or not data.get("second_party_name"):
            return None
        data["show_stamp"] = self.stamp_checkbox.isChecked()
        company_id = self._party_id(self.first_party_combo)
        if company_id is not None:
            try:
                data["first_party_company"] = self.service.get_company_details(company_id) or {}
            except Exception:
                data["first_party_company"] = {}
        return data

    def print_contract(self) -> None:
        data = self.collect_print_data()
        if data is None:
            QMessageBox.information(
                self, "طباعة العقد", "اختر عقداً من السجل أو أدخل اسم الطرفين أولاً."
            )
            return
        from app.ui.screens.supply_contract_print import (
            SupplyContractPreviewDialog,
            choose_supply_contract_builder,
        )

        builder = choose_supply_contract_builder(self)
        if builder is None:
            return
        SupplyContractPreviewDialog(data, parent=self, html_builder=builder).exec()
