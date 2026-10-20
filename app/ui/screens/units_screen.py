"""Units module screen (إدارة الوحدات) — design #5, the stat-dashboard layout.

UI only: it reuses :class:`BaseCrudScreen` bound to the ``units`` table spec, so
it inherits the exact same header, toolbar, form+list split, colours and CRUD
logic as the customers/products screens (same design family). Business/database
logic stays in ``ReviewDataService`` + ``TABLE_SPECS['units']``.

The single design-specific touch (the option the user chose) is a **statistics
bar** injected between the toolbar and the content, showing three live figures:

* إجمالي الوحدات — how many units exist,
* آخر كود مُسجّل — the highest ``UN-####`` code already stored,
* الكود التالي — the code the next saved unit will most likely receive.

``كود الوحدة`` (UN-1001, UN-1002, …) and ``رقم تلقائي`` are both assigned by the
database on save; the screen only previews them. The stats refresh automatically
after every list reload (new / save / delete / search).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.services.review_data_service import ReviewDataService, TABLE_SPECS
from app.ui.common.theme import BORDER, GREEN, TEXT
from app.ui.screens.base_crud_screen import BaseCrudScreen


class UnitsScreen(BaseCrudScreen):
    SPEC_KEY = "units"

    # Units are searched by their code (UN-…) or their name.
    SEARCH_PLACEHOLDER = "البحث بكود الوحدة أو اسم الوحدة"

    # Only two fields on the entry form (code + name), each on its own line —
    # the numeric auto-id is grid-only (hidden_on_form) and assigned on save.
    FORM_COLUMNS = 1

    def __init__(self, service: ReviewDataService, parent: QWidget | None = None) -> None:
        # References filled by _build_stats_bar (called from _build_ui inside
        # super().__init__); declared here for clarity.
        self._stat_count: QLabel | None = None
        self._stat_last: QLabel | None = None
        self._stat_next: QLabel | None = None
        super().__init__(service, TABLE_SPECS[self.SPEC_KEY], parent)

    # --- layout: toolbar → stats bar → content ------------------------------
    def _build_ui(self) -> None:  # type: ignore[override]
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addWidget(self._build_header())
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_stats_bar())
        root.addLayout(self._build_content(), 1)

    def _build_stats_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("QFrame { background:transparent; }")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._stat_count = self._make_stat_card(layout, "إجمالي الوحدات")
        self._stat_last = self._make_stat_card(layout, "آخر كود مُسجّل")
        self._stat_next = self._make_stat_card(layout, "الكود التالي")
        return bar

    def _make_stat_card(self, layout: QHBoxLayout, caption: str) -> QLabel:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:#FFFFFF; border:1px solid {BORDER}; border-radius:9px; }}"
        )
        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 11, 16, 11)
        inner.setSpacing(3)
        value = QLabel("—")
        value.setStyleSheet(
            f"font-size:23px; font-weight:900; color:{GREEN}; background:transparent; border:none;"
        )
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cap = QLabel(caption)
        cap.setStyleSheet(
            f"font-size:12px; font-weight:800; color:#64748B; background:transparent; border:none;"
        )
        cap.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        inner.addWidget(value)
        inner.addWidget(cap)
        layout.addWidget(card, 1)
        return value

    def _refresh_stats(self) -> None:
        if self._stat_count is None:
            return
        try:
            stats = self.service.units_stats()
        except Exception:
            return
        self._stat_count.setText(str(stats["count"]))
        self._stat_last.setText(str(stats["last_code"]))
        self._stat_next.setText(str(stats["next_code"]))

    # --- keep the stats in sync + preview the next unit code ----------------
    def refresh_table(self) -> None:  # type: ignore[override]
        super().refresh_table()
        self._refresh_stats()

    def new_record(self) -> None:  # type: ignore[override]
        super().new_record()
        # Preview the code the DB will assign so the user sees UN-#### while
        # typing the name (the real value is generated on save).
        try:
            next_code = self.service.units_stats()["next_code"]
        except Exception:
            next_code = ""
        code_editor = self.inputs.get("unit_code")
        if code_editor is not None:
            self._set_editor_value(code_editor, next_code)
