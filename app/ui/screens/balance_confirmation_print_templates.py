"""The four extra balance-confirmation letter layouts (picked 2026-10-20).

From the 15-layout gallery the user picked 1, 2, 13 and 14, every one with the
company logo and stamp:

* «الترويسة الكحلية»   — navy letterhead band, boxed title, amount strip;
* «الإطار المزدوج»     — formal letter inside a double frame;
* «الأخضر المؤسسي»     — the app's green, amount on a pale-green strip;
* «المقارنة الجانبية»  — «حسب سجلاتنا» beside an empty «حسب سجلاتكم» box.

They take the same ``data`` dict as :func:`build_balance_confirmation_html`.
The logo and stamp come from ``data["seller"]`` (the chosen company); with
«كل الشركات» there is no company, so the sheet prints without them.
"""

from __future__ import annotations

from typing import Any

from app.ui.screens.balance_confirmation_print import (
    _decimal,
    _esc,
    _iso,
    _slash,
    balance_direction,
)
from app.ui.screens.customer_statement_print import _HIJRI_MONTHS, _HIJRI_SCRIPT, _hijri
from app.ui.screens.saudi_invoice_print import (
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
)
from app.ui.screens.saudi_invoice_print_v28 import _FONTS, _font_face_css

_GREET = "السلام عليكم ورحمة الله وبركاته .. وبعد"
_REQUEST = (
    "ونظراً لأن إجراءات المراجعة لحساباتنا تستدعي تأييدكم لهذا الرصيد إذا كان مطابقاً لسجلاتكم "
    "أو إيضاح الفرق بالتفصيل في حالة عدم مطابقته في التاريخ المشار إليه، ومن ثم التوقيع على الجزء "
    "التالي من هذا الخطاب وإعادته إلينا ..."
)
_THANKS = "وتفضلوا بقبول فائق الاحترام ،،،"
_NOTE = "هذا الخطاب معتمد من قبلنا ما لم يتم الرد عليه خلال 15 يوم من تاريخ الاستلام ولا يقبل المراجعة بعد.."
_DOTS = "........................"
_SIGN = (f"الاسم : {_DOTS} &nbsp;&nbsp; الوظيفة : {_DOTS} &nbsp;&nbsp; التوقيع : {_DOTS}")


def _ctx(data: dict[str, Any]) -> dict[str, Any]:
    """Everything a layout prints, escaped and formatted once."""
    seller = data.get("seller") or {}
    balance = _decimal(data.get("balance"))
    amount = abs(balance)
    date_iso = _iso(data.get("date"))
    meta = " · ".join(
        part for part in (
            f"س.ت {_esc(seller.get('cr'))}" if seller.get("cr") else "",
            f"الرقم الضريبي {_esc(seller.get('vat'))}" if seller.get("vat") else "",
            _esc(seller.get("address")),
        ) if part
    )
    return {
        "seller": seller,
        "company": _esc(seller.get("name")),
        "meta": meta,
        "customer": _esc(data.get("customer")),
        "number": _esc(data.get("number")),
        "date": _esc(_slash(date_iso)),
        "hijri": _hijri(date_iso),
        "amount": f"{amount:,.2f}",
        "words": _esc(amount_in_words_ar(amount)),
        "direction": balance_direction(balance),
        "debit": f"{_decimal(data.get('total_debit')):,.2f}",
        "credit": f"{_decimal(data.get('total_credit')):,.2f}",
        "description": _esc((data.get("description") or "").strip()),
        "logo": company_logo_data_uri(seller),
        "stamp": company_stamp_data_uri(seller),
    }


def _logo(c: dict[str, Any], *, height: int = 64, style: str = "") -> str:
    if not c["logo"]:
        return ""
    return (f'<img src="{c["logo"]}" alt="" style="max-height:{height}px;max-width:200px;'
            f'object-fit:contain;display:block;{style}">')


def _signature(c: dict[str, Any], *, color: str = "#1f2933") -> str:
    """«المدير المالي» with the company stamp under it, on the left."""
    stamp = (f'<img src="{c["stamp"]}" alt="" style="max-height:96px;max-width:130px;'
             'object-fit:contain;display:block;margin:4px auto 0;">' if c["stamp"] else "")
    return (f'<div style="display:flex;justify-content:flex-end;margin:12px 40px 0;">'
            f'<div style="text-align:center;color:{color};"><b>المدير المالي</b>{stamp}</div></div>')


def _reply_to(c: dict[str, Any]) -> str:
    return c["company"] or "........................................"


def _description(c: dict[str, Any]) -> str:
    return f'<p>البيان : {c["description"]}</p>' if c["description"] else ""


def _document(body: str, css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  @page {{ size:A4; margin:0; }}
  .sheet {{ position:relative; width:794px; min-height:1123px; box-sizing:border-box; margin:0 auto;
           background:#fff; color:#1f2933; font-family:{_FONTS}; font-size:15.5px; line-height:1.85; overflow:hidden; }}
  .sheet p {{ margin:0 0 5px; }}
  .num {{ direction:ltr; unicode-bidi:isolate; display:inline-block; }}
  .red {{ color:#9f1239; font-weight:700; font-size:14px; margin-top:10px; }}
  @media print {{ html, body {{ background:#fff; }} .sheet {{ margin:0; }} }}
  {css}
</style>
</head>
<body>
<div class="sheet">{body}</div>
{_HIJRI_SCRIPT % ("[" + ",".join(f'"{m}"' for m in _HIJRI_MONTHS) + "]")}
</body>
</html>"""


# ---------------------------------------------------------------------------
# 1 — الترويسة الكحلية
# ---------------------------------------------------------------------------
def build_balance_confirmation_html_navy(data: dict[str, Any]) -> str:
    c = _ctx(data)
    navy = "#14304a"
    logo = _logo(c, height=62, style="background:#fff;border-radius:6px;padding:4px;")
    body = f"""
<div style="background:{navy};color:#fff;padding:22px 40px;display:flex;justify-content:space-between;align-items:center;gap:16px;">
  <div style="display:flex;align-items:center;gap:14px;">{logo}
    <div><div style="font-size:22px;font-weight:700;">{c["company"]}</div>
    <div style="font-size:11.5px;opacity:.85;">{c["meta"]}</div></div></div>
  <div style="font-size:12px;text-align:left;opacity:.95;">رقم الحركة<br><b class="num" style="font-size:17px;">{c["number"]}</b></div>
</div>
<div style="padding:26px 46px 30px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
    <div style="border:2px solid {navy};padding:6px 20px;font-size:21px;font-weight:700;color:{navy};">مصادقة على صحة الرصيد</div>
    <div style="font-size:13px;text-align:left;line-height:1.5;">حتى تاريخ: <b class="num">{c["date"]}</b><br>
      <span style="color:#0f766e;">{c["hijri"]}</span></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-weight:700;"><span>الإخوة / {c["customer"]}</span><span>المحترمون</span></div>
  <p style="text-align:center;margin-top:6px;">{_GREET}</p>
  <p>نحيط سعادتكم علماً أن رصيد حسابكم في سجلاتنا بتاريخ <b class="num">{c["date"]}</b> هو:</p>
  <div style="display:flex;align-items:stretch;border:1.5px solid {navy};margin:10px 0;">
    <div style="background:{navy};color:#fff;padding:10px 18px;font-weight:700;display:flex;align-items:center;">{c["direction"]}</div>
    <div class="num" style="padding:6px 18px;font-size:26px;font-weight:700;color:{navy};">{c["amount"]} ر.س</div>
    <div style="padding:12px 14px;font-size:12.5px;color:#475569;margin-right:auto;">{c["words"]}</div>
  </div>
  {_description(c)}
  <p>{_REQUEST}</p>
  <p style="text-align:center;">{_THANKS}</p>
  {_signature(c, color=navy)}
  <p class="red">{_NOTE}</p>
  <div style="border-top:2px solid {navy};margin-top:20px;padding-top:14px;">
    <p><b>السادة / {_reply_to(c)}</b></p>
    <p>نفيدكم أن رصيد حسابنا كما تظهره سجلاتنا يساوي مبلغ ( {_DOTS} ) ريال</p>
    <p style="margin-top:6px;">لصالحنا / لصالحكم وذلك في نهاية يوم : <b class="num">{c["date"]}</b></p>
    <p style="margin-top:22px;">{_SIGN}</p>
  </div>
</div>"""
    return _document(body)


# ---------------------------------------------------------------------------
# 2 — الإطار المزدوج الرسمي
# ---------------------------------------------------------------------------
def build_balance_confirmation_html_framed(data: dict[str, Any]) -> str:
    c = _ctx(data)
    ink = "#1f2937"
    body = f"""
<div style="position:absolute;inset:20px;border:4px double {ink};pointer-events:none;"></div>
<div style="padding:46px 56px 40px;position:relative;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;font-size:13px;">
    <span>الرقم : <b class="num">{c["number"]}</b></span>
    {_logo(c, height=74)}
    <span style="text-align:left;line-height:1.6;">التاريخ : <b class="num">{c["date"]}</b><br>الموافق : {c["hijri"]}</span>
  </div>
  <div style="text-align:center;margin:10px 0 2px;font-size:19px;font-weight:700;">{c["company"]}</div>
  <div style="text-align:center;font-size:11.5px;color:#4b5563;">{c["meta"]}</div>
  <div style="text-align:center;font-size:27px;font-weight:700;margin:14px 0 20px;border-bottom:1px solid {ink};padding-bottom:10px;">مصادقة على صحة الرصيد</div>
  <p><b>الإخوة / {c["customer"]} المحترمون</b></p>
  <p style="text-align:center;">{_GREET}</p>
  <p>نحيط سعادتكم علماً أن رصيد حسابكم في سجلاتنا بتاريخ <b class="num">{c["date"]}</b> هو مبلغ
     ( <b class="num" style="font-size:19px;">{c["amount"]}</b> ) ريال <b>{c["direction"]}</b>، {c["words"]}.</p>
  {_description(c)}
  <p>{_REQUEST}</p>
  <p style="text-align:center;">{_THANKS}</p>
  {_signature(c, color=ink)}
  <p class="red" style="text-align:center;">{_NOTE}</p>
  <div style="border-top:4px double {ink};margin-top:18px;padding-top:14px;">
    <p><b>السادة / {_reply_to(c)}</b></p>
    <p>نفيدكم أن رصيد حسابنا كما تظهره سجلاتنا يساوي مبلغ ( {_DOTS} ) ريال</p>
    <p style="margin-top:6px;">لصالحنا / لصالحكم وذلك في نهاية يوم : <b class="num">{c["date"]}</b></p>
    <p style="margin-top:22px;">{_SIGN}</p>
  </div>
</div>"""
    return _document(body)


# ---------------------------------------------------------------------------
# 13 — الأخضر المؤسسي
# ---------------------------------------------------------------------------
def build_balance_confirmation_html_green(data: dict[str, Any]) -> str:
    c = _ctx(data)
    green, dark = "#137a38", "#065f2c"
    owes = c["direction"] == "عليكم"
    chip = ("background:#fee2e2;color:#991b1b;" if owes else "background:#dcfce7;color:#166534;")
    mark = _logo(c, height=60) or (
        f'<div style="width:56px;height:56px;background:{green};color:#fff;border-radius:10px;'
        f'display:grid;place-items:center;font-weight:700;font-size:24px;">{c["company"][:1]}</div>'
        if c["company"] else "")
    body = f"""
<div style="padding:32px 44px 34px;">
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:5px solid {green};padding-bottom:12px;">
    <div style="display:flex;gap:14px;align-items:center;">{mark}
      <div><b style="font-size:20px;">{c["company"]}</b><div style="font-size:11.5px;color:#64748b;">{c["meta"]}</div></div></div>
    <div style="text-align:left;font-size:13px;"><b style="font-size:19px;color:{green};">مصادقة على الرصيد</b><br>
      <span class="num">{c["number"]}</span></div>
  </div>
  <p style="margin-top:16px;font-size:13.5px;">حتى تاريخ : <b class="num">{c["date"]}</b> الموافق {c["hijri"]}</p>
  <p><b>الإخوة / {c["customer"]} المحترمون</b></p>
  <p>{_GREET}</p>
  <p>نحيط سعادتكم علماً أن رصيد حسابكم في سجلاتنا بتاريخ <b class="num">{c["date"]}</b> هو:</p>
  <div style="background:#ecfdf3;border-right:6px solid {green};padding:10px 16px;margin:8px 0;display:flex;justify-content:space-between;align-items:center;">
    <span class="num" style="font-size:27px;font-weight:700;color:{dark};">{c["amount"]} ر.س</span>
    <span style="{chip}border-radius:14px;padding:3px 14px;font-size:13px;font-weight:700;">{c["direction"]}</span>
  </div>
  <p style="font-size:13px;color:{dark};">{c["words"]}</p>
  {_description(c)}
  <p>{_REQUEST}</p>
  <p>{_THANKS}</p>
  {_signature(c, color=dark)}
  <p class="red">{_NOTE}</p>
  <div style="border:1.5px solid #b7e4c7;border-radius:8px;padding:14px 16px;margin-top:16px;">
    <p><b style="color:{green};">السادة / {_reply_to(c)}</b></p>
    <p>نفيدكم أن رصيد حسابنا كما تظهره سجلاتنا يساوي مبلغ ( {_DOTS} ) ريال</p>
    <p style="margin-top:6px;">لصالحنا / لصالحكم وذلك في نهاية يوم : <b class="num">{c["date"]}</b></p>
    <p style="margin-top:20px;">{_SIGN}</p>
  </div>
</div>"""
    return _document(body)


# ---------------------------------------------------------------------------
# 14 — المقارنة الجانبية
# ---------------------------------------------------------------------------
def build_balance_confirmation_html_compare(data: dict[str, Any]) -> str:
    c = _ctx(data)
    ink = "#0f172a"
    body = f"""
<div style="padding:36px 44px 34px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;gap:14px;align-items:center;">{_logo(c, height=62)}
      <div><b style="font-size:20px;">{c["company"]}</b><div style="font-size:11.5px;color:#64748b;">{c["meta"]}</div></div></div>
    <div style="font-size:13px;text-align:left;line-height:1.6;">رقم <b class="num">{c["number"]}</b><br>
      <span class="num">{c["date"]}</span> · {c["hijri"]}</div>
  </div>
  <div style="text-align:center;font-size:25px;font-weight:700;margin:20px 0 16px;">مصادقة على صحة الرصيد</div>
  <p><b>الإخوة / {c["customer"]} المحترمون</b></p>
  <p>{_GREET}</p>
  <p>{_REQUEST}</p>
  {_description(c)}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0;">
    <div style="border:2px solid {ink};border-radius:8px;padding:16px;text-align:center;">
      <div style="font-weight:700;">الرصيد حسب سجلاتنا</div>
      <div class="num" style="font-size:30px;font-weight:700;margin:8px 0;">{c["amount"]}</div>
      <div style="font-size:13px;">{c["direction"]} · حتى <span class="num">{c["date"]}</span></div>
      <div style="font-size:12px;color:#475569;margin-top:6px;">{c["words"]}</div>
    </div>
    <div style="border:2px dashed #94a3b8;border-radius:8px;padding:16px;text-align:center;">
      <div style="font-weight:700;">الرصيد حسب سجلاتكم</div>
      <div style="margin:20px 0;color:#94a3b8;">............................................</div>
      <div style="font-size:13px;">☐ لنا &nbsp;&nbsp; ☐ لكم &nbsp;&nbsp; ☐ مطابق</div>
    </div>
  </div>
  <p>{_THANKS}</p>
  {_signature(c, color=ink)}
  <p class="red">{_NOTE}</p>
  <div style="border-top:1px solid #9ca3af;margin-top:16px;padding-top:14px;">
    <p><b>السادة / {_reply_to(c)}</b></p>
    <p>في حالة عدم المطابقة يرجى ذكر أسباب الفرق : ......................................................................</p>
    <p style="margin-top:22px;">{_SIGN}</p>
    <p style="margin-top:12px;">ختم العميل : ........................</p>
  </div>
</div>"""
    return _document(body)


__all__ = [
    "build_balance_confirmation_html_compare",
    "build_balance_confirmation_html_framed",
    "build_balance_confirmation_html_green",
    "build_balance_confirmation_html_navy",
]
