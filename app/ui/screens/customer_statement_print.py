"""Printable Customer Statement (كشف حساب العميل) — fourteen templates.

Approved in-conversation 2026-07-16. The screen offers the same template picker
the sales-invoice screen uses, on معاينة / طباعة / تصدير PDF:

All three print the SAME four columns — التاريخ / البيان / مدين / دائن (user
2026-07-23); they differ in identity and layout, not in what they carry. The
customer and company appear once, in the letterhead and the filter chips, and
the movement number is folded into the البيان («سند قبض رقم …»), never a column.

* :func:`build_statement_html_v1` — «النموذج الأول», the classic green layout,
  the applied filters as chips and the totals under a green rule. A4 **landscape**.
* :func:`build_statement_html_v2` — «النموذج الثاني», a bank-style statement:
  debit/credit coloured, totals as cards, and a dark closing totals row. A4
  landscape.
* :func:`build_statement_html_v3` — «النموذج الثالث», a formal letterhead sheet
  in النموذج الثامن's navy identity, so statements and invoices look like one
  set of documents. A4 **portrait**.

النموذج الرابع → الثامن were picked by the user on 2026-10-18 from ten mock-ups
rendered with real data. Unlike the first three they may carry a per-row running
balance (الرصيد, from :func:`rows_with_balance`) — the user chose them with it:

* :func:`build_statement_html_v4` — «النموذج الرابع», المصرفي الشهري: summary cards,
  movements grouped by month with each month's subtotal, running balance. Portrait.
* :func:`build_statement_html_v5` — «النموذج الخامس», لوحة الملخص: KPI cards, a
  monthly summary table and bar chart, then the detail table. Landscape.
* :func:`build_statement_html_v6` — «النموذج السادس», ثنائي اللغة: every label in
  Arabic and English, black & gold, running balance. Portrait.
* :func:`build_statement_html_v7` — «النموذج السابع», أعمار الديون: the four columns
  plus an aging of the outstanding balance (0-30 / 31-60 / 61-90 / 90+ days,
  credits settling the oldest debit first). Portrait.
* :func:`build_statement_html_v8` — «النموذج الثامن», الرسمي المؤطر: a green & gold
  frame repeated on every printed page, a statement number, a total row. Portrait.

النموذج التاسع → الثالث عشر were picked the same day from a second batch of ten:

* :func:`build_statement_html_v9`  — «النموذج التاسع», الشريط الجانبي: identity and
  totals in a teal side column fixed on every page. Portrait.
* :func:`build_statement_html_v10` — «النموذج العاشر», الحديث المائل: slanted
  gradient bands top and bottom, pill totals. Portrait.
* :func:`build_statement_html_v11` — «النموذج الحادي عشر», الملوّن حسب النوع: a
  coloured «النوع» pill per row and a total per movement type. Portrait.
* :func:`build_statement_html_v12` — «النموذج الثاني عشر», التقويم: a shaded month
  calendar per month, then the table with a weekday column. Portrait.
* :func:`build_statement_html_v13` — «النموذج الثالث عشر», المالي المؤمّن: a
  guilloche border, logo watermark and the balance in Arabic words. Portrait.

النموذج الرابع عشر was picked on 2026-10-20 from a third batch of ten, without the
mock-up's QR code:

* :func:`build_statement_html_v14` — «النموذج الرابع عشر», الكشف الضريبي المفصّل:
  supplier and customer VAT identities, each invoice split into taxable amount,
  15% VAT and total, a running balance and a VAT summary. Portrait.

Why this module renders through ``QWebEngineView`` and not the shared
``PrintManager`` / ``PdfExporter`` the report used before
-----------------------------------------------------------------------
The old path had *two* renderers behind one report: ``QTextDocument`` (Qt rich
text) for preview/print and ReportLab for PDF, so every design had to be built
twice and could still diverge. More decisively, ``QTextDocument`` was measured
against these designs before they were drawn: it **ignores ``display:flex``**
(side-by-side cards stack) and **drops every ``border-radius``**. None of the
three approved layouts is renderable by it at all.

Chromium renders one HTML for preview, print *and* PDF — one source of truth,
the engine the invoice templates already use. It also **paginates**, which
matters far more here than on an invoice: a statement's row count is unbounded,
so the fixed-sheet approach every invoice template uses (and its silent clipping)
would be exactly wrong. Nothing here uses a fixed height; the table flows and
``thead`` repeats on every page.

``PrintManager`` / ``PdfExporter`` are untouched — Status Analysis and Daily
Follow-up still share them, and Excel export still goes through ``ExcelExporter``.

Presentation only: no database access. Every field printed comes straight from
the read-only service; what the templates derive (running balance, month
subtotals, aging buckets) is plain arithmetic over those same rows.
"""

from __future__ import annotations

import calendar
import html
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from PySide6.QtCore import QMarginsF, Qt, QTimer, QUrl
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.ui.common.saudi_invoice_style import si_icon, style_button
from app.ui.screens.saudi_invoice_print import (
    amount_in_words_ar,
    choose_invoice_template,
    company_logo_data_uri,
    signature_line_html,
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_GREEN = "#137A38"      # the reports' existing brand green — النموذج الأول keeps it
_GREEN_TINT = "#EFF5F0"
_NAVY = "#1A2A6C"       # النموذج الثامن's accent — النموذج الثالث shares it
_NAVY_ON = "#B9C4E8"
_INK = "#0F172A"        # النموذج الثاني's near-black
_DEBIT = "#A32D2D"
_CREDIT = "#0F6E56"
_MUTED = "#94A3B8"
_RULE = "#E2E8F0"
_TINT = "#F1F4FB"
_ZEBRA = "#F8FAFC"

_FONTS = 'Tahoma, Arial, "Segoe UI", "Helvetica Neue", sans-serif'

STATEMENT_TEMPLATE_OPTIONS: tuple[str, ...] = (
    "النموذج الأول",
    "النموذج الثاني",
    "النموذج الثالث",
    "النموذج الرابع",
    "النموذج الخامس",
    "النموذج السادس",
    "النموذج السابع",
    "النموذج الثامن",
    "النموذج التاسع",
    "النموذج العاشر",
    "النموذج الحادي عشر",
    "النموذج الثاني عشر",
    "النموذج الثالث عشر",
    "النموذج الرابع عشر",
)

_ZERO = Decimal("0.00")

# Printed page margin, in millimetres — comfortably outside the unprintable edge
# every common office printer has, and enough for a hole-punch on the statement.
_MARGIN_MM = 12.0


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _money(value: Any) -> str:
    try:
        return f"{Decimal(str(value)):,.2f}"
    except Exception:  # noqa: BLE001 - defensive formatting only
        return "0.00"


def _dash(value: Any) -> str:
    """An empty cell prints «—», so a blank reads as *absent*, not as a fault."""
    text = _esc(value).strip()
    return text if text and text != "-" else f'<span style="color:{_MUTED};">—</span>'


def rows_with_balance(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], Decimal]]:
    """Pair every row with the running balance after it.

    The balance is *derived*, not fetched: the service already returns the debit
    and credit of each row in a deterministic order (transaction_date, then
    source_sequence, then source_id), so the cumulative sum is well defined and
    reproducible across preview / print / PDF.

    Note this is a period balance, not an account balance: the statement has no
    opening balance because the query does not read anything before the period.
    النموذج الثاني therefore labels its last figure «الرصيد المستحق» over the
    period — never «الرصيد الافتتاحي».
    """
    out: list[tuple[dict[str, Any], Decimal]] = []
    balance = _ZERO
    for row in rows:
        debit = row.get("debit") or _ZERO
        credit = row.get("credit") or _ZERO
        balance = balance + Decimal(str(debit)) - Decimal(str(credit))
        out.append((row, balance))
    return out


def _document(body: str, *, landscape: bool) -> str:
    """Wrap a template body in the shared print document.

    ``thead{display:table-header-group}`` is what repeats the column headers on
    every printed page, and ``page-break-inside:avoid`` on rows stops a line item
    being sliced in half across the fold. Both only matter because this document
    flows — see the module docstring.
    """
    width = "1123px" if landscape else "794px"
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: {_FONTS};
    color: #111;
    background: #fff;
    -webkit-font-smoothing: antialiased;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  .sheet {{ width: {width}; margin: 0 auto; padding: 18px 20px; }}
  table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
  thead {{ display: table-header-group; }}
  tr {{ page-break-inside: avoid; }}
  td, th {{ overflow-wrap: anywhere; }}
  .num {{ direction: ltr; }}
  @media print {{
    .sheet {{ width: auto; padding: 0; }}
  }}
</style>
</head>
<body><div class="sheet">{body}</div></body>
</html>"""


def _letterhead(data: dict[str, Any], *, accent: str, rule: str) -> str:
    """The company's letterhead: Arabic right, logo centre, English left.

    Added 2026-07-17 at the user's request. Before it, the company appeared only as
    a grey subtitle (النموذج الأول/الثاني) or a row among the details (النموذج
    الثالث) — and in practice not at all, because the screen fed it the legacy
    ``company_settings`` table, which is empty on this installation. It now reads
    ``data["company"]``: the row of the company picked in the statement's own
    filter, straight from ``companies``.

    ``None`` (the «الكل» filter) prints nothing at all: a statement spanning several
    companies has no single issuer, and heading it with one of them would be a
    claim about the document that is not true.

    The three columns are a grid, not flex, and the side columns are ``minmax(0,1fr)``
    so a long company name wraps inside its own column instead of shoving the logo
    off centre — the failure النموذج الثالث's header bar already had.
    """
    company = data.get("company")
    if not isinstance(company, dict):
        return ""

    name_ar = _esc(company.get("name_ar"))
    name_en = _esc(company.get("name_en"))
    vat = _esc(company.get("vat_number"))
    cr = _esc(company.get("commercial_registration"))
    address_ar = _esc(company.get("address_ar"))
    address_en = _esc(company.get("address_en") or company.get("address_ar"))
    logo = company_logo_data_uri(company)

    def line(text: str, *, size: str = "9.5px", weight: str = "400") -> str:
        return (
            f'<div style="font-size:{size}; font-weight:{weight}; color:#5A6180; '
            f'margin-top:2px; overflow-wrap:anywhere;">{text}</div>'
            if text
            else ""
        )

    arabic = (
        f'<div dir="rtl" style="text-align:right; min-width:0;">'
        f'<div style="font-size:14px; font-weight:700; color:{accent}; '
        f'overflow-wrap:anywhere;">{name_ar}</div>'
        + line(f"الرقم الضريبي: {vat}" if vat else "")
        + line(f"السجل التجاري: {cr}" if cr else "")
        + line(address_ar)
        + "</div>"
    )
    english = (
        f'<div dir="ltr" style="text-align:left; min-width:0;">'
        f'<div style="font-size:13px; font-weight:700; color:{accent}; '
        f'overflow-wrap:anywhere;">{name_en}</div>'
        + line(f"VAT No.: {vat}" if vat else "")
        + line(f"C.R. No.: {cr}" if cr else "")
        + line(address_en)
        + "</div>"
    )
    centre = (
        f'<div style="display:flex; align-items:center; justify-content:center;">'
        f'<img src="{logo}" alt="logo" style="max-width:130px; max-height:64px; '
        f'width:auto; height:auto; object-fit:contain; display:block;" /></div>'
        if logo
        else "<div></div>"   # the column still occupies its third, keeping symmetry
    )
    # `direction:ltr` on the grid is load-bearing, not decoration: the document is
    # `<html dir="rtl">`, so grid items are placed right-to-left and this same
    # source order would put the ENGLISH block on the right. Pinning the track
    # direction makes "English left, Arabic right" true regardless of what the
    # surrounding document does; each block still sets its own `dir` for its text.
    return (
        f'<div style="direction:ltr; display:grid; '
        f'grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); '
        f'gap:14px; align-items:center; padding-bottom:10px; margin-bottom:10px; '
        f'border-bottom:2px solid {rule};">'
        f"{english}{centre}{arabic}</div>"
    )


def _empty_note(data: dict[str, Any]) -> str:
    if not data.get("is_empty"):
        return ""
    message = _esc(data.get("empty_message") or "لا توجد حركات")
    return (
        f'<div style="text-align:center; padding:28px 10px; color:#64748B; '
        f'font-size:13px; border:1px dashed {_RULE}; margin-top:10px;">{message}</div>'
    )


def _auto_note() -> str:
    """Shared footer line printed at the bottom of every statement template:
    the statement is system-generated and needs no stamp (النموذج الثالث had it;
    the user asked for it on the other templates too, 2026-08-22)."""
    return (
        '<div style="margin-top:16px; padding-top:8px; border-top:1px solid #E4E8F3; '
        'display:flex; justify-content:space-between; font-size:9.5px; color:#8189A6;">'
        "<span>هذا الكشف صادر آلياً من النظام ولا يحتاج إلى ختم</span></div>"
    )


# ---------------------------------------------------------------------------
# النموذج الأول — the classic green sheet
# ---------------------------------------------------------------------------
def build_statement_html_v1(data: dict[str, Any]) -> str:
    """The report's long-standing green look — four columns only: التاريخ / البيان
    / المدين / الدائن (user 2026-07-23). اسم العميل and اسم الشركة now live in the
    letterhead and the filter chips, not as repeated per-row columns, and the
    movement number is folded into the البيان («سند قبض رقم …»)."""
    chips = "".join(
        f'<span style="background:{_GREEN_TINT}; color:{_GREEN}; padding:3px 9px; '
        f'border-radius:3px;">{_esc(text)}</span>'
        for text in (
            f"العميل: {data.get('customer_label') or 'الكل'}",
            f"الشركة: {data.get('company_label') or 'الكل'}",
            f"الفترة: {data.get('date_from_label')} إلى {data.get('date_to_label')}",
        )
    )
    head = "".join(
        f'<th style="background:{_GREEN}; color:#fff; font-weight:700; padding:7px 4px; '
        f'width:{width};">{label}</th>'
        for label, width in (
            ("التاريخ", "14%"), ("البيان", "46%"),
            ("المدين", "20%"), ("الدائن", "20%"),
        )
    )
    body = []
    for row in data.get("rows") or []:
        cell = ('<td style="border:1px solid #D1D5DB; padding:5px 4px; '
                'text-align:center;">')
        body.append(
            "<tr>"
            f'{cell}{_esc(row.get("transaction_date"))}</td>'
            '<td style="border:1px solid #D1D5DB; padding:5px 6px; text-align:right;">'
            f'{_esc(row.get("description"))}</td>'
            f'{cell}<span class="num">{_money(row.get("debit"))}</span></td>'
            f'{cell}<span class="num">{_money(row.get("credit"))}</span></td>'
            "</tr>"
        )
    summary = data.get("summary") or {}
    table = (
        f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
        if body
        else ""
    )
    return _document(
        # The company is the letterhead now, not a grey subtitle under the title.
        f'{_letterhead(data, accent=_GREEN, rule=_GREEN)}'
        f'<div style="text-align:center; font-size:20px; font-weight:700; color:{_GREEN};">'
        f'{_esc(data.get("title"))}</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center; '
        f'margin:12px 0; font-size:10.5px;">{chips}</div>'
        f"{table}{_empty_note(data)}"
        f'<div style="border-top:2px solid {_GREEN}; margin:10px 0 7px;"></div>'
        f'<div style="text-align:left; font-size:11.5px; font-weight:700;">'
        f'إجمالي المدين: <span class="num">{_esc(summary.get("total_debit_label"))}</span>'
        "&nbsp;&nbsp;|&nbsp;&nbsp;"
        f'إجمالي الدائن: <span class="num">{_esc(summary.get("total_credit_label"))}</span>'
        "&nbsp;&nbsp;|&nbsp;&nbsp;"
        f'الفرق: <span class="num">{_esc(summary.get("difference_label"))}</span></div>'
        f"{_auto_note()}",
        landscape=True,
    )


build_statement_html_v1.landscape = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الثاني — bank-style, with a running balance
# ---------------------------------------------------------------------------
def _stat_card(label: str, value: str, *, bg: str, label_color: str,
               value_color: str) -> str:
    return (
        f'<div style="background:{bg}; padding:7px 13px; border-radius:5px; '
        f'text-align:center; min-width:104px;">'
        f'<div style="font-size:9.5px; color:{label_color};">{label}</div>'
        f'<div class="num" style="font-size:14px; font-weight:700; color:{value_color};">'
        f"{value}</div></div>"
    )


def build_statement_html_v2(data: dict[str, Any]) -> str:
    """Bank-style: coloured debit/credit and a dark closing totals row.

    Four columns only — التاريخ / البيان / مدين / دائن (user 2026-07-23). The
    per-row running-balance column and the الفاتورة column were dropped; the
    account balance survives as the «الرصيد المستحق» card and the closing row's
    total, which is where a reader looks for it anyway."""
    summary = data.get("summary") or {}
    cards = (
        _stat_card("إجمالي المدين", _esc(summary.get("total_debit_label")),
                   bg="#FCEBEB", label_color=_DEBIT, value_color="#501313")
        + _stat_card("إجمالي الدائن", _esc(summary.get("total_credit_label")),
                     bg="#E1F5EE", label_color=_CREDIT, value_color="#04342C")
        + _stat_card("الرصيد المستحق", _esc(summary.get("difference_label")),
                     bg=_INK, label_color=_MUTED, value_color="#ffffff")
    )
    head = "".join(
        f'<th style="padding:7px 4px; font-weight:700; width:{width}; '
        f'text-align:{align}; color:{color};">{label}</th>'
        for label, width, align, color in (
            ("التاريخ", "12%", "center", "#334155"),
            ("البيان", "auto", "right", "#334155"),
            ("مدين", "20%", "center", _DEBIT),
            ("دائن", "20%", "center", _CREDIT),
        )
    )
    body = []
    for index, row in enumerate(data.get("rows") or []):
        debit = Decimal(str(row.get("debit") or _ZERO))
        credit = Decimal(str(row.get("credit") or _ZERO))
        zebra = f" background:{_ZEBRA};" if index % 2 else ""
        cell = (f'<td style="border-bottom:1px solid {_RULE}; padding:6px 4px; '
                f'text-align:center;{zebra}">')
        # A zero side prints «—», not «0.00»: on a ledger the eye should land on
        # the side that actually moved.
        debit_text = (f'<span class="num" style="color:{_DEBIT};">{_money(debit)}</span>'
                      if debit else f'<span style="color:{_MUTED};">—</span>')
        credit_text = (f'<span class="num" style="color:{_CREDIT};">{_money(credit)}</span>'
                       if credit else f'<span style="color:{_MUTED};">—</span>')
        body.append(
            "<tr>"
            f'{cell}{_esc(row.get("transaction_date"))}</td>'
            f'<td style="border-bottom:1px solid {_RULE}; padding:6px 6px; '
            f'text-align:right;{zebra}">{_esc(row.get("description"))}</td>'
            f"{cell}{debit_text}</td>"
            f"{cell}{credit_text}</td>"
            "</tr>"
        )
    closing = (
        f'<tr style="background:{_INK}; color:#fff;">'
        f'<td colspan="2" style="padding:8px 6px; font-weight:700;">'
        "الرصيد الختامي المستحق على العميل: "
        f'<span class="num">{_esc(summary.get("difference_label"))}</span></td>'
        f'<td style="padding:8px 4px; text-align:center;" class="num">'
        f'{_esc(summary.get("total_debit_label"))}</td>'
        f'<td style="padding:8px 4px; text-align:center;" class="num">'
        f'{_esc(summary.get("total_credit_label"))}</td></tr>'
        if body
        else ""
    )
    table = (
        f'<table style="font-size:10.5px;">'
        f'<thead><tr style="border-bottom:1.5px solid {_INK};">{head}</tr></thead>'
        f'<tbody>{"".join(body)}{closing}</tbody></table>'
        if body
        else ""
    )
    return _document(
        f'{_letterhead(data, accent=_INK, rule=_INK)}'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:flex-start; gap:14px; margin-bottom:12px;">'
        # min-width:0 so a long customer name wraps in this column instead of
        # squeezing the stat cards.
        '<div style="min-width:0;">'
        f'<div style="font-size:20px; font-weight:700; color:{_INK};">'
        f'{_esc(data.get("title"))}</div>'
        f'<div style="font-size:11px; color:#64748B; margin-top:3px; '
        f'overflow-wrap:anywhere;">'
        f'{_esc(data.get("customer_label") or "الكل")} · من '
        f'{_esc(data.get("date_from_label"))} إلى {_esc(data.get("date_to_label"))}</div>'
        "</div>"
        f'<div style="display:flex; gap:8px; flex:none;">{cards}</div>'
        "</div>"
        f"{table}{_empty_note(data)}"
        f"{_auto_note()}",
        landscape=True,
    )


build_statement_html_v2.landscape = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الثالث — formal letterhead, النموذج الثامن's identity
# ---------------------------------------------------------------------------
def build_statement_html_v3(data: dict[str, Any]) -> str:
    """A formal sheet sharing النموذج الثامن's navy identity. Portrait."""
    summary = data.get("summary") or {}
    head = "".join(
        f'<th style="background:{_NAVY}; color:#fff; font-weight:700; padding:7px 4px; '
        f'width:{width}; text-align:{align};">{label}</th>'
        for label, width, align in (
            ("التاريخ", "16%", "center"), ("البيان", "auto", "right"),
            ("المدين", "20%", "center"), ("الدائن", "20%", "center"),
        )
    )
    body = []
    for index, row in enumerate(data.get("rows") or []):
        zebra = f" background:#F7F9FD;" if index % 2 else ""
        cell = (f'<td style="border:1px solid #DBE1F2; padding:5px 4px; '
                f'text-align:center;{zebra}">')
        body.append(
            "<tr>"
            f'{cell}{_esc(row.get("transaction_date"))}</td>'
            f'<td style="border:1px solid #DBE1F2; padding:5px 6px; '
            f'text-align:right;{zebra}">{_esc(row.get("description"))}</td>'
            f'{cell}<span class="num">{_money(row.get("debit"))}</span></td>'
            f'{cell}<span class="num">{_money(row.get("credit"))}</span></td>'
            "</tr>"
        )
    table = (
        f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
        if body
        else ""
    )
    totals = (
        f'<div style="display:flex; justify-content:space-between; font-size:11px; '
        f'padding:5px 9px; border-bottom:1px solid #E4E8F3;">'
        f'<span style="color:#4A5170;">إجمالي المدين</span>'
        f'<span class="num" style="font-weight:700;">'
        f'{_esc(summary.get("total_debit_label"))}</span></div>'
        f'<div style="display:flex; justify-content:space-between; font-size:11px; '
        f'padding:5px 9px; border-bottom:1px solid #E4E8F3;">'
        f'<span style="color:#4A5170;">إجمالي الدائن</span>'
        f'<span class="num" style="font-weight:700;">'
        f'{_esc(summary.get("total_credit_label"))}</span></div>'
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'background:{_NAVY}; color:#fff; padding:9px; margin-top:2px;">'
        '<span style="font-size:12px;">الرصيد المستحق</span>'
        f'<span class="num" style="font-size:15px; font-weight:700;">'
        f'{_esc(summary.get("difference_label"))} SAR</span></div>'
    )
    return _document(
        f'{_letterhead(data, accent=_NAVY, rule=_NAVY)}'
        # The logo used to sit here, opposite the title. It is the letterhead's
        # centre column now, so this is the title alone.
        '<div style="padding-bottom:10px;">'
        f'<div style="font-size:19px; font-weight:700; color:{_NAVY};">'
        f'{_esc(data.get("title"))}</div>'
        '<div dir="ltr" style="font-size:11px; color:#5A6180; text-align:right;">'
        "Customer Statement</div>"
        "</div>"
        # The navy bar is a GRID, not flex. As flex with `gap:24px` a long customer
        # name starved the period field: «الفترة» broke mid-value onto four lines
        # («01-01-2026 / -2026 — / 17-07»). A fixed track + `nowrap` on the period
        # means a long name can only ever wrap in its own column.
        f'<div style="background:{_NAVY}; color:#fff; display:grid; '
        f'grid-template-columns:minmax(0,1fr) auto; gap:8px 24px; '
        f'padding:8px 12px; font-size:11px; align-items:baseline;">'
        f'<span style="min-width:0; overflow-wrap:anywhere;">'
        f'<span style="color:{_NAVY_ON};">العميل</span> '
        f'{_esc(data.get("customer_label") or "الكل")}</span>'
        f'<span style="white-space:nowrap;"><span style="color:{_NAVY_ON};">الفترة</span> '
        f'{_esc(data.get("date_from_label"))} — {_esc(data.get("date_to_label"))}</span>'
        "</div>"
        f'<div style="margin-bottom:12px;"></div>'
        f"{table}{_empty_note(data)}"
        # The «توقيع المحاسب» rule that sat opposite the totals was dropped at the
        # user's request (2026-07-17) for the shared bottom-left signature line —
        # the same one every receipt voucher now prints.
        '<div style="display:flex; gap:12px; margin-top:14px; align-items:flex-start;">'
        f'<div style="flex:1;">{totals}</div>'
        '<div style="flex:1; display:flex; flex-direction:column; '
        'justify-content:flex-end; padding-top:34px;">'
        f'{signature_line_html(font_size="10.5px", color="#6B7290")}'
        "</div></div>"
        f"{_auto_note()}",
        landscape=False,
    )


build_statement_html_v3.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helpers shared by النموذج الرابع → الثامن (added 2026-10-18)
# ---------------------------------------------------------------------------
_MONTHS_AR = ("يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
              "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر")


def _d(value: Any) -> Decimal:
    return Decimal(str(value or _ZERO))


def _amt(value: Any, color: str = "inherit") -> str:
    """Money, or a muted dash for a zero side."""
    v = _d(value)
    if not v:
        return f'<span style="color:{_MUTED};">—</span>'
    return f'<span class="num" style="color:{color};">{_money(v)}</span>'


def _bal(balance: Decimal) -> str:
    """Running balance with its side: مدين (owed by the customer) / دائن."""
    if not balance:
        return '<span class="num">0.00</span>'
    side = "مدين" if balance > 0 else "دائن"
    return (f'<span class="num">{_money(abs(balance))}</span> '
            f'<span style="font-size:0.85em; color:#64748B;">{side}</span>')


def _summary(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("summary") or {}


def _rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("rows") or [])


def _dt(value: Any) -> str:
    """A date isolated from the Arabic run around it (bidi would print
    «2026-07-01» as «01-07-2026» inside Arabic text)."""
    return f'<span style="display:inline-block; direction:ltr;">{_esc(value)}</span>'


def _period(data: dict[str, Any], *_: Any) -> str:
    return f'من {_dt(data.get("date_from_label"))} إلى {_dt(data.get("date_to_label"))}'


def _customer(data: dict[str, Any]) -> str:
    return _esc(data.get("customer_label") or "الكل")


def _parse(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _months(data: dict[str, Any]) -> "OrderedDict[tuple[int,int], dict[str, Any]]":
    """The movements grouped by calendar month, in statement order, each row
    paired with its running balance, plus the month's debit/credit totals."""
    out: "OrderedDict[tuple[int,int], dict[str, Any]]" = OrderedDict()
    for row, balance in rows_with_balance(_rows(data)):
        d = _parse(row.get("transaction_date"))
        key = (d.year, d.month) if d else (0, 0)
        bucket = out.setdefault(key, {"rows": [], "debit": _ZERO, "credit": _ZERO})
        bucket["rows"].append((row, balance))
        bucket["debit"] += _d(row.get("debit"))
        bucket["credit"] += _d(row.get("credit"))
    return out


def _month_name(key: tuple[int, int]) -> str:
    year, month = key
    if not month:
        return "—"
    return f"{_MONTHS_AR[month - 1]} {year}"




# ---------------------------------------------------------------------------
# النموذج الرابع — المصرفي الشهري (grouped by month, running balance). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v4(data: dict[str, Any]) -> str:
    """Bank-statement style: four summary cards, then the movements grouped by
    month — each month opened by its name and closed by its debit/credit
    subtotal — with a running balance column."""
    wine, tint = "#7F1D1D", "#FBF3F3"
    s = _summary(data)

    def box(label: str, value: str, dark: bool = False) -> str:
        bg = wine if dark else tint
        fg = "#fff" if dark else wine
        return (f'<div style="flex:1; background:{bg}; padding:8px 10px; border-radius:4px;">'
                f'<div style="font-size:9.5px; color:{"#F5CACA" if dark else "#9A5A5A"};">{label}</div>'
                f'<div class="num" style="font-size:14px; font-weight:700; color:{fg}; text-align:right;">{value}</div></div>')

    head = "".join(
        f'<th style="padding:7px 4px; background:{wine}; color:#fff; width:{w}; text-align:{a};">{t}</th>'
        for t, w, a in (("التاريخ", "14%", "center"), ("البيان", "auto", "right"),
                        ("مدين", "16%", "center"), ("دائن", "16%", "center"), ("الرصيد", "18%", "center"))
    )
    body = []
    for key, m in _months(data).items():
        body.append(f'<tr><td colspan="5" style="padding:7px 8px 4px; font-weight:700; color:{wine}; '
                    f'border-bottom:1.5px solid {wine}; font-size:11px;">{_month_name(key)}</td></tr>')
        for i, (row, balance) in enumerate(m["rows"]):
            z = " background:#FCFAFA;" if i % 2 else ""
            c = f'<td style="padding:5px 4px; border-bottom:1px solid #F1E4E4; text-align:center;{z}">'
            body.append(
                f"<tr>{c}{_esc(row.get('transaction_date'))}</td>"
                f'<td style="padding:5px 6px; border-bottom:1px solid #F1E4E4;{z}">{_esc(row.get("description"))}</td>'
                f"{c}{_amt(row.get('debit'))}</td>{c}{_amt(row.get('credit'))}</td>{c}{_bal(balance)}</td></tr>"
            )
        body.append(
            f'<tr style="background:{tint}; font-weight:700; font-size:10px;">'
            f'<td colspan="2" style="padding:5px 8px;">مجموع {_month_name(key)}</td>'
            f'<td style="text-align:center;" class="num">{_money(m["debit"])}</td>'
            f'<td style="text-align:center;" class="num">{_money(m["credit"])}</td><td></td></tr>'
        )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead>'
             f"<tbody>{''.join(body)}</tbody></table>") if body else ""
    return _document(
        _letterhead(data, accent=wine, rule=wine)
        + '<div style="display:flex; flex-wrap:wrap; gap:4px 14px; justify-content:space-between; align-items:baseline; margin:4px 0 10px;">'
          f'<div style="font-size:19px; font-weight:700; color:{wine};">{_esc(data.get("title"))}</div>'
          f'<div style="font-size:10.5px; color:#6B4B4B;">العميل: <b>{_customer(data)}</b>'
          f' &nbsp;|&nbsp; الفترة: {_period(data)}</div></div>'
        + '<div style="display:flex; gap:8px; margin-bottom:12px;">'
        + box("عدد الحركات", str(len(_rows(data))))
        + box("إجمالي المدين", _esc(s.get("total_debit_label")))
        + box("إجمالي الدائن", _esc(s.get("total_credit_label")))
        + box("الرصيد الختامي", _esc(s.get("difference_label")), dark=True)
        + "</div>" + table + _empty_note(data) + _auto_note(),
        landscape=False,
    )


build_statement_html_v4.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الخامس — لوحة الملخص (monthly summary + bars, then details). Landscape
# ---------------------------------------------------------------------------
def build_statement_html_v5(data: dict[str, Any]) -> str:
    """A dashboard first page: KPI cards, a monthly summary table and a bar chart
    of each month's debit vs credit, then the detail table with running balance."""
    blue, light = "#1D4ED8", "#DBEAFE"
    green = "#059669"
    s = _summary(data)
    months = _months(data)
    peak = max([max(m["debit"], m["credit"]) for m in months.values()] or [Decimal(1)]) or Decimal(1)

    def kpi(label: str, value: str, color: str) -> str:
        return (f'<div style="border:1px solid #E2E8F0; border-top:3px solid {color}; border-radius:6px; padding:8px 12px;">'
                f'<div style="font-size:9.5px; color:#64748B;">{label}</div>'
                f'<div class="num" style="font-size:16px; font-weight:700; color:#0F172A; text-align:right;">{value}</div></div>')

    mrows = "".join(
        f'<tr><td style="padding:5px 6px; border-bottom:1px solid #EEF2F6;">{_month_name(k)}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #EEF2F6;" class="num">{_money(m["debit"])}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #EEF2F6;" class="num">{_money(m["credit"])}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #EEF2F6; font-weight:700;" class="num">{_money(m["debit"] - m["credit"])}</td></tr>'
        for k, m in months.items()
    )
    bars = "".join(
        '<div style="display:flex; flex-direction:column; align-items:center; gap:4px; flex:1;">'
        '<div style="height:110px; display:flex; align-items:flex-end; gap:4px;">'
        f'<div style="width:16px; height:{int(m["debit"] / peak * 100)}%; background:{blue}; border-radius:3px 3px 0 0;"></div>'
        f'<div style="width:16px; height:{int(m["credit"] / peak * 100)}%; background:{green}; border-radius:3px 3px 0 0;"></div>'
        '</div>'
        f'<div style="font-size:9px; color:#475569;">{_month_name(k)}</div></div>'
        for k, m in months.items()
    )
    legend = (f'<div style="display:flex; gap:12px; font-size:9px; color:#475569; margin-top:6px; justify-content:center;">'
              f'<span><span style="display:inline-block; width:9px; height:9px; background:{blue}; border-radius:2px;"></span> مدين (مبيعات)</span>'
              f'<span><span style="display:inline-block; width:9px; height:9px; background:{green}; border-radius:2px;"></span> دائن (مقبوضات)</span></div>')
    head = "".join(
        f'<th style="padding:7px 4px; background:{light}; color:{blue}; width:{w}; text-align:{a};">{t}</th>'
        for t, w, a in (("التاريخ", "12%", "center"), ("البيان", "auto", "right"),
                        ("مدين", "16%", "center"), ("دائن", "16%", "center"), ("الرصيد", "16%", "center"))
    )
    body = []
    for i, (row, balance) in enumerate(rows_with_balance(_rows(data))):
        z = " background:#F8FAFC;" if i % 2 else ""
        c = f'<td style="padding:5px 4px; text-align:center; border-bottom:1px solid #EEF2F6;{z}">'
        body.append(
            f"<tr>{c}{_esc(row.get('transaction_date'))}</td>"
            f'<td style="padding:5px 6px; border-bottom:1px solid #EEF2F6;{z}">{_esc(row.get("description"))}</td>'
            f"{c}{_amt(row.get('debit'), blue)}</td>{c}{_amt(row.get('credit'), green)}</td>{c}{_bal(balance)}</td></tr>"
        )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead>'
             f"<tbody>{''.join(body)}</tbody></table>") if body else ""
    return _document(
        _letterhead(data, accent=blue, rule=blue)
        + '<div style="display:flex; flex-wrap:wrap; gap:4px 14px; justify-content:space-between; align-items:baseline; margin-bottom:10px;">'
          f'<div style="font-size:19px; font-weight:700; color:{blue};">{_esc(data.get("title"))}</div>'
          f'<div style="font-size:11px; color:#475569;">{_customer(data)} · {_period(data)}</div></div>'
        + '<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin-bottom:12px;">'
        + kpi("عدد الحركات", str(len(_rows(data))), "#64748B")
        + kpi("إجمالي المدين", _esc(s.get("total_debit_label")), blue)
        + kpi("إجمالي الدائن", _esc(s.get("total_credit_label")), green)
        + kpi("الرصيد المستحق", _esc(s.get("difference_label")), "#DC2626")
        + "</div>"
        + '<div style="display:grid; grid-template-columns:1.2fr 1fr; gap:14px; margin-bottom:14px; page-break-inside:avoid;">'
          '<div><div style="font-size:11px; font-weight:700; color:#0F172A; margin-bottom:6px;">الملخص الشهري</div>'
          f'<table style="font-size:10.5px;"><thead><tr style="color:#64748B; font-size:9.5px;">'
          '<th style="text-align:right; padding:5px 6px; border-bottom:1.5px solid #CBD5E1;">الشهر</th>'
          '<th style="border-bottom:1.5px solid #CBD5E1;">المدين</th><th style="border-bottom:1.5px solid #CBD5E1;">الدائن</th>'
          '<th style="border-bottom:1.5px solid #CBD5E1;">الصافي</th></tr></thead>'
          f'<tbody>{mrows}</tbody></table></div>'
          '<div style="border:1px solid #E2E8F0; border-radius:6px; padding:10px;">'
          '<div style="font-size:11px; font-weight:700; color:#0F172A; margin-bottom:6px;">حركة الحساب شهرياً</div>'
          f'<div style="display:flex; gap:6px;">{bars}</div>{legend}</div></div>'
        + '<div style="font-size:11px; font-weight:700; color:#0F172A; margin-bottom:6px;">تفاصيل الحركات</div>'
        + table + _empty_note(data) + _auto_note(),
        landscape=True,
    )


build_statement_html_v5.landscape = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج السادس — ثنائي اللغة (Arabic/English, black & gold). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v6(data: dict[str, Any]) -> str:
    """Bilingual: every heading and total carries its English label beside the
    Arabic one, for customers who file statements in English."""
    black, gold = "#111827", "#B08D57"
    s = _summary(data)

    def cell(ar: str, en: str, value: str) -> str:
        return (f'<div style="padding:6px 10px; border-right:3px solid {gold}; background:#FAF7F2;">'
                f'<div style="display:flex; justify-content:space-between; font-size:9px; color:#8A7350;">'
                f'<span>{ar}</span><span dir="ltr">{en}</span></div>'
                f'<div style="font-size:11.5px; font-weight:700; color:{black}; margin-top:2px;">{value}</div></div>')

    head = "".join(
        f'<th style="padding:6px 4px; background:{black}; color:#fff; width:{w}; text-align:center; '
        f'border-bottom:2px solid {gold};">{ar}<div style="font-size:8.5px; font-weight:400; color:#D6C2A0;">{en}</div></th>'
        for ar, en, w in (("التاريخ", "Date", "14%"), ("البيان", "Description", "auto"),
                          ("مدين", "Debit", "16%"), ("دائن", "Credit", "16%"), ("الرصيد", "Balance", "18%"))
    )
    body = []
    for i, (row, balance) in enumerate(rows_with_balance(_rows(data))):
        z = " background:#FBFAF7;" if i % 2 else ""
        c = f'<td style="padding:5px 4px; text-align:center; border-bottom:1px solid #ECE6DA;{z}">'
        body.append(
            f"<tr>{c}{_esc(row.get('transaction_date'))}</td>"
            f'<td style="padding:5px 6px; border-bottom:1px solid #ECE6DA;{z}">{_esc(row.get("description"))}</td>'
            f"{c}{_amt(row.get('debit'))}</td>{c}{_amt(row.get('credit'))}</td>{c}{_bal(balance)}</td></tr>"
        )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead>'
             f"<tbody>{''.join(body)}</tbody></table>") if body else ""

    def tot(ar: str, en: str, value: str, strong: bool = False) -> str:
        style = (f"background:{black}; color:#fff;" if strong else "border-bottom:1px solid #ECE6DA;")
        return (f'<div style="display:flex; justify-content:space-between; align-items:center; padding:6px 10px; {style}">'
                f'<span style="font-size:10.5px;">{ar} <span style="color:{gold}; font-size:9px;">| {en}</span></span>'
                f'<span class="num" style="font-weight:700; font-size:{"14px" if strong else "11px"};">{value}</span></div>')

    return _document(
        _letterhead(data, accent=black, rule=gold)
        + '<div style="text-align:center; margin:2px 0 12px;">'
          f'<div style="font-size:19px; font-weight:700; color:{black};">{_esc(data.get("title"))}</div>'
          f'<div dir="ltr" style="font-size:11px; letter-spacing:2px; color:{gold}; font-weight:700;">CUSTOMER ACCOUNT STATEMENT</div></div>'
        + '<div style="display:grid; grid-template-columns:1.6fr 1fr 1fr; gap:8px; margin-bottom:12px;">'
        + cell("العميل", "Customer", _customer(data))
        + cell("الفترة", "Period", f'{_period(data)}')
        + cell("العملة", "Currency", "ريال سعودي SAR")
        + "</div>" + table + _empty_note(data)
        + '<div style="display:flex; gap:16px; margin-top:14px; align-items:flex-end;">'
          '<div style="flex:1;">' + signature_line_html(font_size="10.5px", color="#4B5563") + "</div>"
          '<div style="flex:1;">'
        + tot("إجمالي المدين", "Total Debit", _esc(s.get("total_debit_label")))
        + tot("إجمالي الدائن", "Total Credit", _esc(s.get("total_credit_label")))
        + tot("الرصيد المستحق", "Balance Due", f'{_esc(s.get("difference_label"))} SAR', strong=True)
        + "</div></div>" + _auto_note(),
        landscape=False,
    )


build_statement_html_v6.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج السابع — أعمار الديون (statement + aging buckets). Portrait
# ---------------------------------------------------------------------------
def _aging(data: dict[str, Any]) -> list[Decimal]:
    """Outstanding debit by age at date_to: FIFO — every credit settles the
    oldest open debit first."""
    debits = [[_parse(r.get("transaction_date")), _d(r.get("debit"))]
              for r in _rows(data) if _d(r.get("debit"))]
    pool = sum((_d(r.get("credit")) for r in _rows(data)), _ZERO)
    for item in debits:
        take = min(pool, item[1])
        item[1] -= take
        pool -= take
    as_of = _parse(data.get("date_to_label")) or max(
        (d for d, _ in debits if d), default=date.today())
    buckets = [_ZERO] * 4
    for d, rest in debits:
        if not rest:
            continue
        age = (as_of - d).days if d else 0
        buckets[0 if age <= 30 else 1 if age <= 60 else 2 if age <= 90 else 3] += rest
    return buckets


def build_statement_html_v7(data: dict[str, Any]) -> str:
    """The four columns plus an aging of what is still owed at the period's end."""
    orange = "#C2410C"
    s = _summary(data)
    head = "".join(
        f'<th style="padding:7px 4px; border-bottom:2px solid {orange}; color:{orange}; width:{w}; text-align:{a};">{t}</th>'
        for t, w, a in (("التاريخ", "15%", "center"), ("البيان", "auto", "right"),
                        ("مدين", "18%", "center"), ("دائن", "18%", "center"))
    )
    body = "".join(
        f'<tr><td style="padding:5px 4px; text-align:center; border-bottom:1px solid #F3E8E1;">{_esc(r.get("transaction_date"))}</td>'
        f'<td style="padding:5px 6px; border-bottom:1px solid #F3E8E1;">{_esc(r.get("description"))}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #F3E8E1;">{_amt(r.get("debit"))}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #F3E8E1;">{_amt(r.get("credit"))}</td></tr>'
        for r in _rows(data)
    )
    foot = (f'<tr style="font-weight:700; background:#FFF7ED;"><td colspan="2" style="padding:7px 6px;">الإجمالي</td>'
            f'<td style="text-align:center;" class="num">{_esc(s.get("total_debit_label"))}</td>'
            f'<td style="text-align:center;" class="num">{_esc(s.get("total_credit_label"))}</td></tr>')
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{body}{foot}</tbody></table>'
             if body else "")
    buckets = _aging(data)
    total = sum(buckets, _ZERO)
    shades = ("#FED7AA", "#FDBA74", "#FB923C", "#EA580C")
    labels = ("حالي (0 – 30 يوم)", "31 – 60 يوم", "61 – 90 يوم", "أكثر من 90 يوم")
    aging = (
        '<div style="page-break-inside:avoid; margin-top:16px;">'
        f'<div style="font-size:12px; font-weight:700; color:{orange}; margin-bottom:6px;">تحليل أعمار الرصيد المستحق '
        f'<span style="font-weight:400; color:#78716C; font-size:10px;">(حتى {_dt(data.get("date_to_label"))})</span></div>'
        '<div style="display:grid; grid-template-columns:repeat(5, 1fr); border:1px solid #FDBA74; border-radius:6px; overflow:hidden;">'
        + "".join(
            f'<div style="text-align:center; border-left:1px solid #FDBA74;">'
            f'<div style="background:{shades[i]}; color:{"#fff" if i == 3 else "#7C2D12"}; font-size:9.5px; font-weight:700; padding:5px 2px;">{labels[i]}</div>'
            f'<div class="num" style="padding:8px 2px; font-size:12px; font-weight:700;">{_money(buckets[i])}</div></div>'
            for i in range(4)
        )
        + f'<div style="text-align:center;"><div style="background:{orange}; color:#fff; font-size:9.5px; font-weight:700; padding:5px 2px;">الإجمالي المستحق</div>'
          f'<div class="num" style="padding:8px 2px; font-size:12px; font-weight:700; color:{orange};">{_money(total)}</div></div>'
        "</div></div>"
    )
    return _document(
        _letterhead(data, accent=orange, rule=orange)
        + '<div style="display:flex; flex-wrap:wrap; gap:4px 14px; justify-content:space-between; align-items:baseline; margin:2px 0 12px;">'
          f'<div style="font-size:19px; font-weight:700; color:#1C1917;">{_esc(data.get("title"))}</div>'
          f'<div style="font-size:10.5px; color:#57534E;">العميل: <b>{_customer(data)}</b> &nbsp;·&nbsp; '
          f'{_period(data)}</div></div>'
        + table + _empty_note(data) + aging
        + '<div style="display:flex; justify-content:flex-end; margin-top:18px;">'
        + signature_line_html(font_size="11px", color="#44403C") + "</div>" + _auto_note(),
        landscape=False,
    )


build_statement_html_v7.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الثامن — الرسمي المؤطر (framed on every page, green & gold). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v8(data: dict[str, Any]) -> str:
    """A formal framed sheet. The frame is ``position:fixed``, which Chromium
    repeats on every printed page; on screen the sheet's own border stands in."""
    green, gold = "#0B5D3B", "#B8962E"
    s = _summary(data)
    frame = (
        f'<div class="frame" style="position:fixed; inset:0; border:2.5px solid {green}; '
        f'outline:1px solid {gold}; outline-offset:-6px; pointer-events:none; z-index:-1;"></div>'
        '<style>@media screen { .frame { display:none; } .sheet { border:2.5px solid ' + green + '; } }'
        "@media print { .sheet { padding:14px 16px !important; } }</style>"
    )
    # «رقم الكشف»: customer id + the closing month, so a reprint of the same
    # statement carries the same number. «الكل» has no single customer → «—».
    customer_id = data.get("customer_id")
    to_month = str(data.get("date_to_label") or "").replace("-", "")[:6]
    ref = f"ST-{customer_id}-{to_month}" if customer_id and to_month.isdigit() else "—"

    def meta(label: str, value: str) -> str:
        return (f'<div style="border:1px solid {gold}; text-align:center;">'
                f'<div style="background:{green}; color:#fff; font-size:9.5px; padding:3px;">{label}</div>'
                f'<div style="font-size:10.5px; font-weight:700; padding:5px 3px;">{value}</div></div>')

    head = "".join(
        f'<th style="padding:7px 4px; background:{green}; color:#fff; border:1px solid {gold}; width:{w};">{t}</th>'
        for t, w in (("م", "6%"), ("التاريخ", "14%"), ("البيان", "auto"), ("مدين", "17%"), ("دائن", "17%"))
    )
    body = "".join(
        f'<tr><td style="border:1px solid #D9CFA8; text-align:center; padding:5px 3px;">{i}</td>'
        f'<td style="border:1px solid #D9CFA8; text-align:center;">{_esc(r.get("transaction_date"))}</td>'
        f'<td style="border:1px solid #D9CFA8; padding:5px 6px;">{_esc(r.get("description"))}</td>'
        f'<td style="border:1px solid #D9CFA8; text-align:center;">{_amt(r.get("debit"))}</td>'
        f'<td style="border:1px solid #D9CFA8; text-align:center;">{_amt(r.get("credit"))}</td></tr>'
        for i, r in enumerate(_rows(data), 1)
    )
    foot = (f'<tr style="font-weight:700; background:#F6F1E1;"><td colspan="3" style="border:1px solid {gold}; padding:7px 6px;">الإجمالي</td>'
            f'<td style="border:1px solid {gold}; text-align:center;" class="num">{_esc(s.get("total_debit_label"))}</td>'
            f'<td style="border:1px solid {gold}; text-align:center;" class="num">{_esc(s.get("total_credit_label"))}</td></tr>'
            f'<tr style="font-weight:700; background:{green}; color:#fff;"><td colspan="3" style="padding:8px 6px; border:1px solid {gold};">الرصيد المستحق على العميل</td>'
            f'<td colspan="2" style="text-align:center; font-size:13px; border:1px solid {gold};"><span class="num">{_esc(s.get("difference_label"))}</span> ريال سعودي</td></tr>')
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{body}{foot}</tbody></table>'
             if body else "")
    return _document(
        frame + _letterhead(data, accent=green, rule=gold)
        + '<div style="text-align:center; margin:2px 0 10px;">'
          f'<span style="display:inline-block; background:{green}; color:#fff; font-size:17px; font-weight:700; '
          f'padding:5px 34px; border-radius:20px; box-shadow:0 0 0 2px #fff, 0 0 0 3.5px {gold};">{_esc(data.get("title"))}</span></div>'
        + '<div style="display:grid; grid-template-columns:2fr 1fr 1fr 1fr; gap:6px; margin-bottom:12px;">'
        + meta("اسم العميل", _customer(data))
        + meta("رقم الكشف", f'<span class="num">{ref}</span>')
        + meta("من تاريخ", f'<span class="num">{_esc(data.get("date_from_label"))}</span>')
        + meta("إلى تاريخ", f'<span class="num">{_esc(data.get("date_to_label"))}</span>')
        + "</div>" + table + _empty_note(data)
        + '<div style="display:flex; justify-content:flex-end; margin-top:26px;">'
        + signature_line_html(font_size="11px", color="#374151") + "</div>"
        + _auto_note(),
        landscape=False,
    )


build_statement_html_v8.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helpers shared by النموذج التاسع → الثالث عشر (added 2026-10-18)
# ---------------------------------------------------------------------------
def _kind(row: dict[str, Any]) -> str:
    """invoice_cash / invoice_credit / receipt — from the service's own البيان."""
    text = str(row.get("description") or "")
    if _d(row.get("debit")):
        return "invoice_cash" if "نقدية" in text else "invoice_credit"
    return "receipt"


def _words(summary: dict[str, Any]) -> str:
    """The closing balance in Arabic words («فقط … ريالاً لا غير»), sign dropped."""
    raw = str(summary.get("difference_label") or "0").replace(",", "")
    return amount_in_words_ar(raw.lstrip("-"))


def _style(css: str) -> str:
    """Page-level CSS. Fonts live here, never in an inline style attribute —
    a font stack's quotes would close the attribute early."""
    return f"<style>{css}</style>"


# ---------------------------------------------------------------------------
# النموذج التاسع — الشريط الجانبي (identity + totals in a side column on every page). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v9(data: dict[str, Any]) -> str:
    """A coloured side column — logo, company, customer, period, totals and the
    balance due — fixed on every printed page beside a plain table."""
    teal, side_w = "#115E59", 200
    s = _summary(data)
    company = data.get("company") or {}
    logo = company_logo_data_uri(company) if company else ""
    css = _style(f"""
      .sheet {{ position:relative; padding-right:{side_w + 22}px !important; min-height:1080px; }}
      .side {{ position:absolute; top:0; right:0; bottom:0; width:{side_w}px; background:{teal}; color:#fff;
               padding:20px 14px; }}
      @media print {{
        .sheet {{ min-height:0; }}
        .side {{ position:fixed; top:0; bottom:0; }}
      }}
      .side .lbl {{ font-size:9px; color:#99D5CF; margin-top:12px; }}
      .side .val {{ font-size:11.5px; font-weight:700; overflow-wrap:anywhere; }}
      .side .big {{ font-size:19px; font-weight:700; }}
    """)
    side = (
        '<div class="side">'
        + (f'<div style="background:#fff; border-radius:8px; padding:8px; text-align:center;">'
           f'<img src="{logo}" style="max-width:150px; max-height:70px;" alt=""></div>' if logo else "")
        + f'<div style="font-size:12.5px; font-weight:700; margin-top:12px; white-space:pre-line;">{_esc(company.get("name_ar"))}</div>'
        + (f'<div dir="ltr" style="font-size:10px; color:#CDEAE6; text-align:right; margin-top:2px; white-space:pre-line;">{_esc(company.get("name_en"))}</div>' if company.get("name_en") else "")
        + (f'<div class="lbl">الرقم الضريبي</div><div class="val num">{_esc(company.get("vat_number"))}</div>' if company.get("vat_number") else "")
        + (f'<div class="lbl">السجل التجاري</div><div class="val num">{_esc(company.get("commercial_registration"))}</div>' if company.get("commercial_registration") else "")
        + f'<div style="border-top:1px solid #2F7F78; margin:14px 0 0;"></div>'
        f'<div class="lbl">العميل</div><div class="val">{_customer(data)}</div>'
        f'<div class="lbl">من</div><div class="val">{_dt(data.get("date_from_label"))}</div>'
        f'<div class="lbl">إلى</div><div class="val">{_dt(data.get("date_to_label"))}</div>'
        f'<div class="lbl">عدد الحركات</div><div class="val">{len(_rows(data))}</div>'
        f'<div style="border-top:1px solid #2F7F78; margin:14px 0 0;"></div>'
        f'<div class="lbl">إجمالي المدين</div><div class="val num">{_esc(s.get("total_debit_label"))}</div>'
        f'<div class="lbl">إجمالي الدائن</div><div class="val num">{_esc(s.get("total_credit_label"))}</div>'
        f'<div style="background:#fff; color:{teal}; border-radius:8px; padding:8px 10px; margin-top:14px;">'
        f'<div style="font-size:9.5px;">الرصيد المستحق</div><div class="big num">{_esc(s.get("difference_label"))}</div>'
        '<div style="font-size:9px;">ريال سعودي</div></div></div>'
    )
    head = "".join(
        f'<th style="padding:7px 4px; border-bottom:2px solid {teal}; color:{teal}; width:{w}; text-align:{a};">{t}</th>'
        for t, w, a in (("التاريخ", "16%", "center"), ("البيان", "auto", "right"),
                        ("مدين", "19%", "center"), ("دائن", "19%", "center"))
    )
    body = "".join(
        f'<tr><td style="padding:6px 4px; text-align:center; border-bottom:1px solid #E2EEEC;">{_esc(r.get("transaction_date"))}</td>'
        f'<td style="padding:6px 6px; border-bottom:1px solid #E2EEEC;">{_esc(r.get("description"))}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #E2EEEC;">{_amt(r.get("debit"))}</td>'
        f'<td style="text-align:center; border-bottom:1px solid #E2EEEC;">{_amt(r.get("credit"), teal)}</td></tr>'
        for r in _rows(data)
    )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
             if body else "")
    return _document(
        css + side
        + f'<div style="font-size:26px; font-weight:700; color:{teal}; margin:6px 0 2px;">{_esc(data.get("title"))}</div>'
        + '<div dir="ltr" style="font-size:11px; letter-spacing:3px; color:#5E8F8A; text-align:right; margin-bottom:16px;">STATEMENT OF ACCOUNT</div>'
        + table + _empty_note(data)
        + '<div style="display:flex; justify-content:flex-end; margin-top:24px;">'
        + signature_line_html(font_size="11px", color="#374151") + "</div>" + _auto_note(),
        landscape=False,
    )


build_statement_html_v9.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج العاشر — الحديث المائل (diagonal gradient bands, pill totals). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v10(data: dict[str, Any]) -> str:
    """A modern sheet: a gradient title band with a slanted edge, pill-shaped totals,
    and a matching band on the bottom edge of every printed page."""
    a, b = "#6D28D9", "#DB2777"
    s = _summary(data)
    band = (
        f'<div style="position:relative; margin:4px -20px 16px; height:92px; '
        f'background:linear-gradient(110deg, {a} 0%, {b} 100%); clip-path:polygon(0 0, 100% 0, 100% 70%, 0 100%); '
        f'color:#fff; padding:14px 26px;">'
        '<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
        f'<div><div style="font-size:24px; font-weight:700;">{_esc(data.get("title"))}</div>'
        f'<div style="font-size:11px; opacity:.9;">{_customer(data)}</div></div>'
        f'<div style="text-align:left; font-size:10.5px; opacity:.95;">{_period(data)}<br>'
        f'{len(_rows(data))} حركة</div></div></div>'
    )
    pills = "".join(
        f'<div style="flex:1; border-radius:30px; padding:8px 16px; display:flex; justify-content:space-between; align-items:center; {st}">'
        f'<span style="font-size:10.5px;">{lbl}</span><span class="num" style="font-size:14px; font-weight:700;">{val}</span></div>'
        for lbl, val, st in (
            ("إجمالي المدين", _esc(s.get("total_debit_label")), f"border:1.5px solid {a}; color:{a};"),
            ("إجمالي الدائن", _esc(s.get("total_credit_label")), f"border:1.5px solid {b}; color:{b};"),
            ("الرصيد المستحق", _esc(s.get("difference_label")), f"background:linear-gradient(110deg,{a},{b}); color:#fff;"),
        )
    )
    head = "".join(
        f'<th style="padding:8px 4px; color:{a}; font-size:10px; text-align:{al}; width:{w}; border-bottom:2px solid #EDE9FE;">{t}</th>'
        for t, w, al in (("التاريخ", "15%", "center"), ("البيان", "auto", "right"),
                         ("مدين", "19%", "center"), ("دائن", "19%", "center"))
    )
    body = "".join(
        f'<tr><td style="padding:6px 4px; text-align:center;{" background:#FAF5FF;" if i % 2 else ""}">{_esc(r.get("transaction_date"))}</td>'
        f'<td style="padding:6px;{" background:#FAF5FF;" if i % 2 else ""}">{_esc(r.get("description"))}</td>'
        f'<td style="text-align:center;{" background:#FAF5FF;" if i % 2 else ""}">{_amt(r.get("debit"), a)}</td>'
        f'<td style="text-align:center;{" background:#FAF5FF;" if i % 2 else ""}">{_amt(r.get("credit"), b)}</td></tr>'
        for i, r in enumerate(_rows(data))
    )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
             if body else "")
    footer = (f'<div class="diag-foot" style="height:26px; background:linear-gradient(110deg,{a},{b}); '
              'clip-path:polygon(0 60%, 100% 0, 100% 100%, 0 100%);"></div>'
              '<style>.diag-foot { margin:18px -20px -18px; }'
              '@media print { .diag-foot { position:fixed; left:0; right:0; bottom:0; margin:0; } '
              '.sheet { padding-bottom:34px !important; } }</style>')
    return _document(
        _letterhead(data, accent=a, rule="#EDE9FE") + band
        + f'<div style="display:flex; gap:10px; margin-bottom:14px;">{pills}</div>'
        + table + _empty_note(data) + _auto_note() + footer,
        landscape=False,
    )


build_statement_html_v10.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الحادي عشر — الملوّن حسب النوع (type pills + per-type totals). Portrait
# ---------------------------------------------------------------------------
_KIND_LOOK = {
    "invoice_cash": ("فاتورة نقدية", "#1D4ED8", "#DBEAFE"),
    "invoice_credit": ("فاتورة آجلة", "#B45309", "#FEF3C7"),
    "receipt": ("سند قبض", "#047857", "#D1FAE5"),
}


def build_statement_html_v11(data: dict[str, Any]) -> str:
    """A «النوع» column of coloured pills (فاتورة نقدية / آجلة / سند قبض), a matching
    colour edge on every row, and a count + total per movement type."""
    s = _summary(data)
    groups: "OrderedDict[str, list]" = OrderedDict((k, [0, _ZERO]) for k in _KIND_LOOK)
    body = []
    for r in _rows(data):
        k = _kind(r)
        label, fg, bg = _KIND_LOOK[k]
        groups[k][0] += 1
        groups[k][1] += _d(r.get("debit")) or _d(r.get("credit"))
        body.append(
            f'<tr><td style="border-right:4px solid {fg}; padding:6px 6px; text-align:center;">{_esc(r.get("transaction_date"))}</td>'
            f'<td style="text-align:center;"><span style="background:{bg}; color:{fg}; border-radius:10px; padding:2px 9px; font-size:9.5px; font-weight:700; white-space:nowrap;">{label}</span></td>'
            f'<td style="padding:6px;">{_esc(r.get("description"))}</td>'
            f'<td style="text-align:center;">{_amt(r.get("debit"))}</td>'
            f'<td style="text-align:center;">{_amt(r.get("credit"))}</td></tr>'
        )
    css = _style(".ty tbody tr td { border-bottom:1px solid #EEF0F3; }")
    head = "".join(
        f'<th style="padding:7px 4px; background:#F3F4F6; color:#374151; width:{w};">{t}</th>'
        for t, w in (("التاريخ", "13%"), ("النوع", "14%"), ("البيان", "auto"), ("مدين", "17%"), ("دائن", "17%"))
    )
    table = (f'<table class="ty" style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'
             if body else "")
    by_type = (
        '<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; margin:0 0 12px;">'
        + "".join(
            f'<div style="border:1px solid {bg}; background:{bg}55; border-radius:8px; padding:8px 10px;">'
            f'<div style="font-size:10px; color:{fg}; font-weight:700;">{label} · {groups[k][0]}</div>'
            f'<div class="num" style="font-size:14px; font-weight:700; color:#111827; text-align:right;">{_money(groups[k][1])}</div></div>'
            for k, (label, fg, bg) in _KIND_LOOK.items()
        )
        + '<div style="background:#111827; color:#fff; border-radius:8px; padding:8px 10px;">'
          '<div style="font-size:10px; color:#9CA3AF; font-weight:700;">الرصيد المستحق</div>'
          f'<div class="num" style="font-size:14px; font-weight:700; text-align:right;">{_esc(s.get("difference_label"))}</div></div></div>'
    )
    return _document(
        css + _letterhead(data, accent="#111827", rule="#111827")
        + '<div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:baseline; gap:4px 14px; margin-bottom:10px;">'
          f'<div style="font-size:19px; font-weight:700;">{_esc(data.get("title"))}</div>'
          f'<div style="font-size:11px; color:#4B5563;">{_customer(data)} · {_period(data)}</div></div>'
        + by_type + table + _empty_note(data)
        + f'<div style="display:flex; justify-content:space-between; font-weight:700; font-size:11px; margin-top:8px; padding:7px 8px; background:#F3F4F6;">'
          f'<span>الإجمالي</span><span>مدين <span class="num">{_esc(s.get("total_debit_label"))}</span> &nbsp;|&nbsp; '
          f'دائن <span class="num">{_esc(s.get("total_credit_label"))}</span></span></div>'
        + _auto_note(),
        landscape=False,
    )


build_statement_html_v11.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الثاني عشر — التقويم (a calendar per month, then the table). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v12(data: dict[str, Any]) -> str:
    """A calendar for every month in the statement, the days with movements shaded
    by size (● invoice, ○ receipt), then the table with a weekday column."""
    accent = "#0369A1"
    s = _summary(data)
    per_day: dict[date, list[Decimal]] = {}
    for r in _rows(data):
        d = _parse(r.get("transaction_date"))
        if d:
            slot = per_day.setdefault(d, [_ZERO, _ZERO])
            slot[0] += _d(r.get("debit"))
            slot[1] += _d(r.get("credit"))
    peak = max([v[0] + v[1] for v in per_day.values()] or [Decimal(1)]) or Decimal(1)
    months = sorted({(d.year, d.month) for d in per_day})
    cal = calendar.Calendar(firstweekday=6)          # week starts on Sunday
    days = ("أحد", "إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت")

    def month_grid(year: int, month: int) -> str:
        cells = []
        for d in cal.itermonthdates(year, month):
            if d.month != month:
                cells.append('<div></div>')
                continue
            v = per_day.get(d)
            if v:
                alpha = 0.25 + 0.75 * float((v[0] + v[1]) / peak)
                mark = ("●" if v[0] else "") + ("○" if v[1] else "")
                cells.append(
                    f'<div style="background:rgba(3,105,161,{alpha:.2f}); color:#fff; border-radius:4px; '
                    f'padding:3px 0; font-weight:700;">{d.day}<div style="font-size:7px; line-height:1;">{mark}</div></div>')
            else:
                cells.append(f'<div style="background:#F1F5F9; color:#94A3B8; border-radius:4px; padding:3px 0;">{d.day}'
                             '<div style="font-size:7px; line-height:1;">&nbsp;</div></div>')
        return (
            '<div style="border:1px solid #E2E8F0; border-radius:8px; padding:8px;">'
            f'<div style="font-weight:700; color:{accent}; font-size:11.5px; margin-bottom:5px;">{_month_name((year, month))}</div>'
            '<div style="display:grid; grid-template-columns:repeat(7, 1fr); gap:3px; text-align:center; font-size:9px;">'
            + "".join(f'<div style="color:#64748B; font-size:8px;">{n}</div>' for n in days)
            + "".join(cells) + "</div></div>"
        )

    grid = (
        f'<div style="display:grid; grid-template-columns:repeat({min(3, max(1, len(months)))}, 1fr); gap:10px; margin-bottom:6px; page-break-inside:avoid;">'
        + "".join(month_grid(y, m) for y, m in months) + "</div>"
        '<div style="font-size:9px; color:#64748B; margin-bottom:12px;">● يوم فيه فاتورة &nbsp; ○ يوم فيه سداد &nbsp; — كلما غمق اللون زاد حجم الحركة</div>'
    ) if months else ""
    head = "".join(
        f'<th style="padding:7px 4px; background:{accent}; color:#fff; width:{w}; text-align:{al};">{t}</th>'
        for t, w, al in (("التاريخ", "13%", "center"), ("اليوم", "11%", "center"), ("البيان", "auto", "right"),
                         ("مدين", "17%", "center"), ("دائن", "17%", "center"))
    )
    body = []
    for i, r in enumerate(_rows(data)):
        d = _parse(r.get("transaction_date"))
        z = " background:#F0F9FF;" if i % 2 else ""
        body.append(
            f'<tr><td style="padding:5px 4px; text-align:center;{z}">{_esc(r.get("transaction_date"))}</td>'
            f'<td style="text-align:center; color:#475569;{z}">{days[(d.weekday() + 1) % 7] if d else "—"}</td>'
            f'<td style="padding:5px 6px;{z}">{_esc(r.get("description"))}</td>'
            f'<td style="text-align:center;{z}">{_amt(r.get("debit"))}</td>'
            f'<td style="text-align:center;{z}">{_amt(r.get("credit"))}</td></tr>'
        )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'
             if body else "")
    return _document(
        _letterhead(data, accent=accent, rule=accent)
        + '<div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:baseline; gap:4px 14px; margin-bottom:10px;">'
          f'<div style="font-size:19px; font-weight:700; color:{accent};">{_esc(data.get("title"))}</div>'
          f'<div style="font-size:11px; color:#475569;">{_customer(data)} · {_period(data)}</div></div>'
        + grid + table + _empty_note(data)
        + f'<div style="text-align:left; font-size:11.5px; font-weight:700; margin-top:10px;">'
          f'مدين <span class="num">{_esc(s.get("total_debit_label"))}</span> · دائن <span class="num">{_esc(s.get("total_credit_label"))}</span> · '
          f'<span style="color:{accent};">الرصيد المستحق <span class="num">{_esc(s.get("difference_label"))}</span></span></div>'
        + _auto_note(),
        landscape=False,
    )


build_statement_html_v12.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الثالث عشر — المالي المؤمّن (security border, watermark, words). Portrait
# ---------------------------------------------------------------------------
def build_statement_html_v13(data: dict[str, Any]) -> str:
    """A cheque-like sheet: a guilloche security border on every page, the logo as a
    faint watermark, and the balance due spelled out in Arabic words."""
    deep, line = "#1E3A5F", "#7FA7D1"
    s = _summary(data)
    company = data.get("company") or {}
    logo = company_logo_data_uri(company) if company else ""
    guilloche = (
        f"repeating-linear-gradient(45deg, {line} 0 1px, transparent 1px 6px),"
        f"repeating-linear-gradient(-45deg, {line} 0 1px, transparent 1px 6px)"
    )
    css = _style(f"""
      .sec-frame {{ position:fixed; inset:0; background:{guilloche}; z-index:-3; }}
      .sec-inner {{ position:fixed; inset:10px; background:#fff; border:1.5px solid {deep};
                    outline:1px solid {deep}; outline-offset:-5px; z-index:-3; }}
      .sec-mark {{ position:fixed; top:38%; left:50%; transform:translate(-50%,-50%) rotate(-18deg);
                   width:360px; opacity:.07; z-index:-1; }}
      @media screen {{ .sheet {{ position:relative; }} .sec-frame, .sec-inner, .sec-mark {{ position:absolute; }} }}
      @media print {{ .sheet {{ padding:26px 28px !important; }} }}
    """)
    head = "".join(
        f'<th style="padding:7px 4px; border-top:1.5px solid {deep}; border-bottom:1.5px solid {deep}; color:{deep}; width:{w}; text-align:{al};">{t}</th>'
        for t, w, al in (("التاريخ", "15%", "center"), ("البيان", "auto", "right"),
                         ("مدين", "18%", "center"), ("دائن", "18%", "center"))
    )
    body = "".join(
        f'<tr><td style="padding:5px 4px; text-align:center; border-bottom:1px dotted {line};">{_esc(r.get("transaction_date"))}</td>'
        f'<td style="padding:5px 6px; border-bottom:1px dotted {line};">{_esc(r.get("description"))}</td>'
        f'<td style="text-align:center; border-bottom:1px dotted {line};">{_amt(r.get("debit"))}</td>'
        f'<td style="text-align:center; border-bottom:1px dotted {line};">{_amt(r.get("credit"))}</td></tr>'
        for r in _rows(data)
    )
    table = (f'<table style="font-size:10.5px;"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
             if body else "")
    words = _words(s)
    amount_box = (
        f'<div style="display:grid; grid-template-columns:auto 1fr; margin-top:14px; border:1.5px solid {deep}; border-radius:4px; overflow:hidden; page-break-inside:avoid;">'
        f'<div style="background:{deep}; color:#fff; padding:10px 16px; text-align:center;">'
        '<div style="font-size:9.5px; color:#BFD3EA;">الرصيد المستحق</div>'
        f'<div class="num" style="font-size:18px; font-weight:700;">{_esc(s.get("difference_label"))}</div>'
        '<div style="font-size:9px; color:#BFD3EA;">ريال سعودي</div></div>'
        f'<div style="padding:10px 14px; background:{guilloche.split(",")[0].replace(line, "#EAF1F9")}; font-size:11.5px; display:flex; align-items:center;">'
        f'<b>{_esc(words)}</b></div></div>'
    )
    return _document(
        css + '<div class="sec-frame"></div><div class="sec-inner"></div>'
        + _letterhead(data, accent=deep, rule=line)
        # After the letterhead in source order only; it is positioned, so this
        # does not move it on the page.
        + (f'<img class="sec-mark" src="{logo}" alt="">' if logo else "")
        + '<div style="text-align:center; margin:4px 0 12px;">'
          f'<div style="display:inline-block; border:1.5px solid {deep}; padding:5px 28px; letter-spacing:1px; font-size:18px; font-weight:700; color:{deep};">'
          f'{_esc(data.get("title"))}</div>'
          f'<div style="font-size:11px; color:#334E6E; margin-top:6px;">لحساب: <b>{_customer(data)}</b> — {_period(data)}</div></div>'
        + table + _empty_note(data)
        + f'<div style="display:flex; justify-content:space-between; font-size:11px; font-weight:700; color:{deep}; margin-top:8px;">'
          f'<span>إجمالي المدين: <span class="num">{_esc(s.get("total_debit_label"))}</span></span>'
          f'<span>إجمالي الدائن: <span class="num">{_esc(s.get("total_credit_label"))}</span></span></div>'
        + amount_box
        + '<div style="display:flex; justify-content:flex-end; margin-top:20px;">'
        + signature_line_html(font_size="11px", color=deep) + "</div>" + _auto_note(),
        landscape=False,
    )


build_statement_html_v13.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# النموذج الرابع عشر — الكشف الضريبي المفصّل (added 2026-10-20). Portrait
# ---------------------------------------------------------------------------
_VAT_RATE = Decimal("0.15")
_CENT = Decimal("0.01")


def _vat_split(row: dict[str, Any], breakdown: dict[Any, dict[str, Decimal]]) -> tuple[Decimal, Decimal] | None:
    """(taxable, VAT) of an invoice debit row; ``None`` for a credit row.

    The stored split from ``sales_invoices`` (``data["vat_breakdown"]``) when the
    screen supplied it; otherwise the total is split at the standard 15% rate —
    exact for a standard-rated invoice, since any discount is taken before VAT.
    """
    debit = _d(row.get("debit"))
    if not debit:
        return None
    stored = breakdown.get(row.get("source_id")) if row.get("source_type") == "sales_invoice" else None
    if stored:
        return _d(stored.get("taxable")), _d(stored.get("vat"))
    taxable = (debit / (1 + _VAT_RATE)).quantize(_CENT)
    return taxable, debit - taxable


def build_statement_html_v14(data: dict[str, Any]) -> str:
    """A VAT statement: supplier and customer side by side with their VAT and CR
    numbers, every invoice split into its taxable amount, its 15% VAT and its
    total, the running balance, and a VAT summary. No QR (user 2026-10-20)."""
    ink, copper, sand = "#2F3437", "#B5652B", "#F4F1EE"
    s = _summary(data)
    company = data.get("company") or {}
    customer = data.get("customer") or {}
    breakdown = data.get("vat_breakdown") or {}
    css = _style(f"""
      .vt td {{ padding:5px 4px; border-bottom:1px solid #E6E8E9; }}
      .vt tbody tr:nth-child(even) td {{ background:#FAFAF9; }}
      .vt .tot td {{ background:{sand} !important; font-weight:700; border-top:1.5px solid {ink}; border-bottom:1.5px solid {ink}; }}
      .party {{ border:1px solid #DADDDF; border-radius:4px; font-size:10.5px; line-height:1.7; }}
      .party .h {{ padding:4px 10px; background:{sand}; color:{copper}; font-weight:700; border-bottom:1px solid #DADDDF; }}
      .party .b {{ padding:6px 10px; }}
    """)

    def party(title: str, name: str, vat: Any, cr: Any, address: Any) -> str:
        lines = "".join(
            f'<div>{lbl}: <span class="num">{_esc(v)}</span></div>' if lbl != "العنوان" else f"<div>{_esc(v)}</div>"
            for lbl, v in (("الرقم الضريبي", vat), ("السجل التجاري", cr), ("العنوان", address)) if v
        )
        return (f'<div class="party"><div class="h">{title}</div><div class="b">'
                f'<div style="font-size:12px; font-weight:700;">{name}</div>{lines}</div></div>')

    parties = (
        '<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">'
        + party("المورّد", _esc(company.get("name_ar") or data.get("company_label") or "الكل"),
                company.get("vat_number"), company.get("commercial_registration"), company.get("address_ar"))
        + party("العميل", _esc(customer.get("customer_name") or data.get("customer_label") or "الكل"),
                customer.get("vat_number"), customer.get("cr"), customer.get("address"))
        + "</div>"
    )

    taxable_total = vat_total = _ZERO
    invoices = 0
    body = []
    for row, balance in rows_with_balance(_rows(data)):
        split = _vat_split(row, breakdown)
        if split:
            taxable_total += split[0]
            vat_total += split[1]
            invoices += 1
        body.append(
            f'<tr><td style="text-align:center;">{_esc(row.get("transaction_date"))}</td>'
            f'<td>{_esc(row.get("description"))}</td>'
            f'<td style="text-align:center;">{_amt(split[0]) if split else _amt(0)}</td>'
            f'<td style="text-align:center;">{_amt(split[1]) if split else _amt(0)}</td>'
            f'<td style="text-align:center;">{_amt(row.get("debit"))}</td>'
            f'<td style="text-align:center;">{_amt(row.get("credit"))}</td>'
            f'<td style="text-align:center; font-weight:700;">{_bal(balance)}</td></tr>'
        )
    head = "".join(
        f'<th style="padding:6px 4px; background:{ink}; color:#fff; font-weight:400; width:{w}; text-align:{al};">{t}</th>'
        for t, w, al in (("التاريخ", "11%", "center"), ("المستند", "auto", "right"),
                         ("قبل الضريبة", "13%", "center"), ("ضريبة 15٪", "11%", "center"),
                         ("الإجمالي (مدين)", "13%", "center"), ("المسدد (دائن)", "13%", "center"),
                         ("الرصيد", "14%", "center"))
    )
    foot = (
        '<tr class="tot"><td></td><td>الإجمالي</td>'
        f'<td style="text-align:center;" class="num">{_money(taxable_total)}</td>'
        f'<td style="text-align:center;" class="num">{_money(vat_total)}</td>'
        f'<td style="text-align:center;" class="num">{_esc(s.get("total_debit_label"))}</td>'
        f'<td style="text-align:center;" class="num">{_esc(s.get("total_credit_label"))}</td>'
        f'<td style="text-align:center;" class="num">{_esc(s.get("difference_label"))}</td></tr>'
    )
    table = (f'<table class="vt" style="font-size:10px;"><thead><tr>{head}</tr></thead>'
             f'<tbody>{"".join(body)}{foot}</tbody></table>' if body else "")

    def line(label: str, value: str, bold: bool = False) -> str:
        weight = " font-weight:700;" if bold else ""
        return (f'<tr><td style="border:1px solid #DADDDF; background:{sand}; padding:5px 10px; width:60%;">{label}</td>'
                f'<td style="border:1px solid #DADDDF; padding:5px 10px; text-align:left;{weight}"><span class="num">{value}</span></td></tr>')

    vat_box = (
        '<div style="display:flex; justify-content:flex-end; margin-top:14px; page-break-inside:avoid;">'
        '<table style="width:55%; font-size:10.5px;">'
        + line("إجمالي المبيعات الخاضعة للضريبة", _money(taxable_total))
        + line("ضريبة القيمة المضافة 15٪", _money(vat_total))
        + line("الإجمالي شامل الضريبة", _money(taxable_total + vat_total), bold=True)
        + line("عدد الفواتير الضريبية", str(invoices))
        + line("الرصيد المستحق", _esc(s.get("difference_label")), bold=True)
        + "</table></div>"
    ) if body else ""

    customer_id = data.get("customer_id")
    to_month = str(data.get("date_to_label") or "").replace("-", "")[:6]
    ref = f"ST-{customer_id}-{to_month}" if customer_id and to_month.isdigit() else "—"
    title = (
        f'<div style="display:flex; justify-content:space-between; align-items:flex-end; '
        f'border-bottom:2px solid {copper}; padding-bottom:8px; margin-bottom:12px;">'
        f'<div><div style="font-size:19px; font-weight:700; color:{ink};">{_esc(data.get("title"))}</div>'
        f'<div style="font-size:10.5px; color:{copper};">كشف ضريبي مفصّل · <span dir="ltr">VAT Statement of Account</span></div></div>'
        f'<div style="text-align:left; font-size:10.5px; color:#6E7477; line-height:1.7;">'
        f'رقم الكشف <span class="num">{ref}</span><br>{_period(data)}</div></div>'
    )
    return _document(
        css + _letterhead(data, accent=ink, rule=copper) + title + parties
        + table + _empty_note(data) + vat_box + _auto_note(),
        landscape=False,
    )


build_statement_html_v14.landscape = False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Dispatch + page layout
# ---------------------------------------------------------------------------
_BUILDERS: dict[int, Callable[[dict[str, Any]], str]] = {
    1: build_statement_html_v1,
    2: build_statement_html_v2,
    3: build_statement_html_v3,
    4: build_statement_html_v4,
    5: build_statement_html_v5,
    6: build_statement_html_v6,
    7: build_statement_html_v7,
    8: build_statement_html_v8,
    9: build_statement_html_v9,
    10: build_statement_html_v10,
    11: build_statement_html_v11,
    12: build_statement_html_v12,
    13: build_statement_html_v13,
    14: build_statement_html_v14,
}


def choose_statement_builder(
    parent: QWidget | None, action_label: str
) -> "Callable[[dict[str, Any]], str] | None":
    """Ask which statement layout to use; return its builder or ``None``.

    Reuses the sales-invoice picker dialog rather than growing a second one — it
    already takes its options as an argument. Thirteen options (2026-10-18), and
    fourteen since 2026-10-20, are too many for its default single row, so they
    go in its two-column grid.
    """
    choice = choose_invoice_template(
        parent, action_label, STATEMENT_TEMPLATE_OPTIONS, orientation="vertical"
    )
    if choice is None:
        return None
    return _BUILDERS.get(choice, build_statement_html_v1)


def statement_page_layout(html_builder: Callable[[dict[str, Any]], str]) -> QPageLayout:
    """A4 in the orientation the chosen template declares.

    The orientation lives on the builder because it is a property of the design,
    not of the caller: النموذج الأول/الثاني are wide (seven and six columns), while
    النموذج الثالث is a portrait letterhead. Chromium's ``printToPdf`` takes the
    layout as an argument and ignores any CSS ``@page``, so this is the only place
    it can be decided.
    """
    landscape = bool(getattr(html_builder, "landscape", True))
    return QPageLayout(
        QPageSize(QPageSize.A4),
        QPageLayout.Landscape if landscape else QPageLayout.Portrait,
        QMarginsF(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM, _MARGIN_MM),
        # Millimetre, explicitly: QPageLayout's default unit is **Point**, so the
        # same numbers silently meant ~4mm and printed the table hard against the
        # paper edge — inside the unprintable margin of most office printers.
        QPageLayout.Millimeter,
    )


def _default_pdf_name(data: dict[str, Any]) -> str:
    label = str(data.get("customer_label") or "").strip()
    safe = "".join(ch for ch in label if ch.isalnum() or ch in (" ", "-", "_")).strip()
    return f"كشف حساب - {safe}.pdf" if safe and safe != "الكل" else "كشف حساب العميل.pdf"


# ---------------------------------------------------------------------------
# Preview dialog
# ---------------------------------------------------------------------------
class CustomerStatementPreviewDialog(QDialog):
    """On-screen preview of the printable statement, with export/print/close."""

    def __init__(
        self,
        data: dict[str, Any],
        parent: QWidget | None = None,
        html_builder: Callable[[dict[str, Any]], str] = build_statement_html_v1,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._html_builder = html_builder
        self.setWindowTitle("معاينة كشف الحساب")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(1040, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.export_button = QPushButton("تصدير PDF")
        self.export_button.setFixedHeight(36)
        self.export_button.setMinimumWidth(130)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.setIcon(si_icon("fa5s.file-pdf", color="#FFFFFF"))
        style_button(self.export_button, "red")
        self.export_button.clicked.connect(self._on_export)

        self.print_button = QPushButton("طباعة")
        self.print_button.setFixedHeight(36)
        self.print_button.setMinimumWidth(110)
        self.print_button.setCursor(Qt.PointingHandCursor)
        self.print_button.setIcon(si_icon("fa5s.print", color="#374151"))
        style_button(self.print_button, "white")
        self.print_button.clicked.connect(self._on_print)

        close_button = QPushButton("إغلاق")
        close_button.setFixedHeight(36)
        close_button.setMinimumWidth(100)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setIcon(si_icon("fa5s.times", color="#374151"))
        style_button(close_button, "white")
        close_button.clicked.connect(self.reject)

        bar.addWidget(self.export_button)
        bar.addWidget(self.print_button)
        bar.addStretch(1)
        bar.addWidget(close_button)
        root.addLayout(bar)

        self.view = QWebEngineView(self)
        self.view.setStyleSheet(
            "background:#e9e9ea; border:1px solid #E5E7EB; border-radius:8px;"
        )
        self.view.setHtml(html_builder(data))
        root.addWidget(self.view, 1)

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ كشف الحساب PDF", _default_pdf_name(self._data), "PDF (*.pdf)"
        )
        if not path:
            return
        self.export_button.setEnabled(False)

        def _finished(file_path: str, success: bool) -> None:
            self.export_button.setEnabled(True)
            try:
                self.view.page().pdfPrintingFinished.disconnect(_finished)
            except (RuntimeError, TypeError):
                pass
            if success:
                QMessageBox.information(self, "تم", f"تم تصدير كشف الحساب إلى:\n{file_path}")
            else:
                QMessageBox.warning(self, "تعذّر التصدير", "حدث خطأ أثناء إنشاء ملف PDF.")

        self.view.page().pdfPrintingFinished.connect(_finished)
        self.view.page().printToPdf(path, statement_page_layout(self._html_builder))

    def _on_print(self) -> None:
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except Exception:  # noqa: BLE001
            QMessageBox.warning(self, "الطباعة", "خدمة الطباعة غير متاحة.")
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageLayout(statement_page_layout(self._html_builder))
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.Accepted:
            return
        self._printer = printer  # keep a reference during the async print

        def _done(success: bool) -> None:  # noqa: ARG001
            try:
                self.view.printFinished.disconnect(_done)
            except (RuntimeError, TypeError):
                pass

        self.view.printFinished.connect(_done)
        self.view.print(printer)


# ---------------------------------------------------------------------------
# Direct PDF export (toolbar button, no preview window)
# ---------------------------------------------------------------------------
def export_statement_to_pdf(
    parent: QWidget,
    data: dict[str, Any],
    html_builder: Callable[[dict[str, Any]], str] = build_statement_html_v1,
) -> None:
    """Ask for a path and render the statement straight to a PDF file."""
    path, _ = QFileDialog.getSaveFileName(
        parent, "حفظ كشف الحساب PDF", _default_pdf_name(data), "PDF (*.pdf)"
    )
    if not path:
        return

    from PySide6.QtWebEngineCore import QWebEnginePage

    page = QWebEnginePage(parent)
    # Hold a reference on the parent so the page survives the async PDF write.
    holder = getattr(parent, "_statement_pdf_pages", None)
    if holder is None:
        holder = []
        parent._statement_pdf_pages = holder  # type: ignore[attr-defined]
    holder.append(page)

    def _cleanup() -> None:
        try:
            holder.remove(page)
        except ValueError:
            pass
        page.deleteLater()

    def _on_pdf(file_path: str, success: bool) -> None:
        if success:
            QMessageBox.information(parent, "تم", f"تم تصدير كشف الحساب إلى:\n{file_path}")
        else:
            QMessageBox.warning(parent, "تعذّر التصدير", "حدث خطأ أثناء إنشاء ملف PDF.")
        _cleanup()

    def _on_load(ok: bool) -> None:
        if not ok:
            QMessageBox.warning(parent, "تعذّر التصدير", "تعذّر تجهيز مستند كشف الحساب.")
            _cleanup()
            return
        QTimer.singleShot(150, lambda: page.printToPdf(path, statement_page_layout(html_builder)))

    page.pdfPrintingFinished.connect(_on_pdf)
    page.loadFinished.connect(_on_load)
    page.setHtml(html_builder(data))


def print_statement(
    parent: QWidget,
    data: dict[str, Any],
    html_builder: Callable[[dict[str, Any]], str] = build_statement_html_v1,
) -> None:
    """Send the statement straight to a printer, without the preview window.

    Chromium can only print a *loaded* page, and both the load and the print are
    asynchronous, so the view is parented and held on ``parent`` until printing
    reports back — dropping it early cancels the job silently. It is deliberately
    never shown: it exists only to render.
    """
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter

    view = QWebEngineView(parent)
    view.setVisible(False)
    holder = getattr(parent, "_statement_print_views", None)
    if holder is None:
        holder = []
        parent._statement_print_views = holder  # type: ignore[attr-defined]
    holder.append(view)

    def _cleanup() -> None:
        try:
            holder.remove(view)
        except ValueError:
            pass
        view.deleteLater()

    def _on_load(ok: bool) -> None:
        if not ok:
            QMessageBox.warning(parent, "الطباعة", "تعذّر تجهيز مستند كشف الحساب.")
            _cleanup()
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageLayout(statement_page_layout(html_builder))
        dialog = QPrintDialog(printer, parent)
        if dialog.exec() != QPrintDialog.Accepted:
            _cleanup()
            return

        def _done(success: bool) -> None:
            if not success:
                QMessageBox.warning(parent, "الطباعة", "تعذّرت طباعة كشف الحساب.")
            _cleanup()

        view.printFinished.connect(_done)
        view.print(printer)

    view.loadFinished.connect(_on_load)
    view.setHtml(html_builder(data))


__all__ = [
    "STATEMENT_TEMPLATE_OPTIONS",
    "build_statement_html_v1",
    "build_statement_html_v2",
    "build_statement_html_v3",
    "build_statement_html_v4",
    "build_statement_html_v5",
    "build_statement_html_v6",
    "build_statement_html_v7",
    "build_statement_html_v8",
    "build_statement_html_v9",
    "build_statement_html_v10",
    "build_statement_html_v11",
    "build_statement_html_v12",
    "build_statement_html_v13",
    "build_statement_html_v14",
    "choose_statement_builder",
    "statement_page_layout",
    "rows_with_balance",
    "CustomerStatementPreviewDialog",
    "export_statement_to_pdf",
    "print_statement",
]
