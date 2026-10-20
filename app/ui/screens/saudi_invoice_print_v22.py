"""«النموذج الخامس عشر» — «البطاقات» (design #3 of the 2026-10-18 mock-up gallery,
chosen by the user together with #6 and #8).

Every block sits in a soft mint card with rounded corners:
* a header card — logo («Zoom»), seller name (+ English name) and a teal
  «فاتورة ضريبية» pill;
* four small stat cards — رقم الفاتورة · التاريخ (+ time) · طريقة الدفع ·
  الإجمالي المستحق;
* the seller (البائع: address · VAT · CR) and buyer (العميل) cards side by side;
* the items table under a teal header with rounded top corners;
* a closing row: the QR card on the right, the totals card (with the amount in
  words) beside it, and the company stamp under the totals when «إظهار الختم».

Seller, buyer, logo, lines and totals are all live from ``data``; the QR is
``data["qr_payload"]`` (Phase-2 signed; the Phase-1 wrapper swaps it).
"""

from __future__ import annotations

from typing import Any

from app.ui.screens.saudi_invoice_print import QR_PRINT_PX
from app.ui.screens.saudi_invoice_print_kit import (
    esc,
    invoice_context,
    items_table,
    logo_img,
    ltr,
    page_html,
    party_lines,
    qr_img,
    stamp_img,
    totals_rows,
)

_TEAL = "#0f766e"
_DEEP = "#0f3d3a"
_MINT = "#eef7f6"
_LINE = "#d6ebe8"
_SOFT = "#4b7c78"

_PAD = 34
_CONTENT_W = 816 - 2 * _PAD

_CSS = f"""
  .d22 {{ padding:0 {_PAD}px; font-family:'Tajawal','Cairo','Segoe UI','Tahoma',sans-serif;
          color:#16302e; font-size:13px; line-height:1.45; }}
  .d22 .card {{ background:{_MINT}; border-radius:16px; padding:14px 18px; box-sizing:border-box; }}
  .d22 .top {{ display:flex; align-items:center; gap:16px; }}
  .d22 .top .lg {{ background:#ffffff; border-radius:14px; padding:6px; flex:none; }}
  .d22 .top h1 {{ margin:0; font-size:20px; font-weight:800; color:{_DEEP}; line-height:1.3; }}
  .d22 .top .en {{ font-size:12px; color:{_SOFT}; direction:ltr; text-align:right; }}
  .d22 .top .badge {{ margin-right:auto; background:{_TEAL}; color:#ffffff; border-radius:99px;
                      padding:8px 20px; font-weight:800; font-size:16px; white-space:nowrap; flex:none; }}
  .d22 .stats {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin:12px 0; }}
  .d22 .stats .card {{ padding:10px 14px; }}
  .d22 .stats small {{ display:block; color:{_SOFT}; font-size:11.5px; }}
  .d22 .stats b {{ font-size:16px; color:{_DEEP}; white-space:nowrap; }}
  .d22 .stats .tm {{ font-size:11.5px; color:{_SOFT}; margin-right:6px; }}
  .d22 .parties {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px; }}
  .d22 .parties h4 {{ margin:0 0 4px; color:{_TEAL}; font-size:13px; }}
  .d22 .parties .nm {{ font-weight:800; font-size:14.5px; color:{_DEEP}; }}
  .d22 .items {{ border-collapse:separate; border-spacing:0; }}
  .d22 .items > thead > tr > th {{ background:{_TEAL}; color:#ffffff; padding:10px 8px; font-size:12px; font-weight:700; }}
  .d22 .items > thead > tr > th:first-child {{ border-radius:0 12px 0 0; }}
  .d22 .items > thead > tr > th:last-child {{ border-radius:12px 0 0 0; }}
  .d22 .items > tbody > tr > td {{ padding:9px 8px; border-bottom:1px solid {_LINE}; background:#ffffff; }}
  .d22 .items > tbody > tr > td:first-child {{ border-right:1px solid {_LINE}; }}
  .d22 .items > tbody > tr > td:last-child {{ border-left:1px solid {_LINE}; }}
  .d22 .items > tbody > tr.closing > td {{ border:0; background:transparent; padding:0; }}
  .d22 .items .c-total {{ font-weight:700; color:{_DEEP}; }}
  .d22 .closing-row {{ display:flex; gap:12px; margin-top:14px; align-items:stretch; }}
  .d22 .qrcard {{ flex:none; width:{QR_PRINT_PX + 28}px; display:flex; align-items:center; justify-content:center; padding:14px; }}
  .d22 .sum {{ flex:1; }}
  .d22 .sum > div {{ display:flex; justify-content:space-between; padding:5px 0; gap:12px; }}
  .d22 .sum .g {{ border-top:2px solid {_TEAL}; margin-top:6px; padding-top:9px; font-size:18px; font-weight:900; color:{_DEEP}; }}
  .d22 .sum .words {{ display:block; font-size:12px; color:{_SOFT}; margin-top:8px; padding:0; }}
  .d22 .stamp {{ display:flex; justify-content:flex-end; margin-top:12px; }}
"""


def build_invoice_html_v22(data: dict[str, Any]) -> str:
    """Build «النموذج الخامس عشر» (البطاقات) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    logo = logo_img(seller, 76, 76)
    logo_html = f'<div class="lg">{logo}</div>' if logo else ""
    name_en = f'<div class="en">{esc(seller.get("name_en"))}</div>' if seller.get("name_en") else ""
    time_html = f'<span class="tm">{ltr(ctx["time"])}</span>' if ctx["time"] else ""

    stamp = stamp_img(data)
    closing = f"""
      <div class="closing-row">
        <div class="card qrcard">{qr_img(data)}</div>
        <div class="card sum">
          {totals_rows(ctx)}
          <div class="words">المبلغ كتابةً: {ctx["words"]}</div>
        </div>
      </div>
      {f'<div class="stamp">{stamp}</div>' if stamp else ""}"""

    body = f"""
    <div class="card top">
      {logo_html}
      <div class="wrap"><h1>{esc(seller.get("name"))}</h1>{name_en}</div>
      <div class="badge">فاتورة ضريبية</div>
    </div>
    <div class="stats">
      <div class="card"><small>رقم الفاتورة</small><b>{ltr(ctx["number"])}</b></div>
      <div class="card"><small>التاريخ</small><b>{ltr(ctx["date"])}</b>{time_html}</div>
      <div class="card"><small>طريقة الدفع</small><b>{ctx["payment"]}</b></div>
      <div class="card"><small>الإجمالي المستحق</small><b>{ltr(ctx["total"] + " ر.س")}</b></div>
    </div>
    <div class="parties">
      <div class="card wrap"><h4>البائع</h4><div class="nm">{esc(seller.get("name"))}</div>{party_lines(seller)}</div>
      <div class="card wrap"><h4>العميل</h4><div class="nm">{esc(customer.get("name"))}</div>{party_lines(customer)}</div>
    </div>
    {items_table(ctx, _CONTENT_W, closing)}"""

    return page_html(css=_CSS, sheet_class="d22", top=34, bottom=34, body=body)


__all__ = ["build_invoice_html_v22"]
