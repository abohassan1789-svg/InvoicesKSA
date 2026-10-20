"""Printable balance-confirmation letter (خطاب مصادقة على صحة الرصيد).

One A4 page laid out after the user's sample letter (2026-10-20): the title with
«حتى تاريخ» in both calendars, the letter to the customer stating the balance
(«عليكم» when the customer owes, «لكم» when we owe them) in figures and words,
the 15-day note, then the tear-off reply the customer signs and returns.

``data`` keys: ``number``, ``date`` (a ``date`` or «YYYY-MM-DD»), ``customer``,
``balance``, ``description`` and ``seller`` (the company mapping used by every
print template — name / logo / stamp — or ``None`` for «كل الشركات», which
prints without a letterhead).
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.ui.screens.customer_statement_print import _HIJRI_MONTHS, _HIJRI_SCRIPT, _hijri
from app.ui.screens.saudi_invoice_print import (
    amount_in_words_ar,
    company_logo_data_uri,
    company_stamp_data_uri,
)
from app.ui.screens.saudi_invoice_print_v28 import _FONTS, _font_face_css
from app.ui.screens.saudi_receipt_voucher_print import (
    SaudiReceiptVoucherPreviewDialog,
    _page_layout,
)

_INK = "#1f2933"
_BLUE = "#1d4ed8"      # the «حتى تاريخ» dates and the amount, as on the sample
_TEAL = "#0f766e"      # the Hijri date
_RED = "#9f1239"       # the 15-day note
_RULE = "#9ca3af"      # the tear-off separators


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _iso(value: Any) -> str:
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value or "")[:10]


def _slash(value: Any) -> str:
    """«2026-10-20» → «2026/10/20», the sample's date style."""
    return _iso(value).replace("-", "/")


def balance_direction(balance: Any) -> str:
    """«عليكم» when the customer owes (balance ≥ 0), «لكم» when we owe them."""
    return "لكم" if _decimal(balance) < 0 else "عليكم"


def build_balance_confirmation_html(data: dict[str, Any]) -> str:
    seller = data.get("seller") or {}
    balance = _decimal(data.get("balance"))
    amount = abs(balance)
    date_iso = _iso(data.get("date"))
    date_text = _esc(_slash(date_iso))
    customer = _esc(data.get("customer"))
    company = _esc(seller.get("name"))
    number = _esc(data.get("number"))
    words = _esc(amount_in_words_ar(amount))
    direction = balance_direction(balance)
    description = (data.get("description") or "").strip()

    logo = company_logo_data_uri(seller)
    letterhead = ""
    if company or logo:
        logo_img = (f'<img src="{logo}" alt="" style="max-height:70px;max-width:180px;'
                    'object-fit:contain;">' if logo else "")
        letterhead = (
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            f'border-bottom:2px solid {_INK};padding-bottom:8px;margin-bottom:18px;">'
            f'<div style="font-size:20px;font-weight:700;">{company}</div>{logo_img}</div>'
        )
    stamp_uri = company_stamp_data_uri(seller)
    stamp = (f'<img src="{stamp_uri}" alt="" style="max-height:80px;max-width:110px;'
             'object-fit:contain;display:block;margin-top:4px;">' if stamp_uri else "")
    note = (f'<p>البيان: {_esc(description)}</p>' if description else "")
    reply_to = company or "........................................"

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; background:#e9eaec; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  @page {{ size:A4; margin:0; }}
  .sheet {{ width:794px; min-height:1123px; box-sizing:border-box; margin:0 auto; padding:44px 56px;
           background:#fff; color:{_INK}; font-family:{_FONTS}; font-size:16px; line-height:1.9; }}
  .sheet p {{ margin:0 0 4px; }}
  .num {{ direction:ltr; unicode-bidi:isolate; display:inline-block; }}
  .head {{ display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:22px; }}
  .title {{ font-size:26px; font-weight:700; }}
  .asof {{ display:flex; gap:12px; align-items:flex-start; font-size:15px; }}
  .asof .d {{ text-align:left; line-height:1.4; }}
  .to {{ display:flex; justify-content:space-between; font-weight:700; margin:6px 0 14px; }}
  .amount {{ color:{_BLUE}; font-weight:700; }}
  .words {{ color:{_BLUE}; font-size:13px; }}
  .note {{ color:{_RED}; font-weight:700; text-align:center; margin-top:14px; }}
  hr {{ border:0; border-top:1px solid {_RULE}; margin:24px 0; }}
  .sign p {{ margin:0 0 26px; }}
  @media print {{ html, body {{ background:#fff; }} .sheet {{ margin:0; }} }}
</style>
</head>
<body>
<div class="sheet">
  {letterhead}
  <div class="head">
    <div class="title">مصادقة على صحة الرصيد</div>
    <div class="asof"><span>حتى تاريخ:</span>
      <div class="d"><span class="num" style="color:{_BLUE};">{date_text}</span><br>
      <span style="color:{_TEAL};">{_hijri(date_iso)}</span></div></div>
  </div>
  <p style="font-size:13px;color:#4b5563;">رقم الحركة: <span class="num">{number}</span></p>
  <div class="to"><span>الإخوة / {customer}</span><span>المحترمون</span></div>
  <p style="text-align:center;font-weight:700;">السلام عليكم ورحمة الله وبركاته .. وبعد</p>
  <p style="font-weight:700;">نحيط سعادتكم علماً أن رصيد حسابكم في سجلاتنا بتاريخ : <span class="num">{date_text}</span></p>
  <p style="font-weight:700;">هو مبلغ : ( <span class="amount num">{amount:,.2f}</span> )
     <span class="words">{direction} {words}</span></p>
  {note}
  <p>ونظراً لأن إجراءات المراجعة لحساباتنا تستدعي تأييدكم لهذا الرصيد إذا كان مطابقاً لسجلاتكم أو إيضاح
     الفرق بالتفصيل في حالة عدم مطابقته في التاريخ المشار إليه، ومن ثم التوقيع على الجزء التالي من هذا
     الخطاب وإعادته إلينا ...</p>
  <p style="text-align:center;">وتفضلوا بقبول فائق الاحترام ،،،</p>
  <div style="margin:18px 0 0 60px;text-align:left;"><div style="display:inline-block;text-align:center;">
    <b>المدير المالي</b>{stamp}</div></div>
  <p class="note">هذا الخطاب معتمد من قبلنا ما لم يتم الرد عليه خلال 15 يوم من تاريخ الاستلام ولا يقبل المراجعة بعد..</p>
  <hr>
  <p style="font-weight:700;">السادة / {reply_to}</p>
  <p style="font-weight:700;">نفيدكم أن رصيد حسابنا كما تظهره سجلاتنا يساوي مبلغ ( ........................ ) ريال</p>
  <hr>
  <p style="font-weight:700;margin-bottom:22px;">لصالحنا / لصالحكم وذلك في نهاية يوم : <span class="num">{date_text}</span></p>
  <div class="sign"><p>الاسم : ....................................</p>
  <p>الوظيفة : ....................................</p>
  <p>التوقيع : ....................................</p></div>
</div>
{_HIJRI_SCRIPT % ("[" + ",".join(f'"{m}"' for m in _HIJRI_MONTHS) + "]")}
</body>
</html>"""


# The picker shown by «طباعة مصادقة»: the original letter first, then the four
# layouts picked from the 2026-10-20 gallery (its numbers 1, 2, 13 and 14).
BALANCE_CONFIRMATION_TEMPLATE_OPTIONS: tuple[str, ...] = (
    "النموذج الأساسي",
    "الترويسة الكحلية",
    "الإطار المزدوج الرسمي",
    "الأخضر المؤسسي",
    "المقارنة الجانبية",
)


def balance_confirmation_builders() -> dict[int, Callable[[dict[str, Any]], str]]:
    """1-based picker choice → HTML builder, in the order of the options above."""
    from app.ui.screens.balance_confirmation_print_templates import (
        build_balance_confirmation_html_compare,
        build_balance_confirmation_html_framed,
        build_balance_confirmation_html_green,
        build_balance_confirmation_html_navy,
    )

    return {
        1: build_balance_confirmation_html,
        2: build_balance_confirmation_html_navy,
        3: build_balance_confirmation_html_framed,
        4: build_balance_confirmation_html_green,
        5: build_balance_confirmation_html_compare,
    }


def choose_balance_confirmation_builder(
    parent: QWidget | None,
) -> Callable[[dict[str, Any]], str] | None:
    """Ask which letter layout to print; its builder, or ``None`` if cancelled."""
    from app.ui.screens.saudi_invoice_print import choose_invoice_template

    choice = choose_invoice_template(
        parent, "طباعة مصادقة على الرصيد", BALANCE_CONFIRMATION_TEMPLATE_OPTIONS,
        orientation="vertical",
    )
    if choice is None:
        return None
    return balance_confirmation_builders().get(choice, build_balance_confirmation_html)


def _default_pdf_name(data: dict[str, Any]) -> str:
    number = str(data.get("number") or "").strip() or "confirmation"
    safe = "".join(ch for ch in number if ch.isalnum() or ch in ("-", "_")) or "confirmation"
    return f"مصادقة_رصيد_{safe}.pdf"


class BalanceConfirmationPreviewDialog(SaudiReceiptVoucherPreviewDialog):
    """The voucher preview window (PDF / print / close) showing the letter."""

    def __init__(
        self,
        data: dict[str, Any],
        parent: QWidget | None = None,
        html_builder: Callable[[dict[str, Any]], str] = build_balance_confirmation_html,
    ) -> None:
        super().__init__(data, parent=parent, html_builder=html_builder)
        self.setWindowTitle("معاينة مصادقة على الرصيد")

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ المصادقة PDF", _default_pdf_name(self._data), "PDF (*.pdf)"
        )
        if not path:
            return
        self.export_button.setEnabled(False)

        def _finished(file_path: str, success: bool) -> None:
            self.export_button.setEnabled(True)
            try:
                self.view.page().pdfPrintingFinished.disconnect(_finished)
            except (RuntimeError, TypeError):
                pass
            if success:
                QMessageBox.information(self, "تم", f"تم تصدير المصادقة إلى:\n{file_path}")
            else:
                QMessageBox.warning(self, "تعذّر التصدير", "حدث خطأ أثناء إنشاء ملف PDF.")

        self.view.page().pdfPrintingFinished.connect(_finished)
        self.view.page().printToPdf(path, _page_layout())


__all__ = [
    "BALANCE_CONFIRMATION_TEMPLATE_OPTIONS",
    "BalanceConfirmationPreviewDialog",
    "balance_confirmation_builders",
    "choose_balance_confirmation_builder",
    "balance_direction",
    "build_balance_confirmation_html",
]
