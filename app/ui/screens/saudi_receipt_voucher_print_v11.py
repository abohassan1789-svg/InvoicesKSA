"""«سند الامل» — receipt-voucher layout replica (added 2026-10-06).

Copied, position for position, from the user's WhatsApp scan
``تصامبم جديدة\\المنفذ\\WhatsApp Image 2026-10-06 at 1.22.36 PM.jpeg`` (an
Odoo «سند قبض» of مؤسسة الامل الناجح). Like «سند عقيل» only the LAYOUT is
fixed: the seller block, the payer and the stamp come LIVE from ``data``. The
scan carries no logo, so neither does this layout.

Measured off the 1080×1493 scan and scaled ×794/1080 onto the A4 voucher sheet:

* top-left: «سند قبض» + the seller (bold name · address lines), then a hairline;
* right: «مستلم من» + the payer; left: the label/value list (رقم المرجع ·
  التاريخ · النوع · الحساب · المبلغ غير المخصص · المبلغ المخصص · المبلغ) —
  labels bold, hugging their values;
* a borderless 6-column table (# · رقم المرجع · النوع · المبلغ · المبلغ المستحق ·
  التاريخ) with the one row this receipt settles;
* «الوصف» + the purpose, and the company stamp under it, left of centre.

Data keys: ``number``, ``issue_date``, ``amount``, ``received_from``, ``purpose``
(``\\n`` → a new line), ``seller`` and the optional ``reference`` (the settled
invoice's number — the sales screen passes it; blank otherwise). Our data model
has no account / allocation, so — as on the scan — النوع is «قبض», الحساب is
«النقدية في الخزينة», المبلغ غير المخصص 0.00 and المبلغ المخصص = المبلغ, and the
row's النوع is «فاتورة مبيعات» with المبلغ المستحق 0.00.
"""

from __future__ import annotations

import datetime
import html
from typing import Any

from app.ui.screens.saudi_invoice_print import _asset_data_uri, company_stamp_data_uri
from app.ui.screens.saudi_receipt_voucher_print import _money

_INK = "#2b2b2b"       # bold labels, titles
_TEXT = "#5f5f5f"      # regular text (Odoo's muted grey)
_RULE = "#e3e3e3"      # the hairline under the header
_RIYAL_ASSET = "riyal_symbol.png"

_LEFT = 66             # the scan's left text edge (sheet px)
_RIGHT = 147           # … and its right one
_STAMP_W, _STAMP_H = 160, 159

# Items-table columns, right → left: (title, width px). Widths put each column's
# centre where the scan has it.
_COLS = (("#", 16), ("رقم المرجع", 108), ("النوع", 108), ("المبلغ", 114),
         ("المبلغ المستحق", 122), ("التاريخ", 118))


def _esc_lines(value: Any) -> str:
    text = str(value or "").strip()
    return "<br>".join(html.escape(part.strip()) for part in text.splitlines() if part.strip())


def _date_iso(value: Any) -> str:
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return html.escape(str(value or ""))


def build_receipt_voucher_html_v11(data: dict[str, Any]) -> str:
    """Build the «سند الامل» receipt voucher from a live voucher ``data`` dict."""
    seller = data.get("seller") or {}
    name = html.escape(str(seller.get("name") or ""))
    address = _esc_lines(seller.get("address"))

    riyal = _asset_data_uri(_RIYAL_ASSET)

    def money(value: Any) -> str:
        sign = f'<img class="riyal" src="{riyal}" alt="SAR">' if riyal else "SAR "
        return f'<span class="money">{sign}{_money(value)}</span>'

    number = html.escape(str(data.get("number") or ""))
    date = _date_iso(data.get("issue_date"))
    amount = data.get("amount")
    payer = html.escape(str(data.get("received_from") or ""))
    reference = html.escape(str(data.get("reference") or ""))
    purpose = _esc_lines(data.get("purpose"))

    kv = "".join(
        f'<tr class="{cls}"><td class="k">{label}:</td><td class="v">{value}</td></tr>'
        for cls, label, value in (
            ("", "رقم المرجع", f'<span dir="ltr">{number}</span>'),
            ("", "التاريخ", f'<span dir="ltr">{date}</span>'),
            ("", "النوع", "قبض"),
            ("", "الحساب", "النقدية في الخزينة"),
            ("gap", "المبلغ غير المخصص", money(0)),
            ("wide", "المبلغ المخصص", money(amount)),
            ("wide", "المبلغ", money(amount)),
        )
    )
    colgroup = "".join(f'<col style="width:{w}px">' for _, w in _COLS)
    head = "".join(f"<th>{t}</th>" for t, _ in _COLS)
    row = "".join(
        f"<td{cls}>{v}</td>"
        for cls, v in (
            ("", "1"),
            ("", f'<span dir="ltr">{reference}</span>'),
            (' class="b"', "فاتورة مبيعات"),
            ("", money(amount)),
            ("", money(0)),
            ("", f'<span dir="ltr">{date}</span>'),
        )
    )

    stamp = company_stamp_data_uri(seller)
    stamp_html = f'<img class="stamp" src="{stamp}" alt="ختم الشركة">' if stamp else ""

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@300;400;600;700&family=Noto+Sans:wght@400;700&display=swap" rel="stylesheet">
<style>
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ width:794px; min-height:1123px; position:relative; margin:0 auto; background:#fff; color:{_TEXT};
    font-family:'Noto Sans Arabic','Noto Sans','Tahoma',sans-serif; direction:rtl; box-sizing:border-box;
    padding:0 {_RIGHT}px 0 {_LEFT}px; box-shadow:0 1px 6px rgba(0,0,0,.12); overflow:hidden; }}
  .head {{ padding-top:51px; text-align:left; width:330px; margin-right:auto;
    overflow-wrap:anywhere; word-break:break-word; }}
  .title {{ font-size:23px; font-weight:400; color:#3a3a3a; line-height:26px; }}
  .s-name {{ font-size:11.5px; font-weight:700; color:{_INK}; line-height:15px; }}
  .s-addr {{ font-size:10.5px; line-height:12.5px; }}
  .rule {{ border-top:1px solid {_RULE}; margin-top:6px; }}
  .mid {{ display:flex; justify-content:space-between; align-items:flex-start; min-height:185px; }}
  .payer {{ width:330px; padding-top:6px; text-align:right; overflow-wrap:anywhere; }}
  .payer .cap {{ font-size:14.5px; font-weight:700; color:{_INK}; line-height:19px; }}
  .payer .nm {{ font-size:14px; line-height:16px; }}
  .kv {{ border-collapse:collapse; margin-top:14px; font-size:10.5px; }}
  .kv td {{ padding:0; height:20px; vertical-align:top; line-height:14px; white-space:nowrap; }}
  .kv tr.gap td {{ padding-top:3px; height:27px; }}
  .kv tr.wide td {{ height:27px; }}
  .kv .k {{ font-weight:700; color:{_INK}; text-align:left; padding-left:4px; }}
  .kv .v {{ text-align:right; min-width:81px; }}
  .money {{ direction:ltr; unicode-bidi:isolate; white-space:nowrap; }}
  .riyal {{ height:8px; width:auto; vertical-align:0; margin-right:2px; opacity:.85; }}
  .items {{ border-collapse:collapse; table-layout:fixed; width:586px; margin:0 0 0 -5px; }}
  .items th {{ font-size:11.5px; font-weight:700; color:{_INK}; text-align:center; padding:0 0 4px; line-height:16px; white-space:nowrap; }}
  .items td {{ font-size:10.5px; text-align:center; padding:0; line-height:14px; overflow-wrap:anywhere; }}
  .items td.b {{ font-weight:700; color:{_INK}; }}
  .desc-h {{ margin-top:66px; font-size:20px; font-weight:400; color:#3a3a3a; line-height:26px; }}
  .desc-row {{ position:relative; margin-top:38px; min-height:{_STAMP_H + 10}px; }}
  .desc {{ width:220px; font-size:12px; line-height:16px; overflow-wrap:anywhere; }}
  .stamp {{ position:absolute; top:0; left:{260 - _LEFT}px; width:{_STAMP_W}px; height:{_STAMP_H}px; object-fit:contain; }}
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
      <div class="title">سند قبض</div>
      <div class="s-name">{name}</div>
      <div class="s-addr">{address}</div>
    </div>
    <div class="rule"></div>
    <div class="mid">
      <div class="payer"><div class="cap">مستلم من</div><div class="nm">{payer}</div></div>
      <table class="kv">{kv}</table>
    </div>
    <table class="items"><colgroup>{colgroup}</colgroup><thead><tr>{head}</tr></thead><tbody><tr>{row}</tr></tbody></table>
    <div class="desc-h">الوصف</div>
    <div class="desc-row"><div class="desc">{purpose}</div>{stamp_html}</div>
  </div>
</body>
</html>"""


__all__ = ["build_receipt_voucher_html_v11"]
