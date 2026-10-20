"""«النموذج الثامن عشر» — «بطاقة الصعود» (design #1 of the second mock-up gallery,
2026-10-18, chosen together with #2 and #4).

The invoice reads like an airline boarding pass on a pale-sky page:
* a white pass with a perforated stub: a sky-blue bar (logo, seller name,
  «فاتورة ضريبية»), then a «route» — «من · البائع» on the right and «إلى · العميل»
  on the left, each under its city in big letters, joined by a dashed flight line —
  and four flight-data fields (رقم الفاتورة · التاريخ · الوقت · طريقة الدفع);
* the stub (left, past the perforation): invoice number, QR, and a yellow
  «الإجمالي شامل الضريبة» tag;
* «تفاصيل البنود» as a white card (its title row repeats on a continuation page);
* a ticket strip of totals (the grand total in yellow on navy), the amount in
  words in a pill, and a decorative barcode + «شكرًا لتعاملكم معنا».

The big «city» is the first part of each party's address (text before the first
dash/comma/line break) when it is short; otherwise it is left out. Everything is
live from ``data``; the QR is ``data["qr_payload"]`` (the Phase-1 wrapper swaps it).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.ui.screens.saudi_invoice_print import QR_PRINT_PX
from app.ui.screens.saudi_invoice_print_kit import (
    esc,
    esc_lines,
    invoice_context,
    items_table,
    logo_img,
    ltr,
    page_html,
    qr_img,
    stamp_img,
)

_SKY = "#0369a1"
_NAVY = "#0c2d48"
_PAGE = "#e6f1f9"
_YELLOW = "#facc15"
_MUTED = "#5b7a90"
_DASH = "#cfe1ee"

_PAD = 32
_CONTENT_W = 816 - 2 * _PAD
_STUB_W = QR_PRINT_PX + 44
_CITY_MAX = 12

_CSS = f"""
  .d25 {{ padding:0 {_PAD}px; background:{_PAGE}; font-family:'Cairo','Tajawal','Segoe UI','Tahoma',sans-serif;
          color:{_NAVY}; font-size:13px; line-height:1.45; }}
  @media print {{ body {{ background:{_PAGE}; }} }}
  .d25 .pass {{ display:grid; grid-template-columns:1fr {_STUB_W}px; background:#ffffff; border-radius:18px;
                position:relative; box-shadow:0 2px 0 #c9dfee; }}
  .d25 .pass::before, .d25 .pass::after {{ content:""; position:absolute; left:{_STUB_W - 14}px; width:28px; height:28px;
                border-radius:50%; background:{_PAGE}; }}
  .d25 .pass::before {{ top:-14px; }}
  .d25 .pass::after {{ bottom:-14px; }}
  .d25 .pmain {{ border-left:2px dashed #b6d3e7; min-width:0; }}
  .d25 .bar {{ background:{_SKY}; color:#ffffff; display:flex; align-items:center; gap:12px; padding:16px 22px;
               border-radius:0 18px 0 0; }}
  .d25 .bar .lg {{ background:#ffffff; border-radius:50%; padding:5px; flex:none; overflow:hidden; }}
  .d25 .bar h1 {{ margin:0; font-size:17px; font-weight:800; line-height:1.35; }}
  .d25 .bar .t {{ margin-right:auto; text-align:left; font-weight:800; font-size:16px; line-height:1.2; flex:none; }}
  .d25 .bar .t small {{ display:block; font-family:'Readex Pro',sans-serif; font-size:10px; letter-spacing:3px;
                        opacity:.85; font-weight:400; }}
  .d25 .route {{ display:grid; grid-template-columns:1fr 104px 1fr; align-items:center; gap:6px; padding:20px 22px 8px; }}
  .d25 .route .k {{ font-size:11px; color:{_SKY}; font-weight:700; }}
  .d25 .route .city {{ font-weight:800; font-size:34px; line-height:1.15; }}
  .d25 .route .nm {{ font-weight:800; font-size:13.5px; }}
  .d25 .route .sm {{ font-size:11.5px; color:#4a6274; }}
  .d25 .route .dst {{ text-align:left; }}
  .d25 .plane {{ width:104px; height:40px; display:block; }}
  .d25 .fields {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; padding:12px 22px 20px; }}
  .d25 .fields > div {{ border-top:1px solid #e1edf5; padding-top:8px; }}
  .d25 .fields small {{ display:block; font-size:10.5px; color:{_MUTED}; }}
  .d25 .fields b {{ font-size:15px; white-space:nowrap; }}
  .d25 .stub {{ padding:16px 16px; display:flex; flex-direction:column; align-items:center; gap:6px; text-align:center; }}
  .d25 .stub .k {{ font-size:10.5px; color:{_MUTED}; }}
  .d25 .stub .no {{ font-family:'Readex Pro',sans-serif; font-weight:700; font-size:20px; }}
  .d25 .stub .amt {{ background:{_YELLOW}; border-radius:10px; padding:6px 8px; width:100%; box-sizing:border-box;
                     font-weight:800; font-size:16px; margin-top:4px; white-space:nowrap; }}
  .d25 .stub .amt small {{ display:block; font-size:10px; font-weight:600; }}
  .d25 .items {{ border-collapse:separate; border-spacing:0; margin-top:28px; }}
  .d25 .items > thead > tr.ttl > th {{ background:#ffffff; border-radius:14px 14px 0 0; padding:14px 18px 4px; }}
  .d25 .items .ttl .row {{ display:flex; justify-content:space-between; font-size:13px; color:{_SKY}; }}
  .d25 .items .ttl .en {{ font-family:'Readex Pro',sans-serif; font-size:10px; letter-spacing:3px; color:#7fa3bd; font-weight:400; }}
  .d25 .items > thead > tr.cols > th {{ background:#ffffff; font-size:11px; color:{_SKY}; padding:8px 6px;
                                        border-bottom:2px solid {_SKY}; font-weight:700; }}
  .d25 .items > tbody > tr > td {{ background:#ffffff; padding:12px 6px; border-bottom:1px dashed {_DASH}; }}
  .d25 .items > thead > tr.cols > th:first-child, .d25 .items > tbody > tr > td:first-child {{ padding-right:12px; padding-left:2px; }}
  .d25 .items > thead > tr.cols > th:last-child, .d25 .items > tbody > tr > td:last-child {{ padding-left:18px; }}
  .d25 .items > tbody.summary > tr:first-child > td {{ border-bottom:0; padding-bottom:16px; }}
  .d25 .items > tbody.summary > tr:first-child > td:first-child {{ border-radius:0 0 14px 0; }}
  .d25 .items > tbody.summary > tr:first-child > td:last-child {{ border-radius:0 0 0 14px; }}
  .d25 .items > tbody > tr.closing > td {{ background:transparent; border:0; padding:0; }}
  .d25 .items .c-total {{ font-weight:700; }}
  .d25 .strip {{ display:grid; grid-template-columns:repeat(3, 1fr) 1.5fr; background:#ffffff; border-radius:14px;
                 margin-top:24px; overflow:hidden; }}
  .d25 .strip > div {{ padding:18px 16px; border-left:2px dashed {_DASH}; }}
  .d25 .strip > div:last-child {{ border-left:0; background:{_NAVY}; color:#ffffff; }}
  .d25 .strip small {{ display:block; font-size:11px; color:{_MUTED}; }}
  .d25 .strip b {{ font-size:17px; white-space:nowrap; }}
  .d25 .strip .g small {{ color:#9cc3dd; }}
  .d25 .strip .g b {{ color:{_YELLOW}; font-size:24px; }}
  .d25 .words {{ background:#ffffff; border-radius:99px; margin-top:16px; padding:9px 18px; font-size:12.5px; }}
  .d25 .words b {{ color:{_SKY}; }}
  .d25 .bottom {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-top:22px; }}
  .d25 .bottom .ty {{ font-size:14px; font-weight:700; color:{_SKY}; white-space:nowrap; }}
"""

_PLANE = (
    '<svg class="plane" viewBox="0 0 120 40"><line x1="6" y1="20" x2="114" y2="20" stroke="#9cc3dd" '
    'stroke-width="2" stroke-dasharray="4 5"/><g transform="translate(60 20) rotate(180) translate(-14 -14)">'
    '<path d="M2 14 L26 14 M14 4 L20 14 L14 24 M6 9 L9 14 L6 19" stroke="#0369a1" stroke-width="3" fill="none" '
    'stroke-linecap="round" stroke-linejoin="round"/></g><circle cx="6" cy="20" r="4" fill="#facc15"/>'
    '<circle cx="114" cy="20" r="4" fill="#0369a1"/></svg>'
)


def _city(address: Any) -> str:
    """The first part of an address («الرياض — حي العليا» → «الرياض») when short."""
    first = next((ln for ln in str(address or "").splitlines() if ln.strip()), "")
    head = re.split(r"\s*[—–\-،,|/]\s*", first.strip(), maxsplit=1)[0].strip()
    return head if 0 < len(head) <= _CITY_MAX else ""


def _barcode(seed: str, width: int = 300, height: int = 46) -> str:
    """A decorative barcode drawn from the invoice number (not machine-readable data)."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest() * 3
    bars, x = [], 0
    for i, byte in enumerate(digest):
        w = 1 + byte % 3
        if x + w > width:
            break
        if i % 2 == 0:
            bars.append(f'<rect x="{x}" y="0" width="{w}" height="{height}"/>')
        x += w + 1
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true">'
        f'<g fill="{_NAVY}">{"".join(bars)}</g></svg>'
    )


def _party(cap: str, party: dict[str, Any], *, cls: str = "") -> str:
    city = _city(party.get("address"))
    rows = [f'<div class="k">{cap}</div>']
    if city:
        rows.append(f'<div class="city">{esc(city)}</div>')
    rows.append(f'<div class="nm">{esc(party.get("name"))}</div>')
    if party.get("vat"):
        rows.append(f'<div class="sm">الرقم الضريبي {ltr(esc(party.get("vat")))}</div>')
    if party.get("cr"):
        rows.append(f'<div class="sm">السجل التجاري {ltr(esc(party.get("cr")))}</div>')
    if party.get("address"):
        rows.append(f'<div class="sm">{esc_lines(party.get("address"))}</div>')
    return f'<div class="wrap {cls}">{"".join(rows)}</div>'


def build_invoice_html_v25(data: dict[str, Any]) -> str:
    """Build «النموذج الثامن عشر» (بطاقة الصعود) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    logo = logo_img(seller, 46, 46)
    logo_html = f'<div class="lg">{logo}</div>' if logo else ""
    # The discount cell only appears when there is a discount.
    discount_cell = (
        f'<div><small>الخصم {ltr(ctx["discount_rate"])}</small><b>{ltr("-" + ctx["discount"])}</b></div>'
        if ctx["discount"] else ""
    )
    strip_cols = "repeat(3, 1fr) 1.5fr" if ctx["discount"] else "repeat(2, 1fr) 1.5fr"

    closing = f"""
      <div class="strip" style="grid-template-columns:{strip_cols};">
        <div><small>الإجمالي قبل الضريبة</small><b>{ltr(ctx["subtotal"])}</b></div>
        {discount_cell}
        <div><small>ضريبة القيمة المضافة {ltr(ctx["vat_rate"])}</small><b>{ltr(ctx["vat"])}</b></div>
        <div class="g"><small>الإجمالي شامل الضريبة (ر.س)</small><b>{ltr(ctx["total"])}</b></div>
      </div>
      <div class="words"><b>المبلغ كتابةً:</b> {ctx["words"]}</div>
      <div class="bottom">
        {_barcode(str(data.get("invoice_number") or ""))}
        {stamp_img(data, 170, 128)}
        <div class="ty">شكرًا لتعاملكم معنا ✈</div>
      </div>"""

    table = items_table(ctx, _CONTENT_W, closing).replace(
        "<thead><tr>",
        '<thead><tr class="ttl"><th colspan="99"><div class="row"><span>تفاصيل البنود</span>'
        '<span class="en">ITEMS</span></div></th></tr><tr class="cols">',
        1,
    )

    body = f"""
    <div class="pass">
      <div class="pmain">
        <div class="bar">{logo_html}<h1 class="wrap">{esc(seller.get("name"))}</h1>
          <div class="t">فاتورة ضريبية<small>TAX INVOICE</small></div></div>
        <div class="route">
          {_party("من · البائع", seller)}
          {_PLANE}
          {_party("إلى · العميل", customer, cls="dst")}
        </div>
        <div class="fields">
          <div><small>رقم الفاتورة</small><b>{ltr(ctx["number"])}</b></div>
          <div><small>التاريخ</small><b>{ltr(ctx["date"])}</b></div>
          <div><small>الوقت</small><b>{ltr(ctx["time"])}</b></div>
          <div><small>طريقة الدفع</small><b>{ctx["payment"]}</b></div>
        </div>
      </div>
      <div class="stub">
        <div class="k">رقم الفاتورة</div><div class="no">{ltr(ctx["number"])}</div>
        {qr_img(data)}
        <div class="amt"><small>الإجمالي شامل الضريبة</small>{ltr(ctx["total"] + " ر.س")}</div>
      </div>
    </div>
    {table}"""

    return page_html(css=_CSS, sheet_class="d25", top=30, bottom=26, body=body)


__all__ = ["build_invoice_html_v25"]
