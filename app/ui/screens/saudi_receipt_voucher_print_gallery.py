"""Eight receipt-voucher («سند قبض») layouts picked from the 2026-10-20 gallery.

The user asked for fifteen fresh voucher mock-ups (one page, numbered) and chose
eight of them; this module builds those eight from live data. A سند قبض carries
no ZATCA QR, so every layout is offered, unchanged, in BOTH pickers — Phase-2's
:func:`saudi_receipt_voucher_print.choose_voucher_builder` and the Phase-1
«مرحلة أولى ← سندات» roster in ``saudi_voucher_print_phase1``.

Every layout carries exactly what the user listed for the voucher:

* the seller on top (name · السجل التجاري · الرقم الضريبي · address) beside the
  company logo — a dashed «الشعار» placeholder keeps its place when the company
  has none;
* اسم العميل · المبلغ (figures + words in «ريال سعودي» and «هللة») · رقم فاتورة
  البيع · البيان / ملاحظات;
* at the very bottom the signature on one side (right) and the company stamp on
  the other (left); with no stored stamp that corner is simply left blank.

As in the gallery, each design is a half-A4 landscape block (794×561) printed at
the top of the A4 sheet every voucher prints on. Its footer sits at the block's
bottom but stays in the flow, so a long customer name or purpose pushes it down
instead of running underneath it.

Gallery number → picker label (the label is what both pickers show):

* 5  الزاوية المائلة    → «سند الزاوية المائلة»
* 6  اللوحة المركزية    → «سند اللوحة المركزية»
* 7  الترويسة الموجية   → «سند الترويسة الموجية»
* 8  البطاقات الأربع    → «سند البطاقات الأربع»
* 11 زوايا برونزية      → «سند الزوايا البرونزية»
* 12 النصف العلوي الملون → «سند النصف الملون»
* 13 قسيمة الإيداع      → «سند قسيمة الإيداع»
* 15 الشبكة السويسرية   → «سند الشبكة السويسرية»

Data keys (the shared voucher dict): ``number``, ``issue_date``, ``amount``,
``received_from``, ``purpose`` (``\\n`` → a new line), ``seller`` and the
optional ``reference`` — the sales invoice this receipt is for, which the sales
screen passes; the vouchers screen has none, so رقم فاتورة البيع prints «—».
Presentation only: nothing here touches the database.
"""

from __future__ import annotations

import datetime
import html
from collections.abc import Callable
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
)
from app.ui.screens.saudi_receipt_voucher_print import _money

_FONTS = (
    "https://fonts.googleapis.com/css2?family=Almarai:wght@400;700;800"
    "&family=Cairo:wght@400;600;700;800&family=El+Messiri:wght@500;700"
    "&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700"
    "&family=Noto+Naskh+Arabic:wght@400;600;700&family=Readex+Pro:wght@300;400;600;700"
    "&family=Tajawal:wght@400;500;700;800&display=swap"
)
_FALLBACK = "'Noto Sans Arabic','Tahoma','Arial',sans-serif"
_DASH = "—"


# ======================================================================
# Shared pieces
# ======================================================================
def _esc_lines(value: Any) -> str:
    """Escape ``value`` and keep its own line breaks."""
    text = str(value or "").strip()
    return "<br>".join(html.escape(part.strip()) for part in text.splitlines() if part.strip())


def _date_dmy(value: Any) -> str:
    """«20/10/2026»."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return value.strftime("%d/%m/%Y")
    return html.escape(str(value or ""))


def _words(amount: Any) -> str:
    """The amount in words, in «ريال سعودي» and «هللة» as the user asked."""
    return html.escape(amount_in_words_ar(amount).replace("ريالاً", "ريالاً سعودياً"))


def _fields(data: dict[str, Any]) -> dict[str, str]:
    """Every value a layout prints, escaped once."""
    seller = data.get("seller") or {}
    meta = []
    cr = str(seller.get("cr") or "").strip()
    vat = str(seller.get("vat") or "").strip()
    if cr:
        meta.append(f'السجل التجاري <bdi dir="ltr">{html.escape(cr)}</bdi>')
    if vat:
        meta.append(f'الرقم الضريبي <bdi dir="ltr">{html.escape(vat)}</bdi>')
    address = _esc_lines(seller.get("address"))
    if address:
        meta.append(address)
    reference = str(data.get("reference") or "").strip()
    return {
        "name": html.escape(str(seller.get("name") or "")),
        "meta": "<br>".join(meta),
        "meta_inline": " · ".join(m.replace("<br>", " · ") for m in meta),
        "number": f'<bdi dir="ltr">{html.escape(str(data.get("number") or ""))}</bdi>',
        "date": f'<bdi dir="ltr">{_date_dmy(data.get("issue_date"))}</bdi>',
        "amount": f'<bdi dir="ltr">{_money(data.get("amount"))}</bdi>',
        "amount_raw": _money(data.get("amount")),
        "words": _words(data.get("amount")),
        "customer": html.escape(str(data.get("received_from") or "")),
        "invoice": f'<bdi dir="ltr">{html.escape(reference)}</bdi>' if reference else _DASH,
        "invoice_raw": reference,
        "purpose": _esc_lines(data.get("purpose")) or _DASH,
    }


def _logo(data: dict[str, Any], size: int, color: str, bg: str = "none") -> str:
    """The company logo in a ``size``-px box, or the dashed «الشعار» placeholder."""
    uri = company_logo_data_uri(data.get("seller") or {})
    if uri:
        return (
            f'<img src="{uri}" alt="logo" style="width:{size}px;height:{size}px;'
            f'object-fit:contain;display:block;flex:none;">'
        )
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 60 60" style="flex:none;display:block">'
        f'<rect x="1.5" y="1.5" width="57" height="57" rx="8" fill="{bg}" stroke="{color}" '
        f'stroke-width="1.5" stroke-dasharray="4 3"/>'
        f'<path d="M30 13c7 6 7 14 0 20c-7-6-7-14 0-20zM18 26c8 1 12 6 12 13c-8-1-12-6-12-13z'
        f'M42 26c-8 1-12 6-12 13c8-1 12-6 12-13z" fill="{color}" opacity=".85"/>'
        f'<text x="30" y="52" text-anchor="middle" font-size="8.5" fill="{color}" '
        f"font-family=\"Tajawal,sans-serif\">الشعار</text></svg>"
    )


def _foot(data: dict[str, Any], color: str) -> str:
    """Signature on the right, the company stamp (if any) on the left."""
    uri = company_stamp_data_uri(data.get("seller") or {})
    stamp = f'<img src="{uri}" alt="ختم الشركة">' if uri else ""
    return (
        f'<div class="foot" style="color:{color}">'
        f'<div class="sig"><div class="sig-ln">التوقيع</div></div>'
        f'<div class="stamp">{stamp}</div></div>'
    )


def _doc(cls: str, font: str, ink: str, css: str, body: str) -> str:
    """Wrap one half-sheet design in the A4 print scaffold every voucher uses."""
    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<link href="{_FONTS}" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ width:794px; min-height:1123px; position:relative; margin:0 auto; background:#fff; direction:rtl;
    box-sizing:border-box; box-shadow:0 1px 6px rgba(0,0,0,.12); overflow:hidden; }}
  .sheet * {{ box-sizing:border-box; }}
  bdi {{ unicode-bidi:isolate; }}
  .v {{ position:relative; width:794px; min-height:561px; display:flex; flex-direction:column; overflow:hidden;
    font-family:{font},{_FALLBACK}; color:{ink}; font-variant-numeric:tabular-nums;
    overflow-wrap:anywhere; word-break:break-word; }}
  .foot {{ margin-top:auto; position:relative; display:flex; justify-content:space-between; align-items:flex-end;
    padding:18px 44px 22px; min-height:140px; }}
  .sig {{ width:190px; height:70px; display:flex; align-items:flex-end; }}
  .sig-ln {{ width:100%; border-top:1px solid currentColor; padding-top:5px; text-align:center; font-size:13px; font-weight:600; }}
  .stamp {{ width:150px; height:118px; display:flex; align-items:center; justify-content:center; }}
  .stamp img {{ max-width:150px; max-height:118px; object-fit:contain; display:block; }}
  {css}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#fff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; break-inside:avoid; page-break-inside:avoid; }}
  }}
</style>
</head>
<body>
  <div class="sheet"><div class="v {cls}">
{body}
  </div></div>
</body>
</html>"""


# ======================================================================
# Gallery 5 — «سند الزاوية المائلة»
# ======================================================================
def build_receipt_voucher_html_slant(data: dict[str, Any]) -> str:
    """A graphite triangle with an amber edge in the top-left corner carries the
    title; the fields sit on amber underlines."""
    f = _fields(data)
    css = """
  .g5 { padding:30px 42px 0; }
  .g5 .tri2 { position:absolute; top:0; left:0; width:300px; height:172px; background:#e0a526; clip-path:polygon(0 0,100% 0,0 100%); }
  .g5 .tri { position:absolute; top:0; left:0; width:260px; height:150px; background:#2b2f36; clip-path:polygon(0 0,100% 0,0 100%); }
  .g5 .tt { position:absolute; top:22px; left:28px; color:#fff; }
  .g5 .tt h4 { margin:0; font-size:28px; font-weight:800; }
  .g5 .tt div { font-size:12px; color:#f3d48c; }
  .g5 .co { position:relative; display:flex; gap:12px; align-items:center; margin-left:250px; }
  .g5 .co h3 { margin:0; font-size:19px; font-weight:800; }
  .g5 .meta { font-size:11.5px; color:#6b707a; line-height:1.55; }
  .g5 .meta2 { display:flex; gap:26px; margin:18px 0 10px; font-size:13px; }
  .g5 .meta2 b { font-weight:800; }
  .g5 .f { border-bottom:2px solid #e0a526; padding:4px 2px 6px; margin-bottom:8px; }
  .g5 .f span { display:block; font-size:11px; color:#7b808a; }
  .g5 .f b { font-size:15.5px; font-weight:700; }
  .g5 .amt { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; }
  .g5 .amt i { font-style:normal; flex:none; background:#2b2f36; color:#fff; padding:1px 10px; border-radius:2px; font-size:15px; font-weight:700; }
  .g5 .corner { position:absolute; bottom:0; right:0; width:70px; height:40px; background:#e0a526; clip-path:polygon(100% 0,100% 100%,0 100%); }
"""
    body = f"""
    <div class="tri2"></div><div class="tri"></div>
    <div class="tt"><h4>سند قبض</h4><div>رقم {f['number']}</div></div>
    <div class="co">{_logo(data, 58, "#2b2f36")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div>
    <div class="meta2"><span>التاريخ <b>{f['date']}</b></span><span>رقم فاتورة البيع <b>{f['invoice']}</b></span></div>
    <div class="f"><span>اسم العميل</span><b>{f['customer']}</b></div>
    <div class="f amt"><div><span>المبلغ بالحروف</span><b>{f['words']}</b></div><i>{f['amount']} ر.س</i></div>
    <div class="f"><span>البيان / ملاحظات</span><b style="font-weight:500">{f['purpose']}</b></div>
    <div class="corner"></div>
    {_foot(data, "#2b2f36")}"""
    return _doc("g5", "'Tajawal'", "#2b2f36", css, body)


# ======================================================================
# Gallery 6 — «سند اللوحة المركزية»
# ======================================================================
def build_receipt_voucher_html_panel(data: dict[str, Any]) -> str:
    """Every field in white boxes on one soft blue-grey rounded panel, with small
    captions above the values like an on-screen form."""
    f = _fields(data)
    css = """
  .g6 { padding:26px 40px 0; }
  .g6 .top { display:flex; justify-content:space-between; align-items:center; gap:20px; }
  .g6 .co { display:flex; gap:12px; align-items:center; }
  .g6 .co h3 { margin:0 0 3px; font-size:17px; font-weight:800; }
  .g6 .meta { font-size:11px; color:#5d7186; line-height:1.55; }
  .g6 .ttl { flex:none; text-align:center; border:1.5px solid #1d5c8c; border-radius:8px; padding:6px 18px; }
  .g6 .ttl h4 { margin:0; font-size:20px; color:#1d5c8c; font-weight:800; }
  .g6 .ttl div { font-size:11.5px; color:#5d7186; }
  .g6 .panel { background:#eef3f8; border-radius:12px; padding:14px 18px; margin-top:16px; display:grid; grid-template-columns:1fr 1fr; gap:12px 20px; }
  .g6 .p { min-width:0; }
  .g6 .p span { display:block; font-size:11px; color:#5d7186; margin-bottom:3px; }
  .g6 .p b { display:block; background:#fff; border-radius:6px; padding:7px 10px; font-size:14px; font-weight:700; }
  .g6 .p.w2 { grid-column:span 2; }
  .g6 .p .big { font-size:20px; color:#1d5c8c; }
"""
    body = f"""
    <div class="top"><div class="co">{_logo(data, 58, "#1d5c8c")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div>
      <div class="ttl"><h4>سند قبض</h4><div>رقم {f['number']} · {f['date']}</div></div></div>
    <div class="panel">
      <div class="p"><span>اسم العميل</span><b>{f['customer']}</b></div>
      <div class="p"><span>رقم فاتورة البيع</span><b>{f['invoice']}</b></div>
      <div class="p w2"><span>المبلغ</span><b><span class="big">{f['amount']} ر.س</span>&nbsp;&nbsp;{f['words']}</b></div>
      <div class="p w2"><span>البيان / ملاحظات</span><b style="font-weight:400">{f['purpose']}</b></div>
    </div>
    {_foot(data, "#18324a")}"""
    return _doc("g6", "'Almarai'", "#18324a", css, body)


# ======================================================================
# Gallery 7 — «سند الترويسة الموجية»
# ======================================================================
def build_receipt_voucher_html_wave(data: dict[str, Any]) -> str:
    """A deep-blue letterhead with a wavy lower edge carrying the logo and title in
    white; a matching thin wave closes the bottom of the voucher."""
    f = _fields(data)
    css = """
  .g7 .wave { position:absolute; top:0; left:0; width:794px; height:156px; }
  .g7 .head { position:relative; display:flex; justify-content:space-between; align-items:flex-start; gap:20px; padding:20px 40px 0; color:#fff; min-height:150px; }
  .g7 .co { display:flex; gap:12px; align-items:center; }
  .g7 .co h3 { margin:0; font-size:19px; font-weight:800; }
  .g7 .meta { font-size:11px; color:#c8daf0; line-height:1.5; }
  .g7 .tt { flex:none; text-align:left; }
  .g7 .tt h4 { margin:0; font-size:26px; font-weight:800; }
  .g7 .tt div { font-size:12px; color:#c8daf0; }
  .g7 .body { position:relative; padding:4px 44px 0; }
  .g7 .chip { display:inline-block; margin:0 0 12px; background:#d6e6f5; color:#123c69; border-radius:22px; padding:4px 18px; font-weight:800; font-size:18px; }
  .g7 .chips { text-align:left; }
  .g7 .rw { display:flex; gap:12px; align-items:baseline; margin-bottom:12px; font-size:15px; }
  .g7 .rw .k { width:120px; flex:none; font-weight:700; font-size:13.5px; color:#2d6aa3; }
  .g7 .rw .val { flex:1; min-width:0; border-bottom:1px solid #c9daeb; font-weight:600; padding-bottom:2px; }
  .g7 .foot { padding-bottom:46px; }
  .g7 .fw { position:absolute; bottom:0; left:0; width:794px; height:34px; }
"""
    body = f"""
    <svg class="wave" viewBox="0 0 794 132" preserveAspectRatio="none"><path d="M0 0H794V96C640 140 520 70 380 98S120 132 0 104Z" fill="#123c69"/><path d="M0 104C120 132 240 120 380 98S640 140 794 96V104C640 148 520 80 380 106S120 140 0 112Z" fill="#7fb0dd"/></svg>
    <div class="head"><div class="co">{_logo(data, 56, "#ffffff")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div>
      <div class="tt"><h4>سند قبض</h4><div>رقم {f['number']} · {f['date']}</div></div></div>
    <div class="body">
      <div class="chips"><span class="chip">{f['amount']} ر.س</span></div>
      <div class="rw"><span class="k">اسم العميل</span><span class="val">{f['customer']}</span></div>
      <div class="rw"><span class="k">المبلغ بالحروف</span><span class="val">{f['words']}</span></div>
      <div class="rw"><span class="k">رقم فاتورة البيع</span><span class="val">{f['invoice']}</span></div>
      <div class="rw"><span class="k">البيان</span><span class="val">{f['purpose']}</span></div>
    </div>
    {_foot(data, "#123c69")}
    <svg class="fw" viewBox="0 0 794 34" preserveAspectRatio="none"><path d="M0 20C160 0 300 34 420 18S660 4 794 22V34H0Z" fill="#123c69"/></svg>"""
    return _doc("g7", "'Cairo'", "#123c69", css, body)


# ======================================================================
# Gallery 8 — «سند البطاقات الأربع»
# ======================================================================
def build_receipt_voucher_html_tiles(data: dict[str, Any]) -> str:
    """Four bold tiles — voucher no. · date · invoice no. · amount (saffron) —
    readable at a glance, then the rest of the details on ruled lines."""
    f = _fields(data)
    css = """
  .g8 { padding:28px 40px 0; }
  .g8 .top { display:flex; justify-content:space-between; align-items:center; gap:20px; }
  .g8 .co { display:flex; gap:12px; align-items:center; }
  .g8 .co h3 { margin:0 0 3px; font-size:18px; }
  .g8 .meta { font-size:11px; color:#6c7079; line-height:1.55; }
  .g8 .top h4 { flex:none; margin:0; font-size:30px; font-weight:700; border-bottom:4px solid #f2b134; line-height:1.3; }
  .g8 .tiles { display:grid; grid-template-columns:1fr 1fr 1fr 1.6fr; gap:8px; margin:18px 0 16px; }
  .g8 .tile { border:1.5px solid #22252a; border-radius:6px; padding:7px 12px; min-width:0; }
  .g8 .tile span { display:block; font-size:10.5px; color:#6c7079; }
  .g8 .tile b { font-size:17px; }
  .g8 .tile.y { background:#f2b134; border-color:#f2b134; }
  .g8 .tile.y span { color:#5a4310; }
  .g8 .tile.y b { font-size:21px; }
  .g8 .rw { display:flex; gap:12px; margin-bottom:11px; font-size:14.5px; align-items:baseline; }
  .g8 .rw .k { width:110px; flex:none; font-size:12.5px; color:#6c7079; }
  .g8 .rw .val { flex:1; min-width:0; border-bottom:1px solid #e3e4e6; padding-bottom:3px; font-weight:600; }
"""
    body = f"""
    <div class="top"><div class="co">{_logo(data, 56, "#22252a")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div><h4>سند قبض</h4></div>
    <div class="tiles">
      <div class="tile"><span>رقم السند</span><b>{f['number']}</b></div>
      <div class="tile"><span>التاريخ</span><b>{f['date']}</b></div>
      <div class="tile"><span>رقم فاتورة البيع</span><b>{f['invoice']}</b></div>
      <div class="tile y"><span>المبلغ (ريال سعودي)</span><b>{f['amount']}</b></div>
    </div>
    <div class="rw"><span class="k">اسم العميل</span><span class="val">{f['customer']}</span></div>
    <div class="rw"><span class="k">المبلغ بالحروف</span><span class="val">{f['words']}</span></div>
    <div class="rw"><span class="k">البيان</span><span class="val">{f['purpose']}</span></div>
    {_foot(data, "#22252a")}"""
    return _doc("g8", "'IBM Plex Sans Arabic'", "#22252a", css, body)


# ======================================================================
# Gallery 11 — «سند الزوايا البرونزية»
# ======================================================================
def build_receipt_voucher_html_bronze(data: dict[str, Any]) -> str:
    """Bronze L-brackets in the four corners instead of a full frame, and the
    fields in a light four-cell table under a «◆ سند قبض ◆» title."""
    f = _fields(data)
    css = """
  .g11 { padding:32px 50px 0; }
  .g11 .c { position:absolute; width:40px; height:40px; border:0 solid #8a6a2f; }
  .g11 .c1 { top:14px; right:14px; border-top-width:3px; border-right-width:3px; }
  .g11 .c2 { top:14px; left:14px; border-top-width:3px; border-left-width:3px; }
  .g11 .c3 { bottom:14px; right:14px; border-bottom-width:3px; border-right-width:3px; }
  .g11 .c4 { bottom:14px; left:14px; border-bottom-width:3px; border-left-width:3px; }
  .g11 .top { display:flex; justify-content:space-between; align-items:center; gap:20px; }
  .g11 .co { display:flex; gap:12px; align-items:center; }
  .g11 .co h3 { margin:0 0 2px; font-family:'El Messiri',serif; font-size:19px; }
  .g11 .meta { font-size:11px; color:#6d6252; line-height:1.55; }
  .g11 .no { flex:none; text-align:left; font-size:12.5px; line-height:1.7; }
  .g11 .no b { color:#8a6a2f; }
  .g11 .t { text-align:center; margin:12px 0 14px; font-family:'El Messiri',serif; font-size:23px; color:#8a6a2f; }
  .g11 .t i { font-style:normal; font-size:11px; vertical-align:middle; margin:0 10px; }
  .g11 .g { display:grid; grid-template-columns:1.25fr 1fr; border-top:1px solid #cbb48a; border-bottom:1px solid #cbb48a; }
  .g11 .g > div { padding:8px 12px; min-width:0; }
  .g11 .g > div.r { border-left:1px solid #cbb48a; }
  .g11 .g > div.w2 { grid-column:span 2; border-top:1px solid #cbb48a; }
  .g11 .g span { display:block; font-size:11px; color:#8a6a2f; font-weight:600; }
  .g11 .g b { font-size:14.5px; }
"""
    body = f"""
    <i class="c c1"></i><i class="c c2"></i><i class="c c3"></i><i class="c c4"></i>
    <div class="top"><div class="co">{_logo(data, 56, "#8a6a2f")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div>
      <div class="no">رقم السند <b>{f['number']}</b><br>التاريخ <b>{f['date']}</b></div></div>
    <div class="t"><i>◆</i>سند قبض<i>◆</i></div>
    <div class="g">
      <div class="r"><span>اسم العميل</span><b>{f['customer']}</b></div>
      <div><span>رقم فاتورة البيع</span><b>{f['invoice']}</b></div>
      <div class="w2"><span>المبلغ</span><b>{f['amount']} ر.س · {f['words']}</b></div>
      <div class="w2"><span>البيان / ملاحظات</span>{f['purpose']}</div>
    </div>
    {_foot(data, "#2c261c")}"""
    return _doc("g11", "'Noto Naskh Arabic'", "#2c261c", css, body)


# ======================================================================
# Gallery 12 — «سند النصف الملون»
# ======================================================================
def build_receipt_voucher_html_tinted(data: dict[str, Any]) -> str:
    """The upper part on a pale lavender wash (letterhead, title, white amount box);
    the lower part white for the details and the sign-off."""
    f = _fields(data)
    css = """
  .g12 .tint { background:#eceef8; padding:24px 40px 18px; }
  .g12 .top { display:flex; justify-content:space-between; align-items:center; gap:20px; }
  .g12 .co { display:flex; gap:12px; align-items:center; }
  .g12 .co h3 { margin:0 0 2px; font-size:18px; font-weight:800; }
  .g12 .meta { font-size:11px; color:#62668a; line-height:1.55; }
  .g12 .tt { flex:none; text-align:left; font-size:12px; color:#62668a; line-height:1.7; }
  .g12 .tt b { color:#2a2d4a; }
  .g12 .row2 { display:flex; justify-content:space-between; align-items:flex-end; margin-top:12px; }
  .g12 .row2 h4 { margin:0; font-size:32px; font-weight:800; color:#4b4f7a; }
  .g12 .box { background:#fff; border-radius:8px; padding:6px 16px; text-align:left; box-shadow:0 1px 0 #d4d7ea; }
  .g12 .box span { display:block; font-size:10.5px; color:#62668a; }
  .g12 .box b { font-size:24px; font-weight:800; color:#4b4f7a; }
  .g12 .lo { padding:16px 40px 0; }
  .g12 .rw { display:flex; gap:12px; margin-bottom:11px; font-size:15px; align-items:baseline; }
  .g12 .rw .k { width:120px; flex:none; color:#62668a; font-size:13px; }
  .g12 .rw .val { flex:1; min-width:0; font-weight:700; border-bottom:1px dashed #c5c8e0; padding-bottom:2px; }
"""
    body = f"""
    <div class="tint">
      <div class="top"><div class="co">{_logo(data, 56, "#4b4f7a", "#fff")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div>
        <div class="tt">رقم السند <b>{f['number']}</b><br>التاريخ <b>{f['date']}</b></div></div>
      <div class="row2"><h4>سند قبض</h4><div class="box"><span>المبلغ المستلم</span><b>{f['amount']} ر.س</b></div></div>
    </div>
    <div class="lo">
      <div class="rw"><span class="k">اسم العميل</span><span class="val">{f['customer']}</span></div>
      <div class="rw"><span class="k">المبلغ بالحروف</span><span class="val">{f['words']}</span></div>
      <div class="rw"><span class="k">رقم فاتورة البيع</span><span class="val">{f['invoice']}</span></div>
      <div class="rw"><span class="k">البيان</span><span class="val" style="font-weight:500">{f['purpose']}</span></div>
    </div>
    {_foot(data, "#2a2d4a")}"""
    return _doc("g12", "'Tajawal'", "#2a2d4a", css, body)


# ======================================================================
# Gallery 13 — «سند قسيمة الإيداع»
# ======================================================================
def _digit_boxes(text: str) -> str:
    """One box per character («.» and «,» become narrow gaps), left to right."""
    cells = []
    for ch in text:
        if ch == ",":
            continue
        cls = ' class="sep"' if ch == "." else ""
        cells.append(f"<i{cls}>{html.escape(ch)}</i>")
    return f'<div class="digits">{"".join(cells)}</div>'


def build_receipt_voucher_html_slip(data: dict[str, Any]) -> str:
    """Bank deposit-slip style: every field in a box with a small caption in its
    corner, and the invoice number and amount written one digit per box."""
    f = _fields(data)
    invoice = _digit_boxes(f["invoice_raw"]) if f["invoice_raw"] else f"<b>{_DASH}</b>"
    css = """
  .g13 { padding:24px 36px 0; }
  .g13 .top { display:flex; justify-content:space-between; align-items:center; gap:20px; border-bottom:2px solid #34495e; padding-bottom:10px; }
  .g13 .co { display:flex; gap:12px; align-items:center; }
  .g13 .co h3 { margin:0 0 2px; font-size:17px; }
  .g13 .meta { font-size:11px; color:#6a7c8e; line-height:1.55; }
  .g13 .tt { flex:none; text-align:left; }
  .g13 .tt h4 { margin:0; font-size:22px; }
  .g13 .g { display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin-top:12px; }
  .g13 .bx { border:1px solid #9aabbb; border-radius:3px; padding:3px 9px 6px; min-height:46px; min-width:0; }
  .g13 .bx span { display:block; font-size:10px; color:#6a7c8e; }
  .g13 .bx b { font-size:14.5px; color:#1c2b3a; }
  .g13 .s2 { grid-column:span 2; } .g13 .s4 { grid-column:span 4; } .g13 .s6 { grid-column:span 6; }
  .g13 .digits { display:flex; flex-wrap:wrap; gap:3px; direction:ltr; justify-content:flex-end; margin-top:2px; }
  .g13 .digits i { font-style:normal; width:20px; height:24px; border:1px solid #9aabbb; display:flex; align-items:center; justify-content:center;
    font-family:'IBM Plex Mono',monospace; font-size:14px; color:#1c2b3a; background:#f4f7fa; }
  .g13 .digits i.sep { border:0; background:none; width:8px; }
"""
    body = f"""
    <div class="top"><div class="co">{_logo(data, 52, "#34495e")}<div><h3>{f['name']}</h3><div class="meta">{f['meta_inline']}</div></div></div>
      <div class="tt"><h4>سند قبض</h4></div></div>
    <div class="g">
      <div class="bx s2"><span>رقم السند</span><b>{f['number']}</b></div>
      <div class="bx s2"><span>التاريخ</span><b>{f['date']}</b></div>
      <div class="bx s2"><span>رقم فاتورة البيع</span>{invoice}</div>
      <div class="bx s4"><span>اسم العميل</span><b>{f['customer']}</b></div>
      <div class="bx s2"><span>المبلغ (ر.س)</span>{_digit_boxes(f['amount_raw'])}</div>
      <div class="bx s6"><span>المبلغ بالحروف</span><b>{f['words']}</b></div>
      <div class="bx s6"><span>البيان / ملاحظات</span><b style="font-weight:400">{f['purpose']}</b></div>
    </div>
    {_foot(data, "#1c2b3a")}"""
    return _doc("g13", "'IBM Plex Sans Arabic'", "#34495e", css, body)


# ======================================================================
# Gallery 15 — «سند الشبكة السويسرية»
# ======================================================================
def build_receipt_voucher_html_swiss(data: dict[str, Any]) -> str:
    """A very large «سند قبض», one thick cobalt rule, then a tight four-column grid
    with wide white space."""
    f = _fields(data)
    css = """
  .g15 { padding:30px 44px 0; }
  .g15 .top { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; }
  .g15 .top h4 { flex:none; margin:0; font-size:58px; font-weight:700; line-height:.95; }
  .g15 .co { display:flex; gap:12px; align-items:center; flex-direction:row-reverse; text-align:left; }
  .g15 .co h3 { margin:0 0 2px; font-size:15px; font-weight:600; }
  .g15 .meta { font-size:10.5px; color:#666c78; line-height:1.55; }
  .g15 .bar { height:6px; background:#1f4ed8; margin:14px 0; }
  .g15 .g { display:grid; grid-template-columns:120px 1fr 120px 1fr; gap:10px 14px; font-size:14.5px; align-items:baseline; }
  .g15 .k { font-size:11px; color:#1f4ed8; font-weight:600; }
  .g15 .val { font-weight:600; min-width:0; }
  .g15 .full { grid-column:span 3; }
  .g15 .num { font-size:34px; font-weight:700; color:#1f4ed8; line-height:1; }
  .g15 .num small { font-size:14px; font-weight:400; color:#141821; }
"""
    body = f"""
    <div class="top"><h4>سند<br>قبض</h4><div class="co">{_logo(data, 52, "#1f4ed8")}<div><h3>{f['name']}</h3><div class="meta">{f['meta']}</div></div></div></div>
    <div class="bar"></div>
    <div class="g">
      <span class="k">رقم السند</span><span class="val">{f['number']}</span><span class="k">التاريخ</span><span class="val">{f['date']}</span>
      <span class="k">اسم العميل</span><span class="val">{f['customer']}</span><span class="k">رقم فاتورة البيع</span><span class="val">{f['invoice']}</span>
      <span class="k">المبلغ</span><span class="val full"><span class="num">{f['amount']} <small>ريال سعودي</small></span></span>
      <span class="k">بالحروف</span><span class="val full">{f['words']}</span>
      <span class="k">البيان</span><span class="val full" style="font-weight:400">{f['purpose']}</span>
    </div>
    {_foot(data, "#141821")}"""
    return _doc("g15", "'Readex Pro'", "#141821", css, body)


# ======================================================================
# Roster — appended, in this order, to BOTH voucher pickers
# ======================================================================
GALLERY_VOUCHER_TEMPLATES: tuple[tuple[str, Callable[[dict[str, Any]], str]], ...] = (
    ("سند الزاوية المائلة", build_receipt_voucher_html_slant),
    ("سند اللوحة المركزية", build_receipt_voucher_html_panel),
    ("سند الترويسة الموجية", build_receipt_voucher_html_wave),
    ("سند البطاقات الأربع", build_receipt_voucher_html_tiles),
    ("سند الزوايا البرونزية", build_receipt_voucher_html_bronze),
    ("سند النصف الملون", build_receipt_voucher_html_tinted),
    ("سند قسيمة الإيداع", build_receipt_voucher_html_slip),
    ("سند الشبكة السويسرية", build_receipt_voucher_html_swiss),
)


__all__ = [
    "GALLERY_VOUCHER_TEMPLATES",
    "build_receipt_voucher_html_slant",
    "build_receipt_voucher_html_panel",
    "build_receipt_voucher_html_wave",
    "build_receipt_voucher_html_tiles",
    "build_receipt_voucher_html_bronze",
    "build_receipt_voucher_html_tinted",
    "build_receipt_voucher_html_slip",
    "build_receipt_voucher_html_swiss",
]
