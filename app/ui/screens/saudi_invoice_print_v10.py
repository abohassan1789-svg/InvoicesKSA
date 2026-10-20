"""«الإسناد الماسي» — a branded (red/yellow) Saudi tax-invoice layout.

Recreates the design the user supplied (``اسناد الماسي.pdf``) for the company
«شركة الإسناد الماسي الصناعية». The brand furniture is FIXED — printed the same
on every invoice regardless of the selected company, exactly like the fixed logo
of «المتكاملة» (:mod:`saudi_invoice_print_v9`):

* a full-width brand header band (logo + Arabic/English name + social + CR),
* the company's own VAT number + its barcode block (top-right),
* the fixed bank-details table (البنك الأهلي / مصرف الراجحي),
* a full-width brand footer band (diamond logo + contact + a small QR).

Everything else is LIVE invoice data from the shared ``data`` dict: the invoice
number/date, the customer block, the items table and the totals, plus the ZATCA
QR the caller built. The items («التفاصيل») table is laid out left-to-right —
``#`` on the left, ``الصافي`` on the right — to match the original exactly.

Per the user (2026-08-22): «الصافي» is each line's amount AFTER VAT (its full
line total); the «الخصم» column is always ``0.0%`` (the app has no per-line
discount yet). Presentation only — no database, no ZATCA logic of its own.
"""

from __future__ import annotations

import datetime
import html
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    _money,
    _qty,
    amount_in_words_ar,
    qr_vector_data_uri,
    with_print_descriptions,
)
from app.ui.screens.saudi_invoice_print_v3 import _dec

_B = "#111111"          # border / ink
_LABEL_FILL = "#f4f4f4"  # the info table's label-cell fill
_FONTS = "'Tajawal','Cairo','Tahoma','Arial',sans-serif"
_WAREHOUSE = "المستودع الرئيسى"

# The fixed bank details for الإسناد الماسي (printed on every invoice).
_BANKS = (
    ("SA90 1000 0021 0962 5300 0105", "21096253000105", "البنك الاهلي"),
    ("SA9180000129608010090906", "129608010090906", "مصرف الراجحي"),
)


def _info_cell(text: str, *, label: bool = False, colspan: int = 1, width: str = "") -> str:
    fill = _LABEL_FILL if label else "#ffffff"
    w = f"width:{width};" if width else ""
    span = f' colspan="{colspan}"' if colspan > 1 else ""
    align = "right" if label else "center"
    weight = "800" if label else "700"
    return (
        f'<td{span} style="border:1.4px solid {_B}; padding:4px 9px; font-size:13px; '
        f"font-weight:{weight}; background:{fill}; text-align:{align}; "
        f'vertical-align:middle; {w}">{text}</td>'
    )


def _item_head(show_unit: bool = True, show_desc: bool = False) -> str:
    th = (
        f"border:1.4px solid {_B}; padding:4px 4px; font-size:12.5px; font-weight:800; "
        "text-align:center; background:#ffffff;"
    )
    unit_col = (("الوحدة", "8%"),) if show_unit else ()
    cols = (
        ("#", "5%"), ("كود الصنف", "11%"), ("الوصف", "22%"), *unit_col, ("الكميه", "8%"),
        ("السعر قبل الخصم", "13%"), ("الخصم", "8%"), ("السعر", "11%"), ("الصافي", "11%"),
    )
    if show_desc:
        # «وصف الصنف» right after «الوصف» (the item name); width mostly from the name.
        unit_col = (("الوحدة", "7%"),) if show_unit else ()
        cols = (
            ("#", "4%"), ("كود الصنف", "10%"), ("الوصف", "14%"), ("وصف الصنف", "19%"), *unit_col,
            ("الكميه", "7%"), ("السعر قبل الخصم", "11%"), ("الخصم", "6%"), ("السعر", "11%"), ("الصافي", "11%"),
        )
    return "".join(f'<td style="{th} width:{w};">{t}</td>' for t, w in cols)


def _item_row(index: int, line: dict[str, Any], show_unit: bool = True, show_desc: bool = False) -> str:
    td = (
        f"border:1.4px solid {_B}; padding:4px 4px; font-size:12.5px; font-weight:700; "
        "text-align:center; vertical-align:middle;"
    )
    desc = (
        f"border:1.4px solid {_B}; padding:4px 9px; font-size:12.5px; font-weight:700; "
        "text-align:center; vertical-align:middle; overflow-wrap:anywhere;"
    )
    code = html.escape(str(line.get("code") or ""))
    name = html.escape(str(line.get("name") or ""))
    price = _money(line.get("price"))
    unit_cell = (
        f'<td style="{td}">{html.escape(str(line.get("unit") or ""))}</td>'
        if show_unit
        else ""
    )
    item_desc = (
        f'<td style="{desc}">{html.escape(line.get("print_description") or "")}</td>' if show_desc else ""
    )
    return (
        "<tr>"
        f'<td style="{td}">{index}</td>'
        f'<td style="{td}">{code}</td>'
        f'<td style="{desc}">{name}</td>'
        f'{item_desc}{unit_cell}'
        f'<td style="{td}">{_qty(line.get("qty"))}</td>'
        f'<td style="{td}">{price}</td>'
        f'<td style="{td}">0.0%</td>'
        f'<td style="{td}">{price}</td>'
        f'<td style="{td}">{_money(line.get("total"))}</td>'
        "</tr>"
    )


def _totals_span_row(label: str, value: str, label_span: int = 7) -> str:
    """A totals row spanning the 8-column (LTR) items table: value in the two
    left cells, label filling the rest (matches the original's value-on-left)."""
    val = (
        f"border:1.4px solid {_B}; padding:5px 12px; font-size:14px; font-weight:800; "
        "text-align:left; direction:ltr;"
    )
    lab = (
        f"border:1.4px solid {_B}; padding:5px 14px; font-size:14px; font-weight:800; "
        "text-align:center; direction:rtl;"
    )
    return f'<tr><td colspan="2" style="{val}">{value}</td><td colspan="{label_span}" style="{lab}">{label}</td></tr>'


def _bank_rows() -> str:
    th = f"border:1.4px solid {_B}; padding:4px 11px; font-size:13px; font-weight:800; text-align:center;"
    td = f"border:1.4px solid {_B}; padding:4px 11px; font-size:12.5px; font-weight:700; text-align:center;"
    head = (
        f'<tr><td style="{th}">رقم الايبان</td><td style="{th}">رقم الحساب</td>'
        f'<td style="{th}">البنك</td></tr>'
    )
    body = "".join(
        f'<tr><td style="{td}">{iban}</td><td style="{td}">{acc}</td><td style="{td}">{bank}</td></tr>'
        for iban, acc, bank in _BANKS
    )
    return head + body


def build_invoice_html_v10(data: dict[str, Any]) -> str:
    """Build the full printable «الإسناد الماسي» invoice HTML from live data."""
    header = _asset_data_uri("alesnad_header.png")
    footer = _asset_data_uri("alesnad_footer.png")
    vatbar = _asset_data_uri("alesnad_vat.png")
    qr = qr_vector_data_uri(data.get("qr_payload"))

    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        issue_date = issued.strftime("%d-%m-%Y")
    else:
        issue_date = html.escape(str(issued or ""))

    cust_name = html.escape(str(customer.get("name") or ""))
    cust_vat = html.escape(str(customer.get("vat") or ""))
    cust_mobile = html.escape(str(customer.get("mobile") or customer.get("phone") or ""))
    cust_addr = html.escape(str(customer.get("address") or ""))
    salesperson = html.escape(str(data.get("salesperson") or ""))

    subtotal = _dec(totals.get("subtotal"))
    vat_total = _dec(totals.get("vat"))
    grand_total = _dec(totals.get("total"))
    words = html.escape(amount_in_words_ar(grand_total))

    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:82px; height:82px; object-fit:contain;">'
        if qr
        else ""
    )

    # The items and the closing block share ONE table: all but the last item are
    # the normal body; the last item + totals + bank + signatures + QR sit in a
    # second, no-break tbody, so a page break moves the last item WITH the closing
    # block (never the totals/footer alone) and the table's <thead> repeats above.
    show_desc = bool(data.get("show_description"))
    span = 10 if show_desc else 9
    item_rows = [_item_row(i, line, show_unit, show_desc) for i, line in enumerate(lines, start=1)]
    if item_rows:
        main_item_rows = "".join(item_rows[:-1])
        last_item_row = item_rows[-1]
    else:
        main_item_rows = ""
        last_item_row = (
            f'<tr><td colspan="{span}" style="border:1.4px solid {_B}; padding:16px 4px; '
            'text-align:center; color:#888; font-size:12.5px; font-weight:700;">لا توجد أصناف</td></tr>'
        )

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
  .sheet {{ box-sizing:border-box; width:816px; min-height:1056px; margin:0 auto; background:#ffffff;
            padding:0 26px 120px; color:{_B}; direction:rtl; font-family:{_FONTS};
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  /* The items table's own <thead> repeats at the top of every page the items
     run onto, so a continuation page always carries the column titles. */
  thead {{ display: table-header-group; }}
  /* The closing block (last item + totals + bank + signatures + QR) is one
     no-break <tbody>: when it cannot fit at the foot of a page it moves to the
     next page TOGETHER WITH at least one item — the totals are never stranded
     alone on a page of their own (user request 2026-08-22). */
  .summary {{ break-inside: avoid; page-break-inside: avoid; }}
  /* Brand footer pinned to the foot of EVERY printed page: a position:fixed box
     is painted on each page by Chromium's print engine, and the sheet's bottom
     padding reserves its height so content never overlaps it — so the footer is
     always at the bottom and never orphaned onto a page of its own. */
  .pfoot {{ position: fixed; left:26px; right:26px; bottom:0; }}
  .pfoot img {{ width:100%; display:block; }}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
</style>
</head>
<body>
  <div class="sheet">

    <!-- ===== BRAND HEADER (fixed) ===== -->
    <img src="{header}" alt="header" style="width:100%; display:block; margin-top:3px;">

    <!-- ===== VAT+barcode (right, fixed) | title + invoice no. (left) ===== -->
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin:4px 4px 5px;">
      <img src="{vatbar}" alt="vat" style="height:64px; object-fit:contain;">
      <div style="text-align:left; padding-top:4px;">
        <div style="font-size:17px; font-weight:800;">فاتوره ضريبية</div>
        <div style="font-size:15px; font-weight:800; margin-top:6px;">{invoice_number}</div>
      </div>
    </div>

    <!-- ===== CUSTOMER / INVOICE INFO ===== -->
    <table style="width:100%; table-layout:fixed;">
      <tr>
        {_info_cell("العميل", label=True, width="12%")}{_info_cell(cust_name)}
        {_info_cell("تاريخ الفاتورة", label=True, width="12%")}{_info_cell(issue_date, width="18%")}
      </tr>
      <tr>
        {_info_cell("الجوال", label=True)}{_info_cell(cust_mobile)}
        {_info_cell("الرقم الضريبي", label=True)}{_info_cell(cust_vat)}
      </tr>
      <tr>
        {_info_cell("الموقع", label=True)}{_info_cell(cust_addr)}
        {_info_cell("المندوب", label=True)}{_info_cell(salesperson)}
      </tr>
      <tr>
        {_info_cell("مستودع", label=True)}{_info_cell(_WAREHOUSE, colspan=3)}
      </tr>
    </table>

    <!-- ===== ITEMS (details) + CLOSING BLOCK — one table, LTR: # on the left.
              The second <tbody> (last item + totals + bank + signatures + QR)
              never splits, so it always carries an item onto a new page and the
              repeating <thead> gives that page its column titles. ===== -->
    <table style="width:100%; table-layout:fixed; margin-top:8px; direction:ltr;">
      <thead><tr>{_item_head(show_unit, show_desc)}</tr></thead>
      <tbody>{main_item_rows}</tbody>
      <tbody class="summary">
        {last_item_row}
        {_totals_span_row("اجمالي السعر", _money(subtotal), span - 2)}
        {_totals_span_row("الضريبة (E - VAT 15%)", _money(vat_total), span - 2)}
        {_totals_span_row("صافي الفاتورة", _money(grand_total), span - 2)}
        <tr><td colspan="{span}" style="border:1.4px solid {_B}; padding:5px 14px; font-size:14px; font-weight:800; text-align:right; direction:rtl;">{words}</td></tr>
        <tr><td colspan="{span}" style="border:none; padding:0;">
          <div style="direction:rtl;">
            <!-- BANK DETAILS (fixed) -->
            <table style="width:100%; table-layout:fixed; margin-top:8px;">
              {_bank_rows()}
            </table>
            <!-- SIGNATURES -->
            <table style="width:100%; table-layout:fixed;">
              <tr>
                <td style="border:1.4px solid {_B}; border-top:0; padding:5px; font-size:14px; font-weight:800; text-align:center;">توقيع المندوب<div style="margin-top:6px; letter-spacing:2px;">.................................</div></td>
                <td style="border:1.4px solid {_B}; border-top:0; padding:5px; font-size:14px; font-weight:800; text-align:center;">توقيع المستلم<div style="margin-top:6px; letter-spacing:2px;">.................................</div></td>
              </tr>
            </table>
            <!-- ZATCA QR (right) -->
            <div style="text-align:right; margin:4px 6px 2px;">
              {qr_html}
            </div>
          </div>
        </td></tr>
      </tbody>
    </table>

  </div>

  <!-- ===== BRAND FOOTER (fixed) — pinned to the foot of every printed page ===== -->
  <div class="pfoot"><img src="{footer}" alt="footer"></div>
</body>
</html>"""


__all__ = ["build_invoice_html_v10"]
