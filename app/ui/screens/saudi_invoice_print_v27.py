"""«النموذج العشرون» — «الخط الزمني» (design #4 of the second mock-up gallery,
2026-10-18, chosen together with #1 and #2).

A vertical coral line runs down the right edge with numbered dots, and the
invoice walks along it step by step (coral + navy):
* header — logo («Zoom»), seller name and address; «فاتورة ضريبية» with the
  invoice number in a coral pill on the left;
* ١ الإصدار — four chips: رقم الفاتورة · التاريخ · الوقت · طريقة الدفع;
* ٢ الأطراف — seller and buyer cards side by side;
* ٣ البنود — the items table (its header repeats on a continuation page);
* ٤ الحساب — the amount in words on a navy card beside the totals (coral
  grand-total bar);
* ✓ التحقق — the QR, a «scan to verify» note and the company stamp (or a dashed
  «مكان الختم والتوقيع» box when «إظهار الختم» is off or no stamp is stored).

Steps ٤ and ✓ ride in the items table's closing block so they never land on a
page without at least one item. Everything is live from ``data``; the QR is
``data["qr_payload"]`` (the Phase-1 wrapper swaps it).
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
    stamp_img,
    totals_rows,
)

_CORAL = "#ef5b45"
_NAVY = "#1e293b"
_BLUSH = "#f1d5cf"
_TINT = "#fff5f2"
_SLATE = "#64748b"
_FAINT = "#94a3b8"

_PAD = 40
_RAIL = 52            # the timeline column on the right
_CONTENT_W = 816 - 2 * _PAD - _RAIL

_CSS = f"""
  .d27 {{ padding:0 {_PAD}px; font-family:'Tajawal','Cairo','Segoe UI','Tahoma',sans-serif; color:{_NAVY};
          font-size:13px; line-height:1.45; }}
  .d27 .hd {{ display:flex; align-items:center; gap:14px; padding-bottom:12px; border-bottom:1px solid {_BLUSH};
              margin-bottom:14px; }}
  .d27 .hd .lg {{ flex:none; }}
  .d27 .hd h1 {{ margin:0; font-size:20px; font-weight:800; line-height:1.3; }}
  .d27 .hd .s {{ font-size:12px; color:{_SLATE}; }}
  .d27 .hd .t {{ margin-right:auto; text-align:left; flex:none; }}
  .d27 .hd .t b {{ display:block; font-size:24px; font-weight:900; line-height:1.1; }}
  .d27 .hd .t span {{ display:inline-block; margin-top:5px; background:{_CORAL}; color:#ffffff; border-radius:99px;
                      padding:2px 12px; font-weight:700; }}
  .d27 .tl {{ position:relative; padding-right:{_RAIL}px; }}
  .d27 .tl::before {{ content:""; position:absolute; right:16px; top:10px; bottom:40px; width:3px; border-radius:3px;
                      background:linear-gradient({_CORAL}, #fbd0c7); }}
  .d27 .st {{ position:relative; margin-bottom:12px; }}
  .d27 .st .dot {{ position:absolute; right:-{_RAIL}px; top:-2px; width:35px; height:35px; border-radius:50%;
                   box-sizing:border-box; background:#ffffff; border:3px solid {_CORAL}; display:flex;
                   align-items:center; justify-content:center; font-weight:800; color:{_CORAL}; font-size:15px; }}
  .d27 .st.last .dot {{ background:{_CORAL}; color:#ffffff; }}
  .d27 .st h4 {{ margin:2px 0 6px; font-size:15px; display:flex; gap:8px; align-items:baseline; }}
  .d27 .st h4 small {{ font-weight:400; color:{_FAINT}; font-size:11.5px; }}
  .d27 .chips {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; }}
  .d27 .chips > div {{ background:{_TINT}; border-radius:10px; padding:6px 11px; }}
  .d27 .chips small, .d27 .pc small {{ display:block; font-size:11px; color:{_FAINT}; }}
  .d27 .chips b {{ font-size:14.5px; white-space:nowrap; }}
  .d27 .pcs {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  .d27 .pc {{ border:1px solid {_BLUSH}; border-radius:12px; padding:8px 14px; font-size:12.5px; line-height:1.4; }}
  .d27 .pc .nm {{ font-size:14.5px; font-weight:800; margin-bottom:2px; }}
  .d27 .items > thead > tr > th {{ color:{_CORAL}; font-size:11.5px; padding:7px 6px; border-bottom:2px solid {_CORAL}; font-weight:700; }}
  .d27 .items > tbody > tr > td {{ padding:8px 6px; border-bottom:1px solid #f6e3de; }}
  .d27 .items > tbody > tr:nth-child(odd) > td {{ background:#fffaf8; }}
  .d27 .items > tbody > tr.closing > td {{ background:transparent; border:0; padding:10px 0 0; }}
  .d27 .items .c-total {{ font-weight:700; }}
  .d27 .calc {{ display:grid; grid-template-columns:1fr 330px; gap:16px; align-items:start; }}
  .d27 .calc .w {{ background:{_NAVY}; color:#f8fafc; border-radius:12px; padding:12px 14px; font-size:12.5px; line-height:1.7; }}
  .d27 .calc .w small {{ display:block; color:#fca594; font-size:11px; }}
  .d27 .sum > div {{ display:flex; justify-content:space-between; gap:12px; padding:3px 0; border-bottom:1px dashed {_BLUSH}; }}
  .d27 .sum > div > * {{ white-space:nowrap; }}
  .d27 .sum .g {{ border:0; background:{_CORAL}; color:#ffffff; border-radius:10px; padding:8px 12px; margin-top:6px;
                  font-weight:800; font-size:16px; }}
  .d27 .ver {{ display:flex; align-items:center; gap:18px; }}
  .d27 .ver .qrb {{ flex:none; border:1px solid {_BLUSH}; border-radius:10px; padding:4px; }}
  .d27 .ver p {{ margin:0; font-size:12px; color:{_SLATE}; max-width:200px; }}
  .d27 .ver .slot {{ margin-right:auto; }}
  .d27 .ver .ph {{ width:210px; height:90px; border:2px dashed #f1b3a6; border-radius:12px; display:flex;
                   align-items:center; justify-content:center; color:#d8907f; font-size:12px; }}
"""


def build_invoice_html_v27(data: dict[str, Any]) -> str:
    """Build «النموذج العشرون» (الخط الزمني) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    logo = logo_img(seller, 56, 56)
    logo_html = f'<div class="lg">{logo}</div>' if logo else ""
    address = f'<div class="s">{esc_lines(seller.get("address"))}</div>' if seller.get("address") else ""
    count = len(ctx["lines"])

    stamp = stamp_img(data, 180, 135)
    slot = stamp or '<div class="ph">مكان الختم والتوقيع</div>'

    closing = f"""
      <div class="st"><div class="dot">٤</div><h4>الحساب</h4>
        <div class="calc">
          <div class="w"><small>المبلغ كتابةً</small>{ctx["words"]}</div>
          <div class="sum">{totals_rows(ctx)}</div>
        </div>
      </div>
      <div class="st last"><div class="dot">✓</div><h4>التحقق</h4>
        <div class="ver">
          <div class="qrb">{qr_img(data)}</div>
          <p>امسح الرمز بالجوال للتحقق من بيانات الفاتورة الضريبية.</p>
          <div class="slot">{slot}</div>
        </div>
      </div>"""

    body = f"""
    <div class="hd">
      {logo_html}
      <div class="wrap"><h1>{esc(seller.get("name"))}</h1>{address}</div>
      <div class="t"><b>فاتورة ضريبية</b><span>{ltr(ctx["number"])}</span></div>
    </div>
    <div class="tl">
      <div class="st"><div class="dot">١</div><h4>الإصدار <small>بيانات الفاتورة</small></h4>
        <div class="chips">
          <div><small>رقم الفاتورة</small><b>{ltr(ctx["number"])}</b></div>
          <div><small>التاريخ</small><b>{ltr(ctx["date"])}</b></div>
          <div><small>الوقت</small><b>{ltr(ctx["time"])}</b></div>
          <div><small>طريقة الدفع</small><b>{ctx["payment"]}</b></div>
        </div>
      </div>
      <div class="st"><div class="dot">٢</div><h4>الأطراف <small>البائع والعميل</small></h4>
        <div class="pcs">
          <div class="pc wrap"><small>البائع</small><div class="nm">{esc(seller.get("name"))}</div>{party_lines(seller)}</div>
          <div class="pc wrap"><small>العميل</small><div class="nm">{esc(customer.get("name"))}</div>{party_lines(customer)}</div>
        </div>
      </div>
      <div class="st"><div class="dot">٣</div><h4>البنود <small>{ltr(str(count))} {"صنف" if count == 1 else "أصناف"}</small></h4>
        {items_table(ctx, _CONTENT_W, closing)}
      </div>
    </div>"""

    return page_html(css=_CSS, sheet_class="d27", top=32, bottom=26, body=body)


__all__ = ["build_invoice_html_v27"]
