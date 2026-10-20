"""«النموذج السادس عشر» — «الشريط القطري» (design #6 of the 2026-10-18 mock-up
gallery, chosen by the user together with #3 and #8).

Industrial look in charcoal + orange:
* a full-width charcoal header cut on a diagonal, with an orange/charcoal hazard
  stripe along its lower edge — logo («Zoom») in a white tile, seller name, VAT/CR
  line and address on the right, a big orange «فاتورة ضريبية» on the left;
* four grey info pills with an orange edge — رقم الفاتورة · التاريخ · الوقت · الدفع;
* the buyer (العميل) beside the amount in words;
* the items table under a charcoal header with an orange underline, zebra rows;
* the QR on the right and the totals box (orange grand-total bar) on the left,
  with the company stamp between them when «إظهار الختم» is ticked;
* a thin hazard stripe at the foot of every printed page.

Seller, buyer, logo, lines and totals are all live from ``data``; the QR is
``data["qr_payload"]`` (Phase-2 signed; the Phase-1 wrapper swaps it).
"""

from __future__ import annotations

from typing import Any

from app.ui.screens.saudi_invoice_print_kit import (
    esc,
    esc_lines,
    invoice_context,
    items_table,
    logo_img,
    ltr,
    page_html,
    party_lines,
    qr_img,
    seller_id_line,
    stamp_img,
    totals_rows,
)

_CHARCOAL = "#26272b"
_ORANGE = "#f97316"
_GREY = "#f3f4f6"
_MUTED = "#6b7280"

_PAD = 36
_CONTENT_W = 816 - 2 * _PAD
_TOP = 28          # page-top margin on every page; the header bleeds up into it
_BOTTOM = 44       # page-bottom margin; holds the hazard stripe
_STRIPE = f"repeating-linear-gradient(135deg, {_ORANGE} 0 18px, {_CHARCOAL} 18px 36px)"

_CSS = f"""
  .d23 {{ padding:0 {_PAD}px; font-family:'Cairo','Tajawal','Segoe UI','Tahoma',sans-serif;
          color:#1f2937; font-size:13px; line-height:1.45; }}
  .d23 .hd {{ margin:-{_TOP}px -{_PAD}px 0; background:{_CHARCOAL}; color:#ffffff; position:relative;
              padding:30px {_PAD}px 58px; clip-path:polygon(0 0, 100% 0, 100% 84%, 0 100%); }}
  .d23 .hd::after {{ content:""; position:absolute; left:0; right:0; bottom:0; height:26px; background:{_STRIPE}; }}
  .d23 .hd .row {{ display:flex; align-items:center; gap:16px; }}
  .d23 .hd .lg {{ background:#ffffff; border-radius:8px; padding:6px; flex:none; }}
  .d23 .hd h1 {{ margin:0; font-size:20px; font-weight:800; line-height:1.35; }}
  .d23 .hd .sub {{ opacity:.82; font-size:12.5px; }}
  .d23 .hd .t {{ margin-right:auto; text-align:left; flex:none; }}
  .d23 .hd .t b {{ display:block; font-size:34px; line-height:1.05; color:{_ORANGE}; font-weight:800; }}
  .d23 .hd .t span {{ letter-spacing:3px; font-size:11px; }}
  .d23 .pills {{ display:flex; gap:10px; margin:14px 0 16px; }}
  .d23 .pills > div {{ flex:1; background:{_GREY}; border-right:5px solid {_ORANGE}; padding:8px 12px; }}
  .d23 .pills small {{ display:block; color:{_MUTED}; font-size:11px; }}
  .d23 .pills b {{ white-space:nowrap; }}
  .d23 .pp {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:16px; }}
  .d23 .pp h4 {{ margin:0 0 4px; font-size:13px; color:{_ORANGE}; }}
  .d23 .pp .nm {{ font-weight:800; font-size:14.5px; }}
  .d23 .items > thead > tr > th {{ background:{_CHARCOAL}; color:#ffffff; padding:9px 8px; font-size:12px;
                                   font-weight:700; border-bottom:4px solid {_ORANGE}; }}
  .d23 .items > tbody > tr > td {{ padding:9px 8px; border-bottom:1px solid #e5e7eb; }}
  .d23 .items > tbody > tr:nth-child(even) > td {{ background:#fafafa; }}
  .d23 .items > tbody > tr.closing > td {{ border:0; background:transparent; padding:0; }}
  .d23 .items .c-total {{ font-weight:700; }}
  .d23 .end {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-top:16px; }}
  .d23 .sum {{ width:370px; flex:none; }}
  .d23 .sum > div > * {{ white-space:nowrap; }}
  .d23 .sum > div {{ display:flex; justify-content:space-between; gap:12px; padding:6px 10px; }}
  .d23 .sum > div:nth-child(odd):not(.g) {{ background:#fafafa; }}
  .d23 .sum .g {{ background:{_ORANGE}; color:#ffffff; font-weight:800; font-size:17px; }}
  .d23 .foot {{ position:absolute; left:0; right:0; bottom:0; height:16px; background:{_STRIPE}; }}
  @media print {{ .d23 .foot {{ position:fixed; }} }}
"""


def build_invoice_html_v23(data: dict[str, Any]) -> str:
    """Build «النموذج السادس عشر» (الشريط القطري) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    logo = logo_img(seller, 74, 74)
    logo_html = f'<div class="lg">{logo}</div>' if logo else ""
    address = f'<div class="sub">{esc_lines(seller.get("address"))}</div>' if seller.get("address") else ""

    closing = f"""
      <div class="end">
        <div>{qr_img(data)}</div>
        {stamp_img(data, 180, 135)}
        <div class="sum">{totals_rows(ctx)}</div>
      </div>"""

    body = f"""
    <div class="hd">
      <div class="row">
        {logo_html}
        <div class="wrap">
          <h1>{esc(seller.get("name"))}</h1>
          <div class="sub">{seller_id_line(seller)}</div>
          {address}
        </div>
        <div class="t"><b>فاتورة ضريبية</b><span>TAX INVOICE</span></div>
      </div>
    </div>
    <div class="pills">
      <div><small>رقم الفاتورة</small><b>{ltr(ctx["number"])}</b></div>
      <div><small>التاريخ</small><b>{ltr(ctx["date"])}</b></div>
      <div><small>الوقت</small><b>{ltr(ctx["time"])}</b></div>
      <div><small>الدفع</small><b>{ctx["payment"]}</b></div>
    </div>
    <div class="pp">
      <div class="wrap"><h4>العميل</h4><div class="nm">{esc(customer.get("name"))}</div>{party_lines(customer)}</div>
      <div><h4>المبلغ كتابةً</h4>{ctx["words"]}</div>
    </div>
    {items_table(ctx, _CONTENT_W, closing)}"""

    return page_html(
        css=_CSS, sheet_class="d23", top=_TOP, bottom=_BOTTOM, body=body,
        extra='<div class="foot"></div>',
    )


__all__ = ["build_invoice_html_v23"]
