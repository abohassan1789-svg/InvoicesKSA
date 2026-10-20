"""«النموذج السابع عشر» — «الإجمالي أولًا» (design #8 of the 2026-10-18 mock-up
gallery, chosen by the user together with #3 and #6).

The first thing the customer reads is what they owe:
* a slim top line — logo («Zoom»), seller name, VAT/CR line and address, with a
  purple «فاتورة ضريبية» on the left;
* a big purple «hero» panel: «المبلغ المستحق» in very large figures, the amount in
  words, a mini row (رقم الفاتورة · التاريخ · الدفع) and the QR in a white tile;
* the «من / إلى» parties in one outlined box split down the middle;
* the items table under a light-lilac header strip with rounded ends;
* the totals list on the left (purple rule above the grand total), the company
  stamp to its right when «إظهار الختم» is ticked.

Seller, buyer, logo, lines and totals are all live from ``data``; the QR is
``data["qr_payload"]`` (Phase-2 signed; the Phase-1 wrapper swaps it).
"""

from __future__ import annotations

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
    party_lines,
    qr_img,
    seller_id_line,
    stamp_img,
    totals_rows,
)

_VIOLET = "#7c3aed"
_DEEP = "#5b21b6"
_LILAC = "#f6f2ff"
_EDGE = "#e9e3f7"

_PAD = 36
_CONTENT_W = 816 - 2 * _PAD

_CSS = f"""
  .d24 {{ padding:0 {_PAD}px; font-family:'Readex Pro','Tajawal','Segoe UI','Tahoma',sans-serif;
          color:#1f1a2e; font-size:12.5px; line-height:1.5; }}
  .d24 .top {{ display:flex; align-items:center; gap:12px; color:#555; font-size:11.5px; }}
  .d24 .top b {{ display:block; font-size:15px; color:#111; font-weight:600; }}
  .d24 .top .tt {{ margin-right:auto; font-size:15px; color:{_VIOLET}; font-weight:700; white-space:nowrap; flex:none; }}
  .d24 .hero {{ margin:16px 0; border-radius:18px; background:linear-gradient(120deg, {_DEEP}, {_VIOLET});
                color:#ffffff; padding:24px 28px; display:flex; gap:22px; align-items:center; }}
  .d24 .hero .info {{ flex:1; min-width:0; }}
  .d24 .hero small {{ opacity:.85; font-size:12px; }}
  .d24 .hero .amt {{ font-size:46px; font-weight:700; line-height:1.15; margin:4px 0 6px; white-space:nowrap; }}
  .d24 .hero .amt span {{ font-size:20px; }}
  .d24 .hero .w {{ font-size:12px; opacity:.92; }}
  .d24 .hero .mini {{ display:flex; gap:26px; margin-top:14px; font-size:11.5px; opacity:.95; }}
  .d24 .hero .mini b {{ display:block; font-size:14px; white-space:nowrap; }}
  .d24 .hero .qr {{ flex:none; background:#ffffff; border-radius:12px; padding:8px;
                    width:{QR_PRINT_PX + 16}px; box-sizing:border-box; }}
  .d24 .pp {{ display:grid; grid-template-columns:1fr 1fr; border:1px solid {_EDGE}; border-radius:12px; margin-bottom:16px; }}
  .d24 .pp > div {{ padding:12px 16px; }}
  .d24 .pp > div:first-child {{ border-left:1px solid {_EDGE}; }}
  .d24 .pp h4 {{ margin:0 0 3px; font-size:11.5px; color:{_VIOLET}; font-weight:600; }}
  .d24 .pp .nm {{ font-weight:600; font-size:14px; color:#111; }}
  .d24 .items {{ border-collapse:separate; border-spacing:0; }}
  .d24 .items > thead > tr > th {{ font-size:11.5px; color:{_VIOLET}; font-weight:600; padding:8px; background:{_LILAC}; }}
  .d24 .items > thead > tr > th:first-child {{ border-radius:0 8px 8px 0; }}
  .d24 .items > thead > tr > th:last-child {{ border-radius:8px 0 0 8px; }}
  .d24 .items > tbody > tr > td {{ padding:10px 8px; border-bottom:1px solid #f0edf7; }}
  .d24 .items > tbody > tr.closing > td {{ border:0; padding:0; }}
  .d24 .items .c-total {{ font-weight:600; color:{_DEEP}; }}
  .d24 .end {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-top:14px; }}
  .d24 .sum {{ width:330px; flex:none; margin-right:auto; }}
  .d24 .sum > div {{ display:flex; justify-content:space-between; gap:12px; padding:5px 0; }}
  .d24 .sum > div > * {{ white-space:nowrap; }}
  .d24 .sum .g {{ border-top:2px solid {_VIOLET}; margin-top:4px; padding-top:9px; font-weight:700; color:{_DEEP}; font-size:16px; }}
"""


def build_invoice_html_v24(data: dict[str, Any]) -> str:
    """Build «النموذج السابع عشر» (الإجمالي أولًا) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    address = esc_lines(seller.get("address")).replace("<br>", " — ")
    id_line = " · ".join(p for p in (seller_id_line(seller), address) if p)
    time_html = f" {ltr(ctx['time'])}" if ctx["time"] else ""

    closing = f"""
      <div class="end">
        {stamp_img(data, 180, 135)}
        <div class="sum">{totals_rows(ctx)}</div>
      </div>"""

    body = f"""
    <div class="top">
      {logo_img(seller, 54, 54)}
      <div class="wrap"><b>{esc(seller.get("name"))}</b>{id_line}</div>
      <div class="tt">فاتورة ضريبية</div>
    </div>
    <div class="hero">
      <div class="info">
        <small>المبلغ المستحق</small>
        <div class="amt">{ltr(ctx["total"])} <span>ر.س</span></div>
        <div class="w">{ctx["words"]}</div>
        <div class="mini">
          <div>رقم الفاتورة<b>{ltr(ctx["number"])}</b></div>
          <div>التاريخ<b>{ltr(ctx["date"])}{time_html}</b></div>
          <div>الدفع<b>{ctx["payment"]}</b></div>
        </div>
      </div>
      <div class="qr">{qr_img(data)}</div>
    </div>
    <div class="pp">
      <div class="wrap"><h4>من</h4><div class="nm">{esc(seller.get("name"))}</div>{party_lines(seller)}</div>
      <div class="wrap"><h4>إلى</h4><div class="nm">{esc(customer.get("name"))}</div>{party_lines(customer)}</div>
    </div>
    {items_table(ctx, _CONTENT_W, closing)}"""

    return page_html(css=_CSS, sheet_class="d24", top=32, bottom=34, body=body)


__all__ = ["build_invoice_html_v24"]
