"""«ثمار اليرموك» — a replica of the tax invoice the user supplied on 2026-10-22
(``4_5951665430518046570_261017_094037.pdf``: شركة ثمار اليرموك → شركة نورة حزام
سعيد الثبيتى للتجارة, INV/2026/00762, one A4 page printed from Odoo).

A *layout* replica, like «أفنان جيزان» (v29) and «بنشر» (v30): the seller (name,
address, VAT, CR, logo), the buyer («العميل | Bill to»), the items, the totals,
the QR and the stamp come live from the shared ``data`` dict.

What the program has no data for, and how it prints:

* «تاريخ الاستحقاق» and «تاريخ التوريد» print the invoice date, as the source does
  for a same-day invoice;
* «Paid on …» prints for a cash invoice only (paid in full on the invoice date, so
  «Amount Due» is 0.00); a credit invoice prints no «Paid» row and its whole total
  as «Amount Due»;
* «التواصل بشأن الدفع | Payment Communication» carries the invoice number; the
  account line under it («في هذا الحساب | on this account: … - مصرف الراجحى») is
  fixed text, the source's IBAN and bank (user 2026-10-22);
* a discount, which the source has no row for, adds «Discount | الخصم» to the
  totals box only when there is one;
* the buyer's CR (which the source does not print) is a line of its own above the
  VAT line when stored.

Geometry, measured from the A4 source with PyMuPDF, is kept in source points and
scaled ×1056/841.89 onto the 816×1056 Letter sheet (the whole A4 page, centred),
as «بنشر» does. The QR is the shared ``QR_PRINT_PX`` (the source's is smaller);
the totals band follows the last row, as in the source, and moves to a page of
its own when the rows leave no room for it (:mod:`invoice_pagination`).

Fonts as the source: Cairo (Arabic and Latin, SIL OFL, bundled as
``cairo_{arabic,latin}_{400,600,700}.woff2`` from Fontsource) for everything but
the items-table head, which the source sets in DejaVu Sans (Arabic, bundled
subset ``dejavu_sans_arabic.woff2``) and Helvetica (Latin → Arial / Liberation
Sans). The riyal sign is the bundled ``riyal_symbol.png``.
"""

from __future__ import annotations

import base64
import datetime
import html
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.ui.screens.invoice_pagination import paginate, row_height, sheet_style
from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _ASSETS_DIR,
    _STAMP_FILTER,
    company_logo_data_uri,
    company_stamp_data_uri,
    qr_vector_data_uri,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Geometry — source points (A4, 595.28 × 841.89), scaled onto the Letter sheet.
# ---------------------------------------------------------------------------
_SHEET_W = 816
_SHEET_H = 1056
_SCALE = _SHEET_H / 841.89
_OFF_X = round((_SHEET_W - 595.276 * _SCALE) / 2, 2)


def _p(pt: float) -> float:
    """A length in source points → sheet px."""
    return round(pt * _SCALE, 2)


def _x(pt: float) -> float:
    return round(_OFF_X + pt * _SCALE, 2)


_BROWN = "#453223"           # title, info-table frame, totals frame
_INK = "#20272a"
_GREY = "#596467"            # address lines, info captions
_GREEN = "#245b49"           # «العميل | Bill to»
_BODY = "#212529"
_HEAD = "#202326"
_SOFT = "#d9dedc"            # info-table inner rules, totals row rules
_FRAME = "#98a2a0"           # items-table frame
_HEAD_RULE = "#7f8a88"       # under the items head
_COL_RULE = "#b9c2bf"        # items column rules
_GROSS = "#f0efee"           # «Invoice Gross Total» row
_HAIR = 0.6                  # the source's rule width, pt

_LEFT, _RIGHT = 9.6, 585.1   # the content frame

# Items table: column edges (physical left → right) and head / row heights.
_COLS = (
    ("desc", "وصف السلعة او الخدمة", "Description", 226.9),
    ("qty", "الكمية", "Quantity", 265.3),
    ("price", "سعر الوحدة", "Unit Price", 313.3),
    ("rate", "معدل الضريبة", "Taxes", 367.3),
    ("vat", "مبلغ الضريبة", "VAT Amount", 421.3),
    ("before", "الإجمالي قبل الضريبة", "Total Excl. VAT", 499.3),
    ("total", "الإجمالي شامل الضريبة", "Total Incl. VAT", 585.1),
)
_ITEMS_TOP = 219.2
_HEAD_H = 33.0
_ROW = 22.8
_LINE = 7.8 * 1.874          # one Cairo line at the row's 7.8pt (Cairo's own line box)
_PRINT_DESC_W = 70.0         # «وصف الصنف», carved out of «Description» when ticked

# Totals band: the box, the QR, the payment line and the stamp under the rows.
_BAND_GAP = 6.6
_BOX_L = 234.7
_BOX_PAD = 4.8               # frame → first row
_BOX_ROW = 16.2
_PAY_GAP = 22.3              # box bottom → payment line
_PAY_H = 32.4               # two lines, 14.4 apart
_ACCOUNT_IBAN = "SA2080000510608010699851"
_ACCOUNT_BANK = "مصرف الراجحى"
_STAMP_H = 70.0
_QR_PT = QR_PRINT_PX / _SCALE
_PAGE_BOT = 780.0            # rows never run past this on any page

_COUNTRY_RE = re.compile(r"(المملكة\s+العربية\s+السعودية|السعودية|saudi\s+arabia|\bksa\b)", re.IGNORECASE)
_SPLIT_RE = re.compile(r"\s*(?:\n|،|,|\s-\s|\s–\s)\s*")

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
_CAIRO_AR = ("U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0898-08E1,U+08E3-08FF,"
             "U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FE74,U+FE76-FEFC")
_CAIRO_LAT = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,"
              "U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")
_FONT_CACHE: dict[str, str] = {}

CAIRO = "'Cairo31','Arial','AJNaskh',sans-serif"
DEJAVU = "'DejaVu31','DejaVu Sans','Arial',sans-serif"
_HELV = "'Arial','Liberation Sans','Helvetica',sans-serif"


def _font_uri(name: str) -> str:
    if name not in _FONT_CACHE:
        try:
            raw = (_ASSETS_DIR / name).read_bytes()
            _FONT_CACHE[name] = "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")
        except OSError:
            _FONT_CACHE[name] = ""
    return _FONT_CACHE[name]


def font_face_css() -> str:
    """``@font-face`` rules for Cairo (400/600/700, Arabic + Latin) and the DejaVu
    Sans Arabic subset, embedded so printing needs no internet. Shared with the
    «ثمار اليرموك» customer statement (النموذج الرابع والعشرون)."""
    css = []
    for weight in (400, 600, 700):
        for sub, rng in (("arabic", _CAIRO_AR), ("latin", _CAIRO_LAT)):
            uri = _font_uri(f"cairo_{sub}_{weight}.woff2")
            if uri:
                css.append(f"@font-face {{ font-family:'Cairo31'; font-weight:{weight}; "
                           f"src:url({uri}) format('woff2'); unicode-range:{rng}; }}")
    uri = _font_uri("dejavu_sans_arabic.woff2")
    if uri:
        css.append(f"@font-face {{ font-family:'DejaVu31'; src:url({uri}) format('woff2'); }}")
    for weight, name in ((400, "noto_naskh_arabic_regular.woff2"), (700, "noto_naskh_arabic_bold.woff2")):
        uri = _font_uri(name)
        if uri:
            css.append(f"@font-face {{ font-family:'AJNaskh'; font-weight:{weight}; "
                       f"src:url({uri}) format('woff2'); }}")
    return "\n  ".join(css)


def _riyal() -> str:
    if "riyal" not in _FONT_CACHE:
        try:
            raw = (_ASSETS_DIR / "riyal_symbol.png").read_bytes()
            _FONT_CACHE["riyal"] = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        except OSError:
            _FONT_CACHE["riyal"] = ""
    return _FONT_CACHE["riyal"]


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _num(value: Any) -> str:
    return f"{_dec(value).quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}"


def _sar(value: Any) -> str:
    """«⃁ 1,936.00» — the riyal sign left of the figure, as the source."""
    uri = _riyal()
    sign = f'<img class="sar" src="{uri}" alt="SAR">' if uri else "SAR"
    return f'<span class="money">{sign}&nbsp;{_num(value)}</span>'


def _rate(value: Any) -> str:
    rate = _dec(value if value not in (None, "") else 15).normalize()
    return f"{rate:f}%"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def _date(value: Any) -> str:
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value or "")[:10]


def address_lines(text: Any, limit: int) -> list[str]:
    """A free-text address as the source's stacked lines: its own lines, else its
    «،» / «,» / « - » parts; parts past ``limit`` join the last line. The country
    is left out (the templates print it on a line of their own)."""
    raw = _COUNTRY_RE.sub(" ", str(text or ""))
    parts = [p.strip(" -–،,") for p in _SPLIT_RE.split(raw)]
    parts = [re.sub(r"\s+", " ", p) for p in parts if p.strip(" -–،,")]
    if limit <= 0:
        return []
    if len(parts) > limit:
        parts = parts[:limit - 1] + ["، ".join(parts[limit - 1:])]
    return parts


def _is_cash(data: dict[str, Any]) -> bool:
    label = str(data.get("payment_label") or data.get("payment_type") or "").lower()
    return "نقد" in label or "cash" in label


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
def _box(left: float, top: float, width: float, height: float, body: str = "", style: str = "") -> str:
    return (f'<div style="position:absolute; left:{_x(left)}px; top:{_p(top)}px; width:{_p(width)}px; '
            f'height:{_p(height)}px; {style}">{body}</div>')


def _text(right: float | None, top: float, size: float, color: str, body: str, *, weight: int = 400,
          left: float | None = None, width: float = 300.0, align: str = "right", rtl: bool = True,
          extra: str = "") -> str:
    """One absolutely placed line, its box top at the source's text-box top
    (Cairo's own line height, so the glyphs land where the source's do)."""
    if left is None:
        left = (right or 0) - width
    direction = "direction:rtl;" if rtl else "direction:ltr;"
    return (f'<div style="position:absolute; left:{_x(left)}px; top:{_p(top)}px; width:{_p(width)}px; '
            f'{direction} text-align:{align}; font-size:{_p(size)}px; font-weight:{weight}; color:{color}; '
            f'white-space:nowrap; overflow:hidden; {extra}">{body}</div>')


def _header_html(data: dict[str, Any]) -> str:
    seller = data.get("seller") or {}
    out = []
    logo = company_logo_data_uri(seller)
    if logo:
        out.append(_box(512.0, 50.0, 52.0, 45.6,
                        f'<img src="{logo}" alt="logo" style="width:100%; height:100%; object-fit:contain; '
                        'display:block;">'))
    out.append(_text(494.6, 35.4, 14.4, _INK, _esc(seller.get("name")), weight=600, width=330))
    lines = address_lines(seller.get("address"), 4) + ["Saudi Arabia"]
    for i, line in enumerate(lines):
        out.append(_text(494.0, 54.8 + 9.6 * i, 7.8, _GREY, f"<bdi>{_esc(line)}</bdi>", width=300))

    # Title block, centred on x = 111.
    out.append(_text(None, 48.6, 14.4, _BROWN, "فاتورة ضريبية", weight=600, left=11, width=200, align="center"))
    out.append(_text(None, 66.8, 7.8, "#697276", "TAX INVOICE", left=11, width=200, align="center", rtl=False))
    out.append(_text(None, 75.5, 10.8, _INK, _esc(data.get("invoice_number")), weight=600, left=11, width=200,
                     align="center", rtl=False))

    # Info strip: VAT | CR | Invoice Date | Due date | Supply Date, right → left.
    day = _esc(_date(data.get("issue_datetime")))
    cells = (
        ("الرقم الضريبي | VAT", _esc(seller.get("vat"))),
        ("السجل التجاري | CR", _esc(seller.get("cr"))),
        ("تاريخ فاتورة العميل | Invoice Date", day),
        ("تاريخ الاستحقاق | Due date", day),
        ("تاريخ التوريد | Supply Date", day),
    )
    w = (_RIGHT - _LEFT) / 5
    tds = "".join(
        f'<td><div class="cap">{cap}</div><div class="val"><bdi>{val}</bdi></div></td>'
        for cap, val in reversed(cells)
    )
    out.append(f'<table class="info" style="left:{_x(_LEFT)}px; top:{_p(109.4)}px; width:{_p(_RIGHT - _LEFT)}px; '
               f'height:{_p(23.4)}px;"><colgroup>' + f'<col style="width:{_p(w)}px">' * 5
               + f"</colgroup><tr>{tds}</tr></table>")

    # «العميل | Bill to»: name, address lines, country, [CR], VAT.
    customer = data.get("customer") or {}
    cr = customer.get("cr") or customer.get("commercial_registration")
    out.append(_text(580.8, 132.8, 7.8, _GREEN, "العميل | Bill to", weight=600, width=200))
    out.append(_text(580.0, 141.1, 10.2, _INK, _esc(customer.get("name")), weight=500, width=420))
    blines = [f"<bdi>{_esc(t)}</bdi>" for t in address_lines(customer.get("address"), 3 if cr else 4)]
    blines.append("Saudi Arabia")
    if cr:
        blines.append(f'السجل التجاري | <bdi dir="ltr">CR {_esc(cr)}</bdi>')
    if customer.get("vat"):
        blines.append(f'الرقم الضريبي | <bdi dir="ltr">VAT {_esc(customer.get("vat"))}</bdi>')
    for i, line in enumerate(blines):
        out.append(_text(580.8, 153.8 + 9.6 * i, 7.8, _GREY, line, width=420))
    return "".join(out)


def _columns(show_desc: bool) -> list[tuple[str, str, str, float]]:
    out: list[tuple[str, str, str, float]] = []
    left = _LEFT
    for key, ar, en, right in _COLS:
        width = right - left
        left = right
        if key == "desc" and show_desc:
            out += [(key, ar, en, width - _PRINT_DESC_W), ("pdesc", "وصف الصنف", "Item Note", _PRINT_DESC_W)]
        else:
            out.append((key, ar, en, width))
    return out


def _item_label(line: dict[str, Any]) -> str:
    code = str(line.get("code") or "").strip()
    name = _esc(line.get("name"))
    return f"[{_esc(code)}] <bdi>{name}</bdi>" if code else f"<bdi>{name}</bdi>"


def _row_h(line: dict[str, Any], widths: dict[str, float]) -> float:
    """Row height in pt: a long name wraps and grows the row (house rule)."""
    label = (f"[{line.get('code')}] " if line.get("code") else "") + str(line.get("name") or "")
    px = row_height(label, base=_p(_ROW), width_px=_p(widths["desc"] - 11), font_px=_p(7.8),
                    line_height=1.874, chrome=_p(_ROW - _LINE))
    if "pdesc" in widths:
        px = max(px, row_height(str(line.get("print_description") or ""), base=_p(_ROW),
                                width_px=_p(widths["pdesc"] - 10), font_px=_p(7.0), line_height=1.874,
                                chrome=_p(_ROW - _LINE)))
    return px / _SCALE


def _totals_rows(data: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(css class, caption, amount html) for the totals box."""
    totals = data.get("totals") or {}
    total = _dec(totals.get("total"))
    rows: list[tuple[str, str, str]] = []
    if _dec(totals.get("discount")):
        rows.append(("", "Discount | الخصم", _sar(totals.get("discount"))))
    rows += [
        ("", "Invoice Taxable Amount | المبلغ الخاضع للضريبة",
         _sar(totals.get("taxable", totals.get("subtotal", 0)))),
        ("", "VAT Total Amount | إجمالي ضريبة القيمة المضافة", _sar(totals.get("vat", 0))),
        ("gross", "Invoice Gross Total (Inclusive of VAT) | إجمالي قيمة الفاتورة (شامل ضريبة القيمة المضافة)",
         _sar(total)),
    ]
    paid = total if _is_cash(data) else Decimal("0")
    if paid:
        rows.append(("paid", f"Paid on {_esc(_date(data.get('issue_datetime')))}", _sar(paid)))
    rows.append(("due", "Amount Due", _sar(total - paid)))
    return rows


def _band_height(data: dict[str, Any]) -> float:
    box = 2 * _BOX_PAD + len(_totals_rows(data)) * _BOX_ROW + 4.8
    stamp = _STAMP_H + 6 if data.get("show_stamp") and company_stamp_data_uri(data.get("seller") or {}) else 0
    return _BAND_GAP + max(_QR_PT, box + _PAY_GAP + _PAY_H + stamp)


def _band_html(data: dict[str, Any], top: float) -> str:
    """QR (left) · totals box (right) · payment line · stamp, from ``top`` down."""
    top += _BAND_GAP
    out = []
    qr_uri = qr_vector_data_uri(data.get("qr_payload"))
    if qr_uri:
        out.append(f'<img src="{qr_uri}" alt="QR" style="position:absolute; left:{_x(13.0)}px; top:{_p(top)}px; '
                   f'width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; display:block; background:#ffffff;">')
    rows = _totals_rows(data)
    box_h = 2 * _BOX_PAD + len(rows) * _BOX_ROW + 4.8
    trs = "".join(f'<tr class="{cls}" style="height:{_p(_BOX_ROW)}px;"><td class="c">{cap}</td>'
                  f'<td class="a">{amt}</td></tr>' for cls, cap, amt in rows)
    out.append(_box(_BOX_L, top, _RIGHT - _BOX_L, box_h,
                    f'<table class="tot"><colgroup><col><col style="width:{_p(60)}px"></colgroup>{trs}</table>',
                    f"box-sizing:border-box; border:{_p(_HAIR)}px solid {_BROWN}; "
                    f"padding:{_p(_BOX_PAD)}px {_p(5.4)}px;"))
    pay_top = top + box_h + _PAY_GAP
    out.append(_text(_RIGHT, pay_top, 9.6, _HEAD,
                     'التواصل بشأن الدفع | <span dir="ltr">Payment Communication: '
                     f'<b>{_esc(data.get("invoice_number"))}</b></span>', width=420))
    out.append(_text(_RIGHT, pay_top + 14.4, 9.6, _HEAD,
                     f'في هذا الحساب | <span dir="ltr">on this account: <b>{_ACCOUNT_IBAN}</b></span>'
                     f' - <b>{_ACCOUNT_BANK}</b>', width=420))
    stamp_uri = company_stamp_data_uri(data.get("seller") or {}) if data.get("show_stamp") else ""
    if stamp_uri:
        out.append(_box(_RIGHT - 120, pay_top + _PAY_H + 6, 110, _STAMP_H,
                        f'<img src="{stamp_uri}" alt="stamp" style="width:100%; height:100%; object-fit:contain; '
                        f'display:block; filter:{_STAMP_FILTER};">').replace("<div ", '<div data-company-stamp="1" ', 1))
    return "".join(out)


def _footer_html(data: dict[str, Any], index: int, count: int) -> str:
    issued = data.get("issue_datetime")
    stamp = (issued.strftime("%H:%M:%S %Y-%m-%d") if isinstance(issued, datetime.datetime)
             else _esc(_date(issued)))
    vat = _esc((data.get("seller") or {}).get("vat"))
    pages = f" · {index} / {count}" if count > 1 else ""
    return (_text(None, 792.0, 5.4, "#6c757d", stamp, left=197.6, width=200, align="center", rtl=False)
            + _text(None, 799.8, 5.4, "#6b7477", f"· {vat}{pages}", left=197.6, width=200, align="center",
                    rtl=False))


def build_invoice_html_v31(data: dict[str, Any]) -> str:
    """Build «ثمار اليرموك» from the shared invoice data dict."""
    lines = with_print_descriptions(data)
    cols = _columns(bool(data.get("show_description")))
    widths = {k: w for k, _a, _e, w in cols}
    header = _header_html(data)

    colgroup = "".join(f'<col style="width:{_p(w)}px">' for *_r, w in cols)
    head = "<tr>" + "".join(
        f'<th class="h-{k}"><div class="ar">{ar}</div><div class="en">{en}</div></th>' for k, ar, en, _w in cols
    ) + "</tr>"

    def row(line: dict[str, Any]) -> str:
        cells = {
            "desc": _item_label(line),
            "pdesc": f"<bdi>{_esc(line.get('print_description'))}</bdi>",
            "qty": _num(line.get("qty")),
            "price": _sar(line.get("price")),
            "rate": _rate(line.get("vat_rate")),
            "vat": _sar(line.get("vat_amount")),
            "before": _sar(line.get("before")),
            "total": _sar(line.get("total", _dec(line.get("before")) + _dec(line.get("vat_amount")))),
        }
        return f'<tr style="height:{_p(_row_h(line, widths))}px;">' + "".join(
            f'<td class="c-{k}">{cells[k]}</td>' for k, *_r in cols) + "</tr>"

    rows_top = _ITEMS_TOP + _HEAD_H
    band = _band_height(data)
    pages = paginate(lines, lambda ln: _row_h(ln, widths), budget=_PAGE_BOT - rows_top,
                     budget_last=_PAGE_BOT - rows_top - band)
    count = len(pages)
    sheets = []
    for index, page_lines in enumerate(pages, start=1):
        last = index == count
        body = "".join(row(ln) for ln in page_lines)
        table_end = rows_top + sum(_row_h(ln, widths) for ln in page_lines)
        sheets.append(f"""
<div data-sheet class="sheet" style="{sheet_style(last=last)}">
{header}
  <table class="items" style="left:{_x(_LEFT)}px; top:{_p(_ITEMS_TOP)}px;">
    <colgroup>{colgroup}</colgroup>
    <thead>{head}</thead>
    <tbody>{body}</tbody>
  </table>
{_band_html(data, table_end) if last else ""}
{_footer_html(data, index, count)}
</div>""")

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  {font_face_css()}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{CAIRO}; color:{_BODY};
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ position:relative; box-sizing:border-box; width:{_SHEET_W}px; height:{_SHEET_H}px;
            margin:24px auto; background:#ffffff; overflow:hidden; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  bdi {{ unicode-bidi:isolate; }}
  table {{ border-collapse:collapse; position:absolute; table-layout:fixed; direction:ltr; }}
  .info td {{ box-sizing:border-box; vertical-align:top; padding:0 {_p(4.5)}px; direction:rtl; text-align:right;
             border-top:{_p(_HAIR)}px solid {_BROWN}; border-bottom:{_p(_HAIR)}px solid {_BROWN};
             border-left:{_p(_HAIR)}px solid {_SOFT}; white-space:nowrap; overflow:hidden; }}
  .info td:last-child {{ border-right:{_p(_HAIR)}px solid {_BROWN}; }}
  .info .cap {{ font-size:{_p(7.2)}px; font-weight:600; color:{_GREY}; line-height:{_p(8.6)}px;
               margin-top:{_p(2.6)}px; }}
  .info .val {{ font-size:{_p(8.4)}px; color:{_INK}; line-height:{_p(15.8)}px; margin-top:{_p(-1.6)}px; }}
  .items {{ width:{_p(_RIGHT - _LEFT)}px; border:{_p(_HAIR)}px solid {_FRAME}; }}
  .items th {{ box-sizing:border-box; height:{_p(_HEAD_H)}px; vertical-align:top; padding:{_p(2.8)}px {_p(4.8)}px 0;
              font-weight:400; color:{_HEAD}; text-align:right; white-space:nowrap; overflow:hidden;
              border-bottom:{_p(_HAIR)}px solid {_HEAD_RULE}; border-left:{_p(0.3)}px solid {_COL_RULE}; }}
  .items th.h-desc {{ text-align:left; padding-left:{_p(4.6)}px; border-left:0; }}
  .items th .ar {{ font-family:{DEJAVU}; font-size:{_p(7.8)}px; line-height:{_p(14.5)}px; direction:rtl; }}
  .items th.h-desc .ar {{ text-align:left; }}
  .items th .en {{ font-family:{_HELV}; font-size:{_p(7.8)}px; line-height:{_p(9.0)}px; }}
  .items td {{ box-sizing:border-box; vertical-align:top; padding:{_p(2.5)}px {_p(4.9)}px 0;
              font-size:{_p(7.8)}px; color:{_BODY}; text-align:right; white-space:nowrap;
              border-left:{_p(0.3)}px solid {_COL_RULE}; border-top:{_p(0.3)}px solid {_SOFT}; }}
  .items td.c-desc {{ text-align:left; padding-left:{_p(4.6)}px; border-left:0; white-space:normal;
                     overflow-wrap:anywhere; }}
  .items td.c-pdesc {{ text-align:right; direction:rtl; white-space:normal; overflow-wrap:anywhere;
                      font-size:{_p(7.0)}px; }}
  .items tbody tr:first-child td {{ border-top:0; }}
  .sheet > div b {{ font-weight:600; }}
  .money {{ white-space:nowrap; }}
  img.sar {{ height:{_p(6.0)}px; width:auto; vertical-align:{_p(-0.2)}px; }}
  .tot {{ position:static; width:100%; }}
  .tot td {{ font-size:{_p(7.2)}px; color:{_BODY}; padding:0 {_p(4.2)}px; white-space:nowrap; overflow:hidden;
            border-bottom:{_p(0.3)}px solid {_SOFT}; }}
  .tot td.a {{ text-align:right; }}
  .tot tr.gross td {{ background:{_GROSS}; font-weight:600; }}
  .tot tr.paid td.c {{ font-style:italic; }}
  .tot tr.due td {{ font-weight:700; border-bottom:0; }}
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


__all__ = ["build_invoice_html_v31", "address_lines", "font_face_css", "CAIRO", "DEJAVU"]
