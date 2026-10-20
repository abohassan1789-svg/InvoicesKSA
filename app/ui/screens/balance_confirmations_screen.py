"""Balance Confirmations screen (مصادقة على الرصيد).

The «الخطوات الثلاث» layout the user picked from the 2026-10-20 mock-ups
(النموذج الخامس): the usual green header and CRUD toolbar, then three panels
side by side that follow the order of the work —

1. العميل والتاريخ — رقم الحركة, التاريخ, الشركة, اسم العميل;
2. مراجعة الرصيد — the customer's invoices, receipts and remaining balance
   («عليكم» / «لكم»), recomputed live while editing;
3. البيان والحفظ — the optional البيان with «حفظ» and «حفظ وطباعة»;

and the search list of saved confirmations underneath.

``الشركة`` lists «كل الشركات» first (stored as NULL — the balance spans every
company) followed by each company. The balance is never typed: the service
recomputes it from the customer statement on save, and the screen only shows a
live preview of the same figures.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.review_data_service import ALL_COMPANIES_LABEL, ReviewDataService, TABLE_SPECS
from app.ui.common.theme import GREEN, TEXT, _button_style
from app.ui.screens.balance_confirmation_print import balance_direction
from app.ui.screens.base_crud_screen import BaseCrudScreen

_ZERO = Decimal("0.00")

# The three steps, in order: (step key, caption).
STEPS: tuple[tuple[str, str], ...] = (
    ("customer", "العميل والتاريخ"),
    ("balance", "مراجعة الرصيد"),
    ("save", "البيان والحفظ"),
)

_PANEL_STYLE = (
    "QFrame#stepPanel { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:7px; }"
    f"QFrame#stepPanel[active=\"true\"] {{ border:2px solid {GREEN}; }}"
)


def _money(value: Any) -> str:
    try:
        return f"{Decimal(str(value if value not in (None, '') else 0)):,.2f}"
    except Exception:  # noqa: BLE001 - defensive formatting
        return "0.00"


class BalanceConfirmationsScreen(BaseCrudScreen):
    SPEC_KEY = "balance_confirmations"

    SEARCH_PLACEHOLDER = "البحث برقم الحركة أو اسم العميل أو الشركة أو التاريخ"

    def __init__(self, service: ReviewDataService, parent: QWidget | None = None) -> None:
        # The figures shown in step 2 (the stored snapshot, or the live preview).
        self._totals: dict[str, Decimal] = {
            "total_debit": _ZERO, "total_credit": _ZERO, "balance": _ZERO,
        }
        super().__init__(service, TABLE_SPECS[self.SPEC_KEY], parent)

    # --- layout ----------------------------------------------------------------
    def _install_extra_toolbar_buttons(self, layout) -> None:
        self.print_button = QPushButton("طباعة مصادقة")
        self.print_button.setFixedHeight(38)
        self.print_button.setStyleSheet(_button_style("#4338CA", "#3730A3"))
        self.print_button.clicked.connect(self.print_confirmation)
        layout.addWidget(self.print_button)

    def _build_content(self):
        content = QVBoxLayout()
        content.setSpacing(8)
        content.addLayout(self._build_steps_bar())
        content.addLayout(self._build_step_panels())
        content.addWidget(self._build_list_panel(), 1)
        return content

    def _build_steps_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.step_labels: dict[str, QLabel] = {}
        for index, (key, caption) in enumerate(STEPS, start=1):
            label = QLabel(f"{index}   {caption}")
            label.setMinimumHeight(36)
            self.step_labels[key] = label
            bar.addWidget(label, 1)
        return bar

    def _build_step_panels(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        fields = {f.name: f for f in self.spec.fields}

        # Kept for BaseCrudScreen (new_record / _fill_form write to it).
        self.summary_label = QLabel("سجل جديد")
        self.summary_label.setStyleSheet("font-size:12px; font-weight:700; color:#64748B;")

        # 1 — العميل والتاريخ
        panel1, grid1 = self._step_panel("customer", "1 · العميل والتاريخ")
        for line, name in enumerate(("confirmation_number", "confirmation_date", "company_id", "customer_id")):
            self._add_field(grid1, line, fields[name])
        grid1.addWidget(self.summary_label, 4, 0, 1, 2)

        # 2 — مراجعة الرصيد
        panel2, grid2 = self._step_panel("balance", "2 · مراجعة الرصيد")
        self.debit_value = self._figure(grid2, 0, "إجمالي الفواتير")
        self.credit_value = self._figure(grid2, 1, "إجمالي المقبوضات")
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color:#E2E8F0;")
        grid2.addWidget(divider, 2, 0, 1, 2)
        self.balance_value = self._figure(grid2, 3, "الرصيد المتبقي", big=True)
        self.direction_chip = QLabel("")
        self.direction_chip.setAlignment(Qt.AlignCenter)
        grid2.addWidget(self.direction_chip, 4, 0, 1, 2, Qt.AlignLeft)
        self.as_of_label = QLabel("")
        self.as_of_label.setStyleSheet("font-size:12px; font-weight:700; color:#64748B;")
        grid2.addWidget(self.as_of_label, 5, 0, 1, 2)

        # 3 — البيان والحفظ
        panel3, grid3 = self._step_panel("save", "3 · البيان والحفظ")
        self._add_field(grid3, 0, fields["description"])
        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.step_save_button = QPushButton("حفظ")
        self.step_save_print_button = QPushButton("حفظ وطباعة")
        for button, bg, hover in (
            (self.step_save_button, "#2563EB", "#1D4ED8"),
            (self.step_save_print_button, "#4338CA", "#3730A3"),
        ):
            button.setFixedHeight(38)
            button.setStyleSheet(_button_style(bg, hover))
            actions.addWidget(button)
        actions.addStretch(1)
        grid3.addLayout(actions, 1, 0, 1, 2)
        self.step_save_button.clicked.connect(self.save_record)
        self.step_save_print_button.clicked.connect(self.save_and_print)

        for panel in (panel1, panel2, panel3):
            row.addWidget(panel, 1)
        return row

    def _step_panel(self, key: str, title: str) -> tuple[QFrame, QGridLayout]:
        panel = QFrame()
        panel.setObjectName("stepPanel")
        panel.setStyleSheet(_PANEL_STYLE)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(8)
        heading = QLabel(title)
        heading.setStyleSheet(f"font-size:15px; font-weight:900; color:{GREEN}; border:none;")
        outer.addWidget(heading)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        outer.addLayout(grid)
        outer.addStretch(1)
        if not hasattr(self, "step_panels"):
            self.step_panels: dict[str, QFrame] = {}
        self.step_panels[key] = panel
        return panel, grid

    def _add_field(self, grid: QGridLayout, line: int, field) -> None:
        label = QLabel(field.label)
        label.setMinimumWidth(90)
        label.setStyleSheet(f"font-size:14px; font-weight:900; color:{TEXT}; border:none;")
        editor = self._make_editor(field)
        self.inputs[field.name] = editor
        grid.addWidget(label, line, 0)
        grid.addWidget(editor, line, 1)

    def _figure(self, grid: QGridLayout, line: int, caption: str, big: bool = False) -> QLabel:
        label = QLabel(caption)
        value = QLabel("0.00")
        value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if big:
            label.setStyleSheet(f"font-size:16px; font-weight:900; color:{GREEN}; border:none;")
            value.setStyleSheet(f"font-size:26px; font-weight:900; color:{GREEN}; border:none;")
        else:
            label.setStyleSheet("font-size:14px; font-weight:800; color:#334155; border:none;")
            value.setStyleSheet(f"font-size:16px; font-weight:900; color:{TEXT}; border:none;")
        grid.addWidget(label, line, 0)
        grid.addWidget(value, line, 1)
        return value

    # --- editors ---------------------------------------------------------------
    def _make_editor(self, field):
        if field.name == "customer_id":
            combo = self._make_search_combo()
            self._fill_combo(combo, self._customer_options(), "customer_id", "customer_name",
                             skip_blank_labels=True)
            self.customer_combo = combo
            combo.currentIndexChanged.connect(self._on_inputs_changed)
            return combo
        if field.name == "company_id":
            combo = self._make_search_combo()
            self._fill_company_combo(combo)
            self.company_combo = combo
            combo.currentIndexChanged.connect(self._on_inputs_changed)
            return combo
        editor = super()._make_editor(field)
        if field.name == "confirmation_date":
            editor.editingFinished.connect(self._on_inputs_changed)
        return editor

    def _make_search_combo(self) -> QComboBox:
        """Editable combo with contains-completion (search by any part of the name)."""
        combo = self._make_combo(read_only_edit=False)
        combo.setInsertPolicy(QComboBox.NoInsert)
        if combo.completer() is not None:
            combo.completer().setCompletionMode(QCompleter.PopupCompletion)
            combo.completer().setFilterMode(Qt.MatchContains)
        combo.lineEdit().editingFinished.connect(lambda c=combo: self._commit_source_combo_text(c))
        return combo

    def _fill_company_combo(self, combo: QComboBox) -> None:
        """«كل الشركات» (NULL) first, then every company by name."""
        combo.blockSignals(True)
        try:
            combo.addItem(ALL_COMPANIES_LABEL, None)
            try:
                companies = self.service.list_companies_for_selection()
            except Exception:
                companies = []
            for company in companies:
                if company.get("name_ar") not in (None, ""):
                    combo.addItem(str(company["name_ar"]), company.get("id"))
        finally:
            combo.blockSignals(False)

    def _reload_selection_combos(self) -> None:
        """Rebuild the customer/company dropdowns, keeping the current pick."""
        for combo, refill in (
            (getattr(self, "customer_combo", None), lambda c: self._fill_combo(
                c, self._customer_options(force_refresh=True), "customer_id", "customer_name",
                skip_blank_labels=True)),
            (getattr(self, "company_combo", None), self._fill_company_combo),
        ):
            if combo is None:
                continue
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
            refill(combo)
            self._set_editor_value(combo, current)

    def refresh_screen(self) -> None:  # type: ignore[override]
        self._reload_selection_combos()
        super().refresh_screen()

    # --- balance (step 2) ------------------------------------------------------
    def _on_inputs_changed(self, *_args) -> None:
        """Recompute the live balance while a confirmation is being edited."""
        if self.mode not in {"new", "edit"}:
            return
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            self._set_totals(None)
            return
        try:
            totals = self.service.customer_balance(
                customer_id, self.company_combo.currentData(), self._date_text()
            )
        except Exception as exc:
            self._show_error("تعذر حساب الرصيد", exc)
            return
        self._set_totals(totals)

    def _date_text(self) -> str:
        editor = self.inputs.get("confirmation_date")
        text = editor.text().strip() if editor is not None else ""
        return text or datetime.date.today().strftime("%Y-%m-%d")

    def _set_totals(self, totals: dict[str, Any] | None) -> None:
        totals = totals or {}
        self._totals = {
            key: Decimal(str(totals.get(key) or 0))
            for key in ("total_debit", "total_credit", "balance")
        }
        self.debit_value.setText(_money(self._totals["total_debit"]))
        self.credit_value.setText(_money(self._totals["total_credit"]))
        balance = self._totals["balance"]
        self.balance_value.setText(_money(abs(balance)))
        has_customer = totals != {}
        if has_customer:
            owes = balance >= 0
            self.direction_chip.setText(
                "الرصيد صفر" if balance == 0
                else f"{balance_direction(balance)} · {'مدين' if owes else 'دائن'}"
            )
            colors = ("#FEE2E2", "#991B1B", "#FECACA") if owes else ("#DCFCE7", "#166534", "#BBF7D0")
            self.direction_chip.setStyleSheet(
                f"background:{colors[0]}; color:{colors[1]}; border:1px solid {colors[2]}; "
                "border-radius:11px; padding:3px 12px; font-weight:800;"
            )
            self.as_of_label.setText(f"حتى تاريخ {self._date_text()}")
        else:
            self.direction_chip.setText("")
            self.direction_chip.setStyleSheet("border:none;")
            self.as_of_label.setText("اختر العميل لعرض رصيده")
        self._update_steps()

    def _update_steps(self) -> None:
        """Colour the steps bar: done ✓ / current / pending."""
        if not hasattr(self, "step_labels"):
            return
        has_customer = getattr(self, "customer_combo", None) is not None and \
            self.customer_combo.currentData() is not None
        states = {
            "customer": "done" if has_customer else "on",
            "balance": "done" if has_customer else "todo",
            "save": "on" if has_customer else "todo",
        }
        styles = {
            "done": "background:#FFFFFF; color:#065F2C; border:1px solid #B7E4C7;",
            "on": f"background:#FFFFFF; color:{TEXT}; border:2px solid {GREEN};",
            "todo": "background:#FFFFFF; color:#64748B; border:1px solid #E2E8F0;",
        }
        for index, (key, caption) in enumerate(STEPS, start=1):
            state = states[key]
            mark = "✓" if state == "done" else str(index)
            self.step_labels[key].setText(f"  {mark}   {caption}")
            self.step_labels[key].setStyleSheet(
                styles[state] + "border-radius:7px; padding:6px 12px; font-weight:800; font-size:14px;"
            )
            panel = self.step_panels.get(key)
            if panel is not None:
                panel.setProperty("active", "true" if state == "on" else "false")
                panel.setStyleSheet(_PANEL_STYLE)

    # --- CRUD hooks ------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        super().set_mode(mode)
        editing = mode in {"new", "edit"}
        for button in (getattr(self, "step_save_button", None),
                       getattr(self, "step_save_print_button", None)):
            if button is not None:
                button.setEnabled(editing and self._perm_save)
        if mode == "edit":
            # Editing re-sends the letter as of today's figures: show them.
            self._on_inputs_changed()

    def _fill_form(self, record: dict[str, Any]) -> None:
        super()._fill_form(record)
        # A saved confirmation shows the balance it was sent with (its snapshot),
        # not today's figure.
        self._set_totals({key: record.get(key) for key in ("total_debit", "total_credit", "balance")})
        self.as_of_label.setText(f"حتى تاريخ {record.get('confirmation_date') or ''}")
        self.summary_label.setText(f"الحركة الحالية: {record.get('confirmation_number') or ''}")

    def _clear_form(self) -> None:
        super()._clear_form()
        self._set_totals(None)

    def new_record(self) -> None:  # type: ignore[override]
        super().new_record()
        self._set_editor_value(
            self.inputs.get("confirmation_date"), datetime.date.today().strftime("%Y-%m-%d")
        )
        number_editor = self.inputs.get("confirmation_number")
        if number_editor is not None:
            try:
                suggested = self.service.peek_next_balance_confirmation_number()
                hint = f"تلقائي: {suggested}"
            except Exception:
                hint = "تلقائي (BC-...)"
            number_editor.setPlaceholderText(hint)
        self._set_totals(None)

    def save_record(self) -> None:  # type: ignore[override]
        exclude_id = None if self.mode == "new" else self.current_id
        number_editor = self.inputs.get("confirmation_number")
        number = (number_editor.text() if number_editor is not None else "").strip()
        if number:
            try:
                if self.service.value_exists(self.spec, "confirmation_number", number, exclude_id=exclude_id):
                    QMessageBox.warning(self, "قيمة مكررة", "رقم الحركة مستخدم من قبل لمصادقة أخرى.")
                    return
            except Exception:
                pass  # the UNIQUE index stays the final guard
        super().save_record()
        if self.mode != "view" or self.current_id is None:
            return  # the save failed; the base screen already said why
        if number:
            try:
                self.service.register_manual_balance_confirmation_number(number)
            except Exception:
                pass
        # Show what was stored: the automatic BC-<n> and the recomputed balance.
        try:
            record = self.service.get_record(self.spec, self.current_id)
        except Exception:
            record = None
        if record:
            self._fill_form(record)

    def save_and_print(self) -> None:
        self.save_record()
        if self.mode == "view" and self.current_id is not None:
            self.print_confirmation()

    # --- print -----------------------------------------------------------------
    def print_confirmation(self) -> None:
        data = self._collect_print_data()
        if data is None:
            QMessageBox.information(
                self, "طباعة مصادقة", "اختر مصادقة من القائمة أو أدخل بياناتها أولاً."
            )
            return
        from app.ui.screens.balance_confirmation_print import BalanceConfirmationPreviewDialog

        BalanceConfirmationPreviewDialog(data, parent=self).exec()

    def _collect_print_data(self) -> dict[str, Any] | None:
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            return None
        company_id = self.company_combo.currentData()
        seller: dict[str, Any] | None = None
        if company_id is not None:
            try:
                company = self.service.get_company_details(company_id) or {}
            except Exception:
                company = {}
            seller = {
                "name": company.get("name_ar") or self.company_combo.currentText().strip(),
                "logo": company.get("logo"),
                "logo_mime": company.get("logo_mime"),
                "stamp": company.get("stamp"),
                "stamp_mime": company.get("stamp_mime"),
            }
        number_editor = self.inputs.get("confirmation_number")
        description_editor = self.inputs.get("description")
        return {
            "number": number_editor.text().strip() if number_editor is not None else "",
            "date": self._date_text(),
            "customer": self.customer_combo.currentText().strip(),
            "balance": self._totals["balance"],
            "description": description_editor.text().strip() if description_editor is not None else "",
            "seller": seller,
        }
