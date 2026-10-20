"""«النموذج المتكاملة» — a plain black-on-white Saudi tax-invoice layout.

Recreates the design the user supplied (``الزيوت المتكاملة.pdf``): a centred
company logo and «فاتورة مبيعات ضريبية» heading, a right-aligned key/value block
for the seller, a bordered 5-column address table, the same pair for the
customer, a bordered items table (اسم الصنف | الوحدة | الكمية | السعر | المجموع),
a bordered totals table (نوع السداد | الاجمالي قبل .ض | الخصم | الضريبة | الاجمالي
بعد .ض) and a centred QR at the foot.

Like every other invoice template, :func:`build_invoice_html_v9` consumes the one
shared ``data`` dict (``seller`` / ``customer`` / ``lines`` / ``totals`` /
``qr_payload`` …) produced by the sales-invoice screen, so the shared preview
dialog and PDF exporter render it unchanged. Presentation only: no database, no
ZATCA logic of its own — it just draws the QR the caller already built.

The «المجموع» column is the line's amount BEFORE VAT (per the user's request,
2026-08-22); the VAT and grand totals live in the totals table below.
"""

from __future__ import annotations

import datetime
import html
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    _money,
    _qty,
    QR_PRINT_PX,
    qr_vector_data_uri,
    with_print_descriptions,
)
from app.ui.screens.saudi_invoice_print_v3 import _dec

# ---------------------------------------------------------------------------
# Design tokens — deliberately plain: black rules on white, no accent colour.
# ---------------------------------------------------------------------------
_BORDER = "#111111"
_INK = "#111111"
_FONTS = "'Tajawal','Cairo','Segoe UI','Tahoma','Arial',sans-serif"
_COUNTRY = "السعودية"

_SHEET_W = 816
_SHEET_H = 1056
_PAD_X = 40
_PAD_Y = 30


def _kv(label: str, value: str) -> str:
    """One «label : value» row of an info block: the label sits on the right
    (RTL start), the value fills the space to its left."""
    return (
        '<div style="display:grid; grid-template-columns:auto 1fr; gap:24px; '
        'align-items:baseline; padding:2px 0;">'
        f'<div style="font-size:14px; font-weight:700; color:{_INK}; '
        f'white-space:nowrap;">{label}&nbsp;:</div>'
        f'<div style="font-size:14px; font-weight:700; color:{_INK}; '
        f'text-align:right;">{value}</div>'
        "</div>"
    )


def _address_table(country: str, region: str, city: str, building: str, address: str) -> str:
    """The bordered 5-column address block. Columns read, right → left:
    الدولة، المنطقة، المدينة، رقم المبني، العنوان (العنوان is the widest, leftmost)."""
    th = (
        f"padding:9px 6px; border:1.5px solid {_BORDER}; font-size:14px; "
        "font-weight:800; text-align:center;"
    )
    td = (
        f"padding:9px 6px; border:1.5px solid {_BORDER}; font-size:12.5px; "
        "font-weight:700; text-align:center; vertical-align:middle;"
    )
    return f"""
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; margin:10px 0 4px;">
      <tr>
        <td style="{th} width:18%;">الدولة</td>
        <td style="{th} width:18%;">المنطقة</td>
        <td style="{th} width:16%;">المدينة</td>
        <td style="{th} width:22%;">رقم المبني</td>
        <td style="{th} width:26%;">العنوان</td>
      </tr>
      <tr>
        <td style="{td}">{country}</td>
        <td style="{td}">{region}</td>
        <td style="{td}">{city}</td>
        <td style="{td}">{building}</td>
        <td style="{td}">{address}</td>
      </tr>
    </table>"""


def _item_rows(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """The items table body. «المجموع» is each line's amount BEFORE VAT.

    ``show_unit`` gates the «الوحدة» column: when false its ``<td>`` is omitted
    (the header cell is dropped in step) and the fixed-layout table reclaims the
    freed 14%; the over-wide ``colspan`` on the empty row simply clamps.
    """
    td = (
        f"padding:10px 6px; border:1.5px solid {_BORDER}; font-size:13px; "
        "font-weight:700; text-align:center; vertical-align:middle;"
    )
    if not lines:
        return (
            f'<tr><td colspan="{6 if show_desc else 5}" style="{td} color:#888; padding:18px 6px;">'
            "لا توجد أصناف</td></tr>"
        )
    rows: list[str] = []
    for line in lines:
        name = html.escape(str(line.get("name") or ""))
        unit = html.escape(str(line.get("unit") or ""))
        unit_cell = f'<td style="{td}">{unit}</td>' if show_unit else ""
        # «الوصف» column (toggle «إظهار وصف الصنف»), right after the name.
        desc_cell = (
            f'<td style="{td} text-align:center; overflow-wrap:anywhere;">'
            f'{html.escape(line.get("print_description") or "")}</td>'
            if show_desc
            else ""
        )
        rows.append(
            "<tr>"
            f'<td style="{td} text-align:center; overflow-wrap:anywhere;">{name}</td>'
            f'{desc_cell}{unit_cell}'
            f'<td style="{td}">{_qty(line.get("qty"))}</td>'
            f'<td style="{td}">{_money(line.get("price"))}</td>'
            f'<td style="{td}">{_money(line.get("before"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def build_invoice_html_v9(data: dict[str, Any]) -> str:
    """Build the full printable «المتكاملة» invoice HTML from live data."""
    # «المتكاملة» always prints its own fixed logo (bundled asset), never the
    # selected company's stored logo — a deliberate, per-design brand mark.
    logo = _asset_data_uri("mutakamila_logo.png")
    qr = qr_vector_data_uri(data.get("qr_payload"))

    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        issue_date = issued.strftime("%d-%m-%Y")
    else:
        issue_date = html.escape(str(issued or ""))
    payment = html.escape(str(data.get("payment_label") or ""))

    seller_name = html.escape(str(seller.get("name") or ""))
    seller_vat = html.escape(str(seller.get("vat") or ""))
    seller_cr = html.escape(str(seller.get("cr") or ""))
    seller_addr = html.escape(str(seller.get("address") or ""))
    seller_postal = html.escape(str(seller.get("postal_code") or ""))
    salesperson = html.escape(str(data.get("salesperson") or seller.get("salesperson") or ""))

    customer_name = html.escape(str(customer.get("name") or ""))
    customer_vat = html.escape(str(customer.get("vat") or ""))
    customer_addr = html.escape(str(customer.get("address") or ""))
    customer_postal = html.escape(str(customer.get("postal_code") or ""))

    subtotal = _dec(totals.get("subtotal"))
    discount = _dec(totals.get("discount"))
    vat_total = _dec(totals.get("vat"))
    grand_total = _dec(totals.get("total"))

    logo_html = (
        f'<img src="{logo}" alt="logo" style="height:74px; object-fit:contain; '
        f'display:inline-block;">'
        if logo
        else ""
    )
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        f'object-fit:contain; display:inline-block; background:#ffffff;">'
        if qr
        else ""
    )

    th = (
        f"padding:11px 6px; border:1.5px solid {_BORDER}; font-size:14px; "
        "font-weight:800; text-align:center;"
    )
    tv = (
        f"padding:11px 6px; border:1.5px solid {_BORDER}; font-size:14px; "
        "font-weight:800; text-align:center;"
    )

    # «الوحدة» column is optional (default on when the flag is absent). When off,
    # the header cell drops in lock-step with the body cell (_item_rows) and the
    # fixed-layout table reclaims the freed 14%.
    show_unit = bool(data.get("show_unit", True))
    unit_th = f'<td style="{th} width:14%;">الوحدة</td>' if show_unit else ""
    show_desc = bool(data.get("show_description"))
    desc_th = f'<td style="{th} width:22%;">الوصف</td>' if show_desc else ""
    name_w = " width:21%;" if show_desc else ""

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
            background:#ffffff; padding:{_PAD_Y}px {_PAD_X}px; color:{_INK}; direction:rtl;
            font-family:{_FONTS}; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ page-break-inside:auto; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
</style>
</head>
<body>
  <div class="sheet">

    <!-- ===== HEADER: logo + title (centred) ===== -->
    <div style="text-align:center;">
      {logo_html}
      <div style="font-size:16px; font-weight:800; color:{_INK}; margin-top:10px;">فاتورة مبيعات ضريبية</div>
    </div>

    <!-- ===== SELLER INFO (right column) ===== -->
    <div style="width:56%; margin-right:0; margin-left:auto; margin-top:20px;">
      {_kv("رقم الفاتورة", invoice_number)}
      {_kv("تاريخ الفاتورة", issue_date)}
      {_kv("اسم الشركة", seller_name)}
      {_kv("اسم المندوب", salesperson)}
      {_kv("الرقم الضريبي", seller_vat)}
      {_kv("السجل التجاري", seller_cr)}
      {_kv("الرقم البريدي", seller_postal)}
    </div>

    {_address_table(_COUNTRY, "", "", "", seller_addr)}

    <!-- ===== CUSTOMER INFO ===== -->
    <div style="width:56%; margin-right:0; margin-left:auto; margin-top:12px;">
      {_kv("اسم العميل", customer_name)}
      {_kv("الرقم الضريبي", customer_vat)}
      {_kv("الرقم البريدي", customer_postal)}
    </div>

    {_address_table(_COUNTRY, "", "", "", customer_addr)}

    <!-- ===== ITEMS TABLE ===== -->
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; margin-top:14px;">
      <thead>
        <tr>
          <td style="{th}{name_w}">اسم الصنف</td>{desc_th}
          {unit_th}
          <td style="{th} width:13%;">الكمية</td>
          <td style="{th} width:15%;">السعر</td>
          <td style="{th} width:15%;">المجموع</td>
        </tr>
      </thead>
      <tbody>
        {_item_rows(lines, show_unit, show_desc)}
      </tbody>
    </table>

    <!-- ===== TOTALS TABLE ===== -->
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; margin-top:16px;">
      <tr>
        <td style="{th}">نوع السداد</td>
        <td style="{th}">الاجمالي قبل . ض</td>
        <td style="{th}">الخصم</td>
        <td style="{th}">الضريبة</td>
        <td style="{th}">الاجمالي بعد . ض</td>
      </tr>
      <tr>
        <td style="{tv}">{payment}</td>
        <td style="{tv}">{_money(subtotal)}</td>
        <td style="{tv}">{_money(discount)}</td>
        <td style="{tv}">{_money(vat_total)}</td>
        <td style="{tv}">{_money(grand_total)}</td>
      </tr>
    </table>

    <!-- ===== QR ===== -->
    <div style="text-align:center; margin-top:18px;">
      {qr_html}
      <div style="font-size:13px; font-weight:700; color:{_INK}; margin-top:6px;">رمز الاستجابة السريعة</div>
    </div>

  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v9"]
