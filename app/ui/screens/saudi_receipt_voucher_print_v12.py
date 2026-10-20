"""«سند القصر» — receipt-voucher layout replica (added 2026-10-06).

Copied, position for position, from the user's WhatsApp scan
``تصامبم جديدة\\WhatsApp Image 2026-10-06 at 1.22.08 PM.jpeg`` (the bilingual
«سند قبض / Received Voucher» of شركة قصر نصار للصناعة). Like «سند عقيل» only
the LAYOUT is fixed: the logo, the seller block, the payer and the stamp come
LIVE from ``data``.

The scan is a 794-px photo whose left edge cuts the frame, so its positions
were mapped into a symmetric frame (17px each side): x × 0.967, y 1:1. Every
element is absolutely positioned inside the frame, like the scan:

* header: the seller (bold name + address lines, centred under it) right, the
  serial «#n» in a box centre (dark maroon), the logo left («Zoom»), then a
  double rule;
* the amount in a rounded box right, «ســنــد قــبــض» / «Received Voucher»
  (underlined) centre, «التاريخ: dd/mm/yyyy» left;
* four bilingual rows — استلمنا من / Recevied From Mr. (the source's spelling),
  مبلغاً وقدره / The Sum Of, the payment-method row (نقداً · شيك · تحويل
  check-boxes, رقم … No, على خزينة / بنك Main Treasury, بتاريخ date) and
  وذلك مقابل / For — values centred between the two labels;
* three signature columns (توقيع المدير · أمين الصندوق · توقيع المستلم);
* the company stamp below the frame, right of centre.

The box matching ``payment_type`` (نقدي / شيك / تحويل) is ticked; the scan's
boxes are empty because its source printed them for hand-filling. Our data
model has no treasury or cheque number, so «Main Treasury» is fixed and the
رقم/No gap stays blank.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
)

_INK = "#1e1e1e"
_MAROON = "#6d1527"     # the serial number
_RIYAL_ASSET = "riyal_symbol.png"

_FRAME_L, _FRAME_T, _FRAME_W, _FRAME_H = 17, 17, 760, 596
_INNER_W = _FRAME_W - 5          # 2.5px border each side
_VALUE_CX = 435                  # the centre of the row values (frame px)


def _esc_lines(value: Any) -> str:
    text = str(value or "").strip()
    return "<br>".join(html.escape(part.strip()) for part in text.splitlines() if part.strip())


def _date_dmy(value: Any) -> str:
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return value.strftime("%d/%m/%Y")
    return html.escape(str(value or ""))


def _num(value: Any) -> str:
    """«148,000» — whole amounts without decimals, others with two (like the scan)."""
    try:
        amount = Decimal(str(value or 0))
    except Exception:  # noqa: BLE001 - defensive formatting
        amount = Decimal(0)
    if amount == amount.to_integral_value():
        return f"{amount:,.0f}"
    return f"{amount:,.2f}"


def _words(amount: Any) -> str:
    """The scan's wording: «… ريال سعودي فقط لا غير»."""
    text = amount_in_words_ar(amount).strip()
    if text.startswith("فقط "):
        text = text[len("فقط "):]
    text = text.replace("ريالاً", "ريال سعودي")
    if text.endswith("لا غير"):
        text = text[: -len("لا غير")].rstrip() + " فقط لا غير"
    return html.escape(text)


def _method(payment_type: Any) -> str:
    text = str(payment_type or "")
    if "شيك" in text or "cheque" in text.lower():
        return "cheque"
    if "تحويل" in text or "transfer" in text.lower() or "بنك" in text:
        return "transfer"
    if "نقد" in text or "كاش" in text or "cash" in text.lower():
        return "cash"
    return ""


def build_receipt_voucher_html_v12(data: dict[str, Any]) -> str:
    """Build the «سند القصر» receipt voucher from a live voucher ``data`` dict."""
    seller = data.get("seller") or {}
    name = html.escape(str(seller.get("name") or ""))
    name_px = 27 if len(name) <= 26 else 21
    address = _esc_lines(seller.get("address"))
    logo = company_logo_data_uri(seller)
    logo_html = f'<img class="logo" src="{logo}" alt="logo">' if logo else ""
    stamp = company_stamp_data_uri(seller)
    stamp_html = f'<img class="stamp" src="{stamp}" alt="ختم الشركة">' if stamp else ""

    number = html.escape(str(data.get("number") or ""))
    date = _date_dmy(data.get("issue_date"))
    riyal = _asset_data_uri(_RIYAL_ASSET)
    riyal_html = f'<img class="riyal" src="{riyal}" alt="SAR">' if riyal else "SAR"
    payer = html.escape(str(data.get("received_from") or ""))
    purpose = _esc_lines(data.get("purpose"))
    method = _method(data.get("payment_type"))

    def box(key: str) -> str:
        tick = "&#10003;" if key == method else ""
        return f'<span class="cb">{tick}</span>'

    def value(top: float, content: str) -> str:
        return f'<div class="val" style="top:{top}px">{content}</div>'

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ width:794px; height:1123px; position:relative; margin:0 auto; background:#fff; color:{_INK};
    font-family:Arial,'Tahoma',sans-serif; box-sizing:border-box; box-shadow:0 1px 6px rgba(0,0,0,.12); overflow:hidden; }}
  .frame {{ position:absolute; left:{_FRAME_L}px; top:{_FRAME_T}px; width:{_FRAME_W}px; height:{_FRAME_H}px;
    border:2.5px solid #2a2a2a; box-sizing:border-box; }}
  .abs {{ position:absolute; white-space:nowrap; }}
  .ar {{ direction:rtl; }}
  .b {{ font-weight:700; }}
  .seller {{ position:absolute; top:6px; right:15px; width:260px; text-align:center; direction:rtl;
    overflow-wrap:anywhere; word-break:break-word; }}
  .seller .nm {{ font-size:{name_px}px; font-weight:700; line-height:{name_px + 5}px; -webkit-text-stroke:.35px currentColor; }}
  .seller .ad {{ font-size:10px; font-weight:700; line-height:13.5px; margin-top:3px; -webkit-text-stroke:.2px currentColor; }}
  .num {{ position:absolute; left:333px; top:44px; min-width:92px; height:32px; padding:0 6px; box-sizing:border-box;
    border:1.5px solid #222; display:flex; align-items:center; justify-content:center;
    color:{_MAROON}; font-size:17px; font-weight:700; direction:ltr; white-space:nowrap; }}
  .logo-box {{ position:absolute; left:86px; top:9px; width:120px; height:70px; }}
  .logo {{ width:120px; height:70px; object-fit:contain; display:block; }}
  .rule {{ position:absolute; left:9px; right:10px; top:110px; height:4px; background:#2f2f2f; }}
  .rule2 {{ position:absolute; left:9px; right:10px; top:119px; height:1.5px; background:#2f2f2f; }}
  .amount {{ position:absolute; right:15px; top:161px; min-width:136px; padding:0 8px; height:38px; border:1.5px solid #222; border-radius:8px;
    box-sizing:border-box; display:flex; align-items:center; justify-content:center; gap:8px; direction:ltr;
    font-size:17px; font-weight:700; white-space:nowrap; }}
  .riyal {{ height:13px; width:auto; display:block; }}
  .title {{ position:absolute; left:0; width:{_INNER_W - 0}px; text-align:center; }}
  /* Windows' Arial has no bold Arabic face: a hairline stroke gives the scan's weight. */
  .ab {{ -webkit-text-stroke:.4px currentColor; }}
  .val {{ position:absolute; left:{_VALUE_CX - 210}px; width:420px; text-align:center; direction:rtl;
    font-size:15px; font-weight:700; line-height:19px; overflow-wrap:anywhere; -webkit-text-stroke:.4px currentColor; }}
  .en {{ font-size:15.5px; font-weight:700; }}
  .arl {{ font-size:15px; font-weight:700; direction:rtl; -webkit-text-stroke:.4px currentColor; }}
  .cb {{ display:inline-block; width:9px; height:10px; border:1.3px solid #222; vertical-align:-1px;
    margin:0 4px; font-size:10px; line-height:10px; text-align:center; font-weight:700; }}
  .arl.r3 {{ font-size:14px; }}
  .sig {{ position:absolute; width:180px; text-align:center; }}
  .sig .a {{ font-size:15px; font-weight:700; direction:rtl; line-height:18px; -webkit-text-stroke:.4px currentColor; }}
  .sig .e {{ font-size:12.3px; line-height:15px; margin-top:8px; }}
  .sig .ln {{ width:117px; margin:46px auto 0; border-top:1.5px solid #333; }}
  .stamp {{ position:absolute; left:403px; top:667px; width:267px; height:201px; object-fit:contain; }}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#fff; }}
    .sheet {{ margin:0; box-shadow:none; height:900px; break-inside:avoid; page-break-inside:avoid; }}
  }}
</style>
</head>
<body>
  <div class="sheet">
    <div class="frame">
      <div class="seller"><div class="nm">{name}</div><div class="ad">{address}</div></div>
      <div class="num">#{number}</div>
      <div class="logo-box">{logo_html}</div>
      <div class="rule"></div><div class="rule2"></div>

      <div class="amount">{riyal_html}<span>{_num(data.get("amount"))}</span></div>
      <div class="title ar b ab" style="top:135px; font-size:32px; line-height:38px; -webkit-text-stroke:.7px currentColor;">ســنــد قــبــض</div>
      <div class="title b" style="top:183px; font-size:20.5px; line-height:27px;">Received Voucher</div>
      <div class="abs" style="left:{_INNER_W / 2 - 88}px; top:219.5px; width:176px; height:4px; background:#2f2f2f;"></div>
      <div class="abs ar b" style="left:15px; top:162px; font-size:14px;"><span class="ab">التاريخ:</span> <span dir="ltr" style="font-size:16.5px;">{date}</span></div>

      <div class="abs en" style="left:15px; top:242px;">Recevied From Mr.</div>
      {value(244, payer)}
      <div class="abs arl" style="right:16px; top:244px;">استلمنا من</div>

      <div class="abs en" style="left:15px; top:286px;">The Sum Of</div>
      {value(288, _words(data.get("amount")))}
      <div class="abs arl" style="right:16px; top:288px;">مبلغاً وقدره</div>

      <div class="abs ar" style="right:16px; top:331px;"><span class="arl r3">نقداً</span>{box("cash")}<span class="en">Cash</span></div>
      <div class="abs ar" style="right:96px; top:331px;"><span class="arl r3">شيك</span>{box("cheque")}<span class="en">Cheque</span></div>
      <div class="abs ar" style="right:198px; top:331px;"><span class="arl r3">تحويل</span>{box("transfer")}<span class="en">Transfer</span> <span class="arl r3">رقم</span></div>
      <div class="abs en" style="right:389px; top:331px;">No</div>
      <div class="abs arl r3" style="right:414px; top:332px;">على خزينة / بنك</div>
      <div class="abs" style="right:508px; top:332px; font-size:14.5px;">Main Treasury</div>
      <div class="abs ar" style="left:14px; top:332px;"><span class="arl r3">بتاريخ</span> <span dir="ltr" style="font-size:15px;">{date}</span></div>

      <div class="abs en" style="left:14px; top:373px;">For</div>
      {value(375, purpose)}
      <div class="abs arl" style="right:16px; top:375px;">وذلك مقابل</div>

      <div class="sig" style="left:{133 - 90}px; top:465px;"><div class="a">توقيع المدير</div><div class="e">Manager Sig.</div><div class="ln"></div></div>
      <div class="sig" style="left:{379 - 90}px; top:465px;"><div class="a">أمين الصندوق</div><div class="e">Cashier Sig.</div><div class="ln"></div></div>
      <div class="sig" style="left:{623 - 90}px; top:465px;"><div class="a">توقيع المستلم</div><div class="e">Received Sig.</div><div class="ln"></div></div>
    </div>
    {stamp_html}
  </div>
</body>
</html>"""


__all__ = ["build_receipt_voucher_html_v12"]
