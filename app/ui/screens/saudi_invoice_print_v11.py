"""«اقاسيم» — an exact replica of the AQASEEM factory tax-invoice layout.

Recreates the design the user supplied (``اقاسيم.pdf``): a fixed, full-width
brand header image (both companies' data, the flame logo and «فاتورة ضريبية»,
baked into one raster exactly as the original produces it), a bordered
two-column key/value info block with the QR to its left, a 14-column bordered
items table, a right-aligned totals block and a blue grand-total + Arabic
amount-in-words footer bar.

Like «الإسناد الماسي» (:mod:`saudi_invoice_print_v10`), this is a *fixed-brand*
template: the header is always AQASEEM's, ignoring the selected company's stored
name/logo. Everything else (invoice number, date, customer, items, totals, QR)
comes from the one shared ``data`` dict every template consumes, so the shared
preview dialog and PDF exporter render it unchanged. Presentation only: no
database, no ZATCA logic of its own — it just draws the QR the caller built.

Field notes (2026-08-22):
* «المبلغ» / «القيمة» = the line/grand total INCLUDING VAT (matches the source).
* «ضريبة» = the line VAT rate (e.g. ``15%``); «Sales Tax1» = the VAT amount.
* Columns the shared data model does not carry (العبوه، مجاني، تاريخ الانتهاء،
  الدفعه، السيريال، البيان، المندوب، الرقم المرجعي) are rendered empty, exactly
  as most rows of the original leave them.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    _money,
    amount_in_words_ar,
    QR_PRINT_PX,
    qr_vector_data_uri,
    with_print_descriptions,
)
from app.ui.screens.saudi_invoice_print_v3 import _dec

# ---------------------------------------------------------------------------
# Design tokens — plain black rules on white, the original's blue total accent.
# ---------------------------------------------------------------------------
_BORDER = "#111111"
_INK = "#111111"
_BLUE = "#2447ff"
_HEAD_BG = "#dcdcdc"
_FONTS = "'Tajawal','Cairo','Segoe UI','Tahoma','Arial',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056

# Items table columns, right → left, with fixed widths (اسم الصنف takes the rest).
_ITEM_COLS = (
    ("اسم الصنف", "15%"),
    ("الوحده", "6%"),
    ("العبوه", "5%"),
    ("الكمية", "6.5%"),
    ("مجاني", "5%"),
    ("السعر", "7%"),
    ("ضريبة", "6.5%"),
    ("خصم الاصناف", "6.5%"),
    ("المبلغ", "8%"),
    ("تاريخ الانتهاء", "7%"),
    ("الدفعه", "6.5%"),
    ("باركود", "8%"),
    ("السيريال", "7.5%"),
    ("البيان", "5%"),
)
# With «إظهار وصف الصنف»: «الوصف» after «اسم الصنف»; the extra width comes from the
# name and, mostly, from the narrow / always-blank columns.
_ITEM_COLS_DESC = (
    ("اسم الصنف", "11%"),
    ("الوصف", "11.5%"),
    ("الوحده", "5.5%"),
    ("العبوه", "5%"),
    ("الكمية", "6%"),
    ("مجاني", "5%"),
    ("السعر", "6.5%"),
    ("ضريبة", "5.5%"),
    ("خصم الاصناف", "6%"),
    ("المبلغ", "7%"),
    ("تاريخ الانتهاء", "5.5%"),
    ("الدفعه", "6%"),
    ("باركود", "6.5%"),
    ("السيريال", "7.5%"),
    ("البيان", "5%"),
)


def _fmt_datetime(issued: Any) -> str:
    """Format the issue timestamp as ``22-08-2026 7:28:18 AM`` (no leading hour
    zero), matching the original; falls back to the raw string."""
    if isinstance(issued, datetime.datetime):
        return f"{issued.strftime('%d-%m-%Y')} {issued.strftime('%I:%M:%S %p').lstrip('0')}"
    return html.escape(str(issued or ""))


def _pair(label: str, value: str) -> str:
    """One «label : value» cell of the info grid (label right, value to its left)."""
    if not label and not value:
        return '<div style="min-height:20px;"></div>'
    return (
        '<div style="display:grid; grid-template-columns:auto 1fr; gap:8px; '
        'align-items:baseline; padding:4px 0; min-height:20px;">'
        f'<div style="font-size:13px; font-weight:800; white-space:nowrap;">{label} :</div>'
        f'<div style="font-size:13px; font-weight:800; text-align:right;">{value}</div>'
        "</div>"
    )


def _item_rows(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """The 14-column items table body (13 when ``show_unit`` gates «الوحده»)."""
    td = (
        f"padding:11px 3px; border:1.3px solid {_BORDER}; font-size:11.5px; "
        "font-weight:700; text-align:center; vertical-align:middle; "
        "overflow:hidden; overflow-wrap:anywhere; word-break:break-word;"
    )
    if not lines:
        return (
            f'<tr><td colspan="{len(_ITEM_COLS) + show_desc}" style="{td} color:#888; '
            'padding:18px 6px;">لا توجد أصناف</td></tr>'
        )
    rows: list[str] = []
    for line in lines:
        name = html.escape(str(line.get("name") or ""))
        unit = html.escape(str(line.get("unit") or ""))
        barcode = html.escape(str(line.get("code") or ""))
        rate = line.get("vat_rate")
        try:
            # Trim trailing zeros so 15.00 → «15%» (matches the source), 15.5 → «15.5%».
            rate_disp = f"{Decimal(str(rate)).normalize():f}%" if rate not in (None, "") else ""
        except Exception:  # noqa: BLE001
            rate_disp = ""
        amount = _money(line.get("total"))  # المبلغ = إجمالي السطر شامل الضريبة
        unit_cell = f'<td style="{td}">{unit}</td>' if show_unit else ""
        desc_cell = (
            f'<td style="{td} text-align:right; padding-right:6px; overflow-wrap:anywhere;">'
            f'{html.escape(line.get("print_description") or "")}</td>'
            if show_desc
            else ""
        )
        cells = (
            f'<td style="{td} text-align:right; padding-right:6px; overflow-wrap:anywhere;">{name}</td>',
            desc_cell,
            unit_cell,
            f'<td style="{td}"></td>',                                   # العبوه
            f'<td style="{td}">{_money(line.get("qty"))}</td>',          # الكمية (رقمين عشريين كالأصل)
            f'<td style="{td}"></td>',                                   # مجاني
            f'<td style="{td}">{_money(line.get("price"))}</td>',
            f'<td style="{td}">{rate_disp}</td>',
            f'<td style="{td}">0</td>',                                  # خصم الاصناف
            f'<td style="{td}">{amount}</td>',                           # المبلغ (شامل الضريبة)
            f'<td style="{td}"></td>',                                   # تاريخ الانتهاء
            f'<td style="{td}">{amount}</td>',                           # الدفعه = المبلغ (كالأصل)
            f'<td style="{td}">{barcode}</td>',
            f'<td style="{td}">null</td>',                               # السيريال (ثابت كالأصل)
            f'<td style="{td}">0</td>',                                  # البيان (ثابت كالأصل)
        )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "".join(rows)


def _total_line(label: str, value: str) -> str:
    return (
        '<div style="display:flex; justify-content:flex-start; gap:16px; '
        f'font-size:14px; font-weight:800; color:{_INK}; padding:3px 0;">'
        f"<span>{label}</span><span>{value}</span></div>"
    )


def build_invoice_html_v11(data: dict[str, Any]) -> str:
    """Build the full printable «اقاسيم» invoice HTML from live data."""
    # «اقاسيم» always prints its own fixed brand header (bundled asset), never the
    # selected company's stored logo/name — a deliberate, per-design brand mark.
    header = _asset_data_uri("aqaseem_header.png")
    qr = qr_vector_data_uri(data.get("qr_payload"))

    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issue_dt = _fmt_datetime(data.get("issue_datetime"))
    payment = html.escape(str(data.get("payment_label") or ""))
    currency = html.escape(str(data.get("currency") or "SAR"))
    salesperson = html.escape(str(data.get("salesperson") or ""))
    reference = html.escape(str(data.get("reference") or ""))
    statement = html.escape(str(data.get("statement") or data.get("notes") or ""))

    customer_no = html.escape(str(customer.get("code") or ""))
    customer_name = html.escape(str(customer.get("name") or ""))
    customer_vat = html.escape(str(customer.get("vat") or ""))

    # Totals. «القيمة» and the footer amount are the grand total INCLUDING VAT.
    grand_total = _dec(totals.get("total"))
    vat_total = _dec(totals.get("vat"))
    disc_items = _dec(totals.get("discount"))
    total_qty = sum((_dec(ln.get("qty")) for ln in lines), Decimal("0"))

    header_html = (
        f'<img src="{header}" alt="اقاسيم" style="width:100%; display:block;">'
        if header
        else ""
    )
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'object-fit:contain; background:#ffffff;">'
        if qr
        else ""
    )

    # Info grid: right column then middle column, row by row (RTL grid fills R→L).
    right = (
        ("رقم الفاتورة", invoice_number),
        ("طريقة الدفع", payment),
        ("رقم العميل", customer_no),
        ("", ""),
        ("الرقم الضريبي", customer_vat),
        ("", ""),
        ("البيان", statement),
    )
    middle = (
        ("التاريخ", issue_dt),
        ("العملة", currency),
        ("اسم العميل", customer_name),
        ("", ""),
        ("المندوب", salesperson),
        ("", ""),
        ("الرقم المرجعي", reference),
    )
    info_cells = "".join(
        _pair(*r) + _pair(*m) for r, m in zip(right, middle)
    )

    th = (
        f"padding:8px 3px; border:1.3px solid {_BORDER}; font-size:12px; "
        f"font-weight:800; text-align:center; background:{_HEAD_BG}; line-height:1.2;"
    )
    head_html = "".join(
        f'<td style="{th} width:{w};">{label}</td>'
        for label, w in (_ITEM_COLS_DESC if show_desc else _ITEM_COLS)
        if show_unit or label != "الوحده"
    )

    totals_html = "".join(
        (
            _total_line("إجمالي الكمية", _money(total_qty)),
            _total_line("القيمة", _money(grand_total)),
            _total_line("خصم أصناف", _money(disc_items)),
            _total_line("خصم الفاتورة", _money(0)),
            _total_line("Sales Tax1", _money(vat_total)),
            _total_line("الأعباء", _money(0)),
        )
    )

    words = amount_in_words_ar(grand_total)

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; background:#e9e9ea; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ box-sizing:border-box; width:{_SHEET_W}px; min-height:{_SHEET_H}px; margin:0 auto;
            background:#ffffff; padding:16px 18px; color:{_INK}; direction:rtl;
            font-family:{_FONTS}; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ page-break-inside:auto; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
</style>
</head>
<body>
  <div class="sheet">

    <!-- ===== HEADER (fixed brand image) ===== -->
    <div style="border:1.5px solid {_BORDER}; border-bottom:none; padding:4px;">
      {header_html}
    </div>

    <!-- ===== INFO BLOCK + QR ===== -->
    <div style="border:1.5px solid {_BORDER}; border-top:none; display:flex; align-items:stretch;">
      <div style="flex:1; display:grid; grid-template-columns:1fr 1fr; gap:2px 24px;
                  padding:12px 16px; align-content:center;">
        {info_cells}
      </div>
      <div style="width:215px; display:flex; align-items:center;
                  justify-content:flex-start; padding:10px 14px 10px 10px;">
        {qr_html}
      </div>
    </div>

    <!-- ===== ITEMS TABLE ===== -->
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; margin-top:12px;">
      <thead><tr>{head_html}</tr></thead>
      <tbody>{_item_rows(lines, show_unit, show_desc)}</tbody>
    </table>

    <!-- ===== TOTALS ===== -->
    <div style="border:1.5px solid {_BORDER}; border-top:none; padding:8px 16px 4px;">
      {totals_html}
    </div>

    <!-- ===== GRAND TOTAL + AMOUNT IN WORDS ===== -->
    <div style="display:flex; border:1.5px solid {_BORDER};">
      <div style="width:180px; border-left:1.5px solid {_BORDER}; text-align:center;
                  padding:8px; color:{_BLUE}; font-weight:800; font-size:15px;">{_money(grand_total)}</div>
      <div style="flex:1; text-align:center; padding:8px; color:{_BLUE};
                  font-weight:800; font-size:15px;">{words}</div>
    </div>

  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v11"]
