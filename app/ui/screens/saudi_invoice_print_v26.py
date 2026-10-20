"""«النموذج التاسع عشر» — «المرآة ثنائية اللغة» (design #2 of the second mock-up
gallery, 2026-10-18, chosen together with #1 and #4).

The whole page mirrors around a central axis, charcoal + copper:
* the seller in Arabic on the right, in English on the left (``name_en`` /
  ``address_en`` when the company has them), the logo in a round «medal» between;
* «فاتورة ضريبية ◆ TAX INVOICE» on a two-tone axis;
* two «mirror» blocks — بيانات الفاتورة / Invoice Details and العميل / Customer —
  where every row has its Arabic label on one edge, its English label on the
  other and the value centred between;
* the items table with bilingual (Arabic over English) column titles;
* centred mirror totals ending in a copper grand-total pill, the amount in words,
  then the QR between an Arabic and an English «scan to verify» caption; with
  «إظهار الختم» the stamp takes the English side and both captions stack on the
  Arabic side.

Everything is live from ``data``; the QR is ``data["qr_payload"]`` (the Phase-1
wrapper swaps it).
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
    qr_img,
    stamp_img,
)

_INK = "#1f2937"
_COPPER = "#b4652b"
_SAND = "#e8d6c8"
_MUTED = "#6b7280"

_PAD = 46
_CONTENT_W = 816 - 2 * _PAD

_PAYMENT_EN = {"نقدي": "Cash", "نقدا": "Cash", "آجل": "Credit", "تحويل": "Bank Transfer", "شبكة": "Card"}

_CSS = f"""
  .d26 {{ padding:0 {_PAD}px; font-family:'Cairo','Tajawal','Segoe UI','Tahoma',sans-serif; color:{_INK};
          font-size:12.5px; line-height:1.45; }}
  .d26 .en {{ font-family:'Readex Pro','Segoe UI',sans-serif; direction:ltr; unicode-bidi:isolate; }}
  .d26 .top {{ display:grid; grid-template-columns:1fr 112px 1fr; align-items:center; gap:10px; }}
  .d26 .top .ar {{ text-align:right; }}
  .d26 .top .lt {{ text-align:left; direction:ltr; }}
  .d26 .top h1 {{ margin:0; font-size:19px; font-weight:800; line-height:1.3; }}
  .d26 .top .lt h1 {{ font-size:16px; font-weight:600; }}
  .d26 .top .s {{ font-size:11.5px; color:{_MUTED}; }}
  .d26 .medal {{ width:104px; height:104px; border-radius:50%; border:2px solid {_COPPER}; padding:8px; margin:auto;
                 box-sizing:border-box; background:#ffffff; }}
  .d26 .medal .in {{ width:100%; height:100%; border-radius:50%; background:#fbf3ec; display:flex;
                     align-items:center; justify-content:center; overflow:hidden; }}
  .d26 .axis {{ display:grid; grid-template-columns:1fr 30px 1fr; align-items:center; margin:16px 0 12px; }}
  .d26 .axis .a {{ text-align:left; font-size:28px; font-weight:800; padding-left:14px; border-bottom:2px solid {_INK}; }}
  .d26 .axis .b {{ text-align:right; font-size:21px; font-weight:600; color:{_COPPER}; letter-spacing:2px;
                   border-bottom:2px solid {_COPPER}; }}
  .d26 .axis .dia {{ width:16px; height:16px; background:{_COPPER}; transform:rotate(45deg); margin:auto; }}
  .d26 .blocks {{ display:grid; grid-template-columns:1fr 1fr; gap:26px; }}
  .d26 .cap {{ display:flex; justify-content:space-between; font-size:12px; font-weight:800; color:{_COPPER};
               border-bottom:1px solid {_SAND}; padding-bottom:3px; margin-bottom:2px; }}
  .d26 .cap .en {{ font-weight:600; }}
  .d26 .mr {{ display:grid; grid-template-columns:auto 1fr auto; gap:8px; align-items:baseline; padding:5px 0;
              border-bottom:1px dotted #d1d5db; }}
  .d26 .mr .k {{ color:{_MUTED}; white-space:nowrap; }}
  .d26 .mr .v {{ text-align:center; font-weight:700; overflow-wrap:anywhere; word-break:break-word; min-width:0; }}
  .d26 .mr .ke {{ color:#9ca3af; font-size:11px; white-space:nowrap; }}
  .d26 .items {{ margin-top:20px; }}
  .d26 .items > thead > tr > th {{ padding:8px 6px; border-top:2px solid {_INK}; border-bottom:1px solid {_COPPER};
                                   font-size:12px; line-height:1.25; font-weight:700; }}
  .d26 .items > thead > tr > th .en {{ display:block; font-size:9.5px; color:{_COPPER}; font-weight:400; }}
  .d26 .items > tbody > tr > td {{ padding:8px 6px; border-bottom:1px solid #eee7e1; }}
  .d26 .items > tbody > tr.closing > td {{ border:0; padding:0; }}
  .d26 .items .c-total {{ font-weight:700; }}
  .d26 .tot {{ width:560px; margin:14px auto 0; }}
  .d26 .tot .mr {{ grid-template-columns:1fr 170px 1fr; font-size:13px; padding:4px 0; }}
  .d26 .tot .mr .ke {{ text-align:left; }}
  .d26 .tot .g {{ display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:center; margin-top:8px; }}
  .d26 .tot .g .k {{ font-weight:800; font-size:14px; white-space:nowrap; }}
  .d26 .tot .g .ke {{ text-align:left; font-size:12px; color:{_COPPER}; white-space:nowrap; }}
  .d26 .tot .g .v {{ background:{_COPPER}; color:#ffffff; border-radius:99px; padding:6px 26px; font-size:20px;
                     font-weight:800; white-space:nowrap; }}
  .d26 .words {{ text-align:center; margin-top:10px; font-size:12.5px; color:#4b5563; }}
  .d26 .foot {{ display:grid; grid-template-columns:1fr auto 1fr; gap:18px; align-items:center; margin-top:10px; }}
  .d26 .foot .r {{ text-align:left; font-size:12px; color:{_MUTED}; border-left:2px solid {_COPPER}; padding-left:16px; }}
  .d26 .foot .l {{ text-align:right; font-size:11px; color:#9ca3af; border-right:2px solid {_COPPER}; padding-right:16px; }}
  .d26 .foot .r .en {{ font-size:11px; color:#9ca3af; }}
  .d26 .stamp {{ display:flex; justify-content:flex-end; }}
"""


def _mr(label: str, value: str, label_en: str) -> str:
    return (
        f'<div class="mr"><span class="k">{label}</span><span class="v">{value}</span>'
        f'<span class="ke en">{label_en}</span></div>'
    )


def build_invoice_html_v26(data: dict[str, Any]) -> str:
    """Build «النموذج التاسع عشر» (المرآة ثنائية اللغة) from the shared invoice data dict."""
    ctx = invoice_context(data)
    seller, customer = ctx["seller"], ctx["customer"]

    # Arabic seller block (right) and its English mirror (left).
    ar = [f'<h1>{esc(seller.get("name"))}</h1>']
    en = [f'<h1>{esc(seller.get("name_en") or seller.get("name"))}</h1>']
    if seller.get("vat"):
        ar.append(f'<div class="s">الرقم الضريبي {ltr(esc(seller.get("vat")))}</div>')
        en.append(f'<div class="s">VAT No. {esc(seller.get("vat"))}</div>')
    if seller.get("cr"):
        ar.append(f'<div class="s">السجل التجاري {ltr(esc(seller.get("cr")))}</div>')
        en.append(f'<div class="s">C.R. {esc(seller.get("cr"))}</div>')
    if seller.get("address"):
        ar.append(f'<div class="s">{esc_lines(seller.get("address"))}</div>')
    address_en = seller.get("address_en")
    if address_en and address_en != seller.get("address"):
        en.append(f'<div class="s">{esc_lines(address_en)}</div>')

    payment = ctx["payment"]
    payment_en = _PAYMENT_EN.get(str(data.get("payment_label") or "نقدي").strip(), "")
    payment_v = payment + (f' · <span class="en">{payment_en}</span>' if payment_en else "")

    customer_rows = [_mr("الاسم", esc(customer.get("name")), "Name")]
    if customer.get("vat"):
        customer_rows.append(_mr("الرقم الضريبي", ltr(esc(customer.get("vat"))), "VAT No."))
    if customer.get("cr"):
        customer_rows.append(_mr("السجل التجاري", ltr(esc(customer.get("cr"))), "C.R."))
    if customer.get("address"):
        customer_rows.append(_mr("العنوان", esc_lines(customer.get("address")), "Address"))

    total_rows = [_mr("الإجمالي قبل الضريبة", ltr(ctx["subtotal"]), "Subtotal")]
    if ctx["discount"]:
        total_rows.append(_mr(f'الخصم {ltr(ctx["discount_rate"])}', ltr("-" + ctx["discount"]), "Discount"))
    total_rows.append(_mr(f'ضريبة القيمة المضافة {ltr(ctx["vat_rate"])}', ltr(ctx["vat"]), f'VAT {ctx["vat_rate"]}'))

    # QR between the Arabic and English captions; with a stamp, both captions
    # stack on the Arabic side and the stamp takes the English side, so the
    # closing block does not grow taller.
    stamp = stamp_img(data, 180, 135)
    caption_ar = '<div class="r">امسح الرمز للتحقق من الفاتورة'
    caption_en = "Scan to verify this invoice"
    if stamp:
        foot = f'{caption_ar}<div class="en">{caption_en}</div></div>{qr_img(data)}<div class="stamp">{stamp}</div>'
    else:
        foot = f'{caption_ar}</div>{qr_img(data)}<div class="l en">{caption_en}</div>'
    closing = f"""
      <div class="tot">
        {"".join(total_rows)}
        <div class="g"><span class="k">الإجمالي شامل الضريبة</span><span class="v">{ltr(ctx["total"] + " ر.س")}</span>
          <span class="ke en">Total incl. VAT</span></div>
      </div>
      <div class="words">المبلغ كتابةً: {ctx["words"]}</div>
      <div class="foot">{foot}</div>"""

    logo = logo_img(seller, 72, 72)
    body = f"""
    <div class="top">
      <div class="ar wrap">{"".join(ar)}</div>
      <div class="medal"><div class="in">{logo}</div></div>
      <div class="lt en wrap">{"".join(en)}</div>
    </div>
    <div class="axis"><div class="a">فاتورة ضريبية</div><div class="dia"></div><div class="b en">TAX INVOICE</div></div>
    <div class="blocks">
      <div><div class="cap"><span>بيانات الفاتورة</span><span class="en">Invoice Details</span></div>
        {_mr("رقم الفاتورة", ltr(ctx["number"]), "Invoice No.")}
        {_mr("التاريخ", ltr(ctx["date"]), "Date")}
        {_mr("الوقت", ltr(ctx["time"]), "Time")}
        {_mr("طريقة الدفع", payment_v, "Payment")}
      </div>
      <div><div class="cap"><span>العميل</span><span class="en">Customer</span></div>
        {"".join(customer_rows)}
      </div>
    </div>
    {items_table(ctx, _CONTENT_W, closing, bilingual=True)}"""

    return page_html(css=_CSS, sheet_class="d26", top=34, bottom=28, body=body)


__all__ = ["build_invoice_html_v26"]
