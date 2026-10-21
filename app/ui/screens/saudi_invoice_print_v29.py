"""«أفنان جيزان» — a replica of the tax invoice the user supplied on 2026-10-21
(``شركة افنان جيزان للتجارة _ 0352.pdf``: شركة عبير النخبة → شركة افنان جيزان
للتجارة, invoice 0352, thirteen items).

A *layout* replica, like «النموذج الثاني والعشرون» (v28): the seller (both
languages + logo), the buyer, the items, the totals, the amount in words and the
stamp all come live from the shared ``data`` dict. Only the captions are fixed
text, plus «طريقة الدفع: نقدا», which the source prints regardless of the
invoice type.

Design, measured from the A4 source with PyMuPDF (points). Every coordinate is
kept in source points below and scaled ×816/595 (:func:`_p`) onto the 816×1056
Letter sheet every template prints on; the source's content ends at 726pt
(996px), so one uniform scale fits Letter with no squeeze.

* A boxed header (dark slate hairline): English seller block on the left
  (name underlined, address, «CR No», «TRN»), the company logo + short English
  name in the middle between two pale rules, the Arabic block mirrored on the
  right; a full-width rule, «فاتورة ضريبية – TAX INVOICE» centred, another rule;
  then «Bill to:» (bold buyer name, address, mobile, «Client VAT») beside a
  2-row grid: رقم الفاتورة | تاريخ الفاتورة, نوع الفاتورة, طريقة الدفع.
* Items: 9 black-ruled columns, bilingual two-line captions (رقم/No. · الرمز/SKU ·
  الوصف/Description · الكمية/Qty · سعر/Rate · المبلغ الإجمالي/Gross Amt. · VAT% ·
  الضريبة/VAT · الإجمالي/Net Amt.); «VAT x» is the per-unit tax, Net Amt. bold.
* Under the table, in the same frame: the stamp («الختم» under a rule) and the
  QR on the left; المجموع / خصم / الضريبة / الإجمالي مع الضريبة / المبلغ المستحق
  on the right, values «… ريال» in bold.
* A separate «المبلغ بالحروف» box.

Fonts: Latin in Inter (bundled ``inter_latin_*.woff2``, SIL OFL — the source's
face), Arabic and the table figures in Arial (always on Windows) with the bundled
Noto Naskh Arabic as the fallback, the Arabic title in Times New Roman Bold.

The QR is the shared ``QR_PRINT_PX`` (house rule, larger than the source's 112pt),
so the totals band is that much taller than the source; the rows keep their
heights and «المبلغ المستحق» absorbs the difference. The sheet paginates through
:mod:`invoice_pagination`: the header repeats, the totals band and the words box
land on the last page. The QR is ``data["qr_payload"]`` (the «مرحلة أولى» wrapper
swaps in tags 1–5).
"""

from __future__ import annotations

import base64
import datetime
import html
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.ui.screens.invoice_pagination import paginate, row_height, sheet_style
from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _ASSETS_DIR,
    _STAMP_FILTER,
    _clean_ar_words,
    company_logo_data_uri,
    company_stamp_data_uri,
    qr_vector_data_uri,
    with_print_descriptions,
)

# ---------------------------------------------------------------------------
# Geometry — source points, scaled onto the Letter sheet.
# ---------------------------------------------------------------------------
_SCALE = 816 / 594.96
_SHEET_W = 816
_SHEET_H = 1056


def _p(pt: float) -> float:
    """Source points → sheet px."""
    return round(pt * _SCALE, 2)


_SLATE = "#1f2937"           # header frame + rules, «Bill to» grid
_PALE = "#d0d5da"            # the two rules either side of the logo
_HAIR = _p(0.75)             # every rule in the source is 0.75pt

_BOX_L, _BOX_R = 7.875, 587.625
_HEAD_TOP, _HEAD_BOT = 7.875, 193.125
_TABLE_L = 7.5
_TABLE_TOP = 201.0
_HEAD_ROW = 36.8           # 37.5 in the source, less the collapsed border
_ROW = 24.52                 # 13 rows from 238.5 to 557.25
_PAGE_FLOOR = 757.0          # rows never run past this on any sheet (pt; the sheet is 770)

# Items table, physical left → right (key, Arabic, English, width pt).
_COLS = (
    ("no", "رقم", "No.", 29.3),
    ("sku", "الرمز", "SKU", 69.0),
    ("name", "الوصف", "Description", 118.4),
    ("qty", "الكمية", "Qty", 58.6),
    ("rate", "سعر", "Rate", 57.7),
    ("gross", "المبلغ الإجمالي", "Gross Amt.", 57.7),
    ("pct", "", "VAT%", 58.6),
    ("vat", "الضريبة", "VAT", 57.7),
    ("net", "الإجمالي", "Net Amt.", 73.45),
)
_TABLE_W = sum(w for *_x, w in _COLS)          # 580.45pt → 7.5 … 587.95
_DESC_W = 55.0               # «وصف الصنف», carved out of «الوصف» when ticked

# Totals band (under the table, same frame).
_LABEL_L, _VALUE_L = 340.5, 514.5
_TOT_ROWS = (20.3, 21.0, 21.0, 20.4)            # المجموع / خصم / الضريبة / مع الضريبة
_DUE_ROW = 48.0                                 # المبلغ المستحق
_QR_CX = 219.0                                  # QR centre in the source
_QR_PAD = 8                                     # px above / below the QR
_STAMP_BOX = (73.5, 578.25, 69.75, 71.25)       # left, top, w, h (stamp image)
_WORDS_GAP = 7.875
_WORDS_H = 30.75

# Fonts.
_LATIN_RANGE = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, U+20AC"
_INTER_FILES = {400: "inter_latin_400.woff2", 600: "inter_latin_600.woff2",
                700: "inter_latin_700.woff2", 800: "inter_latin_800.woff2"}
_NASKH_FILES = {400: "noto_naskh_arabic_regular.woff2", 700: "noto_naskh_arabic_bold.woff2"}
_FONT_CACHE: dict[str, str] = {}

_SANS = "'AJInter','Arial','AJNaskh',sans-serif"          # header / bill-to
_TABLE_FONTS = "'Arial','Liberation Sans','AJNaskh',sans-serif"
_TITLE_FONTS = "'AJInter','Times New Roman','AJNaskh',serif"


def _font_uri(name: str) -> str:
    if name not in _FONT_CACHE:
        try:
            raw = (_ASSETS_DIR / name).read_bytes()
            _FONT_CACHE[name] = "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")
        except OSError:
            _FONT_CACHE[name] = ""
    return _FONT_CACHE[name]


def _font_face_css() -> str:
    css = []
    for weight, name in _INTER_FILES.items():
        uri = _font_uri(name)
        if uri:
            css.append(f"@font-face {{ font-family:'AJInter'; font-weight:{weight}; "
                       f"src:url({uri}) format('woff2'); unicode-range:{_LATIN_RANGE}; }}")
    for weight, name in _NASKH_FILES.items():
        uri = _font_uri(name)
        if uri:
            css.append(f"@font-face {{ font-family:'AJNaskh'; font-weight:{weight}; "
                       f"src:url({uri}) format('woff2'); }}")
    return "\n  ".join(css)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Any) -> str:
    return f"{_dec(value):,.2f}"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def _lines_of(value: Any) -> list[str]:
    return [p.strip() for p in str(value or "").splitlines() if p.strip()]


def _pct(value: Any) -> str:
    rate = _dec(value if value not in (None, "") else 15).normalize()
    return f"{rate:f}%"


def _unit_vat(line: dict[str, Any]) -> Decimal:
    """The source's «VAT x» column: the tax on one unit (price × rate)."""
    rate = _dec(line.get("vat_rate") if line.get("vat_rate") not in (None, "") else 15)
    return (_dec(line.get("price")) * rate / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _short_name_en(name: str) -> str:
    """«ABEER AL-NOKHBA COMPANY» → «ABEER AL-NOKHBA», the caption under the logo."""
    words = name.split()
    while len(words) > 1 and words[-1].strip(".,").upper() in {"COMPANY", "CO", "EST", "LTD"}:
        words.pop()
    return " ".join(words)


def _issued_text(issued: Any) -> str:
    if isinstance(issued, datetime.datetime):
        return issued.strftime("%d/%m/%Y %I:%M %p")
    if isinstance(issued, datetime.date):
        return issued.strftime("%d/%m/%Y")
    return str(issued or "")


def amount_in_words_afnan(total: Any) -> str:
    """The source's wording: «ثلاثة وثلاثون ألف وواحد وتسعون ريال وخمسة وعشرون
    هللة فقط لا غير»."""
    amount = _dec(total).quantize(Decimal("0.01"), ROUND_HALF_UP)
    riyals = int(amount)
    halalas = int((amount - riyals) * 100)

    def words(n: int) -> str:
        try:
            from num2words import num2words

            text = _clean_ar_words(num2words(n, lang="ar"))
        except Exception:  # noqa: BLE001 - fall back to digits if the lib misbehaves
            return str(n)
        for tanween, bare in (("ألفاً", "ألف"), ("مليوناً", "مليون"), ("ملياراً", "مليار")):
            text = text.replace(tanween, bare)
        return text

    text = f"{words(riyals)} ريال"
    if halalas:
        text += f" و{words(halalas)} هللة"
    return text + " فقط لا غير"


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
def _abs(left_pt: float, top_pt: float, width_pt: float, body: str, style: str = "") -> str:
    return (f'<div style="position:absolute; left:{_p(left_pt)}px; top:{_p(top_pt)}px; '
            f'width:{_p(width_pt)}px; {style}">{body}</div>')


def _rule(left: float, top: float, width: float, height: float, color: str) -> str:
    return (f'<div style="position:absolute; left:{_p(left)}px; top:{_p(top)}px; '
            f'width:{_p(width)}px; height:{_p(height)}px; background:{color};"></div>')


def _seller_html(seller: dict[str, Any]) -> str:
    name = str(seller.get("name") or "")
    name_en = str(seller.get("name_en") or "") or name
    address = _lines_of(seller.get("address"))
    address_en = _lines_of(seller.get("address_en")) or address
    vat = str(seller.get("vat") or "")
    cr = str(seller.get("cr") or "")

    fs_name, fs = _p(7.35), _p(6.15)
    lh = _p(11.3)

    def block(side: str, title: str, addr: list[str], cr_line: str, vat_line: str) -> str:
        align = "left" if side == "left" else "right"
        direction = "ltr" if side == "left" else "rtl"
        pos = f"left:{_p(13.5)}px;" if side == "left" else f"right:{_p(594.96 - 582.0)}px;"
        addr_html = "".join(f"<div>{_esc(a)}</div>" for a in addr)
        extra = ""
        if cr:
            extra += f'<div style="margin-top:{_p(1.4)}px;">{cr_line}</div>'
        if vat:
            extra += f'<div style="margin-top:{_p(2.2)}px;">{vat_line}</div>'
        return (
            f'<div dir="{direction}" style="position:absolute; {pos} top:{_p(11.6)}px; '
            f'width:{_p(206.3)}px; text-align:{align};">'
            f'<div style="font-weight:700; font-size:{fs_name}px; line-height:{_p(12.4)}px; '
            f'white-space:nowrap; overflow:hidden; text-overflow:clip;">{_esc(title)}</div>'
            f'<div style="height:{_HAIR}px; background:{_SLATE}; margin-top:{_p(0.2)}px;"></div>'
            f'<div style="font-size:{fs}px; line-height:{lh}px; margin-top:{_p(1.4)}px;">'
            f"{addr_html}{extra}</div></div>"
        )

    left = block("left", name_en, address_en, f"CR No: {_esc(cr)}", f"TRN: {_esc(vat)}")
    right = block("right", name, address, f"رقم السجل التجاري: {_esc(cr)}", f"الرقم الضريبي: {_esc(vat)}")

    logo_uri = company_logo_data_uri(seller)
    logo = (
        f'<img src="{logo_uri}" alt="logo" style="position:absolute; left:{_p(282.75)}px; '
        f'top:{_p(13.5)}px; width:{_p(30)}px; height:{_p(30)}px; object-fit:contain; display:block;">'
        if logo_uri else ""
    )
    brand = _abs(232.0, 45.6, 131.5, _esc(_short_name_en(name_en)),
                 f"text-align:center; font-weight:600; font-size:{_p(6.38)}px; line-height:{_p(9)}px; "
                 "white-space:nowrap; overflow:hidden;")
    return (left + right + logo + brand
            + _rule(227.25, 13.5, 0.75, 41.25, _PALE) + _rule(367.5, 13.5, 0.75, 41.25, _PALE))


def _bill_to_html(customer: dict[str, Any]) -> str:
    rows = [f'<div style="margin-bottom:{_p(3.5)}px;">Bill to:</div>']
    rows.append(f"<div>{_esc(customer.get('name'))},</div>")
    address = " - ".join(_lines_of(customer.get("address")))
    if address:
        rows.append(f"<div>{_esc(address)}</div>")
    phone = str(customer.get("phone") or "").strip()
    if phone:
        rows.append(f"<div>رقم الجوال: {_esc(phone)}</div>")
    if customer.get("vat"):
        rows.append(f'<div style="margin-top:{_p(7.2)}px;">Client VAT : {_esc(customer.get("vat"))}</div>')
    return (
        f'<div dir="ltr" style="position:absolute; left:{_p(11.25)}px; top:{_p(110.6)}px; '
        f'width:{_p(282)}px; height:{_p(82)}px; overflow:hidden; text-align:left; font-weight:700; '
        f'font-size:{_p(7.5)}px; line-height:{_p(10.85)}px;">{"".join(rows)}</div>'
    )


def _info_cell(left: float, top: float, width: float, en: str, ar: str, value: str) -> str:
    fs, lh = _p(5.25), _p(7.5)
    return (
        f'<div style="position:absolute; left:{_p(left)}px; top:{_p(top)}px; width:{_p(width)}px; '
        f'font-size:{fs}px; line-height:{lh}px;">'
        f'<div style="position:absolute; left:{_p(4.4)}px; top:{_p(4.0)}px; white-space:nowrap;">{en}</div>'
        f'<div dir="rtl" style="position:absolute; right:{_p(4.5)}px; top:{_p(4.0)}px; white-space:nowrap;">{ar}</div>'
        f'<div style="position:absolute; left:0; width:100%; top:{_p(15.1)}px; text-align:center; '
        f'white-space:nowrap; overflow:hidden;">{value}</div></div>'
    )


def _header_html(data: dict[str, Any]) -> str:
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    payment = str(data.get("payment_label") or "")
    credit = "آجل" in payment or "credit" in payment.lower()
    inv_type = "Credit | آجل" if credit else "Cash | نقدي"

    frame = (
        f'<div style="position:absolute; left:{_p(_BOX_L) - _HAIR / 2}px; top:{_p(_HEAD_TOP) - _HAIR / 2}px; '
        f'width:{_p(_BOX_R - _BOX_L)}px; height:{_p(_HEAD_BOT - _HEAD_TOP)}px; '
        f'border:{_HAIR}px solid {_SLATE};"></div>'
    )
    title = _abs(_BOX_L, 89.6, _BOX_R - _BOX_L,
                 f'<span dir="ltr">فاتورة ضريبية – TAX INVOICE</span>',
                 f"text-align:center; font-family:{_TITLE_FONTS}; font-weight:800; "
                 f"font-size:{_p(9)}px; line-height:{_p(13)}px;")
    grid = (
        _rule(297.0, 107.25, 0.75, 85.5, _SLATE)
        + _rule(441.75, 107.25, 0.75, 28.5, _SLATE)
        + _rule(297.75, 135.0, 289.5, 0.75, _SLATE)
        + _rule(297.75, 163.5, 289.5, 0.75, _SLATE)
        + _rule(297.75, 192.0, 289.5, 0.75, _SLATE)
        + _info_cell(297.75, 107.25, 144.0, "Invoice No:", "رقم الفاتورة",
                     f'<bdi dir="ltr">{_esc(data.get("invoice_number"))}</bdi>')
        + _info_cell(442.5, 107.25, 144.75, "Invoice Date:", "تاريخ الفاتورة",
                     f'<bdi dir="ltr">{_esc(_issued_text(data.get("issue_datetime")))}</bdi>')
        + _info_cell(297.75, 135.75, 289.5, "Invoice Type:", "نوع الفاتورة",
                     f'<span dir="ltr">{_esc(inv_type)}</span>')
        + _info_cell(297.75, 164.25, 289.5, "Paid By:", "طريقة الدفع", "نقدا")
    )
    return (frame + _seller_html(seller)
            + _rule(8.25, 81.75, 579.0, 0.75, _SLATE) + title
            + _rule(8.25, 106.5, 579.0, 0.75, _SLATE)
            + _bill_to_html(customer) + grid)


def _columns(show_desc: bool) -> list[tuple[str, str, str, float]]:
    """The table's columns; with «إظهار وصف الصنف» a «وصف الصنف» column follows
    the item name and takes part of its width."""
    if not show_desc:
        return list(_COLS)
    out: list[tuple[str, str, str, float]] = []
    for key, ar, en, w in _COLS:
        if key == "name":
            out += [(key, ar, en, w - _DESC_W), ("desc", "وصف الصنف", "Item Desc.", _DESC_W)]
        else:
            out.append((key, ar, en, w))
    return out


def _row_h(line: dict[str, Any], widths: dict[str, float]) -> float:
    """Row height in pt (the name wraps and grows the row, by house rule)."""
    px = row_height(str(line.get("name") or ""), base=_p(_ROW), width_px=_p(widths["name"] - 7),
                    font_px=_p(8.25), line_height=1.25, chrome=_p(8))
    if "desc" in widths:
        px = max(px, row_height(str(line.get("print_description") or ""), base=_p(_ROW),
                                width_px=_p(widths["desc"] - 7), font_px=_p(8.25),
                                line_height=1.25, chrome=_p(8)))
    return px / _SCALE


def _band_html(data: dict[str, Any], width_pt: float) -> tuple[str, float]:
    """The totals band (stamp · QR · totals) and the words box; returns (html, height pt)."""
    seller = data.get("seller") or {}
    totals = data.get("totals") or {}
    total = totals.get("total", 0)

    rows_h = sum(_TOT_ROWS)
    band_h = max(rows_h + _DUE_ROW, (QR_PRINT_PX + 2 * _QR_PAD) / _SCALE)
    due_h = band_h - rows_h
    rows = (
        ("Total Excl VAT (المجموع)", totals.get("subtotal", totals.get("taxable", 0))),
        ("Discount (خصم)", totals.get("discount", 0)),
        ("VAT (الضريبة)", totals.get("vat", 0)),
        ("Total with VAT (الإجمالي مع الضريبة)", total),
    )
    tr = "".join(
        f'<tr style="height:{_p(h)}px;"><td class="lab">{lab}</td>'
        f'<td class="val"><bdi dir="ltr">{_money(v)} ريال</bdi></td></tr>'
        for (lab, v), h in zip(rows, _TOT_ROWS)
    )
    tr += (
        f'<tr style="height:{_p(due_h)}px;"><td class="lab">Outstanding Amount (المبلغ المستحق)</td>'
        f'<td class="val due"><div><bdi dir="ltr">{_money(total)}</bdi></div><div>ريال</div></td></tr>'
    )
    totals_table = (
        f'<table class="tot" style="position:absolute; left:{_p(_LABEL_L - _TABLE_L)}px; top:0; '
        f'width:{_p(width_pt - (_LABEL_L - _TABLE_L))}px;"><colgroup>'
        f'<col style="width:{_p(_VALUE_L - _LABEL_L)}px"><col></colgroup>{tr}</table>'
    )

    qr_uri = qr_vector_data_uri(data.get("qr_payload"))
    qr_html = (
        f'<img src="{qr_uri}" alt="QR" style="position:absolute; left:{_p(_QR_CX - _TABLE_L) - QR_PRINT_PX / 2}px; '
        f'top:{(_p(band_h) - QR_PRINT_PX) / 2}px; width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; '
        f'display:block; background:#ffffff;">'
        if qr_uri else ""
    )

    # The stamp keeps its source spot relative to the band's middle.
    mid = band_h / 2
    s_left, s_top, s_w, s_h = _STAMP_BOX
    s_top = mid - (622.1 - s_top)           # 622.1 = the source band's middle
    stamp_uri = company_stamp_data_uri(seller) if data.get("show_stamp") else ""
    stamp_html = (
        f'<div data-company-stamp="1" style="position:absolute; left:{_p(s_left - _TABLE_L)}px; '
        f'top:{_p(s_top)}px; width:{_p(s_w)}px; height:{_p(s_h)}px;"><img src="{stamp_uri}" alt="stamp" '
        f'style="width:100%; height:100%; object-fit:contain; display:block; filter:{_STAMP_FILTER};"></div>'
        if stamp_uri else ""
    )
    caption_top = s_top + 72.75
    stamp_caption = (
        _rule(82.5 - _TABLE_L, caption_top, 52.5, 0.75, "#333333")
        + _abs(75.0 - _TABLE_L, caption_top + 1.6, 67.5, "الختم",
               f"text-align:center; font-size:{_p(8.25)}px; line-height:{_p(11)}px;")
    )

    words = amount_in_words_afnan(total)
    words_box = (
        f'<div dir="rtl" style="position:absolute; left:{_p(_BOX_L - _TABLE_L) - _HAIR / 2}px; '
        f'top:{_p(_WORDS_GAP)}px; width:{_p(_BOX_R - _BOX_L)}px; height:{_p(_WORDS_H)}px; '
        f'border:{_HAIR}px solid #000000; box-sizing:border-box; font-weight:700; display:flex; '
        f'align-items:center; justify-content:space-between; padding:0 {_p(15.3)}px; '
        f'font-family:{_TABLE_FONTS};">'
        f'<div style="font-size:{_p(12)}px; white-space:nowrap;">المبلغ بالحروف</div>'
        f'<div style="font-size:{_p(9.75)}px; text-align:left; margin-right:{_p(12)}px;">{_esc(words)}</div>'
        "</div>"
    )
    band = (
        f'<div style="position:relative; width:{_p(width_pt)}px; height:{_p(band_h)}px; '
        f'box-sizing:border-box; border:{_HAIR}px solid #000000; border-top:none;">'
        f"{stamp_html}{stamp_caption}{qr_html}{totals_table}</div>"
        f'<div style="position:relative; height:0;">{words_box}</div>'
    )
    return band, band_h + _WORDS_GAP + _WORDS_H


def build_invoice_html_v29(data: dict[str, Any]) -> str:
    """Build «أفنان جيزان» from the shared invoice data dict."""
    lines = with_print_descriptions(data)
    cols = _columns(bool(data.get("show_description")))
    widths = {k: w for k, _a, _e, w in cols}
    header_html = _header_html(data)

    colgroup = "".join(f'<col style="width:{_p(w)}px">' for *_x, w in cols)
    head = "".join(
        f'<th style="height:{_p(_HEAD_ROW)}px;">' + (f"{ar}<br>{en}" if ar else en) + "</th>"
        for _k, ar, en, _w in cols
    )

    def row(line: dict[str, Any]) -> str:
        cells = {
            "no": str(line["_no"]),
            "sku": _esc(line.get("code")),
            "name": _esc(line.get("name")),
            "desc": _esc(line.get("print_description")),
            "qty": _money(line.get("qty")),
            "rate": _money(line.get("price")),
            "gross": _money(line.get("before")),
            "pct": _pct(line.get("vat_rate")),
            "vat": f"VAT {_money(_unit_vat(line))}",
            "net": _money(line.get("total", _dec(line.get("before")) + _dec(line.get("vat_amount")))),
        }
        return "<tr>" + "".join(f'<td class="c-{k}">{cells[k]}</td>' for k, *_r in cols) + "</tr>"

    numbered = [{**ln, "_no": i} for i, ln in enumerate(lines, start=1)]
    band_html, band_h = _band_html(data, _TABLE_W)

    budget = _PAGE_FLOOR - _TABLE_TOP - _HEAD_ROW
    pages = paginate(numbered, lambda ln: _row_h(ln, widths), budget=budget, budget_last=budget - band_h)
    count = len(pages)
    sheets = []
    for index, page_lines in enumerate(pages, start=1):
        last = index == count
        body = "".join(row(ln) for ln in page_lines)
        if not numbered and last:
            body = f'<tr><td colspan="{len(cols)}" style="text-align:center;">لا توجد أصناف</td></tr>'
        counter = (
            _abs(0, 759, 594.96, f"{index} / {count}", f"text-align:center; font-size:{_p(6.5)}px; line-height:{_p(8)}px;")
            if count > 1 else ""
        )
        sheets.append(f"""
<div data-sheet class="sheet" style="{sheet_style(last=last)}">
{header_html}
  <div style="position:absolute; left:{_p(_TABLE_L)}px; top:{_p(_TABLE_TOP)}px; width:{_p(_TABLE_W)}px;">
    <table class="items">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>
{band_html if last else ""}
  </div>
  {counter}
</div>""")

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_SANS}; color:#000000;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ position:relative; box-sizing:border-box; width:{_SHEET_W}px; height:{_SHEET_H}px;
            margin:24px auto; background:#ffffff; overflow:hidden; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  td, th {{ box-sizing:border-box; }}
  .items {{ width:{_p(_TABLE_W)}px; table-layout:fixed; direction:ltr; font-family:{_TABLE_FONTS}; }}
  .items th {{ font-weight:700; font-size:{_p(8.25)}px; line-height:{_p(12)}px; border:{_HAIR}px solid #000000;
               text-align:center; vertical-align:middle; padding:0 2px; }}
  .items td {{ height:{_p(_ROW)}px; font-size:{_p(8.25)}px; line-height:1.25; border:{_HAIR}px solid #000000;
               text-align:center; vertical-align:middle; padding:{_p(2)}px {_p(3.5)}px;
               overflow-wrap:anywhere; word-break:break-word; }}
  .items td.c-no {{ text-align:right; padding-right:{_p(4.1)}px; }}
  .items td.c-name, .items td.c-desc {{ direction:rtl; text-align:right; }}
  .items td.c-net {{ font-weight:700; }}
  .tot {{ table-layout:fixed; direction:ltr; font-family:{_TABLE_FONTS}; }}
  .tot td {{ border:{_HAIR}px solid #000000; vertical-align:middle; font-size:{_p(8.25)}px;
             text-align:right; padding:0 {_p(6)}px; white-space:nowrap; }}
  .tot tr:first-child td {{ border-top:none; }}
  .tot tr:last-child td {{ border-bottom:none; }}
  .tot td.val {{ font-weight:700; border-right:none; }}
  .tot td.due {{ font-size:{_p(13.5)}px; line-height:{_p(18.7)}px; }}
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


__all__ = ["amount_in_words_afnan", "build_invoice_html_v29"]
