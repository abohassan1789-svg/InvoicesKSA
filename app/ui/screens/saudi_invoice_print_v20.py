"""«قصر نصار» — a layout replica of the scanned invoice the user supplied
(``تصامبم جديدة\\WhatsApp Image 2026-10-05 at 5.51.33 PM.jpeg``, invoice #202 of
«شركة قصر نصار للصناعة» to «مصنع روائع الدار للحجر والرخام والجرانيت»).

Same idea as «دروب الاتحاد» / «موضي عقيل» (user 2026-10-06): places, look and
design are copied; the logo, the seller («من») and the buyer («فاتورة إلى») come
live from the shared ``data`` dict. The source is a 1021×1515 phone scan of an A4
page, so the geometry was measured off the image (×0.82 → the 816-px Letter sheet).

Design:
* Top: «فاتورة» + the QR on the LEFT, the company logo on the right («Zoom»:
  scaled to fit, never stretched); under the logo, right-aligned, the bold
  «رقم الفاتورة 202#» and the two stacked dates (تاريخ الفاتورة / تاريخ الإستحقاق —
  both the issue date, the system keeps no separate due date).
* «فاتورة إلى:» (buyer: bold name · address · «الرقم الضريبي: …» · «سجل تجارى/ رقم
  موحد: …») on the right, «من:» (seller: bold name · CR label over CR · VAT label
  over VAT · address) in the middle-left, like the scan.
* Borderless items table, 5 columns (البند · الوصف · الكمية · سعر الوحدة ·
  المجموع), bold titles over one dark rule. «البند» = item name, «الوصف» = the
  line's «وصف الصنف» (``item_description``); «المجموع» = the line total before VAT
  (1,380 × 180.00 = 248,400 in the scan).
* «ملخص الفاتورة» totals on the left under a thin rule: المجموع · القيمة المضافة
  (15%) · الإجمالي (bold) · مدفوع · الرصيد المستحق, riyal sign left of each figure.
  Cash → مدفوع = total, due 0.00; otherwise مدفوع 0.00, due = total.
* Figures Daftra-style like the scan: whole amounts «248,400», fractions 2dp,
  zero «0.00»; unit price always 2dp («180.00»); quantity grouped («1,380»).
* Company stamp (when «إظهار الختم» is ticked) to the right of the totals, lower
  down, where the scan has it.
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
    company_logo_data_uri,
    company_stamp_data_uri,
    qr_vector_data_uri,
)

# ---------------------------------------------------------------------------
# Design tokens — sampled from the scan.
# ---------------------------------------------------------------------------
_INK = "#1c1c1c"            # all text
_HEAD_RULE = "#2a2a2a"      # rule under the items titles
_SUM_RULE = "#6e6e6e"       # rule under «ملخص الفاتورة»
_FONTS = "'Noto Sans Arabic','Noto Sans','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_LEFT = 51                  # the scan's margins (62 / 114 image px × 0.82)
_RIGHT = 93
_CONTENT_W = _SHEET_W - _LEFT - _RIGHT   # 672
_TOP = 66
_BOTTOM = 36

_RIYAL_ASSET = "riyal_symbol.png"

# Items table, physical right → left (RTL): (title, width px, align).
_ITEM_COLS = (
    ("البند", 203, "right"),
    ("الوصف", 195, "right"),
    ("الكمية", 93, "right"),
    ("سعر الوحدة", 85, "right"),
    ("المجموع", 96, "left"),
)


def _columns(show_description: bool) -> tuple:
    """The item columns to print. With «إظهار وصف الصنف» unticked the «الوصف»
    column is dropped and its width goes to «البند» (user 2026-10-06)."""
    if show_description:
        return _ITEM_COLS
    item, desc, *rest = _ITEM_COLS
    width_at = 2 if len(item) == 3 and isinstance(item[2], int) else 1
    merged = list(item)
    merged[width_at] = item[width_at] + desc[width_at]
    return (tuple(merged), *rest)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _num(value: Any) -> str:
    """Scan-style figure: «248,400», «7,500.50», zero → «0.00»."""
    d = _dec(value)
    if d == 0:
        return "0.00"
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d:,.2f}"


def _money(value: Any) -> str:
    return f"{_dec(value):,.2f}"


def _qty(value: Any) -> str:
    text = format(_dec(value).normalize(), ",f")
    return text if text not in ("", "-0") else "0"


def _rate(value: Any) -> str:
    return f"{_dec(value).normalize():f}%"


def _fmt_date(issued: Any) -> str:
    """``18/01/2026`` — day/month/year, zero-padded, like the scan."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return issued.strftime("%d/%m/%Y")
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _item_row(line: dict[str, Any], show_description: bool = True) -> str:
    # «البند» = the item name; «الوصف» = the line's own «وصف الصنف» (item_description).
    cells = (
        html.escape(str(line.get("name") or "")),
        html.escape(str(line.get("description") or "")),
        _qty(line.get("qty")),
        _money(line.get("price")),
        _num(line.get("before")),
    )
    if not show_description:
        cells = cells[:1] + cells[2:]
    return "<tr>" + "".join(
        f'<td style="text-align:{align};">{value}</td>'
        for value, (_t, _w, align) in zip(cells, _columns(show_description))
    ) + "</tr>"


def _total_row(label: str, value_html: str, bold: bool = False) -> str:
    weight = ' style="font-weight:700;"' if bold else ""
    return (
        f"<tr{weight}>"
        f'<td class="t-lab">{label}</td>'
        f'<td class="t-val"><span dir="ltr">{value_html}</span></td>'
        "</tr>"
    )


def build_invoice_html_v20(data: dict[str, Any]) -> str:
    """Build «قصر نصار» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = data.get("lines") or []
    show_desc = bool(data.get("show_description"))
    cols = _columns(show_desc)

    esc = lambda v: html.escape(str(v or ""))  # noqa: E731
    # Addresses keep the line breaks typed in the master record (the scan's
    # addresses are stacked lines).
    esc_lines = lambda v: "<br>".join(html.escape(p.strip()) for p in str(v or "").splitlines() if p.strip())  # noqa: E731
    invoice_number = esc(data.get("invoice_number"))
    issued = esc(_fmt_date(data.get("issue_datetime")))
    credit = _is_credit(str(data.get("payment_label") or ""))

    subtotal = _dec(totals.get("subtotal", totals.get("taxable", 0)))
    discount = _dec(totals.get("discount", 0))
    vat_total = _dec(totals.get("vat", 0))
    grand_total = _dec(totals.get("total", 0))
    paid = Decimal("0") if credit else grand_total
    due = grand_total - paid

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:154px; height:76px; object-fit:contain; display:block;">'
        if logo
        else ""
    )
    qr = qr_vector_data_uri(data.get("qr_payload"))
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'display:block; background:#ffffff;">'
        if qr
        else ""
    )
    riyal = _asset_data_uri(_RIYAL_ASSET)
    sign = (
        f'<img src="{riyal}" alt="SAR" style="height:12px; width:auto; vertical-align:-1px;">'
        if riyal
        else "SAR"
    )

    def amount(value: Any) -> str:
        return f"{sign} {_num(value)}"

    # Buyer: name · address · VAT · CR (CR line only when the customer has one).
    cust_lines = []
    if customer.get("address"):
        cust_lines.append(f'<div>{esc_lines(customer.get("address"))}</div>')
    if customer.get("vat"):
        cust_lines.append(f'<div>الرقم الضريبي: {esc(customer.get("vat"))}</div>')
    if customer.get("cr"):
        cust_lines.append(f'<div>سجل تجارى/ رقم موحد: {esc(customer.get("cr"))}</div>')

    # Seller: CR label over CR · VAT label over VAT · address.
    seller_lines = []
    if seller.get("cr"):
        seller_lines.append(f'<div>سجل تجارى/ رقم موحد</div><div>{esc(seller.get("cr"))}</div>')
    if seller.get("vat"):
        seller_lines.append(f'<div>الرقم الضريبي</div><div>{esc(seller.get("vat"))}</div>')
    if seller.get("address"):
        seller_lines.append(f'<div>{esc_lines(seller.get("address"))}</div>')

    total_rows = [_total_row("المجموع", amount(subtotal))]
    if discount:
        total_rows.append(_total_row("الخصم", amount(-discount)))
    total_rows += [
        _total_row(f'القيمة المضافة <bdi dir="ltr">({vat_rate}%)</bdi>', amount(vat_total)),
        _total_row("الإجمالي", amount(grand_total), bold=True),
        _total_row("مدفوع", amount(paid)),
        _total_row("الرصيد المستحق", amount(due)),
    ]

    # Stamp to the right of the totals, lower down — only when «إظهار الختم» is ticked.
    stamp_html = ""
    if data.get("show_stamp"):
        stamp = company_stamp_data_uri(seller)
        if stamp:
            stamp_html = (
                f'<div data-company-stamp="1" style="margin:84px 0 0 0; padding-right:20px;">'
                f'<img src="{stamp}" alt="stamp" style="width:240px; height:180px; object-fit:contain; '
                f'filter:{_STAMP_FILTER};"></div>'
            )

    head_html = "".join(
        f'<th style="text-align:{align};">{title}</th>' for title, _w, align in cols
    )
    colgroup = "".join(f'<col style="width:{w}px">' for _t, w, _a in cols)

    # The closing block (last item + totals + stamp) is one no-break <tbody>, so the
    # totals always travel to a new page together with at least one item.
    if lines:
        main_rows = "".join(_item_row(ln, show_desc) for ln in lines[:-1])
        last_row = _item_row(lines[-1], show_desc)
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;700&family=Noto+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK}; font-size:13.5px; font-weight:500;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ box-sizing:border-box; width:{_SHEET_W}px; min-height:{_SHEET_H}px; margin:24px auto;
            background:#ffffff; padding:0 {_RIGHT}px 0 {_LEFT}px; direction:rtl;
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  td, th {{ box-sizing:border-box; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  tfoot {{ display:table-footer-group; }}
  .page {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .page > * > tr > td {{ padding:0; vertical-align:top; }}
  .summary {{ break-inside:avoid; page-break-inside:avoid; }}
  .meta {{ line-height:21px; font-size:13.5px; }}
  .party {{ text-align:right; line-height:20.5px; overflow-wrap:anywhere; word-break:break-word; }}
  .party .cap {{ font-size:13px; line-height:20px; margin-bottom:6px; }}
  .party .nm {{ font-weight:700; font-size:17px; line-height:24px; margin-bottom:6px; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .items > thead > tr > th {{ font-weight:700; font-size:14.5px; line-height:20px; vertical-align:bottom;
              padding:0 4px 5px 4px; white-space:nowrap; border-bottom:1.5px solid {_HEAD_RULE}; }}
  .items > tbody > tr > td {{ vertical-align:top; padding:9px 4px 7px 4px; line-height:19px;
              overflow-wrap:anywhere; word-break:break-word; }}
  .items > tbody > tr > td:last-child {{ white-space:nowrap; }}
  .sumhead {{ width:293px; font-weight:700; font-size:14.5px; line-height:20px; text-align:right;
              padding:0 0 6px 0; border-bottom:1px solid {_SUM_RULE}; }}
  .tot {{ width:293px; table-layout:fixed; margin-top:4px; }}
  .tot td {{ height:33px; vertical-align:middle; padding:0; line-height:18px; }}
  .tot .t-lab {{ text-align:right; }}
  .tot .t-val {{ width:110px; text-align:right; padding-right:18px; white-space:nowrap; }}
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

    <!-- ===== TOP: «فاتورة» + QR (left) · logo, number, dates (right) ===== -->
    <div style="position:relative; height:330px;">
      <div style="position:absolute; left:0; top:0; text-align:left;">
        <div style="font-size:20px; line-height:26px; text-align:left;">فاتورة</div>
        <div style="margin-top:8px;">{qr_html}</div>
      </div>
      <div style="position:absolute; right:32px; top:8px; width:154px; height:76px;">{logo_html}</div>
      <div style="position:absolute; right:0; top:150px; text-align:right;">
        <div style="font-weight:700; font-size:23px; line-height:30px;">رقم الفاتورة <bdi dir="ltr">{invoice_number}#</bdi></div>
        <div class="meta" style="margin-top:30px;">تاريخ الفاتورة</div>
        <div class="meta"><bdi dir="ltr">{issued}</bdi></div>
        <div class="meta" style="margin-top:27px;">تاريخ الإستحقاق</div>
        <div class="meta"><bdi dir="ltr">{issued}</bdi></div>
      </div>
    </div>

    <!-- ===== «فاتورة إلى» (right) · «من» (left) ===== -->
    <div style="display:flex; align-items:flex-start; margin-top:18px;">
      <div class="party" style="width:380px;">
        <div class="cap">فاتورة إلى:</div>
        <div class="nm">{esc(customer.get("name"))}</div>
        {"".join(cust_lines)}
      </div>
      <div style="width:22px;"></div>
      <div class="party" style="width:270px;">
        <div class="cap">من:</div>
        <div class="nm">{esc(seller.get("name"))}</div>
        {"".join(seller_lines)}
      </div>
    </div>

    <!-- ===== ITEMS + CLOSING BLOCK ===== -->
    <table class="items" style="margin-top:44px;">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head_html}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(cols)}" style="padding:0;">
          <div style="display:flex; flex-direction:row-reverse; justify-content:space-between; align-items:flex-start; margin-top:40px;">
            <div style="width:293px;">
              <div class="sumhead">ملخص الفاتورة</div>
              <table class="tot"><colgroup><col><col style="width:110px"></colgroup>{"".join(total_rows)}</table>
            </div>
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


__all__ = ["build_invoice_html_v20"]
