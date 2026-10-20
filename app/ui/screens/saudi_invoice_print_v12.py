"""«الخطوط السعودية» — an exact replica of the Saudi Safwa Medical monthly
statement-invoice supplied by the user (``الخطوط السعودية فواتير ديسمبر.pdf``).

The source is a monthly VAT statement issued *by* «مجمع صفوة السعودية الطبي /
Saudi Safwa Medical» *to* «شركة الخطوط السعودية SGS». Like «الإسناد الماسي»
(:mod:`saudi_invoice_print_v10`) and «اقاسيم» (:mod:`saudi_invoice_print_v11`),
this is a *fixed-brand* template: the header logo, the orange rule, the seller
info block, the bank line and the bilingual address footer are always Saudi
Safwa Medical's, regardless of the selected company. Everything invoice-specific
— the number, date, customer block, the 8-column items table, the totals box and
the QR — is filled from the one shared ``data`` dict every template consumes, so
the shared preview dialog and PDF exporter render it unchanged.

Design notes (from the source PDF):
* Brand colour is a red-orange rule ``#EE4A20`` under the logo and above the
  footer address (a subtle left→right gradient).
* «الحساب / Account» column = the line item name; «سعر الوحدة / Unit price»
  prints the stored price with up to 4 decimals (matching ``483.3333`` / ``310.00``
  in the source); «المبلغ / Amount» = amount before VAT; «الضريبة / Tax» = the
  rate; «مبلغ الضريبة / Tax Amount» = the VAT amount; «الإجمالي / Total» = line
  total incl. VAT.
* The items table is RTL (# on the right, الإجمالي on the left), followed by a
  summary row that totals the Amount and Tax-Amount columns.
* The optional company stamp uses the shared live-stamp mechanism
  (:func:`stamp_overlay_html` is not used; the stamp is drawn bottom-left beside
  the QR via :func:`company_stamp_data_uri`).
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    _money,
    _qty,
    company_stamp_data_uri,
    QR_PRINT_PX,
    qr_vector_data_uri,
    with_print_descriptions,
)
from app.ui.screens.saudi_invoice_print_v3 import _dec, _unit_price

# ---------------------------------------------------------------------------
# Design tokens — the source's red-orange brand rule on a plain black/white grid.
# ---------------------------------------------------------------------------
_BRAND = "#EE4A20"                       # the orange header/footer rule
_BRAND_GRAD = "linear-gradient(90deg, #F4531F 0%, #EA4410 45%, #F2603A 100%)"
_BORDER = "#000000"
_INK = "#111111"
_MUTED = "#222222"
_FONTS = "'Tajawal','Cairo','Segoe UI','Tahoma','Arial',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056

# ---------------------------------------------------------------------------
# Fixed brand identity — Saudi Safwa Medical (the issuer / seller).
# ---------------------------------------------------------------------------
_BRAND_VAT = "302087323500003"
_SELLER_NAME = "مجمع صفوة السعودية الطبي"
_SELLER_ADDRESS = "جدة – حي الشرفية – شمال الاسكان – شارع خالد بن هشام"
_BANK_LINE = "PAYMENT DETAILS : PANK NEME : ALHALY BANK IBAN:SA4010000039600000510108"

_FOOTER_EN_1 = "Jeddah - Al-Sharafiah - Eskan North - Khaled Bin Hesham St."
_FOOTER_EN_2 = "P.O.Box 372 Jeddah 21411 Tel.: 012-6518850 / 012-6530711"
_FOOTER_AR_1 = "جدة – الشرفية – شمال الإسكان – شارع خالد بن هشام"
_FOOTER_AR_2 = "ص. ب ٣٧٢ جدة ٢١٤١١ – تليفون: ٦٥١٨٨٥٠-٠١٢ / ٦٥٣٠٧١١-٠١٢"

# Default customer identity (the namesake «الخطوط السعودية»), used when the live
# ``data["customer"]`` leaves a field blank so the template still reads exactly
# like the source out of the box.
_DEF_CUST_NAME = "شركة الخطوط السعودية SGS"
_DEF_CUST_ADDRESS = "جدة حل البساتين / طريق الملك عبد العزيز مبني رقم 6649 –وحدة رقم3"
_DEF_CUST_VAT = "300000776210003"

_MONTHS_EN = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# Items table columns, right → left (RTL): Arabic label, English label, width.
_ITEM_COLS = (
    ("#", "", "5%"),
    ("الحساب", "Account", "14%"),
    ("الوحدة", "Unit", "8%"),
    ("الكمية", "Qty", "9%"),
    ("سعر الوحدة", "Unit price", "12%"),
    ("المبلغ", "Amount", "13%"),
    ("الضريبة", "Tax", "9%"),
    ("مبلغ الضريبة", "Tax Amount", "14%"),
    ("الإجمالي", "Total", "16%"),
)
# With «إظهار وصف الصنف»: «الوصف» after «الحساب», widened from all the columns.
_ITEM_COLS_DESC = (
    ("#", "", "4%"),
    ("الحساب", "Account", "12%"),
    ("الوصف", "Description", "17%"),
    ("الوحدة", "Unit", "7%"),
    ("الكمية", "Qty", "7%"),
    ("سعر الوحدة", "Unit price", "11%"),
    ("المبلغ", "Amount", "11%"),
    ("الضريبة", "Tax", "7%"),
    ("مبلغ الضريبة", "Tax Amount", "12%"),
    ("الإجمالي", "Total", "12%"),
)


def _rate_disp(value: Any) -> str:
    try:
        d = Decimal(str(value)).normalize()
        return f"{d:f}%"
    except Exception:  # noqa: BLE001
        return "15%"


def _statement_line(invoice_number: str, city: str, issued: Any) -> str:
    """«invoice No 360 Jeddah INVOICE STATMENT FOR THE MONTH OF December 2025».

    ``STATMENT`` is deliberately reproduced as spelt in the source.
    """
    if isinstance(issued, datetime.datetime):
        month = f"{_MONTHS_EN[issued.month - 1]} {issued.year}"
    else:
        month = ""
    city_part = f"{city} " if city else ""
    return (
        f"invoice No {invoice_number} {city_part}INVOICE STATMENT "
        f"FOR THE MONTH OF {month}".strip()
    )


def _party_block(name: str, address: str, vat: str) -> str:
    """One RTL info column: bold name, address, «الرقم الضريبي ...»."""
    return (
        f'<div style="font-size:12.5px; font-weight:800; color:{_INK}; '
        f'line-height:1.5; overflow-wrap:anywhere; word-break:break-word;">{name}</div>'
        f'<div style="font-size:11px; color:{_MUTED}; line-height:1.5; '
        f'margin-top:2px; overflow-wrap:anywhere; word-break:break-word;">{address}</div>'
        f'<div style="font-size:11px; color:{_MUTED}; margin-top:6px;">'
        f'الرقم الضريبي {vat}</div>'
    )


def _item_rows(lines: list[dict[str, Any]], show_unit: bool = True,
               show_desc: bool = False) -> tuple[str, Decimal, Decimal]:
    """The items table body + (sum before, sum vat) for the summary row.

    ``show_unit`` gates the «الوحدة» column: its per-row cell and the matching
    blank cell in the summary row are dropped in step with the header column.
    """
    td = (
        f"padding:12px 4px; border:1px solid {_BORDER}; font-size:12px; "
        "text-align:center; vertical-align:middle; color:#111; "
        "overflow-wrap:anywhere; word-break:break-word;"
    )
    if not lines:
        empty = (
            f'<tr><td colspan="{len(_ITEM_COLS) + show_desc}" style="{td} color:#888; '
            'padding:20px 6px;">لا توجد بنود</td></tr>'
        )
        return empty, Decimal("0"), Decimal("0")

    sum_before = Decimal("0")
    sum_vat = Decimal("0")
    rows: list[str] = []
    for index, line in enumerate(lines, start=1):
        name = html.escape(str(line.get("name") or ""))
        before = _dec(line.get("before"))
        vat_amount = _dec(line.get("vat_amount"))
        sum_before += before
        sum_vat += vat_amount
        unit_cell = (
            f'<td style="{td}">{html.escape(str(line.get("unit") or ""))}</td>'
            if show_unit
            else ""
        )
        cells = (
            f'<td style="{td}">{index}</td>',
            f'<td style="{td} font-weight:700;">{name}</td>',
            f'<td style="{td}">{html.escape(line.get("print_description") or "")}</td>' if show_desc else "",
            unit_cell,
            f'<td style="{td}">{_qty(line.get("qty")) if line.get("qty") not in (None, "") else ""}</td>',
            f'<td style="{td}">{_unit_price(line.get("price"))}</td>',
            f'<td style="{td}">{_money(before)}</td>',
            f'<td style="{td}">{_rate_disp(line.get("vat_rate"))}</td>',
            f'<td style="{td}">{_money(vat_amount)}</td>',
            f'<td style="{td} font-weight:700;">{_money(line.get("total"))}</td>',
        )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    # Summary row: totals under «المبلغ» and «مبلغ الضريبة», the rest blank.
    st = (
        f"padding:14px 4px; border:1px solid {_BORDER}; font-size:12px; "
        "text-align:center; vertical-align:middle; color:#111;"
    )
    unit_summary = f'<td style="{st}"></td>' if show_unit else ""
    desc_summary = f'<td style="{st}"></td>' if show_desc else ""
    summary = (
        "<tr>"
        f'<td style="{st}"></td>'
        f'<td style="{st}"></td>'
        f'{desc_summary}{unit_summary}'
        f'<td style="{st}"></td>'
        f'<td style="{st}"></td>'
        f'<td style="{st}">{_money(sum_before)}</td>'
        f'<td style="{st}"></td>'
        f'<td style="{st}">{_money(sum_vat)}</td>'
        f'<td style="{st}"></td>'
        "</tr>"
    )
    return "".join(rows) + summary, sum_before, sum_vat


def _totals_box(subtotal: Decimal, discount: Decimal, taxable: Decimal, vat_total: Decimal, grand_total: Decimal,
                rate: str) -> str:
    """The bordered totals box on the left: subtotal / discount / VAT / total."""
    amt = (
        f"width:130px; border-left:1px solid {_BORDER}; text-align:center; "
        "padding:8px 10px; font-size:12.5px; font-weight:700; white-space:nowrap;"
    )
    lbl = "padding:8px 12px; font-size:12px; line-height:1.4;"
    rows = (
        (subtotal, "المجموع الفرعي", "Subtotal", False),
        (discount, "خصم الفاتورة", "Invoice Discount", False),
        (taxable, "المبلغ الخاضع للضريبة", "Taxable Amount", False),
        (vat_total, f"ضريبة القيمة المضافة {rate}", "", False),
        (grand_total, "الإجمالي", "Total", True),
    )
    out: list[str] = []
    for i, (value, ar, en, bold) in enumerate(rows):
        top = "" if i == 0 else f"border-top:1px solid {_BORDER};"
        fw = "font-weight:800;" if bold else "font-weight:700;"
        en_html = (
            f'<div style="font-size:10.5px; color:#333; {fw}">{en}</div>' if en else ""
        )
        out.append(
            f'<div style="display:flex; {top}">'
            f'<div style="{amt} {"font-weight:800;" if bold else ""}">'
            f'{_money(value)} ريال</div>'
            f'<div style="flex:1; {lbl}">'
            f'<div style="{fw} color:{_INK};">{ar}</div>{en_html}</div>'
            "</div>"
        )
    return (
        f'<div style="width:47%; border:1px solid {_BORDER};">'
        + "".join(out)
        + "</div>"
    )


def build_invoice_html_v12(data: dict[str, Any]) -> str:
    """Build the full printable «الخطوط السعودية» statement-invoice HTML."""
    logo = _asset_data_uri("khutoot_saudia_logo.png")
    qr = qr_vector_data_uri(data.get("qr_payload"))

    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        issue_date = issued.strftime("%d-%m-%Y")
    else:
        issue_date = html.escape(str(issued or ""))
    city = html.escape(str(data.get("city") or ""))

    cust_name = html.escape(str(customer.get("name") or "")) or _DEF_CUST_NAME
    cust_addr = html.escape(str(customer.get("address") or "")) or _DEF_CUST_ADDRESS
    cust_vat = html.escape(str(customer.get("vat") or "")) or _DEF_CUST_VAT

    subtotal = _dec(totals.get("subtotal"))
    discount = _dec(totals.get("discount"))
    taxable = _dec(totals.get("taxable", subtotal - discount))
    vat_total = _dec(totals.get("vat"))
    grand_total = _dec(totals.get("total"))
    rate = _rate_disp(lines[0].get("vat_rate")) if lines else "15%"

    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))
    rows_html, _sb, _sv = _item_rows(lines, show_unit, show_desc)
    statement = html.escape(_statement_line(invoice_number, city, issued))

    # Header items table head (Arabic over English), RTL.
    th = (
        f"padding:8px 4px; border:1px solid {_BORDER}; text-align:center; "
        "vertical-align:middle; background:#ffffff; line-height:1.25;"
    )
    head_cells = []
    for ar, en, w in (_ITEM_COLS_DESC if show_desc else _ITEM_COLS):
        if not show_unit and ar == "الوحدة":
            continue
        en_html = (
            f'<div style="font-size:11px; font-weight:800; color:#111;">{en}</div>'
            if en else ""
        )
        head_cells.append(
            f'<td style="{th} width:{w};">'
            f'<div style="font-size:12.5px; font-weight:800; color:#111;">{ar}</div>'
            f"{en_html}</td>"
        )
    head_html = "".join(head_cells)

    # QR + optional live company stamp, bottom row.
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'object-fit:contain; background:#ffffff;">'
        if qr
        else ""
    )
    stamp_uri = company_stamp_data_uri(data.get("seller")) if data.get("show_stamp") else ""
    stamp_html = (
        f'<img src="{stamp_uri}" alt="stamp" style="max-width:230px; max-height:150px; '
        'object-fit:contain; filter:saturate(1.2) contrast(1.1);">'
        if stamp_uri
        else ""
    )

    totals_box = _totals_box(subtotal, discount, taxable, vat_total, grand_total, rate)

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
            background:#ffffff; color:{_INK}; direction:rtl; position:relative;
            font-family:{_FONTS}; box-shadow:0 6px 28px rgba(0,0,0,.16);
            padding:22px 34px 96px; }}
  table {{ page-break-inside:auto; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  @page {{ size:Letter; margin:0; }}
  @media print {{
    html, body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
</style>
</head>
<body>
  <div class="sheet">

    <!-- ===== HEADER: logo (right) ===== -->
    <div style="display:flex; justify-content:flex-start;">
      <img src="{logo}" alt="Saudi Safwa Medical" style="height:74px; display:block;">
    </div>

    <!-- ===== VAT No. + orange rule ===== -->
    <div style="display:flex; align-items:center; gap:10px; margin-top:4px; direction:ltr;">
      <div style="font-size:14px; font-weight:800; color:{_INK}; white-space:nowrap;">VAT No.: {_BRAND_VAT}</div>
      <div style="flex:1; height:13px; background:{_BRAND_GRAD};"></div>
    </div>

    <!-- ===== TITLE ===== -->
    <div style="text-align:center; margin:26px 0 22px; font-size:30px; font-weight:800; color:{_INK}; direction:ltr;">
      <span dir="ltr">Vat Invoice No {invoice_number} - {invoice_number}</span>
      <span dir="rtl"> فاتورة رقم</span>
    </div>

    <!-- ===== INFO ROW: customer | date | seller ===== -->
    <div style="display:flex; align-items:stretch; gap:0; margin-bottom:18px;">
      <div style="flex:1; min-width:0; padding:0 6px;">{_party_block(cust_name, cust_addr, cust_vat)}</div>
      <div style="width:150px; flex:none; padding:0 14px; border-left:1px solid #bbb; border-right:1px solid #bbb; text-align:center;">
        <div style="font-size:12px; color:{_MUTED};">تاريخ الفاتورة</div>
        <div style="font-size:12.5px; font-weight:800; color:{_INK}; margin-top:2px;">Invoice date</div>
        <div style="font-size:12.5px; color:{_INK}; margin-top:6px; direction:ltr;">{issue_date}</div>
      </div>
      <div style="flex:1; min-width:0; padding:0 6px;">{_party_block(_SELLER_NAME, _SELLER_ADDRESS, _BRAND_VAT)}</div>
    </div>

    <!-- ===== STATEMENT LINE ===== -->
    <div style="font-size:14px; font-weight:800; color:{_INK}; direction:ltr; text-align:left; margin:6px 2px 14px;">{statement}</div>

    <!-- ===== ITEMS TABLE ===== -->
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; direction:rtl;">
      <thead><tr>{head_html}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>

    <!-- ===== TOTALS BOX (left) ===== -->
    <div style="display:flex; justify-content:flex-end; margin-top:18px;">
      {totals_box}
    </div>

    <!-- ===== PAYMENT / BANK ===== -->
    <div style="text-align:center; font-size:13px; font-weight:700; color:{_INK}; direction:ltr; margin-top:26px;">{_BANK_LINE}</div>

    <!-- ===== STAMP (left) + QR (right) ===== -->
    <div style="display:flex; align-items:flex-end; justify-content:space-between; margin-top:24px; min-height:150px; direction:ltr;">
      <div style="flex:1; display:flex; align-items:flex-end; justify-content:flex-start;">{stamp_html}</div>
      <div style="display:flex; align-items:flex-end;">{qr_html}</div>
    </div>

    <!-- ===== FOOTER (orange rule + bilingual address) ===== -->
    <div style="position:absolute; left:0; right:0; bottom:0; padding:0 34px 14px;">
      <div style="height:4px; background:{_BRAND_GRAD}; margin-bottom:8px;"></div>
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div style="direction:ltr; text-align:left; font-size:11.5px; font-weight:800; color:{_INK}; line-height:1.6;">
          <div>{_FOOTER_EN_1}</div><div>{_FOOTER_EN_2}</div>
        </div>
        <div style="direction:rtl; text-align:right; font-size:11.5px; font-weight:800; color:{_INK}; line-height:1.6;">
          <div>{_FOOTER_AR_1}</div><div>{_FOOTER_AR_2}</div>
        </div>
      </div>
    </div>

  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v12"]
