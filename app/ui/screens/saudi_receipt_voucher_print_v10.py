"""«سند عقيل» — receipt-voucher layout replica (added 2026-10-06).

Copied, position for position, from the user's WhatsApp scan
``تصامبم جديدة\\WhatsApp Image 2026-10-06 at 1.22.21 PM.jpeg`` (a Daftra
«عملية دفع عميل» receipt of مؤسسة موضي عقيل العتيبي). Like the invoice layout
replicas (v15–v21) only the LAYOUT is fixed: the logo, the seller block and the
payer come LIVE from ``data`` — the selected company and customer.

Measured off the 1080×1503 scan and scaled ×794/1080 onto the A4 voucher sheet
(794×1123, the size every voucher prints at):

* top: the seller block (bold name · «السجل التجاري - Register Number : …» ·
  «الرقم الضريبي - Tax Number : …» · address lines) right-aligned beside the
  logo, which sits in the far top-right corner («Zoom» — scaled to fill its box,
  never stretched);
* a full-width bordered frame: the amount box (riyal sign + figure) top-right,
  «عملية دفع عميل #n» centred, «التاريخ: Y/M/D» top-left, then five
  «label / value» rows — استلمنا من · مبلغاً وقدره · طريقة الدفع · إلى خزينة ·
  وذلك مقابل;
* under the frame: «Accountant - المحاسب» right, «Manager - المدير» left and the
  company stamp centred between them.

Data keys: ``number``, ``issue_date``, ``amount``, ``received_from`` (+ optional
``received_from_code``, printed «#code - name» like the scan), ``payment_type``
(«نقدي» when blank), ``purpose`` (``\\n`` → a new line) and ``seller``. Our data
model has no treasury, so «إلى خزينة» always prints the scan's «الخزنة الرئيسية»;
the scan's «الرمزالبريدي» line has no field either and is not printed.
"""

from __future__ import annotations

import datetime
import html
from typing import Any

from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
)
from app.ui.screens.saudi_receipt_voucher_print import _money

_INK = "#1b1b1b"
_RIYAL_ASSET = "riyal_symbol.png"
_TREASURY = "الخزنة الرئيسية"

# Geometry (sheet px) — scan px × 794/1080.
_SIDE = 54          # the frame's left/right inset
_FRAME_TOP = 171    # the frame's top edge
_LOGO_W, _LOGO_H = 146, 96
_STAMP_W, _STAMP_H = 173, 170


def _esc_lines(value: Any) -> str:
    """Escape ``value`` and keep its own line breaks."""
    text = str(value or "").strip()
    return "<br>".join(html.escape(part.strip()) for part in text.splitlines() if part.strip())


def _date_ymd(value: Any) -> str:
    """«2026/2/5» — year first, no zero padding, like the scan."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return f"{value.year}/{value.month}/{value.day}"
    return html.escape(str(value or ""))


def _words(amount: Any) -> str:
    """The scan's wording: «… ريال سعودي لا غير.» (no leading «فقط»)."""
    text = amount_in_words_ar(amount).strip()
    if text.startswith("فقط "):
        text = text[len("فقط "):]
    text = text.replace("ريالاً", "ريال سعودي")
    return html.escape(text.rstrip(".") + ".")


def build_receipt_voucher_html_v10(data: dict[str, Any]) -> str:
    """Build the «سند عقيل» receipt voucher from a live voucher ``data`` dict."""
    seller = data.get("seller") or {}
    name = html.escape(str(seller.get("name") or ""))
    cr = html.escape(str(seller.get("cr") or "").strip())
    vat = html.escape(str(seller.get("vat") or "").strip())
    address = _esc_lines(seller.get("address"))

    seller_lines = [f'<div class="s-name">{name}</div>']
    if cr:
        seller_lines.append(
            f'<div>السجل التجاري - <bdi dir="ltr">Register Number : {cr}</bdi></div>'
        )
    if vat:
        seller_lines.append(f'<div>الرقم الضريبي - <bdi dir="ltr">Tax Number : {vat}</bdi></div>')
    if address:
        seller_lines.append(f"<div>{address}</div>")

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img class="logo" src="{logo}" alt="logo">' if logo else ""
    )

    number = html.escape(str(data.get("number") or ""))
    amount = _money(data.get("amount"))
    riyal = _asset_data_uri(_RIYAL_ASSET)
    riyal_html = f'<img class="riyal" src="{riyal}" alt="SAR">' if riyal else "SAR"

    payer = html.escape(str(data.get("received_from") or ""))
    code = html.escape(str(data.get("received_from_code") or "").strip())
    if code:
        payer = f'<span class="code">#{code}</span> - {payer}'
    payment = html.escape(str(data.get("payment_type") or "").strip() or "نقدي")
    purpose = _esc_lines(data.get("purpose"))

    stamp = company_stamp_data_uri(seller)
    stamp_html = f'<img class="stamp" src="{stamp}" alt="ختم الشركة">' if stamp else ""

    rows = "".join(
        f'<div class="row"><span class="lbl">{label} / </span>{value}</div>'
        for label, value in (
            ("استلمنا من", payer),
            ("مبلغاً وقدره", _words(data.get("amount"))),
            ("طريقة الدفع", payment),
            ("إلى خزينة", _TREASURY),
            ("وذلك مقابل", purpose),
        )
    )

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;700;800&family=Noto+Sans:wght@400;700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ width:794px; min-height:1123px; position:relative; margin:0 auto; background:#fff; color:{_INK};
    font-family:'Noto Sans Arabic','Noto Sans','Tahoma',sans-serif; direction:rtl; box-sizing:border-box;
    box-shadow:0 1px 6px rgba(0,0,0,.12); overflow:hidden; }}
  .head {{ position:relative; min-height:{_FRAME_TOP}px; padding:39px 0 14px; box-sizing:border-box; }}
  .logo-box {{ position:absolute; top:51px; right:65px; width:{_LOGO_W}px; height:{_LOGO_H}px; }}
  .logo {{ width:{_LOGO_W}px; height:{_LOGO_H}px; object-fit:contain; display:block; }}
  .seller {{ margin-right:256px; width:330px; text-align:right;
    font-size:15px; line-height:17.4px; overflow-wrap:anywhere; word-break:break-word; }}
  .seller .s-name {{ font-size:19px; font-weight:700; line-height:24px; margin-bottom:6px; }}
  bdi {{ unicode-bidi:isolate; }}
  .code {{ display:inline-block; direction:ltr; }}
  .frame {{ margin:0 {_SIDE}px; min-height:302px; border:1.5px solid #222; box-sizing:border-box;
    padding:17px 14px 38px; position:relative; }}
  .top {{ position:relative; height:35px; }}
  .amount {{ position:absolute; right:0; top:0; min-width:120px; padding:0 8px; height:35px; border:1.5px solid #222; box-sizing:border-box;
    display:flex; align-items:center; justify-content:center; gap:6px; direction:ltr;
    font-size:17px; font-weight:700; white-space:nowrap; }}
  .riyal {{ height:15px; width:auto; display:block; }}
  .title {{ position:absolute; left:0; right:0; top:-4px; text-align:center; font-size:20px; font-weight:700; line-height:35px; }}
  .date {{ position:absolute; left:1px; top:0; font-size:17px; font-weight:700; line-height:35px; white-space:nowrap; }}
  .row {{ font-size:18.5px; font-weight:700; line-height:22px; margin-top:18px; padding-right:1px;
    overflow-wrap:anywhere; word-break:break-word; }}
  .top + .row {{ margin-top:8px; }}
  .foot {{ position:relative; height:200px; margin:0 {_SIDE}px; }}
  .sign {{ position:absolute; top:24px; font-size:15px; line-height:20px; white-space:nowrap; }}
  .sign.r {{ right:8px; }}
  .sign.l {{ left:51px; }}
  .stamp {{ position:absolute; top:0; left:50%; transform:translateX(-50%); width:{_STAMP_W}px; height:{_STAMP_H}px;
    object-fit:contain; }}
  @page {{ size:A4; margin:0; }}
  @media print {{
    html, body {{ background:#fff; }}
    .sheet {{ margin:0; box-shadow:none; min-height:0; break-inside:avoid; page-break-inside:avoid; }}
  }}
</style>
</head>
<body>
  <div class="sheet">
    <div class="head">
      <div class="seller">{''.join(seller_lines)}</div>
      <div class="logo-box">{logo_html}</div>
    </div>
    <div class="frame">
      <div class="top">
        <div class="amount">{riyal_html}<span>{amount}</span></div>
        <div class="title">عملية دفع عميل <bdi dir="ltr">#{number}</bdi></div>
        <div class="date">التاريخ: <bdi dir="ltr">{_date_ymd(data.get("issue_date"))}</bdi></div>
      </div>
      {rows}
    </div>
    <div class="foot">
      <div class="sign r">المحاسب - <bdi dir="ltr">Accountant</bdi></div>
      {stamp_html}
      <div class="sign l">المدير - <bdi dir="ltr">Manager</bdi></div>
    </div>
  </div>
</body>
</html>"""


__all__ = ["build_receipt_voucher_html_v10"]
