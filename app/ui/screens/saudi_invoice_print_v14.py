"""«نموذج أطياف» — an exact replica of the «نهلة الخليج التجارية» tax invoice the
user supplied (``اطياف 7.pdf``, invoice 2026-6611 issued to شركة اطياف القمة
التجارية).

Fixed-brand, like المتكاملة/الإسناد الماسي/اقاسيم/مواسم الفاكهة: the blue seller
header (name/CR/VAT + logo) and the blue address footer are the source PDF's own
rasters, extracted 1:1 with PyMuPDF into ``atyaf_header.png`` / ``atyaf_footer.png``.
The selected company is ignored (user request 2026-10-05: «نفس البائع من فوق ...
الـ header والـ footer هيبقوا ثابتين»). Both are pinned to EVERY printed page:
``position:fixed`` boxes in print (Chromium paints them on each page), with the
outer ``.page`` table's repeating ``<thead>``/``<tfoot>`` spacers reserving their
height so the content never runs under them.

Everything between them is live from the shared ``data`` dict: the customer/
invoice info grid, the 8-column items table, the totals block, the Arabic
amount-in-words and the QR. Offered on the Phase-1 (المرحلة الأولى) picker via
``build_phase1_invoice_atyaf``, which swaps in the tags 1–5 QR.

Geometry measured from the A4 source (595pt wide) and scaled ×816/595 onto the
816×1056 Letter sheet every template prints on; the source's content ends at
744pt (1020px), so it fits Letter with no vertical squeeze.

Field notes:
* «No.» and «SKU» both print the item code — the source repeats it in both.
* «Qty» prints the quantity with 2 decimals and the unit name beneath it.
* «Invoice Type» = مدفوع for a cash invoice, آجل otherwise; «Paid By» = نقدا / آجل.
* «Mobile» — the shared data model carries no customer phone, so it prints the
  source's «0» unless a ``phone``/``mobile`` key is supplied.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _asset_data_uri,
    _clean_ar_words,
    qr_vector_data_uri,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — measured from the reference PDF.
# ---------------------------------------------------------------------------
_INK = "#000000"
_BORDER = "#242424"          # table / grid rules
_GRID_SOFT = "#a9a9a9"       # the info grid's inner horizontal rules
_RULE = "#555555"            # the two full-width separators (under header / above footer)
_HEAD_BG = "#5F8DBD"         # items-table header band (white bold text)
_BEIGE = "#F5E6D7"           # totals / amount-in-words cells
_FONTS = "'Arial','Tahoma','Segoe UI',sans-serif"

_SHEET_W = 816
_SHEET_H = 1056
_SIDE = 38.5                 # 28.5pt left/right margin → px
_CONTENT_W = 739             # 538.5pt → px

_HEADER_ASSET = "atyaf_header.png"
_FOOTER_ASSET = "atyaf_footer.png"

# Vertical reservations for the fixed header/footer on every page (px).
_HEADER_RESERVE = 180        # header image 40→151 + rule at 171
_FOOTER_RESERVE = 122        # rule at 943 → page bottom 1056, plus a small gap

# Info-grid column widths, physical left -> right (EN label | value | AR label, x2).
_INFO_COLS = (90, 210, 89, 106, 166, 78)

# Items-table columns, physical left → right (the table is LTR like the source).
_ITEM_COLS = (
    ("No.", "الرقم", 65),
    ("SKU", "الرمز", 64),
    ("Description البيان", "", 164),
    ("Qty", "الكمية", 65),
    ("U.Price", "سعر الوحدة", 78),
    ("T.Price", "سعر الاجمالي", 91),
    ("VAT15%", "الضريبة", 80),
    ("Total with Vat", "اجمالي مع ضريبة", 132),
)
# With «إظهار وصف الصنف»: «وصف الصنف» right after the name; same 739px total.
_ITEM_COLS_DESC = (
    ("No.", "الرقم", 50),
    ("SKU", "الرمز", 56),
    ("Description البيان", "", 100),
    ("Item Description", "وصف الصنف", 140),
    ("Qty", "الكمية", 55),
    ("U.Price", "سعر الوحدة", 68),
    ("T.Price", "سعر الاجمالي", 80),
    ("VAT15%", "الضريبة", 68),
    ("Total with Vat", "اجمالي مع ضريبة", 122),
)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _plain(value: Any) -> str:
    """Table figures: 2 decimals, no thousands separator (``4320.00``)."""
    return f"{_dec(value):.2f}"


def _money(value: Any) -> str:
    """Totals figures: 2 decimals with thousands separators (``28,420.00``)."""
    return f"{_dec(value):,.2f}"


def amount_in_words_atyaf(total: Any) -> str:
    """The source's wording: «اثنان وثلاثون ألفاً وستمائة وثلاثة وثمانون ريالا»
    (no «فقط … لا غير»), with «و … هللة» appended when there are halalas."""
    amount = _dec(total).quantize(Decimal("0.01"))
    riyals = int(amount)
    halalas = int((amount - riyals) * 100)
    try:
        from num2words import num2words

        words = f"{_clean_ar_words(num2words(riyals, lang='ar'))} ريالا"
        if halalas:
            words += f" و{_clean_ar_words(num2words(halalas, lang='ar'))} هللة"
    except Exception:  # noqa: BLE001 - fall back to digits if the lib misbehaves
        words = f"{amount} ريالا"
    return words


def _fmt_datetime(issued: Any) -> str:
    """``17/06/2026 04:31 PM`` like the source; raw string otherwise."""
    if isinstance(issued, datetime.datetime):
        return issued.strftime("%d/%m/%Y %I:%M %p")
    if isinstance(issued, datetime.date):
        return issued.strftime("%d/%m/%Y")
    return str(issued or "")


def _is_credit(payment_label: str) -> bool:
    return "آجل" in payment_label or "credit" in payment_label.lower()


def _info_row(cells: tuple[str, str, str, str, str, str], *, first: bool, last: bool) -> str:
    """One row of the info grid: EN label | value | AR label ‖ EN label | value | AR label.

    Outer box + the central divider are dark; the rules between rows are soft grey,
    except the grid's bottom edge, which is dark — exactly as drawn in the source (the
    soft rules are dashed)."""
    top = f"1px solid {_BORDER}" if first else "none"
    bottom = f"1px solid {_BORDER}" if last else f"1px dashed {_GRID_SOFT}"
    base = (
        f"border-top:{top}; border-bottom:{bottom}; padding:0 3px; height:17px; "
        "font-size:11.6px; text-align:center; vertical-align:middle; white-space:nowrap; "
        "overflow:hidden;"
    )
    edge_l = f"border-left:1px solid {_BORDER};"
    edge_r = f"border-right:1px solid {_BORDER};"
    styles = (edge_l, "", edge_r, "", "", edge_r)
    tds = []
    for i, (text, extra) in enumerate(zip(cells, styles)):
        dir_attr = ' dir="rtl"' if i in (2, 5) else ""
        tds.append(f'<td style="{base} {extra}"{dir_attr}>{text}</td>')
    return "<tr>" + "".join(tds) + "</tr>"


def _head_cells(show_desc: bool = False) -> str:
    th = (
        f"background:{_HEAD_BG}; color:#ffffff; font-weight:700; font-size:11.6px; "
        f"border:1px solid {_BORDER}; text-align:center; vertical-align:middle; "
        "padding:1px 2px; height:33px; line-height:1.3;"
    )
    cells = []
    for en, ar, _w in (_ITEM_COLS_DESC if show_desc else _ITEM_COLS):
        body = f"{en}<br>{ar}" if ar else en
        cells.append(f'<th style="{th}">{body}</th>')
    return "".join(cells)


_TD = (
    f"border:1px solid {_BORDER}; text-align:center; vertical-align:middle; "
    "font-size:11.6px; padding:1px 3px; height:32px; line-height:1.3; "
    "overflow-wrap:anywhere; word-break:break-word;"
)


def _item_row(line: dict[str, Any], show_unit: bool, show_desc: bool = False) -> str:
    code = html.escape(str(line.get("code") or ""))
    name = html.escape(str(line.get("name") or ""))
    unit = html.escape(str(line.get("unit") or "")) if show_unit else ""
    qty = _plain(line.get("qty"))
    qty_cell = f"{qty}<br>{unit}" if unit else qty
    desc_td = (
        f'<td style="{_TD}" dir="rtl">{html.escape(line.get("print_description") or "")}</td>' if show_desc else ""
    )
    return (
        "<tr>"
        f'<td style="{_TD}"><bdi dir="ltr">{code}</bdi></td>'
        f'<td style="{_TD}"><bdi dir="ltr">{code}</bdi></td>'
        f'<td style="{_TD}" dir="rtl">{name}</td>'
        f'{desc_td}'
        f'<td style="{_TD}">{qty_cell}</td>'
        f'<td style="{_TD}">{_plain(line.get("price"))}</td>'
        f'<td style="{_TD}">{_plain(line.get("before"))}</td>'
        f'<td style="{_TD}">{_plain(line.get("vat_amount"))}</td>'
        f'<td style="{_TD}">{_plain(line.get("total"))}</td>'
        "</tr>"
    )


def _totals_block(taxable: Any, vat_total: Any, grand_total: Any, vat_label: str,
                  notes: str) -> str:
    """The 3×3 totals grid: notes / words on the left, beige labels + values right."""
    cell = f"border:1px solid {_BORDER}; font-size:11.6px; vertical-align:middle;"
    label = f"{cell} background:{_BEIGE}; text-align:right; padding:0 6px;"
    value = f"{cell} background:{_BEIGE}; text-align:center; padding:0 4px;"
    words = html.escape(amount_in_words_atyaf(grand_total))

    def val(amount: Any) -> str:
        return f'<span dir="ltr">{_money(amount)} ريال</span>'

    return f"""
      <table style="width:{_CONTENT_W}px; border-collapse:collapse; table-layout:fixed; direction:ltr;">
        <colgroup><col style="width:338px"><col style="width:258px"><col style="width:143px"></colgroup>
        <tr style="height:30px;">
          <td style="{cell} text-align:center;" dir="rtl">Note ملاحظات{('<br>' + notes) if notes else ''}</td>
          <td style="{label}" dir="ltr">Total Before VAT&nbsp;&nbsp;&nbsp;الاجمالي قبل الضريبة</td>
          <td style="{value}">{val(taxable)}</td>
        </tr>
        <tr style="height:29px;">
          <td style="{cell}"></td>
          <td style="{label}" dir="ltr">{vat_label} الضريبة</td>
          <td style="{value}">{val(vat_total)}</td>
        </tr>
        <tr style="height:34px;">
          <td style="{cell} background:{_BEIGE}; text-align:center; line-height:1.4;" dir="rtl">
            <span dir="ltr">in words المبلغ كتابة</span><br>{words}</td>
          <td style="{label}" dir="ltr">Grand Total المبلغ الإجمالي</td>
          <td style="{value}">{val(grand_total)}</td>
        </tr>
      </table>"""


def build_invoice_html_v14(data: dict[str, Any]) -> str:
    """Build «نموذج أطياف» from the shared invoice data dict."""
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issued = html.escape(_fmt_datetime(data.get("issue_datetime")))
    payment_label = str(data.get("payment_label") or "")
    credit = _is_credit(payment_label)
    invoice_type = "آجل" if credit else "مدفوع"
    paid_by = "آجل" if credit else "نقدا"
    notes = html.escape(str(data.get("notes") or ""))

    cust_name = html.escape(str(customer.get("name") or ""))
    cust_vat = html.escape(str(customer.get("vat") or ""))
    cust_mobile = html.escape(str(customer.get("phone") or customer.get("mobile") or "0"))
    cust_addr = html.escape(str(customer.get("address") or ""))

    taxable = totals.get("taxable", totals.get("subtotal", 0))
    vat_total = totals.get("vat", 0)
    grand_total = totals.get("total", 0)

    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    rate = f"{rates.pop():f}" if len(rates) == 1 else "15"
    vat_label = f"VAT {rate}%"

    header = _asset_data_uri(_HEADER_ASSET)
    footer = _asset_data_uri(_FOOTER_ASSET)
    qr = qr_vector_data_uri(data.get("qr_payload"))
    qr_img = (
        f'<img src="{qr}" alt="QR" style="width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        'display:block; background:#ffffff;">'
        if qr
        else ""
    )

    info_rows = (
        ("Customer :", cust_name, "العميـــل :", "Invoice No:", invoice_number, "رقم الفاتورة :"),
        ("VAT No:", cust_vat, "الرقم الضريبي :", "Date :", issued, "التاريخ :"),
        ("Mobile :", cust_mobile, "الجوال :", "Invoice Type :", invoice_type, "نوع الفاتورة :"),
        ("Address:", cust_addr, "العنوان :", "Paid By:", paid_by, "طريقة الدفع :"),
    )
    info_cols = "".join(f'<col style="width:{w}px">' for w in _INFO_COLS)
    info_html = "".join(
        _info_row(row, first=i == 0, last=i == len(info_rows) - 1)
        for i, row in enumerate(info_rows)
    )

    # The closing block (last item + totals + signature + QR) is one no-break
    # <tbody>: when it cannot fit at the foot of a page it moves on TOGETHER with
    # at least one item, so the totals never strand alone on a page.
    show_desc = bool(data.get("show_description"))
    item_cols = _ITEM_COLS_DESC if show_desc else _ITEM_COLS
    if lines:
        main_rows = "".join(_item_row(ln, show_unit, show_desc) for ln in lines[:-1])
        last_row = _item_row(lines[-1], show_unit, show_desc)
    else:
        main_rows = ""
        last_row = (
            f'<tr><td colspan="{len(item_cols)}" style="{_TD} color:#888;">لا توجد أصناف</td></tr>'
        )
    colgroup = "".join(f'<col style="width:{w}px">' for _en, _ar, w in item_cols)

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK};
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ position:relative; box-sizing:border-box; width:{_SHEET_W}px; min-height:{_SHEET_H}px;
            margin:24px auto; background:#ffffff; padding:0 {_SIDE}px;
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  tfoot {{ display:table-footer-group; }}
  .page {{ width:{_CONTENT_W}px; table-layout:fixed; }}
  .page > tbody > tr > td, .page > thead > tr > td, .page > tfoot > tr > td {{ padding:0; vertical-align:top; }}
  .summary {{ break-inside:avoid; page-break-inside:avoid; }}
  /* Fixed brand header / footer. On screen they sit at the sheet's top/bottom;
     in print they are position:fixed, so Chromium paints them on EVERY page. */
  .phead, .pfoot {{ position:absolute; left:0; width:{_SHEET_W}px; }}
  .phead {{ top:0; height:{_HEADER_RESERVE}px; }}
  .pfoot {{ bottom:0; height:{_FOOTER_RESERVE}px; }}
  @page {{ size:Letter; margin:0; }}
  @media print {{
    body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
    .phead, .pfoot {{ position:fixed; }}
  }}
</style>
</head>
<body>
  <div class="sheet">
  <div class="phead">
    <img src="{header}" alt="header" style="position:absolute; left:39px; top:40px; width:739px; height:111px; display:block;">
    <div style="position:absolute; left:39px; top:170px; width:740px; height:1px; background:{_RULE};"></div>
  </div>

  <table class="page">
    <thead><tr><td style="height:{_HEADER_RESERVE}px;"></td></tr></thead>
    <tfoot><tr><td style="height:{_FOOTER_RESERVE}px;"></td></tr></tfoot>
    <tbody><tr><td>

    <!-- ===== TITLE ===== -->
    <div dir="ltr" style="text-align:center; font-size:23px; line-height:1; margin-top:30px; height:26px;">فاتورة ضريبية TAX INVOICE</div>

    <!-- ===== CUSTOMER / INVOICE INFO ===== -->
    <table style="width:{_CONTENT_W}px; table-layout:fixed; margin-top:9px; direction:ltr;">
      <colgroup>{info_cols}</colgroup>
      {info_html}
    </table>

    <!-- ===== ITEMS + CLOSING BLOCK (LTR like the source: No. on the left) ===== -->
    <table style="width:{_CONTENT_W}px; table-layout:fixed; direction:ltr;">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{_head_cells(show_desc)}</tr></thead>
      <tbody>{main_rows}</tbody>
      <tbody class="summary">
        {last_row}
        <tr><td colspan="{len(item_cols)}" style="padding:0; border:none;">
          {_totals_block(taxable, vat_total, grand_total, vat_label, notes)}
          <div style="position:relative; height:{QR_PRINT_PX + 8}px; margin-top:2px;">
            <div style="position:absolute; left:113px; width:100px; top:2px; text-align:center;
                        font-size:13.5px;" dir="rtl">المدير العام</div>
            <div style="position:absolute; left:{576 - QR_PRINT_PX // 2}px; top:4px;">{qr_img}</div>
          </div>
        </td></tr>
      </tbody>
    </table>

    </td></tr></tbody>
  </table>

  <div class="pfoot">
    <div style="position:absolute; left:24px; top:9px; width:769px; height:1px; background:{_RULE};"></div>
    <img src="{footer}" alt="footer" style="position:absolute; left:39px; top:29px; width:739px; height:57px; display:block;">
  </div>
  </div>
</body>
</html>"""


__all__ = ["build_invoice_html_v14", "amount_in_words_atyaf"]
