"""«نوافذ» — a layout replica of the scanned Daftra-style tax invoice the user
supplied (``تصامبم جديدة\\WhatsApp Image 2026-10-05 at 5.51.32 PM.jpeg``, invoice
#725 of «شركة نوافذ الوطنية للنقليات» to «مصنع روائع الدار…»).

Same idea as «دروب الاتحاد» / «قصر نصار» (user 2026-10-06): places, look and
design are copied; the logo, the seller and the buyer come live from the shared
``data`` dict. The source is a 1080×1533 phone screenshot of an A4 page, so the
geometry was measured off the image (×0.756 → the 816-px Letter sheet).

Design:
* Header: «فاتورة ضريبية» over «TAX Invoice» (bold) with the QR under them on the
  LEFT; the seller block (bold name · «الرقم الضريبي : …» · address lines) in the
  middle-right; the logo on the far right («Zoom»: scaled to fit, never
  stretched). The source's «هاتف :» line is not printed — the system stores no
  company phone. Then a full-width double rule (thick over thin).
* «العميل / Client» caption on the right edge, the buyer beside it: bold name ·
  first address line · «الرقم الضريبي: …» · «سجل تجارى/ رقم موحد: …» · the remaining
  address lines (that is the scan's order). On the left the «رقم الفاتورة /
  Invoice NO» and «تاريخ الفاتورة / Invoice Date» bilingual labels with their values.
* Items grid, 8 columns, framed, grey header band with bilingual titles broken
  like the scan: البند (item name) · الوصف (the line's «وصف الصنف») · السعر · الكمية ·
  المجموع قبل الضريبة · نسبة الضريبة · قيمة الضريبة · المجموع مع الضريبة.
* Totals list on the left under the grid: bilingual bold labels right, riyal sign
  + figure left, a dark rule under each row, «الإجمالي بعد الضريبة» on a grey band.
  Daftra figures: whole amounts «4,140», VAT and unit figures 2dp. A cash invoice is
  shown fully paid (Paid = −total, Due 0.00), like «دروب الاتحاد»; otherwise Paid
  0.00 and the total due.
* Company stamp (when «إظهار الختم» is ticked) to the right of the totals.
* Font Tahoma (the scan's own face), Noto Sans Arabic as fallback.
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
_INK = "#111111"
_GRID = "#3a3a3a"           # items-grid lines
_HEAD_BG = "#e6e6e6"        # items header band / «Total After VAT» band
_RULE = "#1a1a1a"           # rules under the totals rows, the header double rule
_FONTS = "'Tahoma','Noto Sans Arabic','Segoe UI',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_SIDE = 65                  # 86 / 87 image px × 0.756
_CONTENT_W = _SHEET_W - 2 * _SIDE   # 686
_TOP = 56
_BOTTOM = 36

_RIYAL_ASSET = "riyal_symbol.png"

# Items grid, physical right → left (RTL): (title html, width px). Title breaks are
# pinned with <br> where the scan breaks them.
_ITEM_COLS = (
    ("البند<br>Item", 42),
    ("الوصف<br>Description", 103),
    ("السعر<br>Price", 92),
    ("الكمية<br>Qty", 93),
    ("المجموع قبل<br>الضريبة<br>Total Before<br>Tax", 93),
    ("نسبة الضريبة<br>VAT {rate}%", 92),
    ("قيمة الضريبة<br>VAT Amount", 92),
    ("المجموع<br>مع الضريبة<br>Total With<br>VAT", 79),
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
    """Daftra-style figure: «4,140», «7,500.50», zero → «0.00»."""
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
    """``01/01/2026`` — day/month/year like the scan."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return issued.strftime("%d/%m/%Y")
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _split_lines(value: Any) -> list[str]:
    return [p.strip() for p in str(value or "").splitlines() if p.strip()]


def _item_row(line: dict[str, Any], show_description: bool = True) -> str:
    # «البند» = the item name; «الوصف» = the line's own «وصف الصنف» (item_description).
    name = html.escape(str(line.get("name") or ""))
    description = html.escape(str(line.get("description") or ""))
    description_cell = f'<td class="txt">{description}</td>' if show_description else ""
    return (
        "<tr>"
        f'<td class="txt">{name}</td>'
        f"{description_cell}"
        f"<td>{_money(line.get('price'))}</td>"
        f"<td>{_qty(line.get('qty'))}</td>"
        f"<td>{_money(line.get('before'))}</td>"
        f"<td>{_rate(line.get('vat_rate'))}</td>"
        f"<td>{_money(line.get('vat_amount'))}</td>"
        f"<td>{_num(line.get('total'))}</td>"
        "</tr>"
    )


def _total_row(label_html: str, value: str, sign: str, *, band: bool = False, bold_value: bool = False) -> str:
    cls = ' class="band"' if band else ""
    weight = "font-weight:700;" if bold_value else ""
    return (
        f"<tr{cls}>"
        f'<td class="t-lab">{label_html}</td>'
        f'<td class="t-val" style="{weight}"><span dir="ltr">{sign} {value}</span></td>'
        "</tr>"
    )


def build_invoice_html_v21(data: dict[str, Any]) -> str:
    """Build «نوافذ» from the shared invoice data dict."""
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

    subtotal = _dec(totals.get("subtotal", totals.get("taxable", 0)))
    discount = _dec(totals.get("discount", 0))
    vat_total = _dec(totals.get("vat", 0))
    grand_total = _dec(totals.get("total", 0))
    paid = Decimal("0") if credit else -grand_total
    due = grand_total + paid

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:159px; height:88px; object-fit:contain; display:block;">'
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
        f'<img src="{riyal}" alt="SAR" style="height:12px; width:auto; vertical-align:-1px; '
        'filter:brightness(0.35);">'
        if riyal
        else "SAR"
    )

    # Seller: bold name · VAT · address lines (no phone stored in the system).
    seller_rows = [f'<div class="nm">{esc(seller.get("name"))}</div>']
    if seller.get("vat"):
        seller_rows.append(f'<div>الرقم الضريبي : {esc(seller.get("vat"))}</div>')
    seller_rows += [f"<div>{html.escape(p)}</div>" for p in _split_lines(seller.get("address"))]

    # Buyer, in the scan's order: name · first address line · VAT · CR · the rest.
    address = _split_lines(customer.get("address"))
    cust_rows = [f'<div class="nm">{esc(customer.get("name"))}</div>']
    if address:
        cust_rows.append(f"<div>{html.escape(address[0])}</div>")
    if customer.get("vat"):
        cust_rows.append(f'<div>الرقم الضريبي: {esc(customer.get("vat"))}</div>')
    if customer.get("cr"):
        cust_rows.append(f'<div>سجل تجارى/ رقم موحد: {esc(customer.get("cr"))}</div>')
    cust_rows += [f"<div>{html.escape(p)}</div>" for p in address[1:]]

    total_rows = [_total_row("<div>الإجمالي قبل الضريبة</div><div>Total Before VAT</div>", _num(subtotal), sign)]
    if discount:
        total_rows.append(_total_row("<div>الخصم</div><div>Discount</div>", _num(-discount), sign))
    total_rows += [
        _total_row(f'<div><bdi dir="ltr">VAT ({vat_rate}%)</bdi></div>', _money(vat_total), sign),
        _total_row("<div>الإجمالي بعد الضريبة</div><div>Total After VAT</div>", _num(grand_total), sign,
                   band=True, bold_value=True),
        _total_row("<div>مدفوع</div><div>Paid</div>", _num(paid), sign),
        _total_row("<div>الرصيد المستحق</div><div>Due Amount</div>", _num(due), sign),
    ]

    # Stamp to the right of the totals — only when «إظهار الختم» is ticked.
    stamp_html = ""
    if data.get("show_stamp"):
        stamp = company_stamp_data_uri(seller)
        if stamp:
            stamp_html = (
                f'<div data-company-stamp="1" style="margin:26px 0 0 0; padding-right:8px;">'
                f'<img src="{stamp}" alt="stamp" style="width:205px; height:205px; object-fit:contain; '
                f'filter:{_STAMP_FILTER};"></div>'
            )

    head_html = "".join(f"<th>{title.format(rate=vat_rate)}</th>" for title, _w in cols)
    colgroup = "".join(f'<col style="width:{w}px">' for _t, w in cols)

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
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;700&display=swap" rel="stylesheet">
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
  .h1 {{ font-weight:700; font-size:26px; line-height:30px; }}
  .blk {{ line-height:17px; text-align:right; overflow-wrap:anywhere; word-break:break-word; }}
  .blk .nm {{ font-weight:700; font-size:17px; line-height:21px; }}
  .lab {{ font-weight:700; line-height:16px; white-space:nowrap; }}
  .cust .nm {{ font-size:13.5px; line-height:17px; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:38px; }}
  .items > thead > tr > th {{ background:{_HEAD_BG}; border:1px solid {_GRID}; border-bottom:2px solid {_GRID};
              font-weight:700; text-align:center; vertical-align:middle; padding:5px 2px;
              line-height:16px; white-space:nowrap; height:74px; }}
  .items > tbody > tr > td {{ border:1px solid {_GRID}; text-align:center; vertical-align:top;
              padding:6px 3px 4px 3px; line-height:16px; height:42px;
              overflow-wrap:anywhere; word-break:break-word; }}
  .items > tbody > tr > td.txt {{ text-align:right; padding:6px 3px 4px 2px; overflow-wrap:break-word; word-break:normal; }}
  .tot {{ width:274px; table-layout:fixed; }}
  .tot td {{ border-bottom:1.5px solid {_RULE}; padding:4px 0 4px 0; line-height:16px; vertical-align:top; }}
  .tot .t-lab {{ text-align:right; font-weight:700; font-size:13.5px; padding-right:8px; }}
  .tot .t-val {{ width:122px; text-align:right; padding-right:30px; white-space:nowrap; font-size:13.5px; }}
  .tot tr.band td {{ background:{_HEAD_BG}; }}
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

    <!-- ===== HEADER: title + QR (left) · seller (middle) · logo (right) ===== -->
    <div style="position:relative; height:{max(QR_PRINT_PX + 66, 200)}px;">
      <div style="position:absolute; left:0; top:0; text-align:left;">
        <div class="h1">فاتورة ضريبية</div>
        <div class="h1" dir="ltr">TAX Invoice</div>
        <div style="margin-top:6px;">{qr_html}</div>
      </div>
      <div class="blk" style="position:absolute; right:204px; top:0; width:250px;">{"".join(seller_rows)}</div>
      <div style="position:absolute; right:0; top:2px; width:159px; height:88px;">{logo_html}</div>
    </div>
    <div style="border-top:2.5px solid {_RULE}; border-bottom:1px solid {_RULE}; height:2px; margin-top:6px;"></div>

    <!-- ===== CLIENT (right) · invoice no / date (left) ===== -->
    <div style="position:relative; margin-top:26px;">
      <div style="display:flex; align-items:flex-start;">
        <div class="lab" style="width:46px; text-align:right;"><div>العميل</div><div>Client</div></div>
        <div class="blk cust" style="width:330px; margin-right:15px;">{"".join(cust_rows)}</div>
      </div>
      <div style="position:absolute; left:0; top:0; width:170px;" dir="ltr">
        <div style="display:flex; align-items:center; height:32px;">
          <div style="width:65px; text-align:right;">{invoice_number}</div>
          <div class="lab" style="margin-left:22px; text-align:left;" dir="rtl"><div>رقم الفاتورة</div><div dir="ltr">Invoice NO</div></div>
        </div>
        <div style="display:flex; align-items:center; height:32px;">
          <div style="width:65px; text-align:right;">{issued}</div>
          <div class="lab" style="margin-left:22px; text-align:left;" dir="rtl"><div>تاريخ الفاتورة</div><div dir="ltr">Invoice Date</div></div>
        </div>
      </div>
    </div>

    <!-- ===== ITEMS + CLOSING BLOCK ===== -->
    <table class="items">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head_html}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(cols)}" style="padding:0; border:none; height:auto;">
          <div style="display:flex; flex-direction:row-reverse; justify-content:space-between; align-items:flex-start; margin-top:4px;">
            <table class="tot"><colgroup><col><col style="width:122px"></colgroup>{"".join(total_rows)}</table>
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


__all__ = ["build_invoice_html_v21"]
