"""«الامل الناجح» — a layout replica of the scanned tax invoice the user supplied
(``تصامبم جديدة\\WhatsApp Image 2026-10-05 at 5.51.34 PM.jpeg``, INV169 of «مؤسسة
الامل الناجح للتجارة والمقاولات», an Odoo-style ZATCA invoice).

Same idea as the other layout replicas (user 2026-10-06): places, look and design
are copied; the seller block, the customer block and the stamp come live from the
shared ``data`` dict. The 483×605 phone scan is cropped tight to the paper, so the
measured positions are mapped into a 24-px side margin on the 816-px Letter sheet.

Design:
* Header: seller top-right — name (bold) · address · VAT number (no label, as
  the scan) · «رقم ٧٠٠: <CR>» (bold label); the QR top-left; a full-width grey
  rule. (The scan has no logo, so none is printed.)
* «فاتورة ضريبية» centred; the customer right under a grey «بيانات العميل :» band
  (name · «الرقم الضريبي :» · «رقم السجل :»); the invoice meta left as a two-column
  label/value list (رقم الفاتورة · تاريخ الإصدار · تاريخ الاستحقاق · المبلغ المستحق —
  our invoices carry one date, so both dates print it; the amount due is 0.00 for
  cash and the total for a credit/آجل invoice).
* «التفاصيل», then a 9-column BORDERLESS items table (# · البيان · سعر الوحدة ·
  الكمية · الخصم · الاجمالي قبل الضريبة · % الضريبة · قيمة الضريبة · الإجمالي شامل
  الضريبة), centred figures with the riyal sign; the discount cell is the
  source's «0.0% / ⃁ 0.00» (our discount is invoice-level, never per line).
* Totals bottom-left with a grey rule under each row, a full-width rule beneath,
  and the company stamp (when «إظهار الختم» is ticked) to the right of the totals.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _STAMP_FILTER,
    _asset_data_uri,
    company_stamp_data_uri,
    qr_vector_data_uri,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — sampled from the scan.
# ---------------------------------------------------------------------------
_INK = "#1c1c1e"
_RULE = "#aaabb0"            # header rule, totals rules, closing rule
_BAND = "#e5e6eb"            # «بيانات العميل :» band
_FONTS = "'Almarai','Tajawal','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_SIDE = 24
_CONTENT_W = _SHEET_W - 2 * _SIDE    # 768
_TOP = 8
_BOTTOM = 36

_RIYAL_ASSET = "riyal_symbol.png"

# Items table, physical right → left (RTL): (title html, width px, small title?).
_ITEM_COLS = (
    ("#", 25, False),
    ("البيان", 185, False),
    ("سعر الوحدة", 97, False),
    ("الكمية", 80, False),
    ("الخصم", 76, False),
    ("الاجمالي<br>قبل الضريبة", 77, False),
    ('<span dir="ltr">%</span> الضريبة', 74, False),
    ("قيمة الضريبة", 77, False),
    ("الإجمالي شامل<br>الضريبة", 77, True),
)
# With «إظهار وصف الصنف»: «الوصف» right after «البيان»; still 768px in all.
_ITEM_COLS_DESC = (
    ("#", 25, False),
    ("البيان", 100, False),
    ("الوصف", 127, False),
    ("سعر الوحدة", 80, False),
    ("الكمية", 65, False),
    ("الخصم", 66, False),
) + _ITEM_COLS[5:]


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any) -> str:
    return f"{_dec(value):,.2f}"


def _plain(value: Any) -> str:
    d = _dec(value).normalize()
    text = format(d, "f")
    return text if text not in ("", "-0") else "0"


def _fmt_date(issued: Any) -> str:
    """``2025-11-13`` — ISO date, like the scan."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return issued.strftime("%Y-%m-%d")
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def build_invoice_html_v19(data: dict[str, Any]) -> str:
    """Build «الامل الناجح» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)

    esc = lambda v: html.escape(str(v or ""))  # noqa: E731
    invoice_number = esc(data.get("invoice_number"))
    issued = esc(_fmt_date(data.get("issue_datetime")))
    credit = _is_credit(str(data.get("payment_label") or ""))

    subtotal = _dec(totals.get("subtotal", totals.get("taxable", 0)))
    discount = _dec(totals.get("discount", 0))
    taxable = _dec(totals.get("taxable", subtotal - discount))
    vat_total = totals.get("vat", 0)
    grand_total = _dec(totals.get("total", 0))
    due = grand_total if credit else Decimal("0")

    riyal = _asset_data_uri(_RIYAL_ASSET)
    sign = (
        f'<img src="{riyal}" alt="SAR" style="height:11px; width:auto; vertical-align:-1px;">'
        if riyal
        else "SAR"
    )

    def sar(amount: Any) -> str:
        """«⃁ 6,000.00» — the riyal sign to the LEFT of the figure, as the scan."""
        return f'<span dir="ltr" style="white-space:normal;">{sign} {_money(amount)}</span>'

    qr = qr_vector_data_uri(data.get("qr_payload"))
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'display:block; background:#ffffff;">'
        if qr
        else ""
    )

    cr = esc(seller.get("cr"))
    seller_html = (
        f'<div style="font-weight:800; font-size:15px; line-height:22px;">{esc(seller.get("name"))}</div>'
        f'<div style="font-size:12.5px; line-height:19px; margin-top:4px;">{esc(seller.get("address"))}</div>'
        f'<div style="font-size:12.5px; line-height:19px; margin-top:24px;">{esc(seller.get("vat"))}</div>'
        + (f'<div style="font-size:12.5px; line-height:19px; margin-top:27px;"><b>رقم ٧٠٠:</b> {cr}</div>' if cr else "")
    )

    meta = (
        ("رقم الفاتورة:", invoice_number),
        ("تاريخ الإصدار:", issued),
        ("تاريخ الاستحقاق:", issued),
        ("المبلغ المستحق:", sar(due)),
    )
    meta_labels = "".join(f"<div>{label}</div>" for label, _v in meta)
    meta_values = "".join(f'<div dir="ltr">{value}</div>' for _l, value in meta)

    show_desc = bool(data.get("show_description"))
    cols = _ITEM_COLS_DESC if show_desc else _ITEM_COLS
    head_html = "".join(
        f'<th class="sm">{title}</th>' if small else f"<th>{title}</th>"
        for title, _w, small in cols
    )
    colgroup = "".join(f'<col style="width:{w}px">' for _t, w, _s in cols)

    def item_row(index: int, line: dict[str, Any]) -> str:
        rate = _plain(line.get("vat_rate"))
        # No grid lines here, so a right gutter keeps it from running into the name.
        desc_td = (
            f'<td class="nm" style="padding-right:10px;">{esc(line.get("print_description"))}</td>'
            if show_desc
            else ""
        )
        return (
            "<tr>"
            f"<td>{index}</td>"
            f'<td class="nm">{esc(line.get("name"))}</td>'
            f"{desc_td}"
            f"<td>{_money(line.get('price'))}</td>"
            f"<td>{_plain(line.get('qty'))}</td>"
            f'<td><div dir="ltr">0.0%</div>{sar(0)}</td>'
            f"<td>{sar(line.get('before'))}</td>"
            f'<td><span dir="ltr">% {rate}</span></td>'
            f"<td>{sar(line.get('vat_amount'))}</td>"
            f"<td>{sar(line.get('total'))}</td>"
            "</tr>"
        )

    total_rows = [("الإجمالي قبل الضريبة", subtotal, 32, False)]
    if discount:
        total_rows.append(("الخصم", -discount, 32, False))
    total_rows += [
        ("ضريبة القيمة المضافة", vat_total, 38, False),
        ("الإجمالي شامل ضريبة القيمة المضافة", grand_total, 44, True),
    ]
    totals_html = "".join(
        f'<tr style="height:{h}px;"><td class="t-val{" grand" if grand else ""}">{sar(amount)}</td>'
        f'<td class="t-lab" dir="rtl">{label}</td></tr>'
        for label, amount, h, grand in total_rows
    )

    stamp_html = ""
    if data.get("show_stamp"):
        stamp = company_stamp_data_uri(seller)
        if stamp:
            stamp_html = (
                f'<div data-company-stamp="1" style="position:absolute; left:485px; top:30px; '
                f'width:164px; height:164px;"><img src="{stamp}" alt="stamp" '
                f'style="width:164px; height:164px; object-fit:contain; filter:{_STAMP_FILTER};"></div>'
            )

    # The closing block (last item + totals) is one no-break <tbody>, so the totals
    # always travel to a new page together with at least one item.
    if lines:
        main_rows = "".join(item_row(i, ln) for i, ln in enumerate(lines[:-1], 1))
        last_row = item_row(len(lines), lines[-1])
    else:
        main_rows = ""
        last_row = f'<tr><td colspan="{len(cols)}" style="color:#999;">لا توجد أصناف</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Almarai:wght@400;700;800&family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK}; font-size:13px;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ box-sizing:border-box; width:{_SHEET_W}px; min-height:{_SHEET_H}px; margin:24px auto;
            background:#ffffff; padding:0 {_SIDE}px; direction:rtl;
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  td, th {{ box-sizing:border-box; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  tfoot {{ display:table-footer-group; }}
  .page {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .page > * > tr > td {{ padding:0; vertical-align:top; }}
  .summary {{ break-inside:avoid; page-break-inside:avoid; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:8px; }}
  .items > thead > tr > th {{ font-weight:700; font-size:12px; line-height:15px; text-align:center;
              vertical-align:bottom; padding:0 2px 8px; }}
  .items > thead > tr > th.sm {{ font-size:9.5px; line-height:12px; }}
  .items > tbody > tr > td {{ height:36px; padding:2px 2px; text-align:center; vertical-align:middle;
              line-height:16px; overflow-wrap:anywhere; word-break:break-word; }}
  .items > tbody > tr > td.nm {{ text-align:right; padding-right:2px; }}
  .tot {{ width:419px; table-layout:fixed; direction:ltr; margin-top:14px; }}
  .tot td {{ border-bottom:1px solid {_RULE}; vertical-align:middle; }}
  .tot .t-val {{ width:196px; text-align:right; }}
  .tot .t-val.grand {{ font-weight:800; font-size:14px; }}
  .tot .t-lab {{ text-align:right; padding-right:5px; font-weight:700; line-height:16px; }}
  @page {{ size:Letter; margin:0; }}
  @media print {{
    body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
</style>
</head>
<body>
  <div class="sheet">
  <table class="page">
    <thead><tr><td style="height:{_TOP}px;"></td></tr></thead>
    <tfoot><tr><td style="height:{_BOTTOM}px;"></td></tr></tfoot>
    <tbody><tr><td>

    <!-- ===== HEADER: seller (right) · QR (left) · rule ===== -->
    <div style="position:relative; height:204px;" dir="ltr">
      <div dir="rtl" style="position:absolute; right:25px; top:16px; width:380px; text-align:right;
                  overflow-wrap:anywhere; word-break:break-word;">{seller_html}</div>
      <div style="position:absolute; left:125px; top:0;">{qr_html}</div>
    </div>
    <div style="height:1px; background:{_RULE};"></div>

    <!-- ===== TITLE · CUSTOMER (right) · META (left) · «التفاصيل» ===== -->
    <div style="position:relative; height:192px;" dir="ltr">
      <div style="position:absolute; left:0; right:0; top:15px; text-align:center; font-weight:700; font-size:15px;">فاتورة ضريبية</div>
      <div dir="rtl" style="position:absolute; right:0; top:49px; width:368px; height:25px; background:{_BAND};
                  font-weight:700; line-height:25px; text-align:right; padding-right:14px; box-sizing:border-box;">بيانات العميل :</div>
      <div dir="rtl" style="position:absolute; right:28px; top:84px; width:340px; text-align:right; line-height:26.5px;
                  overflow-wrap:anywhere; word-break:break-word;">
        <div>{esc(customer.get("name"))}</div>
        <div>الرقم الضريبي : {esc(customer.get("vat"))}</div>
        <div>رقم السجل : {esc(customer.get("cr"))}</div>
      </div>
      <div dir="rtl" style="position:absolute; right:377px; top:52px; width:170px; text-align:right;
                  font-weight:700; line-height:25.5px;">{meta_labels}</div>
      <div style="position:absolute; right:572px; top:52px; width:190px; text-align:right;
                  line-height:25.5px;">{meta_values}</div>
      <div dir="rtl" style="position:absolute; right:541px; top:166px; text-align:right; font-weight:700; font-size:14px;">التفاصيل</div>
    </div>

    <!-- ===== ITEMS (borderless) + CLOSING BLOCK ===== -->
    <table class="items">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head_html}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(cols)}" style="height:auto; padding:0;">
          <div dir="ltr" style="position:relative; text-align:left; min-height:{200 if stamp_html else 0}px;">
            <table class="tot"><colgroup><col style="width:196px"><col></colgroup>{totals_html}</table>
            <div style="height:1px; background:{_RULE}; margin-top:18px;"></div>
            {stamp_html}
          </div>
        </td></tr>
      </tbody>
    </table>

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v19"]
