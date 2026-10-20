"""«موضي عقيل» — a layout replica of the scanned tax invoice the user supplied
(``تصامبم جديدة\\WhatsApp Image 2026-10-05 at 5.51.36 PM.jpeg``, INV-0423 of «مؤسسة
موضي عقيل العتيبي للمقاولات», a Zoho-style invoice).

Same idea as «دروب الاتحاد» / «إنتار الغربيا» (user 2026-10-06): places, look and
design are copied; the logo, the seller (FROM) and the buyer (TO) come live from
the shared ``data`` dict. The source is a 485×680 phone scan of an A4 page, so the
geometry was measured off the image (×816/485 → the 816-px Letter sheet).

Design:
* Top band: «فاتورة ضريبية / TAX INVOICE» + four meta lines (number · date ·
  «حالة الدفع - Payment Status» · Paid/Unpaid) on the LEFT, the QR in the middle,
  the company logo on the right («Zoom»: scaled to fit, never stretched).
* «من - FROM» (right column: seller name, VAT, address) and «الى - TO» (buyer
  name, VAT — the source prints no buyer address), grey captions over dark values.
  Our shared QR is larger than the scan's, so this band starts lower to clear it.
* Items grid, 7 columns, light ``#f3f4f8`` header band, grey hairlines, every cell
  right-aligned and top-aligned like the source; the column titles break exactly
  where the source breaks them. «البند» = the item name, «الوصف» = the line's
  «وصف الصنف» (``sales_invoice_lines.item_description``, typed per line on the
  invoice screen; blank when none).
* Totals list bottom-left: value right-aligned in a narrow column, the bilingual
  label left-aligned beside it, a rule under each row: Pre-Tax Total · VAT (rate%)
  · Total (riyal sign) · Due (riyal sign). Cash invoices print «Paid - مدفوعة» and a
  0.00 due; anything else «Unpaid - غير مدفوعة» with the total due.
* The company stamp (when «إظهار الختم» is ticked) sits under the totals on the
  left, where the scan has it — outside the no-break closing block, so it never
  drags the totals onto a new page by itself.
* Letter is ~90px shorter than the scan's A4 and the shared QR is larger than the
  scan's, so the vertical rhythm is ~8% tighter than a straight width-scale.
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
_INK = "#141414"            # titles, names, values
_META = "#2c2c2e"           # the four meta lines
_CAPTION = "#8a8a8a"        # «من - FROM :» style captions
_GRID = "#9a9a9a"           # items-table hairlines
_RULE = "#686868"           # rules under the totals rows
_HEAD_BG = "#f3f4f8"        # items header band
_FONTS = "'Noto Kufi Arabic','Noto Sans','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_LEFT = 56                  # the scan's margins (33 / 48 image px)
_RIGHT = 80
_CONTENT_W = _SHEET_W - _LEFT - _RIGHT   # 680
_TOP = 36
_BOTTOM = 36

_RIYAL_ASSET = "riyal_symbol.png"

# Items grid, physical right → left (RTL): (arabic, english, width px). Title
# breaks are pinned with <br> exactly where the scan breaks them.
_ITEM_COLS = (
    ("البند", "Item", 93),
    ("الوصف", "Description", 115),
    ("السعر", "Price", 85),
    ("الكمية", "Quantity", 84),
    ("المجموع<br>بدون<br>الضريبة", "Pre-Tax<br>Total", 101),
    ("نسبة<br>الضريبة", "Tax<br>Percentage", 105),
    ("المجموع", "Total", 97),
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


def _money(value: Any) -> str:
    return f"{_dec(value):,.2f}"


def _plain(value: Any) -> str:
    d = _dec(value).normalize()
    text = format(d, "f")
    return text if text not in ("", "-0") else "0"


def _rate(value: Any) -> str:
    return f"{_dec(value).normalize():f}%"


def _fmt_date(issued: Any) -> str:
    """``2025/10/4`` — year/month/day without zero padding, like the scan."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return f"{issued.year}/{issued.month}/{issued.day}"
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _caption(text: str) -> str:
    return f'<div class="cap">{text}</div>'


def _item_row(index: int, line: dict[str, Any], show_description: bool = True) -> str:
    # «البند / Item» = the item name; «الوصف / Description» = the line's own
    # «وصف الصنف» (item_description), typed on the invoice screen (user 2026-10-06).
    name = html.escape(str(line.get("name") or ""))
    description = html.escape(str(line.get("description") or ""))
    description_cell = f"<td>{description}</td>" if show_description else ""
    return (
        "<tr>"
        f"<td>{name}</td>"
        f"{description_cell}"
        f"<td>{_money(line.get('price'))}</td>"
        f"<td>{_plain(line.get('qty'))}</td>"
        f"<td>{_money(line.get('before'))}</td>"
        f"<td>{_rate(line.get('vat_rate'))}</td>"
        f"<td>{_money(line.get('total'))}</td>"
        "</tr>"
    )


def _total_row(label_html: str, amount: Any, height: int) -> str:
    return (
        f'<tr style="height:{height}px;">'
        f'<td class="t-val">{_money(amount)}</td>'
        f'<td class="t-lab">{label_html}</td>'
        "</tr>"
    )


def build_invoice_html_v17(data: dict[str, Any]) -> str:
    """Build «موضي عقيل» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = data.get("lines") or []
    show_desc = bool(data.get("show_description"))
    cols = _columns(show_desc)

    esc = lambda v: html.escape(str(v or ""))  # noqa: E731
    invoice_number = esc(data.get("invoice_number"))
    issued = esc(_fmt_date(data.get("issue_datetime")))
    credit = _is_credit(str(data.get("payment_label") or ""))
    status = "Unpaid - غير مدفوعة" if credit else "Paid - مدفوعة"

    subtotal = _dec(totals.get("subtotal", totals.get("taxable", 0)))
    discount = _dec(totals.get("discount", 0))
    taxable = _dec(totals.get("taxable", subtotal - discount))
    vat_total = totals.get("vat", 0)
    grand_total = _dec(totals.get("total", 0))
    due = grand_total if credit else Decimal("0")

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:143px; height:91px; object-fit:contain; display:block;">'
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

    # Stamp under the totals, on the left — only when «إظهار الختم» is ticked.
    stamp_html = ""
    if data.get("show_stamp"):
        stamp = company_stamp_data_uri(seller)
        if stamp:
            stamp_html = (
                f'<div data-company-stamp="1" dir="ltr" style="margin:10px 0 0 0; padding-left:15px; text-align:left; '
                f'break-inside:avoid; page-break-inside:avoid;">'
                f'<img src="{stamp}" alt="stamp" style="width:160px; height:135px; object-fit:contain; '
                f'filter:{_STAMP_FILTER};"></div>'
            )

    head_html = "".join(
        f'<th><div>{ar}</div><div>{en}</div></th>' for ar, en, _w in cols
    )
    colgroup = "".join(f'<col style="width:{w}px">' for _a, _e, w in cols)

    total_rows = [_total_row('<div dir="rtl">الإجمالي قبل الضريبة</div><div>Pre-Tax Total</div>',
                             taxable if discount else subtotal, 38)]
    if discount:
        total_rows.insert(0, _total_row('<div dir="rtl">الخصم</div><div>Discount</div>', -discount, 38))
    total_rows += [
        _total_row(f'<div dir="rtl">القيمة المضافة <span dir="ltr">%{vat_rate}</span></div>', vat_total, 30),
        _total_row(f'<div dir="rtl">الإجمالي ({sign})</div><div>Total (SAR)</div>', grand_total, 42),
        _total_row(f'<div dir="rtl">المستحق ({sign})</div><div>Due (SAR)</div>', due, 42),
    ]

    # The closing block (last item + totals + stamp) is one no-break <tbody>, so the
    # totals always travel to a new page together with at least one item.
    if lines:
        main_rows = "".join(_item_row(i, ln, show_desc) for i, ln in enumerate(lines[:-1], 1))
        last_row = _item_row(len(lines), lines[-1], show_desc)
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Kufi+Arabic:wght@400;500;600;700&family=Noto+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK}; font-size:13.5px;
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
  .meta {{ color:{_META}; font-weight:600; font-size:13.5px; line-height:17.7px; }}
  .cap {{ color:{_CAPTION}; font-size:12.5px; line-height:21px; }}
  .party {{ text-align:right; line-height:21px; overflow-wrap:anywhere; word-break:break-word; }}
  .party .nm {{ font-weight:700; font-size:15.5px; }}
  .party .vat {{ font-weight:700; font-size:14.5px; }}
  .party .addr {{ line-height:17px; font-size:13.5px; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:14px; }}
  .items > thead > tr > th {{ background:{_HEAD_BG}; border:1px solid {_GRID}; font-weight:400; text-align:right;
              vertical-align:top; padding:6px 14px 4px 4px; line-height:16.5px; white-space:nowrap; }}
  .items > tbody > tr > td {{ border:1px solid {_GRID}; text-align:right; vertical-align:top;
              padding:6px 14px 8px 4px; line-height:17px; height:44px;
              overflow-wrap:anywhere; word-break:break-word; }}
  .tot {{ width:303px; table-layout:fixed; margin-top:2px; direction:ltr; }}
  .tot td {{ vertical-align:top; padding-top:3px; border-bottom:1px solid {_RULE}; line-height:17px; }}
  .tot .t-val {{ width:108px; text-align:right; padding-right:26px; }}
  .tot .t-lab {{ text-align:left; }}
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

    <!-- ===== TOP BAND: title + meta (left) · QR (middle) · logo (right) ===== -->
    <div style="position:relative; height:{QR_PRINT_PX + 8}px;" dir="ltr">
      <div style="position:absolute; left:0; top:0; text-align:left;">
        <div style="font-weight:700; font-size:16px; line-height:20px;" dir="rtl">فاتورة ضريبية</div>
        <div style="font-weight:700; font-size:16px; line-height:20px;">TAX INVOICE</div>
        <div class="meta" style="margin-top:20px;">{invoice_number}&nbsp;&nbsp;&nbsp;الرقم - Number</div>
        <div class="meta">{issued}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;التاريخ - Date</div>
        <div class="meta">حالة الدفع - Payment Status</div>
        <div class="meta">{status}</div>
      </div>
      <div style="position:absolute; left:238px; top:0;">{qr_html}</div>
      <div style="position:absolute; left:524px; top:11px; width:143px; height:91px;">{logo_html}</div>
    </div>

    <!-- ===== FROM (right) · TO (left) ===== -->
    <div style="display:flex; align-items:flex-start;">
      <div class="party" style="width:296px;">
        {_caption("من - FROM :")}
        <div class="nm">{esc(seller.get("name"))}</div>
        {_caption("الرقم الضريبي - TAX NUMBER :")}
        <div class="vat">{esc(seller.get("vat"))}</div>
        {_caption("العنوان - ADDRESS :")}
        <div class="addr">{esc(seller.get("address"))}</div>
      </div>
      <div style="width:57px;"></div>
      <div class="party" style="width:255px;">
        {_caption("الى - TO :")}
        <div class="nm">{esc(customer.get("name"))}</div>
        {_caption("الرقم الضريبي - TAX NUMBER :")}
        <div class="vat">{esc(customer.get("vat"))}</div>
      </div>
    </div>

    <!-- ===== ITEMS + CLOSING BLOCK ===== -->
    <table class="items">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head_html}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(cols)}" style="height:auto; padding:0; border:none;">
          <div dir="ltr" style="text-align:left;">
            <table class="tot"><colgroup><col style="width:108px"><col></colgroup>{"".join(total_rows)}</table>
          </div>
        </td></tr>
      </tbody>
    </table>
    {stamp_html}

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v17"]
