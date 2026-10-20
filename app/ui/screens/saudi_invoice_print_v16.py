"""«إنتار الغربيا» — a layout replica of the tax invoice the user supplied
(``تصامبم جديدة\\فاتورة27.09.2026.pdf``, INV-1056 of «شركة إنتار الغربيا تريدينغ»).

Same idea as «دروب الاتحاد» (user 2026-10-05: «نفس الفكرة»): the design, places and
look are copied 1:1, while the logo, the seller block and the customer block come
live from the shared ``data`` dict (the selected company / customer).

Design, measured from the A4 source with PyMuPDF and scaled ×816/595.28 onto the
816×1056 Letter sheet every template prints on (font: Tajawal, ink ``#061d2b``):
* Header: seller block top-right — name (bold), address, «رقم السجل التجاري:» and
  «رقم التسجيل الضريبي:», ALL centred in the block (user 2026-10-06; the source
  right-aligned the last two) and wrapping inside it; the company logo top-left («Zoom»: scaled to fit its frame,
  never stretched); a 2px slate rule ``#546572`` across the sheet.
* Title «فاتورة ضريبية Tax Invoice» centred (Tajawal Medium).
* Info grid, 3 rows × (grey ``#f5f5f5`` label cell + value cell) × 2: customer /
  invoice number, address / date, VAT number / CR number (the CUSTOMER's CR, as
  in the source). Labels are bold Arabic over a small English line.
* Items table, 7 columns (# · description · qty · price · taxable amount · VAT ·
  amount), grey header band, ``#d1e0e8`` hairline grid.
* Bottom: totals left (Subtotal / Total VAT / Total including VAT, «SAR» in slate
  ``#546673``, a hairline above the grand total), the QR right with the bilingual
  ZATCA caption under it.
* Date is printed like the source: ``YYYY/MM/DD`` in Arabic-Indic digits
  (glyph order verified with PyMuPDF rawdict).
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    company_logo_data_uri,
    qr_vector_data_uri,
    stamp_overlay_html,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — measured from the reference PDF.
# ---------------------------------------------------------------------------
_INK = "#061d2b"            # body text / titles
_HEAD_INK = "#1f2937"       # items-table header text
_SLATE = "#546572"          # header rule
_SAR = "#546673"            # the «SAR» tags
_GRID = "#d1e0e8"           # every hairline
_LABEL_BG = "#f5f5f5"       # label cells + items header band
_FONTS = "'Tajawal','Segoe UI','Tahoma',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_SIDE = 36                  # 26.1pt side margin → px
_CONTENT_W = _SHEET_W - 2 * _SIDE   # 744
_TOP = 55                   # 40pt top margin (repeats on continuation pages)
_BOTTOM = 50

# Info grid widths (physical right → left): label · customer value · label · invoice value.
_INFO_W = (112, 260, 111, 261)

# Items table, physical right → left (RTL): (arabic, english, width px).
_ITEM_COLS = (
    ("#", "Item", 31),
    ("المنتج / الوصف", "Description", 264),
    ("الكمية", "Qty", 62),
    ("السعر", "Price", 77),
    ("المبلغ الخاضع للضريبة", "Taxable amount", 116),
    ("القيمة المضافة", "VAT", 93),         # + the rate line, see _head_cells
    ("المجموع", "Amount", 101),
)
# With «إظهار وصف الصنف»: «وصف الصنف» right after the name, its width taken from it.
_ITEM_COLS_DESC = (
    _ITEM_COLS[0], ("المنتج / الوصف", "Description", 145), ("وصف الصنف", "Item Description", 119),
) + _ITEM_COLS[2:]

_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any) -> str:
    """«2,044.10» — two decimals with thousands separators."""
    return f"{_dec(value):,.2f}"


def _plain(value: Any) -> str:
    """Qty / unit price as typed: «10», «1.6», «204.41» (trailing zeros dropped)."""
    d = _dec(value).normalize()
    text = format(d, "f")
    return text if text not in ("", "-0") else "0"


def _fmt_date(issued: Any) -> str:
    """``٢٠٢٦/٠٩/٢٧`` — YYYY/MM/DD in Arabic-Indic digits, like the source."""
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return issued.strftime("%Y/%m/%d").translate(_AR_DIGITS)
    return str(issued or "")


def _label(ar: str, en: str) -> str:
    return (
        f'<div style="font-weight:700; font-size:13px; line-height:13.5px;">{ar}</div>'
        f'<div style="font-size:11.9px; line-height:12.5px;">{en}</div>'
    )


def _info_rows(rows: tuple[tuple[str, str, str, str], ...]) -> str:
    """Each row: (customer-side label, customer value, invoice-side label, invoice value)."""
    heights = (34, 34, 48)
    out = []
    for (lab_r, val_r, lab_l, val_l), h in zip(rows, heights):
        out.append(
            f'<tr style="height:{h}px;">'
            f'<td class="lab">{lab_r}</td><td class="val">{val_r}</td>'
            f'<td class="lab">{lab_l}</td><td class="val">{val_l}</td>'
            "</tr>"
        )
    return "".join(out)


def _head_cells(vat_rate: str, show_desc: bool = False) -> str:
    cells = []
    for ar, en, _w in (_ITEM_COLS_DESC if show_desc else _ITEM_COLS):
        # The source prints the rate as «%15» (sign first), so pin that order.
        rate = f'<div class="ar" dir="ltr">%{vat_rate}</div>' if en == "VAT" else ""
        cells.append(f'<th><div class="ar">{ar}</div>{rate}<div class="en">{en}</div></th>')
    return "".join(cells)


def _item_row(index: int, line: dict[str, Any], show_desc: bool = False) -> str:
    name = html.escape(str(line.get("name") or ""))
    # Roomier leading than the 14px row line: a description often wraps to several lines.
    desc_td = (
        f'<td class="desc" style="line-height:16px; padding-top:3px; padding-bottom:3px;">'
        f'{html.escape(line.get("print_description") or "")}</td>'
        if show_desc
        else ""
    )
    return (
        '<tr class="it-row">'
        f'<td class="sm">{index}</td>'
        f'<td class="desc">{name}</td>'
        f'{desc_td}'
        f'<td>{_plain(line.get("qty"))}</td>'
        f'<td>{_plain(line.get("price"))}</td>'
        f'<td class="sm">{_money(line.get("before"))}</td>'
        f'<td class="sm">{_money(line.get("vat_amount"))}</td>'
        f'<td class="sm">{_money(line.get("total"))}</td>'
        "</tr>"
    )


def _total_row(ar: str, en: str, amount: Any, *, grand: bool = False) -> str:
    rule = f" border-top:1px solid {_GRID};" if grand else ""
    weight = 800 if grand else 700
    sar_weight = 700 if grand else 400
    return (
        f'<div style="position:relative; height:33.6px;{rule}">'
        f'<div style="position:absolute; left:0; top:5px; font-weight:{weight}; font-size:14.2px;" dir="ltr">{_money(amount)}</div>'
        f'<div style="position:absolute; left:106px; top:6px; color:{_SAR}; font-weight:{sar_weight};">SAR</div>'
        f'<div style="position:absolute; right:0; top:0; text-align:right;">{_label(ar, en)}</div>'
        "</div>"
    )


def build_invoice_html_v16(data: dict[str, Any]) -> str:
    """Build «إنتار الغربيا» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)

    esc = lambda v: html.escape(str(v or ""))  # noqa: E731
    invoice_number = esc(data.get("invoice_number"))
    issued = esc(_fmt_date(data.get("issue_datetime")))

    subtotal = totals.get("subtotal", totals.get("taxable", 0))
    discount = _dec(totals.get("discount", 0))
    vat_total = totals.get("vat", 0)
    grand_total = totals.get("total", 0)

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    vat_rate = f"{rates.pop():f}" if len(rates) == 1 else "15"

    # ---- seller block (name/address centred, CR/VAT right-aligned — as the source) ----
    # User 2026-10-06: the WHOLE seller block is centred (text-align:center), and it
    # flows — a long name/address wraps inside the block instead of running off it.
    seller_lines = [
        f'<div style="font-weight:700;">{esc(seller.get("name"))}</div>',
        f'<div>{esc(seller.get("address"))}</div>',
    ]
    if seller.get("cr"):
        seller_lines.append(
            f'<div>رقم السجل التجاري:&nbsp; {esc(seller.get("cr"))}</div>'
        )
    if seller.get("vat"):
        seller_lines.append(
            f'<div style="margin-top:3px;">رقم التسجيل الضريبي:&nbsp; {esc(seller.get("vat"))}</div>'
        )

    # «Zoom», never stretch: scaled up or down to fill its frame, proportions kept.
    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img src="{logo}" alt="logo" style="width:178px; height:97px; object-fit:contain; display:block;">'
        if logo
        else ""
    )
    qr = qr_vector_data_uri(data.get("qr_payload"))
    qr_html = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'display:block; margin:0 auto; background:#ffffff;">'
        if qr
        else ""
    )

    info_html = _info_rows((
        (_label("العميل", "Customer"), esc(customer.get("name")),
         _label("رقم الفاتورة", "Invoice number"), invoice_number),
        (_label("العنوان", "Address"), esc(customer.get("address")),
         _label("التاريخ", "Date"), f'<span dir="ltr">{issued}</span>'),
        (_label("رقم التسجيل<br>الضريبي", "VAT number"), esc(customer.get("vat")),
         _label("رقم السجل<br>التجاري", "CR Number"), esc(customer.get("cr"))),
    ))
    info_cols = "".join(f'<col style="width:{w}px">' for w in _INFO_W)
    show_desc = bool(data.get("show_description"))
    cols = _ITEM_COLS_DESC if show_desc else _ITEM_COLS
    item_cols = "".join(f'<col style="width:{w}px">' for _a, _e, w in cols)

    totals_html = _total_row("المجموع الفرعي", "Subtotal", subtotal)
    if discount:
        totals_html += _total_row("الخصم", "Discount", -discount)
    totals_html += _total_row(f"إجمالي ضريبة القيمة المضافة ({vat_rate}%)", "Total VAT", vat_total)
    totals_html += _total_row("المجموع شامل القيمة المضافة", "Total including VAT", grand_total, grand=True)

    # The closing block (last item + totals + QR) is one no-break <tbody>: it moves
    # to a new page TOGETHER with at least one item, never stranding the totals.
    if lines:
        main_rows = "".join(_item_row(i, ln, show_desc) for i, ln in enumerate(lines[:-1], 1))
        last_row = _item_row(len(lines), lines[-1], show_desc)
    else:
        main_rows = ""
        last_row = f'<tr class="it-row"><td colspan="{len(cols)}" style="color:#999;">لا توجد أصناف</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
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
  .info {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .info td {{ border:1px solid {_GRID}; text-align:center; vertical-align:top; }}
  .info td.lab {{ background:{_LABEL_BG}; padding:3px 4px 2px; }}
  .info td.val {{ padding:5px 6px 2px; line-height:14px; overflow-wrap:anywhere; word-break:break-word; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; margin-top:27px; }}
  .items th {{ background:{_LABEL_BG}; border:1px solid {_GRID}; color:{_HEAD_INK}; font-weight:400;
              vertical-align:top; padding:3px 2px 3px; height:42px; text-align:center; }}
  .items th .ar {{ font-weight:700; font-size:10.1px; line-height:12px; }}
  .items th .en {{ font-size:11.9px; line-height:12.5px; }}
  .items td {{ border:1px solid {_GRID}; height:25.3px; padding:0 3px; text-align:center;
              vertical-align:middle; line-height:14px; }}
  .items td.sm {{ font-size:10.7px; }}
  .items td.desc {{ text-align:right; padding-right:3px; overflow-wrap:anywhere; word-break:break-word; }}
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

    <!-- ===== HEADER: seller (right) · logo (left) · rule · title ===== -->
    <div style="position:relative; height:200px;">
      <div style="position:absolute; right:0; top:20px; width:353px; max-height:96px; overflow:hidden;
                  line-height:16.7px; text-align:center; overflow-wrap:anywhere; word-break:break-word;">
        {"".join(seller_lines)}
      </div>
      <div style="position:absolute; left:96px; top:6px; width:178px; height:97px;">{logo_html}</div>
      <div style="position:absolute; left:0; right:0; top:118.6px; height:2.3px; background:{_SLATE};"></div>
      <div style="position:absolute; left:0; right:0; top:141px; text-align:center; font-weight:500;
                  font-size:30.8px; line-height:36px;">فاتورة ضريبية Tax Invoice</div>
    </div>

    <!-- ===== INFO GRID ===== -->
    <table class="info"><colgroup>{info_cols}</colgroup>{info_html}</table>

    <!-- ===== ITEMS + CLOSING BLOCK ===== -->
    <table class="items">
      <colgroup>{item_cols}</colgroup>
      <thead><tr>{_head_cells(vat_rate, show_desc)}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(cols)}" style="height:auto; padding:0; border:none; text-align:right;">
          <div style="position:relative; height:{QR_PRINT_PX + 62}px; margin-top:13px;" dir="ltr">
            <div style="position:absolute; left:0; top:14px; width:381px;" dir="rtl">{totals_html}</div>
            <div style="position:absolute; left:{578 - 154}px; top:0; width:308px; text-align:center;" dir="rtl">
              {qr_html}
              <div style="font-size:9.5px; line-height:11.8px; margin-top:5px;">رمز استجابة سريع معتمد حسب متطلبات هيئة الزكاة والضريبة والجمارك للفوترة الإلكترونية</div>
              <div style="font-size:9.5px; line-height:11.8px; margin-top:5px;" dir="ltr">This QR code is encoded as per ZATCA e-invoicing requirements</div>
            </div>
          </div>
          {stamp_overlay_html(data)}
        </td></tr>
      </tbody>
    </table>

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v16"]
