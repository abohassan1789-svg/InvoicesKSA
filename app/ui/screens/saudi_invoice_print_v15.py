"""«دروب الاتحاد» — a replica of the Daftra-style tax invoice the user supplied
(``تصامبم جديدة\\فاتورة رقم 001542 - شركة دروب الاتحاد للمقاولات المحدودة.pdf``).

Unlike the fixed-brand replicas (أطياف / مواسم الفاكهة / …), this one is a
*layout* replica only (user request 2026-10-05: «ممكن اللوجو يتغير … بيانات التاجر
وبيانات البائع ممكن تتغير عادي … بس الأماكن تكون في مكانها ونفس الشكل»): the
logo, the seller block and the buyer block all come live from the shared ``data``
dict (the selected company / customer), exactly like النماذج الأول→الثامن.

Design, measured from the A4 source with PyMuPDF and scaled ×816/595 onto the
816×1056 Letter sheet every template prints on:
* Header: QR top-left, the company logo centred-left, «فاتورة ضريبية» over «TAX
  Invoice» on the right (bold, grey ``#575656``), then «رقم الفاتورة» and
  «التاريخ» label/value pairs, then a thin grey rule.
* «معلومات البائع» / «معلومات المشتري»: a 4-cell row each (name · address · VAT
  · CR), every cell closed by a light vertical rule on its right edge.
* Items table: 6 columns, grey hairlines, no outer side borders. Column titles
  are two lines (Arabic over English) — the source stacked them one word per
  line, which the user found too tall (2026-10-06) — keeping the source's own
  «المجموع بعد الضريبة / Total Before VAT» caption on the VAT-inclusive
  line-total column.
* Totals: label right · value left with the new Saudi riyal sign (the source draws
  it as a custom glyph, so it ships as the ``riyal_symbol.png`` asset, lifted 1:1
  from the PDF). Rows: Total Before VAT · VAT (rate%) · Total After VAT (framed) ·
  Paid · Due Amount. A cash invoice is shown fully paid (Paid = −total, Due =
  0.00); any other payment type leaves Paid at 0.00 and the total due.
* Numbers follow Daftra's style: whole amounts print without decimals
  («315,000»), fractional ones with two, and zero as «0.00».
* The source's «أنشئ بواسطة daftra free version» advert line is NOT reproduced —
  it is the generator's watermark, not part of the invoice.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _asset_data_uri,
    company_logo_data_uri,
    qr_vector_data_uri,
    stamp_overlay_html,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — measured from the reference PDF.
# ---------------------------------------------------------------------------
_INK = "#575656"            # titles, labels, values (the source's grey ink)
_BLACK = "#000000"          # invoice-number / date pair
_RULE = "#d0d0d0"           # the header separator
_GRID = "#cccccc"           # cell / table hairlines
_FRAME = "#e5e5e5"          # the «Total After VAT» row frame
_FONTS = "'Noto Sans Arabic','Noto Sans','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_SIDE = 31                  # 22.5pt side margin → px
_CONTENT_W = _SHEET_W - 2 * _SIDE   # 754
_TABLE_W = 745              # items + totals: 26.2→569.2pt (4px in from the right, 5px from the left)
_TOP = 31                   # top margin (repeats on continuation pages)
_BOTTOM = 40

_RIYAL_ASSET = "riyal_symbol.png"

# Items table, physical right → left (RTL): (header lines, width px).
# User 2026-10-06 («رؤوس الأعمدة كبيرة أوي في الارتفاع»): every title is TWO lines
# (Arabic over English, never wrapped further), «البنود» narrowed 471→305 and the
# freed width given to the numeric columns so each title — and a figure like
# «10,867.50» — fits on one line. Total stays 745.
_ITEM_COLS = (
    (("البنود", "Items"), 305),
    (("السعر", "Price"), 75),
    (("الكمية", "Qty"), 60),
    (("نسبة الضريبة", "Tax Percent"), 90),
    (("قيمة الضريبة", "Tax Value"), 90),
    (("المجموع بعد الضريبة", "Total Before VAT"), 125),
)
# With «إظهار وصف الصنف»: «الوصف» right after «البنود», its width taken from it.
_ITEM_COLS_DESC = ((("البنود", "Items"), 170), (("الوصف", "Description"), 135)) + _ITEM_COLS[1:]


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _num(value: Any) -> str:
    """Daftra-style figure: «315,000», «7,500.50», «-362,250», zero → «0.00»."""
    d = _dec(value)
    if d == 0:
        return "0.00"
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d:,.2f}"


def _rate(value: Any) -> str:
    d = _dec(value).normalize()
    return f"{d:f}%"


def _fmt_datetime(issued: Any) -> str:
    """``31/08/2026 - 21:54:05`` like the source; raw string otherwise."""
    if isinstance(issued, datetime.datetime):
        return issued.strftime("%d/%m/%Y - %H:%M:%S")
    if isinstance(issued, datetime.date):
        return issued.strftime("%d/%m/%Y")
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _party_section(title: str, cells: tuple[tuple[str, str], ...]) -> str:
    """«معلومات البائع/المشتري»: heading + four label/value cells (right → left),
    each closed by a light vertical rule on its right edge."""
    widths = (177, 224, 224, 129)   # name · address · VAT · CR (sum = 754)
    tds = "".join(
        f'<td style="width:{w}px; border-right:1px solid {_GRID}; vertical-align:top; '
        f'padding:4px 6px 4px 4px; height:73px; text-align:right;">'
        f'<div>{label}</div><div class="val">{value}</div></td>'
        for (label, value), w in zip(cells, widths)
    )
    return f"""
    <div class="h2">{title}</div>
    <table class="party"><tr>{tds}</tr></table>"""


def _item_row(line: dict[str, Any], show_desc: bool = False) -> str:
    name = html.escape(str(line.get("name") or ""))
    cells = (
        f'<td class="it-name">{name}</td>',
        f'<td class="it-name">{html.escape(line.get("print_description") or "")}</td>' if show_desc else "",
        f'<td>{_num(line.get("price"))}</td>',
        f'<td>{_num(line.get("qty"))}</td>',
        f'<td>{_rate(line.get("vat_rate"))}</td>',
        f'<td>{_num(line.get("vat_amount"))}</td>',
        f'<td>{_num(line.get("total"))}</td>',
    )
    return '<tr class="it-row">' + "".join(cells) + "</tr>"


def _total_row(label: str, amount: Any, riyal: str, *, framed: bool = False) -> str:
    cls = ' class="framed"' if framed else ""
    sign = f'<img src="{riyal}" alt="SAR" class="riyal">' if riyal else "SAR "
    return (
        f"<tr{cls}>"
        f'<td class="t-label">{label}</td>'
        f'<td class="t-val"><span dir="ltr">{sign}{_num(amount)}</span></td>'
        "</tr>"
    )


def build_invoice_html_v15(data: dict[str, Any]) -> str:
    """Build «دروب الاتحاد» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)

    esc = lambda v: html.escape(str(v or ""))  # noqa: E731
    invoice_number = esc(data.get("invoice_number"))
    issued = esc(_fmt_datetime(data.get("issue_datetime")))

    subtotal = _dec(totals.get("subtotal", totals.get("taxable", 0)))
    discount = _dec(totals.get("discount", 0))
    vat_total = _dec(totals.get("vat", 0))
    grand_total = _dec(totals.get("total", 0))
    credit = _is_credit(str(data.get("payment_label") or ""))
    paid = Decimal("0") if credit else -grand_total
    due = grand_total + paid

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    logo = company_logo_data_uri(seller)
    # «Zoom», never stretch (user 2026-10-05): the logo is scaled up OR down to fill
    # the 154×108 frame while keeping its own proportions (object-fit:contain).
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:154px; height:108px; '
        'object-fit:contain; object-position:center; display:block;">'
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

    seller_html = _party_section("معلومات البائع", (
        ("اسم البائع", esc(seller.get("name"))),
        ("عنوان البائع", esc(seller.get("address"))),
        ("رقم تسجيل القيمة المضافة للبائع", esc(seller.get("vat"))),
        ("رقم السجل التجاري", esc(seller.get("cr"))),
    ))
    buyer_html = _party_section("معلومات المشتري", (
        ("اسم المشتري", esc(customer.get("name"))),
        ("عنوان المشتري", esc(customer.get("address"))),
        ("رقم تسجيل القيمة المضافة للمشتري", esc(customer.get("vat"))),
        ("رقم السجل التجاري", esc(customer.get("cr"))),
    ))

    show_desc = bool(data.get("show_description"))
    item_cols = _ITEM_COLS_DESC if show_desc else _ITEM_COLS
    head_html = "".join(
        f'<th style="width:{w}px;">{"<br>".join(parts)}</th>' for parts, w in item_cols
    )

    total_rows = [_total_row("المجموع قبل الضريبة&nbsp; Total Before VAT", subtotal, riyal)]
    if discount:
        total_rows.append(_total_row("الخصم&nbsp; Discount", -discount, riyal))
    total_rows += [
        _total_row(f"القيمة المضافة ({vat_rate}%)", vat_total, riyal),
        _total_row("الإجمالي بعد الضريبة&nbsp; Total After VAT", grand_total, riyal, framed=True),
        _total_row("مدفوع&nbsp; Paid", paid, riyal),
        _total_row("الرصيد المستحق&nbsp; Due Amount", due, riyal),
    ]

    # The closing block (last item + totals + optional stamp) is one no-break
    # <tbody>: it moves to a new page TOGETHER with at least one item, so the
    # totals never strand alone on a page.
    if lines:
        main_rows = "".join(_item_row(ln, show_desc) for ln in lines[:-1])
        last_row = _item_row(lines[-1], show_desc)
    else:
        main_rows = ""
        last_row = f'<tr class="it-row"><td colspan="{len(item_cols)}" style="color:#999;">لا توجد أصناف</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;700;900&family=Noto+Sans:wght@400;700;900&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK}; font-size:12.3px;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ box-sizing:border-box; width:{_SHEET_W}px; min-height:{_SHEET_H}px; margin:24px auto;
            background:#ffffff; padding:0 {_SIDE}px; direction:rtl;
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  .items th, .items td, .tot td, .party td {{ box-sizing:border-box; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  tfoot {{ display:table-footer-group; }}
  .page {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .page > * > tr > td {{ padding:0; vertical-align:top; }}
  .summary {{ break-inside:avoid; page-break-inside:avoid; }}
  .h1 {{ font-weight:700; font-size:31px; line-height:1.2; text-align:center; }}
  .h2 {{ font-weight:700; font-size:18.5px; line-height:1.2; margin:0 2px 0 0; }}
  .party {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:16px; line-height:23.7px; }}
  .party .val {{ overflow-wrap:anywhere; word-break:break-word; }}
  .items {{ width:{_TABLE_W}px; table-layout:fixed; margin:42px 4px 0 0; }}
  .items th {{ font-weight:700; line-height:19px; padding:6px 2px; text-align:center; white-space:nowrap;
              vertical-align:middle; border-top:1px solid {_GRID}; border-bottom:1px solid {_GRID};
              border-left:1px solid {_GRID}; }}
  .items td {{ height:34px; padding:0 3px; text-align:center; vertical-align:middle;
              border-bottom:1px solid {_GRID}; border-left:1px solid {_GRID};
              overflow-wrap:anywhere; word-break:break-word; }}
  .items th:last-child, .items td:last-child {{ border-left:none; }}
  .tot {{ width:{_TABLE_W}px; table-layout:fixed; margin:21px 0 0 0; }}
  .tot td {{ height:36px; vertical-align:middle; border:1px solid transparent; }}
  .tot .t-label {{ width:{_TABLE_W - 186}px; text-align:right; padding-right:5px;
                  font-weight:900; font-size:14.4px; }}
  .tot .t-val {{ width:186px; text-align:left; padding-left:5px; font-weight:700; font-size:14.4px; }}
  .tot tr.framed td {{ border:1px solid {_FRAME}; }}
  .riyal {{ height:13px; width:auto; vertical-align:-1px; margin-right:5px; }}
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

    <!-- ===== HEADER: title + invoice no/date (right) · logo · QR (left) ===== -->
    <div style="position:relative; height:186px;">
      <div style="position:absolute; right:43px; top:13px; width:240px;">
        <div class="h1">فاتورة ضريبية</div>
        <div class="h1" style="margin-top:24px;">TAX Invoice</div>
      </div>
      <div style="position:absolute; right:11px; top:129px; width:140px; text-align:center; color:{_BLACK}; line-height:23.7px;">
        <div>رقم الفاتورة&nbsp;&nbsp; Invoice NO</div><div>{invoice_number}</div>
      </div>
      <div style="position:absolute; right:164px; top:129px; width:160px; text-align:center; color:{_BLACK}; line-height:23.7px;">
        <div>التاريخ</div><div dir="ltr">{issued}</div>
      </div>
      <div style="position:absolute; left:194px; top:30px; width:154px; height:108px;
                  display:flex; align-items:center; justify-content:center;">{logo_html}</div>
      <div style="position:absolute; left:0; top:-9px;">{qr_html}</div>
    </div>
    <div style="height:1px; background:{_RULE}; margin-top:2px;"></div>

    <div style="height:27px;"></div>
    {seller_html}
    <div style="height:39px;"></div>
    {buyer_html}

    <!-- ===== ITEMS + CLOSING BLOCK ===== -->
    <table class="items">
      <thead><tr>{head_html}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(item_cols)}" style="height:auto; padding:0; border:none; text-align:right;">
          <table class="tot">{"".join(total_rows)}</table>
          {stamp_overlay_html(data)}
        </td></tr>
      </tbody>
    </table>

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v15"]
