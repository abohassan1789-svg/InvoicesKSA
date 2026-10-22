"""«بنشر» — a replica of the price quotation the user supplied on 2026-10-22
(``عرض الأسعار 4000060_1_20261011_2038.PDF``: بنشر المشاري لخدمات السيارات,
quotation 4000060, 25 items over two A4 pages, printed by Microsoft Reporting
Services), turned into a sales-invoice template.

A *layout* replica, like «أفنان جيزان» (v29): the seller (both languages + logo),
the buyer, the items, the totals and the stamp come live from the shared ``data``
dict. What changed because this prints an invoice, not a quotation:

* the title reads «Tax Invoice - فاتورة ضريبية» (was «Quotation - عرض سعر») and
  «Invoice No / رقم الفاتورة» replaces «Document No / رقم العرض»;
* the QR (which a quotation does not have) sits left of the totals, at the shared
  ``QR_PRINT_PX``; the totals table narrows to make room, keeping its proportions,
  and the stamp sits above it;
* the totals and the column-sum row print on the last page only (house rule,
  :mod:`invoice_pagination`); the source repeats them on every page.

Left blank, as there is no such data in the program: «الفرع», «البيان», «رصيد
العميل», «الموقع» and the seller's «رقم التواصل». Every line's «خصومات» is 0.00
(discounts are per invoice; the invoice discount shows in the sum row and the
totals). The national-address rows (city, street, district, postal / additional /
building no.) are read out of the free-text address by :func:`national_address`;
the seller's «الدولة» defaults to «المملكة العربية السعودية». «طباعة بواسطة» is
``data["printed_by"]`` (the signed-in user), «تاريخ الطباعة» the moment of printing.

Geometry, measured from the A4 source with PyMuPDF, is kept in source points and
scaled ×1056/841.89 onto the 816×1056 Letter sheet — the whole A4 page, exactly
as printing the PDF on Letter with «fit to page» would, so every page holds what
the source's page holds (centred, 34.7px side margins).

Fonts as the source: Arial Bold (Arabic, figures and most Latin — the source's
Helvetica-Bold is Arial on Windows) and Times New Roman Bold for the handful of
Latin words the source sets in Times-Bold (Name, Code, District, Postal Code,
Document, Taxable Amount, Rate). Fallbacks: Liberation Sans / Serif (metric
clones), then the bundled Noto Naskh Arabic.
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


_GREY = "#808080"            # info / items / totals rules
_DIM = "#696969"             # buyer / seller rules
_BAND = "#dcdcdc"            # title, section bars, table heads, sum row, totals values
_PALE = "#f5f5f5"            # info-table caption cells
_RULE = _p(0.75)

# Info tables (Branch … / Date …): columns and rows.
_INFO_L = (14.2, 75.7, 234.5, 295.2)
_INFO_R = (303.8, 362.4, 516.8, 573.5)
_INFO_TOP_L, _INFO_TOP_R, _INFO_ROW = 122.6, 122.2, 14.76

# Buyer / seller.
_PARTY_L = (14.2, 75.7, 234.5, 295.2)
_PARTY_R = (304.6, 361.6, 517.6, 574.6)
_BAR_TOP, _BAR_BOT = 172.9, 191.5
_PARTY_TOP, _PARTY_ROW = 192.1, 14.76

# Items: column edges, physical left → right (key, Arabic, English, right edge).
_ITEMS_L = 14.4
_COLS = (
    ("no", "م.س", "S.N", 36.6),
    ("code", "رقم الصنف", "Product Code", 116.7),
    ("name", "اسم الصنف", "Product Name", 230.8),
    ("loc", "الموقع", "Location", 273.8),
    ("qty", "الكمية", "QTY", 309.7),
    ("price", "السعر", "Price", 357.2),
    ("taxable", "المبلغ الخاضع<br>للضريبة", '<span class="t">Taxable<br>Amount</span>', 407.5),
    ("disc", "خصومات", "Discount", 450.5),
    ("rate", "نسبة<br>الضريبة", 'Tax<br><span class="t">Rate</span>', 482.1),
    ("vat", "مبلغ<br>الضريبة", "Tax<br>Amount", 525.1),
    ("total", "اجمالي شامل<br>الضريبة", "Total With<br>Tax", 574.4),
)
_ITEMS_TOP = 349.1
_HEAD_AR, _HEAD_EN = 24.2, 22.0
_ROW = 17.008
_DESC_W = 44.0               # «وصف الصنف», carved out of «اسم الصنف» when ticked

# Totals band (last page), anchored to the bottom like the source.
_TOT_L, _TOT_R = 12.6, 575.2
_TOT_SPLIT = (206.2, 150.3, 206.1)          # EN caption | value | AR caption
_TOT_BOT, _TOT_ROW = 790.3, 16.94
_TOT_GAP = 12.0                              # sum row → QR (the source: 21.2 to its totals)
_QR_GAP = 8.0
_QR_PT = QR_PRINT_PX / _SCALE
_BAND_TOP = _TOT_BOT - _QR_PT                # the QR is the band's tallest piece
_PAGE_BOT = _TOT_BOT                         # rows never run past this on any page

# Fonts.
_NASKH_FILES = {400: "noto_naskh_arabic_regular.woff2", 700: "noto_naskh_arabic_bold.woff2"}
_FONT_CACHE: dict[str, str] = {}
_SANS = "'Arial','Liberation Sans','AJNaskh',sans-serif"
_SERIF = "'Times New Roman','Liberation Serif','AJNaskh',serif"

_KSA = "المملكة العربية السعودية"


def _font_face_css() -> str:
    css = []
    for weight, name in _NASKH_FILES.items():
        if name not in _FONT_CACHE:
            try:
                raw = (_ASSETS_DIR / name).read_bytes()
                _FONT_CACHE[name] = "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")
            except OSError:
                _FONT_CACHE[name] = ""
        if _FONT_CACHE[name]:
            css.append(f"@font-face {{ font-family:'AJNaskh'; font-weight:{weight}; "
                       f"src:url({_FONT_CACHE[name]}) format('woff2'); }}")
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
    return f"{_dec(value).quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}"


def _qty(value: Any) -> str:
    """«48», not «48.00» — the source prints whole quantities bare."""
    q = _dec(value)
    if q == q.to_integral_value():
        return str(int(q))
    return f"{q.normalize():f}"


def _rate(value: Any) -> str:
    rate = _dec(value if value not in (None, "") else 15).normalize()
    return f"%{rate:f}"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""))


def _date(value: Any) -> str:
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y/%m/%d")
    return str(value or "")


# ---------------------------------------------------------------------------
# National address out of a free-text address
# ---------------------------------------------------------------------------
_LABELS = (
    ("postal", ("الرمز البريدي", "رمز بريدي", "postal code", "postal", "zip code", "zip")),
    ("additional", ("الرقم الإضافي", "الرقم الاضافي", "رقم إضافي", "رقم اضافي", "additional no",
                    "additional number", "additional")),
    ("building", ("رقم المبنى", "رقم المبني", "المبنى", "المبني", "مبنى", "مبني", "building no",
                  "building number", "building")),
    ("district", ("الحي", "حي", "district")),
    ("street", ("اسم الشارع", "الشارع", "شارع", "street name", "street", "st.")),
    ("city", ("المدينة", "مدينة", "city")),
    ("country", ("الدولة", "country")),
)
_COUNTRY_RE = re.compile(r"(المملكة\s+العربية\s+السعودية|السعودية|kingdom\s+of\s+saudi\s+arabia|"
                         r"saudi\s+arabia|\bksa\b)", re.IGNORECASE)
_SPLIT_RE = re.compile(r"\s*(?:\n|،|,|\||\s-\s|\s–\s)\s*")
# A labelled part that follows another without a separator («… حي النخيل …»).
_INNER_RE = re.compile(r"\s+(?=(?:حي|شارع|الرمز البريدي|الرقم الإضافي|الرقم الاضافي|رقم المبنى)\s)")


def national_address(text: Any) -> dict[str, str]:
    """Split a free-text address into the national-address rows the source prints
    (country, city, street, district, postal, additional, building).

    Labelled parts («حي …», «شارع …», «الرمز البريدي: …») go where they say; a bare
    5-digit number is the postal code and bare 4-digit numbers the building, then
    the additional number; «المملكة العربية السعودية» is the country. Unlabelled
    words are read from the end, largest first: the last is the city, the one before
    it the district, anything earlier the street."""
    out = {k: "" for k in ("country", "city", "street", "district", "postal", "additional", "building")}
    raw = str(text or "")
    if _COUNTRY_RE.search(raw):
        out["country"] = _KSA
        raw = _COUNTRY_RE.sub(" ", raw)
    parts: list[str] = []
    for chunk in _SPLIT_RE.split(raw):
        parts += [p for p in _INNER_RE.split(chunk) if p.strip()]

    loose: list[str] = []
    for part in parts:
        part = part.strip(" -–:،,.")
        if not part:
            continue
        key = None
        low = part.lower()
        for field, labels in _LABELS:
            for label in labels:
                if low.startswith(label) and (len(part) == len(label) or not part[len(label)].isalnum()):
                    key, part = field, part[len(label):].strip(" -–:،,.")
                    break
            if key:
                break
        if key and not part:
            continue                     # a bare label («الدولة» once the country was taken out)
        if key and not out[key]:
            out[key] = part
            continue
        words = []
        for word in part.split():
            if word.isdigit() and len(word) == 5 and not out["postal"]:
                out["postal"] = word
            elif word.isdigit() and len(word) == 4 and not out["building"]:
                out["building"] = word
            elif word.isdigit() and len(word) == 4 and not out["additional"]:
                out["additional"] = word
            else:
                words.append(word)
        if words:
            loose.append(" ".join(words))

    for field in ("city", "district"):
        if loose and not out[field]:
            out[field] = loose.pop()
    if loose:
        out["street"] = " - ".join(([out["street"]] if out["street"] else []) + loose)
    return out


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
def _box(left: float, top: float, width: float, height: float, body: str = "", style: str = "") -> str:
    return (f'<div style="position:absolute; left:{_x(left)}px; top:{_p(top)}px; width:{_p(width)}px; '
            f'height:{_p(height)}px; {style}">{body}</div>')


def _header_html(seller: dict[str, Any]) -> str:
    name = str(seller.get("name") or "")
    name_en = str(seller.get("name_en") or "") or name
    vat = _esc(seller.get("vat"))
    cr = _esc(seller.get("cr"))

    address = " - ".join(p.strip() for p in str(seller.get("address") or "").splitlines() if p.strip())
    address_en = " - ".join(p.strip() for p in str(seller.get("address_en") or "").splitlines() if p.strip())
    address_en = address_en or address

    frame = _box(12.42, 24.45, 576.61 - 12.42, 89.62 - 24.45, "",
                 f"box-sizing:border-box; border:{_p(1)}px dashed #000000;")

    def column(left: float, width: float, rtl: bool, title: str, addr: str, cr_line: str, vat_line: str) -> str:
        # Name (up to two lines), address, CR, VAT — spread over the frame's height
        # like the source's name / activity / VAT lines; at most 2 + 2 + 1 + 1 lines.
        one = "white-space:nowrap; overflow:hidden;"
        rows = [f'<div class="clamp2" style="font-size:{_p(12 if rtl else 11)}px; line-height:{_p(12)}px;">'
                f"{_esc(title)}</div>"]
        if addr:
            rows.append(f'<div class="clamp2" style="font-size:{_p(8.5)}px; line-height:{_p(9.2)}px;">{_esc(addr)}</div>')
        if cr_line:
            rows.append(f'<div style="font-size:{_p(10)}px; line-height:{_p(10.5)}px; {one}">{cr_line}</div>')
        if vat_line:
            rows.append(f'<div style="font-size:{_p(11)}px; line-height:{_p(11.6)}px; {one}">{vat_line}</div>')
        align = "direction:rtl; text-align:right;" if rtl else "text-align:left;"
        return _box(left, 25.2, width, 64.0, "".join(rows),
                    f"{align} display:flex; flex-direction:column; justify-content:space-between;")

    left = column(17.6, 198, False, name_en, address_en,
                  f"CR No : {cr}" if cr else "", f"VAT No : {vat}" if vat else "")
    right = column(370.8, 198, True, name, address,
                   f"السجل التجاري : <bdi>{cr}</bdi>" if cr else "",
                   f"الرقم الضريبي : <bdi>{vat}</bdi>" if vat else "")
    logo_uri = company_logo_data_uri(seller)
    logo = _box(220.7, 26.2, 145.0, 56.8,
                f'<img src="{logo_uri}" alt="logo" style="width:100%; height:100%; object-fit:contain; display:block;">',
                "") if logo_uri else ""
    title = _box(208.6, 98.7, 179.6, 18.3, "Tax Invoice - فاتورة ضريبية",
                 f"background:{_BAND}; text-align:center; font-size:{_p(13)}px; line-height:{_p(18.3)}px; "
                 "white-space:nowrap;")
    return frame + left + logo + right + title


def _grid(cols: tuple[float, ...], top: float, row_h: float, rows: list[tuple[str, str, str]],
          rule: str, caption_fill: str = "", value_px: float = 8.0) -> str:
    """A 3-column caption | value | caption table (English left, Arabic right)."""
    w = [cols[1] - cols[0], cols[2] - cols[1], cols[3] - cols[2]]
    fill = f"background:{caption_fill};" if caption_fill else ""
    trs = "".join(
        f'<tr style="height:{_p(row_h)}px;"><td class="en" style="{fill}">{en}</td>'
        f'<td class="v" style="font-size:{_p(value_px)}px;">{val}</td>'
        f'<td class="ar" style="{fill}">{ar}</td></tr>'
        for en, val, ar in rows
    )
    return (
        f'<table class="grid" style="left:{_x(cols[0])}px; top:{_p(top)}px; width:{_p(cols[3] - cols[0])}px; '
        f'--rule:{rule};"><colgroup>' + "".join(f'<col style="width:{_p(x)}px">' for x in w)
        + f"</colgroup>{trs}</table>"
    )


def _info_html(data: dict[str, Any]) -> str:
    left = [
        ("Branch", "", "الفرع"),
        ("Note", "", "البيان"),
        ('Client <span class="reg">B</span>alance', "", "رصيد العميل"),
    ]
    right = [
        ("Date", _esc(_date(data.get("issue_datetime"))), "التاريخ"),
        ("Invoice No", f'<bdi dir="ltr">{_esc(data.get("invoice_number"))}</bdi>', "رقم الفاتورة"),
        ("Payment", _esc(data.get("payment_label")), "طريقة الدفع"),
    ]
    return (_grid(_INFO_L, _INFO_TOP_L, _INFO_ROW, left, _GREY, _PALE)
            + _grid(_INFO_R, _INFO_TOP_R, _INFO_ROW, right, _GREY, _PALE))


def _party_html(data: dict[str, Any]) -> str:
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    s_addr = national_address(seller.get("address"))
    c_addr = national_address(customer.get("address"))

    def v(text: Any) -> str:
        return f"<bdi>{_esc(text)}</bdi>" if text else ""

    buyer = [
        ('Client <span class="t">Name</span>', v(customer.get("name")), "اسم العميل"),
        ("Vat No", v(customer.get("vat")), "الرقم الضريبي"),
        ('Country <span class="t">Code</span>', "SA" if c_addr["country"] == _KSA else v(c_addr["country"]), "رمز الدولة"),
        ("City", v(c_addr["city"]), "المدينة"),
        ("Street Name", v(c_addr["street"]), "اسم الشارع"),
        ('<span class="t">District</span>', v(c_addr["district"]), "اسم الحي"),
        ('<span class="t">Postal Code</span>', v(c_addr["postal"]), "الرمز البريدي"),
        ("Additional No", v(c_addr["additional"]), "الرقم الاضافي"),
        ("Building No", v(c_addr["building"]), "رقم المبنى"),
        ("Client Mobile", v(customer.get("phone")), "هاتف العميل"),
    ]
    sell = [
        ('Seller <span class="t">Name</span>', v(seller.get("name")), "اسم البائع"),
        ("Vat No", v(seller.get("vat")), "الرقم الضريبي"),
        ("Country", v(s_addr["country"] or _KSA), "الدولة"),
        ("City", v(s_addr["city"]), "المدينة"),
        ("Street Name", v(s_addr["street"]), "اسم الشارع"),
        ('<span class="t">District</span>', v(s_addr["district"]), "اسم الحي"),
        ('<span class="t">Postal Code</span>', v(s_addr["postal"]), "الرمز البريدي"),
        ("Additional No", v(s_addr["additional"]), "الرقم الاضافي"),
        ("Building No", v(s_addr["building"]), "رقم المبنى"),
        ("Contact US", "", "رقم التواصل"),
    ]
    bar_style = (f"background:{_BAND}; box-sizing:border-box; border:{_p(1)}px solid #dcdcdc; text-align:center; "
                 f"font-size:{_p(9)}px; line-height:{_p(_BAR_BOT - _BAR_TOP)}px; white-space:nowrap;")
    bars = (
        _box(_PARTY_L[0], _BAR_TOP, _PARTY_L[3] - _PARTY_L[0], _BAR_BOT - _BAR_TOP,
             '<span dir="ltr">Buyer - <span dir="rtl">المشتري</span></span>', bar_style)
        + _box(_PARTY_R[0], _BAR_TOP, _PARTY_R[3] - _PARTY_R[0], _BAR_BOT - _BAR_TOP - 0.4,
               '<span dir="ltr">Seller - <span dir="rtl">البائع</span></span>', bar_style)
    )
    return (bars + _grid(_PARTY_L, _PARTY_TOP, _PARTY_ROW, buyer, _DIM, value_px=8.5)
            + _grid(_PARTY_R, _PARTY_TOP, _PARTY_ROW, sell, _DIM, value_px=8.5))


def _columns(show_desc: bool) -> list[tuple[str, str, str, float]]:
    """(key, Arabic, English, width pt); «إظهار وصف الصنف» adds «وصف الصنف» after
    the item name, taking part of its width."""
    out: list[tuple[str, str, str, float]] = []
    left = _ITEMS_L
    for key, ar, en, right in _COLS:
        width = right - left
        left = right
        if key == "name" and show_desc:
            out += [(key, ar, en, width - _DESC_W), ("desc", "وصف الصنف", "Description", _DESC_W)]
        else:
            out.append((key, ar, en, width))
    return out


def _row_h(line: dict[str, Any], widths: dict[str, float]) -> float:
    """Row height in pt (a long name wraps and grows the row, by house rule)."""
    px = row_height(str(line.get("name") or ""), base=_p(_ROW), width_px=_p(widths["name"] - 4),
                    font_px=_p(9), line_height=1.2, chrome=_p(4))
    if "desc" in widths:
        px = max(px, row_height(str(line.get("print_description") or ""), base=_p(_ROW),
                                width_px=_p(widths["desc"] - 4), font_px=_p(8), line_height=1.2,
                                chrome=_p(4)))
    return px / _SCALE


def _totals_html(data: dict[str, Any]) -> str:
    """QR · stamp · the five totals rows, bottom-anchored like the source."""
    seller = data.get("seller") or {}
    totals = data.get("totals") or {}
    qr_uri = qr_vector_data_uri(data.get("qr_payload"))
    qr = (
        f'<img src="{qr_uri}" alt="QR" style="position:absolute; left:{_x(_TOT_L)}px; top:{_p(_BAND_TOP)}px; '
        f'width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; display:block; background:#ffffff;">'
        if qr_uri else ""
    )
    tot_l = _TOT_L + _QR_PT + _QR_GAP
    k = (_TOT_R - tot_l) / sum(_TOT_SPLIT)
    widths = [w * k for w in _TOT_SPLIT]
    rows = (
        ("Total", totals.get("subtotal", totals.get("taxable", 0)), "الاجمالي"),
        ('Total <span style="font-size:{fs}px">Discount</span>', totals.get("discount", 0), "اجمالي الخصومات"),
        ("Total Taxable Amount", totals.get("taxable", totals.get("subtotal", 0)), "الاجمالي الخاضع للضريبة"),
        ("Total Tax", totals.get("vat", 0), "اجمالي الضريبة"),
        ("Total With Tax", totals.get("total", 0), "الاجمالي شامل الضريبة"),
    )
    top = _TOT_BOT - 5 * _TOT_ROW
    trs = "".join(
        f'<tr style="height:{_p(_TOT_ROW)}px;"><td class="en">{en.format(fs=_p(10))}</td>'
        f'<td class="v">{_money(val)}</td><td class="ar">{ar}</td></tr>'
        for en, val, ar in rows
    )
    table = (
        f'<table class="tot" style="left:{_x(tot_l)}px; top:{_p(top)}px; width:{_p(_TOT_R - tot_l)}px;">'
        "<colgroup>" + "".join(f'<col style="width:{_p(w)}px">' for w in widths) + f"</colgroup>{trs}</table>"
    )
    stamp_uri = company_stamp_data_uri(seller) if data.get("show_stamp") else ""
    stamp = ""
    if stamp_uri:
        s_h = top - _BAND_TOP - 3
        s_w = s_h * 1.25
        s_left = tot_l + widths[0] + widths[1] / 2 - s_w / 2
        stamp = _box(s_left, _BAND_TOP, s_w, s_h,
                     f'<img src="{stamp_uri}" alt="stamp" style="width:100%; height:100%; object-fit:contain; '
                     f'display:block; filter:{_STAMP_FILTER};">', "").replace("<div ", '<div data-company-stamp="1" ', 1)
    return qr + stamp + table


def _footer_html(data: dict[str, Any], index: int, count: int, printed: str) -> str:
    by = _esc(data.get("printed_by"))
    fs = f"font-size:{_p(10)}px; line-height:{_p(14)}px; white-space:nowrap;"
    return (
        _box(18.7, 798.6, 200, 14, f'<span dir="rtl">تاريخ الطباعة <bdi dir="ltr">{printed}</bdi></span>', fs)
        + _box(197.6, 798.6, 200, 14, f'<span dir="rtl">صفحة رقم&nbsp;&nbsp;(&nbsp;{index}&nbsp; / {count}&nbsp;)</span>',
               f"{fs} text-align:center;")
        + _box(370.3, 798.6, 200, 14, f"طباعة بواسطة : &nbsp;&nbsp;{by}", f"{fs} direction:rtl; text-align:right;")
        + _box(15.7, 816.1, 557.2, 1.0, "", "background:#000000;")
    )


def build_invoice_html_v30(data: dict[str, Any]) -> str:
    """Build «بنشر» from the shared invoice data dict."""
    lines = with_print_descriptions(data)
    cols = _columns(bool(data.get("show_description")))
    widths = {k: w for k, _a, _e, w in cols}
    totals = data.get("totals") or {}
    fixed = (_header_html(data.get("seller") or {}) + _info_html(data) + _party_html(data))
    printed = _esc(data.get("printed_at") or datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    colgroup = "".join(f'<col style="width:{_p(w)}px">' for *_x_, w in cols)
    head = (f'<tr style="height:{_p(_HEAD_AR)}px;">' + "".join(f'<th class="ar">{ar}</th>' for _k, ar, _e, _w in cols)
            + f'</tr><tr style="height:{_p(_HEAD_EN)}px;">'
            + "".join(f'<th class="en">{en}</th>' for _k, _a, en, _w in cols) + "</tr>")

    def row(line: dict[str, Any]) -> str:
        cells = {
            "no": str(line["_no"]),
            "code": _esc(line.get("code")),
            "name": _esc(line.get("name")),
            "desc": _esc(line.get("print_description")),
            "loc": "",
            "qty": _qty(line.get("qty")),
            "price": _money(line.get("price")),
            "taxable": _money(line.get("before")),
            "disc": "0.00",
            "rate": _rate(line.get("vat_rate")),
            "vat": _money(line.get("vat_amount")),
            "total": _money(line.get("total", _dec(line.get("before")) + _dec(line.get("vat_amount")))),
        }
        return f'<tr style="height:{_p(_ROW)}px;">' + "".join(
            f'<td class="c-{k}">{cells[k]}</td>' for k, *_r in cols) + "</tr>"

    sums = {
        "qty": _qty(sum((_dec(ln.get("qty")) for ln in lines), Decimal("0"))),
        "taxable": _money(totals.get("subtotal", sum((_dec(ln.get("before")) for ln in lines), Decimal("0")))),
        "disc": _money(totals.get("discount", 0)),
        "vat": _money(totals.get("vat", 0)),
        "total": _money(totals.get("total", 0)),
    }
    sum_row = f'<tr class="sum" style="height:{_p(_ROW)}px;">' + "".join(
        f'<td>{sums.get(k, "")}</td>' for k, *_r in cols) + "</tr>"

    numbered = [{**ln, "_no": i} for i, ln in enumerate(lines, start=1)]
    rows_top = _ITEMS_TOP + _HEAD_AR + _HEAD_EN
    budget = _PAGE_BOT - rows_top
    budget_last = _BAND_TOP - _TOT_GAP - _ROW - rows_top
    pages = paginate(numbered, lambda ln: _row_h(ln, widths), budget=budget, budget_last=budget_last)
    count = len(pages)
    sheets = []
    for index, page_lines in enumerate(pages, start=1):
        last = index == count
        body = "".join(row(ln) for ln in page_lines)
        if last:
            body += sum_row
        sheets.append(f"""
<div data-sheet class="sheet" style="{sheet_style(last=last)}">
{fixed}
  <table class="items" style="left:{_x(_ITEMS_L)}px; top:{_p(_ITEMS_TOP)}px;">
    <colgroup>{colgroup}</colgroup>
    <thead>{head}</thead>
    <tbody>{body}</tbody>
  </table>
{_totals_html(data) if last else ""}
{_footer_html(data, index, count, printed)}
</div>""")

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; font-family:{_SANS}; font-weight:700; color:#000000;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ position:relative; box-sizing:border-box; width:{_SHEET_W}px; height:{_SHEET_H}px;
            margin:24px auto; background:#ffffff; overflow:hidden; box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  .t {{ font-family:{_SERIF}; }}
  .reg {{ font-weight:400; }}
  .clamp2 {{ display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  table {{ border-collapse:collapse; position:absolute; table-layout:fixed; direction:ltr; }}
  td, th {{ box-sizing:border-box; padding:0 {_p(2)}px; text-align:center; vertical-align:middle;
            overflow:hidden; }}
  .grid td {{ border:{_RULE}px solid var(--rule); white-space:nowrap; text-overflow:clip; }}
  .grid td.en {{ font-size:{_p(8)}px; }}
  .grid td.ar {{ font-size:{_p(8.5)}px; direction:rtl; }}
  .grid td.v {{ direction:rtl; }}
  .items {{ width:{_p(_COLS[-1][3] - _ITEMS_L)}px; }}
  .items th {{ background:{_BAND}; border:{_RULE}px solid {_GREY}; font-weight:700; padding:0; white-space:nowrap; }}
  .items th.ar {{ font-size:{_p(10)}px; line-height:{_p(11.1)}px; direction:rtl; }}
  .items th.en {{ font-size:{_p(9)}px; line-height:{_p(10)}px; }}
  .items td {{ border:{_RULE}px solid {_GREY}; font-size:{_p(9)}px; line-height:1.2;
               overflow-wrap:anywhere; word-break:break-word; }}
  .items td.c-code {{ font-size:{_p(8)}px; }}
  .items td.c-name, .items td.c-desc {{ direction:rtl; }}
  .items td.c-desc {{ font-size:{_p(8)}px; }}
  .items tr.sum td {{ background:{_BAND}; }}
  .tot td {{ border:{_RULE}px solid {_GREY}; white-space:nowrap; }}
  .tot td.en {{ text-align:left; font-size:{_p(9)}px; padding-left:{_p(1.9)}px; }}
  .tot td.v {{ background:{_BAND}; font-size:{_p(10)}px; }}
  .tot td.ar {{ text-align:right; direction:rtl; font-size:{_p(10)}px; padding-right:{_p(1.9)}px; }}
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


__all__ = ["build_invoice_html_v30", "national_address"]
