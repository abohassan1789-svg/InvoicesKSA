"""«النموذج الثاني والعشرون» — a replica of the plain tax invoice the user supplied
on 2026-10-20 (``barakah-raqia-template-stamped.pdf``: شركة زيادة البركة التجارية
→ مؤسسة الراقية للسبح والهدايا التجارية, BAR-2026-001/002).

A *layout* replica, like دروب الاتحاد / النماذج ١٥–٢٠: the seller block, the
buyer block, the items, the totals and the stamp all come live from the shared
``data`` dict (the selected company / customer). The source's seller ships as a
company of its own (``tools/barakah_company``) so picking it prints the PDF 1:1.

Design, measured from the A4 source with PyMuPDF. Horizontal geometry is scaled
×816/595 onto the 816×1056 Letter sheet every template prints on; vertical gaps
are scaled ×1.2 instead, because the shared QR (``QR_PRINT_PX``, house rule) is
larger than the source's and A4 is taller than Letter — that is what keeps the
source's seven items, the totals and the stamp on one page, as in the PDF.

* Header: seller name (large) + address · الرقم الضريبي · السجل التجاري on the
  right; «فاتورة ضريبية» over «TAX INVOICE» on the left with the QR beneath;
  a thin grey rule.
* «المشتري:» block (name · address · الرقم الضريبي · السجل التجاري / الموحد).
* تاريخ الإصدار / وقت الإصدار «بتوقيت السعودية» on the right, the invoice
  number alone on the left.
* Items: 6 centred columns with hairline borders and a pale header band, laid
  out left → right as the source: البند · الوصف · الكمية · الوحدة · سعر الوحدة ·
  قبل الضريبة.
* Totals: a 2-column box (value «… SAR» | label) under the table on the left,
  the grand-total row tinted; the company stamp to its right («إظهار الختم»).
* Footer on every page: «العملة: الريال السعودي | سعر الوحدة قبل الضريبة» on
  the right and the page counter «n / i» on the left.

The sheet is fixed-height and paginates through :mod:`invoice_pagination`: the
header repeats on every page, the totals + stamp always land on the last one.
The QR is ``data["qr_payload"]`` (the «مرحلة أولى» wrapper swaps in tags 1–5).
"""

from __future__ import annotations

import base64
import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.invoice_pagination import paginate, row_height, sheet_style
from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _ASSETS_DIR,
    _STAMP_FILTER,
    company_stamp_data_uri,
    qr_vector_data_uri,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Design tokens — measured from the reference PDF.
# ---------------------------------------------------------------------------
_INK = "#243442"             # every text run in the source
_GRID = "#a6adb3"            # table / totals hairlines
_BAND = "#ebf0f2"            # items header + grand-total row
_RULE = "#c7ccd1"            # the separator under the header

# Arabic in Noto Naskh Arabic, Latin + figures in a Helvetica face (the source's
# NimbusSans). Naskh ships with the app (``noto_naskh_arabic_*.woff2``, SIL OFL)
# and is embedded in the page, so the print matches the PDF without internet or
# an installed font. Arial also carries Arabic glyphs, so the Latin face is fenced
# to the Latin ranges with unicode-range; Arabic then falls through to Naskh.
_LATIN_RANGE = "U+0000-024F, U+2000-206F, U+20AC"
_FONTS = "'B22Latin','B22Naskh','Noto Naskh Arabic','Traditional Arabic','Arial',serif"
_FONT_FILES = {400: "noto_naskh_arabic_regular.woff2", 700: "noto_naskh_arabic_bold.woff2"}
_FONT_CACHE: dict[int, str] = {}


def _font_uri(weight: int) -> str:
    if weight not in _FONT_CACHE:
        try:
            raw = (_ASSETS_DIR / _FONT_FILES[weight]).read_bytes()
            _FONT_CACHE[weight] = "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")
        except OSError:
            _FONT_CACHE[weight] = ""
    return _FONT_CACHE[weight]


def _font_face_css() -> str:
    css = [
        "@font-face { font-family:'B22Latin'; src:local('Arial'), local('Helvetica'), "
        f"local('Liberation Sans'), local('Nimbus Sans'); unicode-range:{_LATIN_RANGE}; }}",
        "@font-face { font-family:'B22Latin'; font-weight:700; src:local('Arial Bold'), "
        "local('Arial-BoldMT'), local('Helvetica Bold'), local('Liberation Sans Bold'), "
        f"local('Nimbus Sans Bold'); unicode-range:{_LATIN_RANGE}; }}",
    ]
    for weight in _FONT_FILES:
        uri = _font_uri(weight)
        if uri:
            css.append(f"@font-face {{ font-family:'B22Naskh'; font-weight:{weight}; "
                       f"src:url({uri}) format('woff2'); }}")
    return "\n  ".join(css)


_SHEET_W = 816
_SHEET_H = 1056
_LEFT = 48                   # 35pt
_RIGHT = 48                  # 595 − 560pt
_CONTENT_W = _SHEET_W - _LEFT - _RIGHT   # 720 = 525pt

# Items table, physical left → right (key, title, width px).
_COLS = (
    ("no", "البند", 41),
    ("name", "الوصف", 302),
    ("qty", "الكمية", 78),
    ("unit", "الوحدة", 66),
    ("price", "سعر الوحدة", 110),
    ("before", "قبل الضريبة", 123),
)

_DESC_W = 140                # «وصف الصنف», carved out of «الوصف»

_TABLE_TOP = 545
_HEAD_H = 35
_ROW_H = 34
_TABLE_FONT = 12.3           # 9pt
_ROWS_LIMIT = 1000           # rows never run past this on any sheet
_BAND_GAP = 30               # table → totals
_TOT_ROW_H = 37
_TOT_VALUE_W = 178           # 130pt
_TOT_LABEL_W = 291           # 212pt
_STAMP_PX = 150
_STAMP_LEFT = 576            # centred on the source's 475pt
_FOOT_TOP = 1020

_ROW_BUDGET = _ROWS_LIMIT - _TABLE_TOP - _HEAD_H


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any) -> str:
    return f"{_dec(value):,.2f}"


def _qty(value: Any) -> str:
    text = format(_dec(value).normalize(), "f")
    return text if text not in ("", "-0") else "0"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def _one_line(value: Any) -> str:
    """A multi-line master-record address on one line, «… - …» like the source."""
    return " - ".join(p.strip() for p in str(value or "").splitlines() if p.strip())


def _ltr(text: str) -> str:
    return f'<bdi dir="ltr">{text}</bdi>'


def _vat_rate(lines: list[dict[str, Any]]) -> str:
    rates = {_dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    return f"{rates.pop():f}" if len(rates) == 1 else "15"


def _columns(show_unit: bool, show_desc: bool) -> list[tuple[str, str, int]]:
    """The table's columns. Without «الوحدة» its width goes to «الوصف» (the item
    name); with «إظهار وصف الصنف» a «وصف الصنف» column follows the name and
    takes part of its width."""
    cols = list(_COLS)
    if not show_unit:
        unit_w = dict((k, w) for k, _t, w in cols)["unit"]
        cols = [(k, t, w + unit_w if k == "name" else w) for k, t, w in cols if k != "unit"]
    if show_desc:
        out = []
        for k, t, w in cols:
            if k == "name":
                out += [(k, t, w - _DESC_W), ("desc", "وصف الصنف", _DESC_W)]
            else:
                out.append((k, t, w))
        cols = out
    return cols


def _row_h(line: dict[str, Any], widths: dict[str, int]) -> float:
    h = row_height(str(line.get("name") or ""), base=_ROW_H, width_px=widths["name"] - 12,
                   font_px=_TABLE_FONT, line_height=1.35, chrome=12)
    if "desc" in widths:
        h = max(h, row_height(line.get("print_description") or "", base=_ROW_H,
                              width_px=widths["desc"] - 12, font_px=_TABLE_FONT,
                              line_height=1.35, chrome=12))
    return h


def _abs(left: float, top: float, width: float, body: str, style: str = "") -> str:
    return (f'<div style="position:absolute; left:{left}px; top:{top}px; width:{width}px; '
            f'{style}">{body}</div>')


def build_invoice_html_v28(data: dict[str, Any]) -> str:
    """Build «النموذج الثاني والعشرون» from the shared invoice data dict."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))
    issued = data.get("issue_datetime")

    if isinstance(issued, (datetime.datetime, datetime.date)):
        date_text = issued.strftime("%d/%m/%Y")
    else:
        date_text = str(issued or "")
    time_text = issued.strftime("%H:%M") if isinstance(issued, datetime.datetime) else ""

    # ---------------- header (repeats on every sheet) ----------------
    right = f"right:{_RIGHT}px; text-align:right;"
    seller_lines = []
    if seller.get("address"):
        seller_lines.append(_esc(_one_line(seller.get("address"))))
    if seller.get("vat"):
        seller_lines.append(f"الرقم الضريبي: {_ltr(_esc(seller.get('vat')))}")
    if seller.get("cr"):
        seller_lines.append(f"السجل التجاري: {_ltr(_esc(seller.get('cr')))}")
    seller_html = "".join(
        f'<div style="position:absolute; {right} top:{91 + 21 * i}px; width:420px; font-size:13.7px; '
        f'line-height:20px;" dir="rtl">{text}</div>'
        for i, text in enumerate(seller_lines)
    )

    buyer_lines = [f'<b>المشتري:</b> {_esc(customer.get("name"))}']
    if customer.get("address"):
        buyer_lines.append(_esc(_one_line(customer.get("address"))))
    if customer.get("vat"):
        buyer_lines.append(f"الرقم الضريبي: {_ltr(_esc(customer.get('vat')))}")
    if customer.get("cr"):
        buyer_lines.append(f"السجل التجاري / الموحد: {_ltr(_esc(customer.get('cr')))}")
    buyer_html = "".join(
        f'<div style="position:absolute; {right} top:{343 + 22 * i}px; width:560px; font-size:15px; '
        f'line-height:22px;" dir="rtl">{text}</div>'
        for i, text in enumerate(buyer_lines)
    )

    qr_uri = qr_vector_data_uri(data.get("qr_payload"))
    qr_html = (
        f'<img src="{qr_uri}" alt="QR" style="position:absolute; left:52px; top:112px; '
        f'width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; display:block; background:#ffffff;">'
        if qr_uri else ""
    )
    rule_top = max(318, 112 + QR_PRINT_PX + 12)

    time_html = (
        f'<div style="position:absolute; {right} top:490px; width:400px; font-size:13.7px; line-height:20px;" '
        f'dir="rtl">وقت الإصدار: {_ltr(_esc(time_text))} بتوقيت السعودية</div>'
        if time_text else ""
    )
    header_html = f"""
  <div style="position:absolute; {right} top:40px; width:520px; font-size:20.6px; line-height:30px;"
       dir="rtl">{_esc(seller.get("name"))}</div>
  {seller_html}
  {_abs(98, 30, 210, "فاتورة ضريبية", "text-align:center; font-size:20.6px; line-height:30px;")}
  {_abs(98, 76, 210, "TAX INVOICE", "text-align:center; font-size:13.7px; line-height:20px;")}
  {qr_html}
  <div style="position:absolute; left:{_LEFT}px; top:{rule_top}px; width:{_CONTENT_W}px; height:0;
              border-top:1px solid {_RULE};"></div>
  {buyer_html}
  <div style="position:absolute; {right} top:468px; width:400px; font-size:13.7px; line-height:20px;"
       dir="rtl">تاريخ الإصدار: {_ltr(_esc(date_text))}</div>
  {time_html}
  {_abs(_LEFT, 468, 300, _ltr(_esc(data.get("invoice_number"))), "font-size:13.7px; line-height:20px;")}
"""

    # ---------------- items ----------------
    cols = _columns(show_unit, bool(data.get("show_description")))
    widths = {k: w for k, _t, w in cols}
    colgroup = "".join(f'<col style="width:{w}px">' for _k, _t, w in cols)
    head = "".join(f'<th style="height:{_HEAD_H}px;">{t}</th>' for _k, t, _w in cols)

    def row(line: dict[str, Any]) -> str:
        cells = {
            "no": _ltr(str(line["_no"])),
            "name": _esc(line.get("name")),
            "desc": _esc(line.get("print_description")),
            "qty": _ltr(_qty(line.get("qty"))),
            "unit": _esc(line.get("unit")),
            "price": _ltr(_money(line.get("price"))),
            "before": _ltr(_money(line.get("before"))),
        }
        return "<tr>" + "".join(f'<td class="c-{k}">{cells[k]}</td>' for k, _t, _w in cols) + "</tr>"

    numbered = [{**ln, "_no": i} for i, ln in enumerate(lines, start=1)]

    # ---------------- totals + stamp (last sheet only) ----------------
    rate = _vat_rate(lines)
    discount = _dec(totals.get("discount", 0))
    rows = [("الإجمالي قبل الضريبة", totals.get("subtotal", totals.get("taxable", 0)))]
    if discount:
        rows.append(("الخصم", -discount))
        rows.append(("الإجمالي بعد الخصم", totals.get("taxable", 0)))
    rows.append((f"ضريبة القيمة المضافة {rate}%", totals.get("vat", 0)))
    rows.append(("الإجمالي شامل الضريبة", totals.get("total", 0)))
    grand = ' class="g"'
    tot_rows = "".join(
        f'<tr{grand if i == len(rows) - 1 else ""}>'
        f'<td>{_ltr(_money(v) + " SAR")}</td><td dir="rtl">{lab}</td></tr>'
        for i, (lab, v) in enumerate(rows)
    )
    tot_h = len(rows) * _TOT_ROW_H

    stamp_uri = company_stamp_data_uri(seller) if data.get("show_stamp") else ""
    stamp_html = (
        f'<div data-company-stamp="1" style="position:absolute; left:{_STAMP_LEFT}px; top:-3px; '
        f'width:{_STAMP_PX}px; height:{_STAMP_PX}px;"><img src="{stamp_uri}" alt="stamp" '
        f'style="width:{_STAMP_PX}px; height:{_STAMP_PX}px; object-fit:contain; display:block; '
        f'filter:{_STAMP_FILTER};"></div>'
        if stamp_uri else ""
    )
    band_h = _BAND_GAP + max(tot_h, _STAMP_PX - 3 if stamp_uri else 0)
    band_html = f"""
    <div style="position:relative; margin-top:{_BAND_GAP}px; height:{band_h - _BAND_GAP}px; width:{_SHEET_W}px;">
      <table class="tot" style="position:absolute; left:{_LEFT}px; top:0;">
        <colgroup><col style="width:{_TOT_VALUE_W}px"><col style="width:{_TOT_LABEL_W}px"></colgroup>
        {tot_rows}
      </table>
      {stamp_html}
    </div>"""

    pages = paginate(
        numbered, lambda ln: _row_h(ln, widths),
        budget=_ROW_BUDGET, budget_last=_ROW_BUDGET - band_h,
    )
    count = len(pages)
    sheets = []
    for index, page_lines in enumerate(pages, start=1):
        last = index == count
        body = "".join(row(ln) for ln in page_lines)
        if not numbered and last:
            body = f'<tr><td colspan="{len(cols)}" style="color:#8a949c;">لا توجد أصناف</td></tr>'
        sheets.append(f"""
<div data-sheet class="sheet" style="{sheet_style(last=last)}">
{header_html}
  <div style="position:absolute; left:0; top:{_TABLE_TOP}px; width:{_SHEET_W}px;">
    <table class="items" style="margin-left:{_LEFT}px;">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>
{band_html if last else ""}
  </div>
  <div style="position:absolute; {right} top:{_FOOT_TOP}px; width:520px; font-size:11px; line-height:16px;"
       dir="rtl">العملة: الريال السعودي | سعر الوحدة قبل الضريبة</div>
  {_abs(110, _FOOT_TOP, 80, _ltr(f"{count} / {index}"), "font-size:11px; line-height:16px;")}
</div>""")

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_FONTS}; color:{_INK};
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ position:relative; box-sizing:border-box; width:{_SHEET_W}px; height:{_SHEET_H}px;
            margin:24px auto; background:#ffffff; overflow:hidden; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  td, th {{ box-sizing:border-box; }}
  .items {{ width:{_CONTENT_W}px; table-layout:fixed; direction:ltr; }}
  .items th {{ background:{_BAND}; font-weight:400; font-size:{_TABLE_FONT}px; border:1px solid {_GRID};
               text-align:center; vertical-align:middle; padding:0 4px; white-space:nowrap; }}
  .items td {{ height:{_ROW_H}px; font-size:{_TABLE_FONT}px; border:1px solid {_GRID}; text-align:center;
               vertical-align:middle; padding:5px 6px; line-height:1.35;
               overflow-wrap:anywhere; word-break:break-word; }}
  .items td.c-name, .items td.c-desc {{ direction:rtl; }}
  .tot {{ table-layout:fixed; width:{_TOT_VALUE_W + _TOT_LABEL_W}px; direction:ltr; }}
  .tot td {{ height:{_TOT_ROW_H}px; border:1px solid {_GRID}; text-align:center; vertical-align:middle;
             font-size:{_TABLE_FONT}px; padding:0 6px; }}
  .tot tr.g td {{ background:{_BAND}; }}
  @page {{ size:Letter; margin:0; }}
  @media print {{
    body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; }}
  }}
</style>
</head>
<body>
{"".join(sheets)}
</body>
</html>"""


__all__ = ["build_invoice_html_v28"]
