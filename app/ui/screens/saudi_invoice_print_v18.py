"""«ميج السعودية» — a layout replica of the scanned tax invoice the user supplied
(``تصامبم جديدة\\WhatsApp Image 2026-10-05 at 5.51.35 PM.jpeg``, INV-1-0532 of «شركة
ميج السعودية المحدودة», a Zoho-style invoice — the same family as «موضي عقيل»).

Same idea as the other layout replicas (user 2026-10-06): places, look and design
are copied; the logo, the seller blocks and the customer block come live from the
shared ``data`` dict. Geometry was measured off the 485×668 phone scan of an A4
page (×816/485 → the 816-px Letter sheet); the content ends ~870px down, so the
Letter sheet needs no vertical squeeze.

Design:
* Header: the seller twice — ARABIC block right (name · «السجل التجاري :» ·
  «الرقم الضريبي :» · address) and ENGLISH block left (name_en · «Register
  Number :» · «Tax Number :» · address_en), all bold; the company logo centred
  between them («Zoom»: scaled to fit, never stretched).
* «فاتورة ضريبية» centred, then the customer right (العميل / الرقم الضريبي /
  السجل التجاري) and the invoice meta left (رقم الفاتورة · تاريخ الانشاء · تاريخ
  الاصدار · تاريخ الاستحقاق — our invoices carry one date, so all three print it).
* Items grid, 7 columns (م · البند · الكمية · السعر · المجموع بدون الضريبة · قيمة
  الضريبة · المجموع): grey ``#f3f4f8`` header band with CENTRED bilingual titles
  (broken like the scan), values right-aligned and top-aligned. The quantity cell
  carries the unit name when «إظهار عمود الوحدة» is ticked («40 دراجة»).
* Totals list bottom-left (value right-aligned, bilingual label beside it, a rule
  under each row): Pre-Tax Total · VAT (rate%) · Total (riyal sign) · a LARGER
  Due (riyal sign). Due = the total for a credit (آجل) invoice, 0.00 for cash.
* The QR bottom-right under the totals band; the company stamp (when «إظهار
  الختم» is ticked) under the totals, left of centre, where the scan has it.
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
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — sampled from the scan (same family as «موضي عقيل»).
# ---------------------------------------------------------------------------
_INK = "#1a1a1a"
_GRID = "#9a9a9a"           # items-table hairlines
_RULE = "#555555"           # rules under the totals rows
_HEAD_BG = "#f3f4f8"        # items header band
_FONTS = "'Noto Kufi Arabic','Noto Sans','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_LEFT = 42                  # the scan's margins (25 / 30 image px)
_RIGHT = 50
_CONTENT_W = _SHEET_W - _LEFT - _RIGHT   # 724
_TOP = 40
_BOTTOM = 40

_RIYAL_ASSET = "riyal_symbol.png"

# Items grid, physical right → left (RTL): (arabic, english, width px). Title
# breaks are pinned with <br> exactly where the scan breaks them.
_ITEM_COLS = (
    ("م", "No.", 52),
    ("البند", "Item", 146),
    ("الكمية", "Quantity", 83),
    ("السعر", "Price", 70),
    ("المجموع بدون<br>الضريبة", "Pre-Tax Total", 157),
    ("قيمة<br>الضريبة", "Tax Value", 108),
    ("المجموع", "Total", 108),
)
# With «إظهار وصف الصنف»: «الوصف» right after «البند»; still 724px in all.
_ITEM_COLS_DESC = (
    ("م", "No.", 45),
    ("البند", "Item", 100),
    ("الوصف", "Description", 130),
    ("الكمية", "Quantity", 72),
    ("السعر", "Price", 62),
    ("المجموع بدون<br>الضريبة", "Pre-Tax Total", 132),
    ("قيمة<br>الضريبة", "Tax Value", 92),
    ("المجموع", "Total", 91),
)


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
    """``2025/10/2`` — year/month/day without zero padding, like the scan."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return f"{issued.year}/{issued.month}/{issued.day}"
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _line(text: str, *, ltr: bool = False) -> str:
    if not text:
        return ""
    attr = ' dir="ltr"' if ltr else ""
    return f"<div{attr}>{text}</div>"


def _item_row(index: int, line: dict[str, Any], show_unit: bool, show_desc: bool = False) -> str:
    name = html.escape(str(line.get("name") or ""))
    unit = html.escape(str(line.get("unit") or "")) if show_unit else ""
    qty = _plain(line.get("qty"))
    qty_html = f'<span dir="ltr">{qty} {unit}</span>' if unit else qty
    desc_td = f'<td>{html.escape(line.get("print_description") or "")}</td>' if show_desc else ""
    return (
        "<tr>"
        f"<td>{index}</td>"
        f"<td>{name}</td>"
        f"{desc_td}"
        f"<td>{qty_html}</td>"
        f"<td>{_money(line.get('price'))}</td>"
        f"<td>{_money(line.get('before'))}</td>"
        f"<td>{_money(line.get('vat_amount'))}</td>"
        f"<td>{_money(line.get('total'))}</td>"
        "</tr>"
    )


def _total_row(label_html: str, amount: Any, height: int, *, big: bool = False) -> str:
    cls = ' class="big"' if big else ""
    return (
        f'<tr{cls} style="height:{height}px;">'
        f'<td class="t-val">{_money(amount)}</td>'
        f'<td class="t-lab">{label_html}</td>'
        "</tr>"
    )


def build_invoice_html_v18(data: dict[str, Any]) -> str:
    """Build «ميج السعودية» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))

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

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    # ---- seller blocks (Arabic right, English left) ----
    cr, vat = esc(seller.get("cr")), esc(seller.get("vat"))
    seller_ar = "".join((
        _line(esc(seller.get("name"))),
        _line(f"السجل التجاري : {cr}" if cr else ""),
        _line(f"الرقم الضريبي : {vat}" if vat else ""),
        _line(esc(seller.get("address"))),
    ))
    seller_en = "".join((
        _line(esc(seller.get("name_en")), ltr=True),
        _line(f"Register Number : {cr}" if cr else "", ltr=True),
        _line(f"Tax Number : {vat}" if vat else "", ltr=True),
        _line(esc(seller.get("address_en")), ltr=True),
    ))

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:110px; height:72px; object-fit:contain; display:block;">'
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

    # QR (right) + optional stamp (left of centre) under the totals, as the scan has them.
    stamp_html = ""
    if data.get("show_stamp"):
        stamp = company_stamp_data_uri(seller)
        if stamp:
            stamp_html = (
                f'<div data-company-stamp="1" style="position:absolute; left:200px; top:99px; '
                f'width:200px; height:150px;"><img src="{stamp}" alt="stamp" '
                f'style="width:200px; height:150px; object-fit:contain; filter:{_STAMP_FILTER};"></div>'
            )
    band_h = max(27 + QR_PRINT_PX, 99 + 150 if stamp_html else 0)
    bottom_band = (
        f'<div dir="ltr" style="position:relative; height:{band_h}px; break-inside:avoid; '
        f'page-break-inside:avoid;">'
        f'<div style="position:absolute; right:2px; top:27px;">{qr_html}</div>{stamp_html}</div>'
    )

    # English title lines are pinned LTR so «No.» keeps its period on the right.
    show_desc = bool(data.get("show_description"))
    cols = _ITEM_COLS_DESC if show_desc else _ITEM_COLS
    head_html = "".join(f'<th><div>{ar}</div><div dir="ltr">{en}</div></th>' for ar, en, _w in cols)
    colgroup = "".join(f'<col style="width:{w}px">' for _a, _e, w in cols)

    total_rows = []
    if discount:
        total_rows.append(_total_row('<div dir="rtl">الخصم</div><div>Discount</div>', -discount, 46))
    total_rows += [
        _total_row('<div dir="rtl">الإجمالي قبل الضريبة</div><div>Pre-Tax Total</div>', taxable if discount else subtotal, 46),
        _total_row(f'<div dir="rtl">القيمة المضافة <span dir="ltr">%{vat_rate}</span></div>', vat_total, 38),
        _total_row(f'<div dir="rtl">الإجمالي ({sign})</div><div>Total (SAR)</div>', grand_total, 51),
        _total_row(f'<div dir="rtl">المستحق ({sign})</div><div>Due (SAR)</div>', due, 52, big=True),
    ]

    # The closing block (last item + totals) is one no-break <tbody>, so the totals
    # always travel to a new page together with at least one item.
    if lines:
        main_rows = "".join(_item_row(i, ln, show_unit, show_desc) for i, ln in enumerate(lines[:-1], 1))
        last_row = _item_row(len(lines), lines[-1], show_unit, show_desc)
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
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK}; font-size:13px;
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
  .blk {{ font-weight:700; font-size:14px; line-height:21px; overflow-wrap:anywhere; word-break:break-word; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:24px; }}
  .items > thead > tr > th {{ background:{_HEAD_BG}; border:1px solid {_GRID}; font-weight:600; text-align:center;
              vertical-align:top; padding:7px 4px 6px; line-height:17px; white-space:nowrap; }}
  .items > tbody > tr > td {{ border:1px solid {_GRID}; text-align:right; vertical-align:top; font-weight:600;
              padding:10px 15px 9px 4px; line-height:18px; height:48px;
              overflow-wrap:anywhere; word-break:break-word; }}
  .tot {{ width:371px; table-layout:fixed; direction:ltr; }}
  .tot td {{ vertical-align:top; padding-top:6px; border-bottom:1.5px solid {_RULE}; line-height:18px;
            font-weight:700; }}
  .tot .t-val {{ width:122px; text-align:right; padding-right:29px; }}
  .tot .t-lab {{ text-align:left; }}
  .tot tr.big td {{ font-size:16px; line-height:20px; }}
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

    <!-- ===== HEADER: seller (AR right) · logo (centre) · seller (EN left) ===== -->
    <div style="position:relative; min-height:110px;" dir="ltr">
      <div class="blk" dir="rtl" style="position:absolute; right:0; top:2px; width:250px; text-align:right;">{seller_ar}</div>
      <div style="position:absolute; left:{362 - 55}px; top:24px; width:110px; height:72px;">{logo_html}</div>
      <div class="blk" style="position:absolute; left:2px; top:0; width:240px; text-align:left;">{seller_en}</div>
    </div>

    <!-- ===== TITLE ===== -->
    <div style="text-align:center; font-weight:700; font-size:15px; line-height:22px; margin-top:22px;">فاتورة ضريبية</div>

    <!-- ===== CUSTOMER (right) · INVOICE META (left) ===== -->
    <div style="position:relative; height:84px; margin-top:24px;" dir="ltr">
      <div class="blk" dir="rtl" style="position:absolute; right:0; top:4px; width:400px; text-align:right; line-height:25px;">
        <div>العميل : {esc(customer.get("name"))}</div>
        <div>الرقم الضريبي : {esc(customer.get("vat"))}</div>
        <div>السجل التجاري : {esc(customer.get("cr"))}</div>
      </div>
      <div class="blk" dir="rtl" style="position:absolute; left:0; top:0; width:190px; text-align:right; line-height:20px;">
        <div>رقم الفاتورة : <span dir="ltr">{invoice_number}</span></div>
        <div>تاريخ الانشاء : <span dir="ltr">{issued}</span></div>
        <div>تاريخ الاصدار : <span dir="ltr">{issued}</span></div>
        <div>تاريخ الاستحقاق : <span dir="ltr">{issued}</span></div>
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
            <table class="tot"><colgroup><col style="width:122px"><col></colgroup>{"".join(total_rows)}</table>
          </div>
        </td></tr>
      </tbody>
    </table>
    {bottom_band}

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v18"]
