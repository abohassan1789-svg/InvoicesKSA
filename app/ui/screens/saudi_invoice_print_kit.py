"""Shared building blocks for the in-house designs the user picked on 2026-10-18 —
three from the first ten-mock-up gallery
(``D:\\PHASEINV2\\mockups\\new_invoice_designs.html``):

* «النموذج الخامس عشر» — «البطاقات»       (:mod:`saudi_invoice_print_v22`)
* «النموذج السادس عشر» — «الشريط القطري»  (:mod:`saudi_invoice_print_v23`)
* «النموذج السابع عشر» — «الإجمالي أولًا» (:mod:`saudi_invoice_print_v24`)

and three from the second one
(``D:\\PHASEINV2\\mockups\\new_invoice_designs_batch2.html``):

* «النموذج الثامن عشر» — «بطاقة الصعود»        (:mod:`saudi_invoice_print_v25`)
* «النموذج التاسع عشر» — «المرآة ثنائية اللغة» (:mod:`saudi_invoice_print_v26`)
* «النموذج العشرون»    — «الخط الزمني»         (:mod:`saudi_invoice_print_v27`)

Unlike the layout replicas (v15–v21) these have no reference document: the
approved mock-up IS the spec. They share one data binding, one items table and
one page skeleton, so only the look (CSS + header) lives in each design module.

Page skeleton: a flow layout on a Letter sheet. An outer ``.page`` table's
thead/tfoot spacers reserve the top/bottom margins on every printed page; the
items table's ``<thead>`` repeats on a continuation page, and the last item +
the closing block (totals, QR, stamp) sit in ONE no-break ``<tbody>`` so the
totals never land on a page alone.

Each design reads its QR from ``data["qr_payload"]`` (the signed tags 1–9 code on
the Phase-2 screen); the «مرحلة أولى» wrappers swap in the tags 1–5 payload.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    QR_PRINT_PX,
    _STAMP_FILTER,
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
    qr_vector_data_uri,
)

SHEET_W = 816
SHEET_H = 1056

GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800'
    "&family=Tajawal:wght@400;500;700;800;900&family=Readex+Pro:wght@300;400;600;700"
    '&display=swap" rel="stylesheet">'
)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def money(value: Any) -> str:
    return f"{dec(value):,.2f}"


def qty(value: Any) -> str:
    text = format(dec(value).normalize(), ",f")
    return text if text not in ("", "-0") else "0"


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def esc_lines(value: Any) -> str:
    """Escape, keeping the line breaks typed in the master record."""
    return "<br>".join(html.escape(p.strip()) for p in str(value or "").splitlines() if p.strip())


def ltr(text: str) -> str:
    """Isolate a figure/code so RTL text around it never reorders it."""
    return f'<bdi dir="ltr">{text}</bdi>'


def fmt_date(issued: Any) -> str:
    if isinstance(issued, (datetime.datetime, datetime.date)):
        return issued.strftime("%Y-%m-%d")
    return str(issued or "")


def fmt_time(issued: Any) -> str:
    if isinstance(issued, datetime.datetime):
        return issued.strftime("%H:%M")
    return ""


def vat_rate_label(lines: list[dict[str, Any]]) -> str:
    """«15%» — the one VAT rate on the invoice (falls back to 15)."""
    rates = {dec(ln.get("vat_rate")).normalize() for ln in lines if ln.get("vat_rate") not in (None, "")}
    rate = f"{rates.pop():f}" if len(rates) == 1 else "15"
    return f"{rate}%"


# ---------------------------------------------------------------------------
# Data binding
# ---------------------------------------------------------------------------
def invoice_context(data: dict[str, Any]) -> dict[str, Any]:
    """Everything a design prints, already escaped / formatted."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = list(data.get("lines") or [])
    issued = data.get("issue_datetime")
    discount = dec(totals.get("discount", 0))
    rate = dec(totals.get("discount_rate", 0))
    return {
        "seller": seller,
        "customer": customer,
        "lines": lines,
        "number": esc(data.get("invoice_number")),
        "date": esc(fmt_date(issued)),
        "time": esc(fmt_time(issued)),
        "payment": esc(data.get("payment_label") or "نقدي"),
        "subtotal": money(totals.get("subtotal", totals.get("taxable", 0))),
        "discount": money(discount) if discount else "",
        "discount_rate": f"{rate.normalize():f}%" if discount and rate else "",
        "vat": money(totals.get("vat", 0)),
        "total": money(totals.get("total", 0)),
        "words": esc(amount_in_words_ar(totals.get("total", 0))),
        "vat_rate": vat_rate_label(lines),
        "show_unit": bool(data.get("show_unit", True)),
        "show_desc": bool(data.get("show_description")),
    }


def seller_id_line(seller: dict[str, Any], sep: str = " · ") -> str:
    """«الرقم الضريبي … · السجل التجاري …» — CR is optional (since 2026-09-29)."""
    parts = []
    if seller.get("vat"):
        parts.append(f"الرقم الضريبي {ltr(esc(seller.get('vat')))}")
    if seller.get("cr"):
        parts.append(f"السجل التجاري {ltr(esc(seller.get('cr')))}")
    return sep.join(parts)


def party_lines(party: dict[str, Any], *, with_vat: bool = True) -> str:
    """Address · VAT · CR lines (each only when the record has it)."""
    out = []
    if party.get("address"):
        out.append(f"<div>{esc_lines(party.get('address'))}</div>")
    if with_vat and party.get("vat"):
        out.append(f"<div>الرقم الضريبي {ltr(esc(party.get('vat')))}</div>")
    if party.get("cr"):
        out.append(f"<div>السجل التجاري {ltr(esc(party.get('cr')))}</div>")
    return "".join(out)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def logo_img(seller: dict[str, Any], width: int, height: int) -> str:
    """The company logo, «Zoom»-fitted (scaled to the box, never stretched)."""
    uri = company_logo_data_uri(seller)
    if not uri:
        return ""
    return (
        f'<img src="{uri}" alt="logo" style="width:{width}px; height:{height}px; '
        'object-fit:contain; display:block;">'
    )


def qr_img(data: dict[str, Any], size: int = QR_PRINT_PX) -> str:
    uri = qr_vector_data_uri(data.get("qr_payload"))
    if not uri:
        return ""
    return (
        f'<img src="{uri}" alt="QR" style="width:{size}px; height:{size}px; '
        'display:block; background:#ffffff;">'
    )


def stamp_img(data: dict[str, Any], width: int = 200, height: int = 150) -> str:
    """The company stamp — only when «إظهار الختم» is ticked and one is stored."""
    if not data.get("show_stamp"):
        return ""
    uri = company_stamp_data_uri(data.get("seller"))
    if not uri:
        return ""
    return (
        f'<div data-company-stamp="1"><img src="{uri}" alt="stamp" style="width:{width}px; '
        f'height:{height}px; object-fit:contain; display:block; filter:{_STAMP_FILTER};"></div>'
    )


# ---------------------------------------------------------------------------
# Items table
# ---------------------------------------------------------------------------
# English sub-titles for the bilingual column headers (النموذج التاسع عشر).
_EN_TITLES = {
    "no": "No.", "name": "Item", "unit": "Unit", "qty": "Qty", "price": "Unit Price",
    "before": "Taxable Amount", "vat": "VAT", "total": "Total",
}


def item_columns(ctx: dict[str, Any], content_w: int) -> list[tuple[str, str, int]]:
    """(key, title, width px) physical right → left; «الصنف» takes what is left."""
    fixed = [
        ("no", "#", 34),
        ("name", "الصنف", 0),
        ("unit", "الوحدة", 62),
        ("qty", "الكمية", 60),
        ("price", "السعر", 78),
        ("before", "قبل الضريبة", 92),
        ("vat", f"الضريبة {ctx['vat_rate']}", 82),
        ("total", "الإجمالي", 96),
    ]
    if not ctx["show_unit"]:
        fixed = [c for c in fixed if c[0] != "unit"]
    name_w = content_w - sum(w for _k, _t, w in fixed)
    return [(k, t, name_w if k == "name" else w) for k, t, w in fixed]


def item_cells(line: dict[str, Any], index: int, ctx: dict[str, Any]) -> dict[str, str]:
    name = esc(line.get("name"))
    desc = str(line.get("description") or "").strip() if ctx["show_desc"] else ""
    if desc:
        name += f'<div class="desc">{esc_lines(desc)}</div>'
    return {
        "no": ltr(str(index)),
        "name": name,
        "unit": esc(line.get("unit")),
        "qty": ltr(qty(line.get("qty"))),
        "price": ltr(money(line.get("price"))),
        "before": ltr(money(line.get("before"))),
        "vat": ltr(money(line.get("vat_amount"))),
        "total": ltr(money(line.get("total"))),
    }


def items_table(ctx: dict[str, Any], content_w: int, closing_html: str, *, bilingual: bool = False) -> str:
    """The items table with the closing block glued to the last item.

    ``bilingual`` adds an English sub-title (``<span class="en">``) under each
    Arabic column title."""
    cols = item_columns(ctx, content_w)
    colgroup = "".join(f'<col style="width:{w}px">' for _k, _t, w in cols)
    sub = (lambda k: f'<span class="en">{_EN_TITLES[k]}</span>') if bilingual else (lambda k: "")
    head = "".join(f'<th class="c-{k}">{t}{sub(k)}</th>' for k, t, _w in cols)

    def row(line: dict[str, Any], i: int) -> str:
        cells = item_cells(line, i, ctx)
        return "<tr>" + "".join(f'<td class="c-{k}">{cells[k]}</td>' for k, _t, _w in cols) + "</tr>"

    lines = ctx["lines"]
    if lines:
        main = "".join(row(ln, i) for i, ln in enumerate(lines[:-1], start=1))
        last = row(lines[-1], len(lines))
    else:
        main = ""
        last = f'<tr><td colspan="{len(cols)}" style="color:#999;">لا توجد أصناف</td></tr>'
    return f"""<table class="items">
      <colgroup>{colgroup}</colgroup>
      <thead><tr>{head}</tr></thead>
      <tbody>{main}</tbody>
      <tbody class="summary">
        {last}
        <tr class="closing"><td colspan="{len(cols)}">{closing_html}</td></tr>
      </tbody>
    </table>"""


def totals_rows(ctx: dict[str, Any], *, grand_class: str = "g", currency: str = " ر.س") -> str:
    """قبل الضريبة · [الخصم] · الضريبة · الإجمالي, as label/value flex rows."""
    rows = [("الإجمالي قبل الضريبة", ctx["subtotal"])]
    if ctx["discount"]:
        label = "الخصم" + (f" {ltr(ctx['discount_rate'])}" if ctx["discount_rate"] else "")
        rows.append((label, "-" + ctx["discount"]))
    rows.append((f"ضريبة القيمة المضافة {ltr(ctx['vat_rate'])}", ctx["vat"]))
    out = "".join(f"<div><span>{lab}</span>{ltr(val)}</div>" for lab, val in rows)
    out += f'<div class="{grand_class}"><span>الإجمالي شامل الضريبة</span>{ltr(ctx["total"] + currency)}</div>'
    return out


# ---------------------------------------------------------------------------
# Page skeleton
# ---------------------------------------------------------------------------
BASE_CSS = f"""
  html, body {{ margin:0; padding:0; }}
  body {{ background:#e9e9ea; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ box-sizing:border-box; width:{SHEET_W}px; min-height:{SHEET_H}px; margin:24px auto;
            background:#ffffff; direction:rtl; text-align:right; position:relative;
            box-shadow:0 6px 28px rgba(0,0,0,.16); }}
  table {{ border-collapse:collapse; }}
  td, th {{ box-sizing:border-box; }}
  tr {{ break-inside:avoid; page-break-inside:avoid; }}
  thead {{ display:table-header-group; }}
  tfoot {{ display:table-footer-group; }}
  .page {{ width:100%; table-layout:fixed; }}
  .page > * > tr > td {{ padding:0; vertical-align:top; }}
  .summary {{ break-inside:avoid; page-break-inside:avoid; }}
  .items {{ width:100%; table-layout:fixed; }}
  .items > thead > tr > th {{ text-align:right; white-space:nowrap; }}
  .items > tbody > tr > td {{ vertical-align:top; overflow-wrap:anywhere; word-break:break-word; }}
  .items > tbody > tr.closing > td {{ padding:0; border:0; background:transparent; }}
  .items .c-no {{ text-align:center; white-space:nowrap; }}
  .items .desc {{ font-size:11.5px; opacity:.75; margin-top:2px; }}
  .wrap {{ overflow-wrap:anywhere; word-break:break-word; min-width:0; }}
  @page {{ size:Letter; margin:0; }}
  @media print {{
    body {{ background:#ffffff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; }}
  }}
"""


def page_html(*, css: str, sheet_class: str, top: int, bottom: int, body: str, extra: str = "") -> str:
    """A full HTML document: the shared skeleton around one design's body.

    ``top``/``bottom`` are the page margins reserved on every printed page;
    ``extra`` is markup placed directly in the sheet (e.g. a fixed footer band).
    """
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{GOOGLE_FONTS}
<style>{BASE_CSS}{css}</style>
</head>
<body>
  <div class="sheet {sheet_class}">
  {extra}
  <table class="page">
    <thead><tr><td style="height:{top}px;"></td></tr></thead>
    <tfoot><tr><td style="height:{bottom}px;"></td></tr></tfoot>
    <tbody><tr><td>
{body}
    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""
