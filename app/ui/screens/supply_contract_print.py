"""Printable fruit & vegetable supply contract (عقد توريد خضار وفواكه).

The user's two-page contract (2026-10-20), word for word: the parties, the
preamble, then clauses أولاً … سابعاً and the signatures. Only the blanks come
from ``data``; every clause is fixed text (:func:`contract_sections`), and an
empty blank prints as dots. :func:`build_supply_contract_html` is the original
layout; ``supply_contract_print_templates`` lays the same sections out in the
five extra designs offered by :func:`choose_supply_contract_builder`.

``data`` keys are the ``supply_contracts`` column names (``contract_number``,
``contract_date``, ``first_party_name`` … ``bank_account``), plus an optional
``first_party_company`` mapping (name / ``logo`` / ``stamp``) whose stamp prints
under the first party's «الختم» unless ``show_stamp`` is false.
"""

from __future__ import annotations

import datetime
import html
from typing import Any, Callable

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.ui.screens.saudi_invoice_print import company_stamp_data_uri
from app.ui.screens.saudi_invoice_print_v28 import _FONTS, _font_face_css
from app.ui.screens.saudi_receipt_voucher_print import SaudiReceiptVoucherPreviewDialog

_GREEN = "#16a34a"     # the title, as on the user's contract
_RED = "#dc2626"       # the two rules above the title

_WEEKDAYS_AR = ("الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد")

# How many dots an empty blank prints (short numbers vs. names).
_DOTS_SHORT = "............"
_DOTS_LONG = "................................"


def _parse_date(value: Any) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value or "").strip()[:10]
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def contract_day_name(value: Any) -> str:
    """Arabic weekday of the contract date («الثلاثاء»), or "" when unset."""
    day = _parse_date(value)
    return _WEEKDAYS_AR[day.weekday()] if day else ""


def contract_date_text(value: Any) -> str:
    """«20 / 10 / 2026» — day first, as the blank «.... / .... / 2026م» reads."""
    day = _parse_date(value)
    return f"{day.day:02d} / {day.month:02d} / {day.year}" if day else ""


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    return "" if value is None else str(value).strip()


# The contract in order, one block per part: the clauses are fixed text and
# every blank goes through ``blank(value, long)``. Templates lay the blocks out.
SECTION_KEYS = (
    "title", "opening", "parties", "capacity", "preamble", "first", "second", "third",
    "fourth", "fifth", "sixth", "seventh", "closing", "signatures",
)


def contract_sections(
    data: dict[str, Any], blank: Callable[[str, bool], str], stamp_html: str = ""
) -> list[tuple[str, str]]:
    """``(key, html)`` for each part of the contract, in ``SECTION_KEYS`` order."""

    def b(key: str, long: bool = False) -> str:
        return blank(_text(data, key), long)

    day = blank(contract_day_name(data.get("contract_date")), False)
    date = blank(contract_date_text(data.get("contract_date")), False)
    return [
        ("title", """<div class="ttl">عقد توريد خضار وفواكه</div>"""),
        ("opening", f"""<p class="c">أنه في يوم {day} الموافق : {date}م تم الاتفاق بين كل من:-</p>"""),
        ("parties", f"""<p>الطرف الأول السادة / {b("first_party_name", True)} سجل تجاري رقم ( {b("first_party_cr")} ) مصدرها {b("first_party_cr_city")}</p>
<p>ويمثلها السيد / {b("first_party_rep_name", True)} الجنسية {b("first_party_rep_nationality")} سجل مدني ( {b("first_party_rep_id")} ) بصفته {b("first_party_rep_title")} وعنوانها {b("first_party_address")}</p>
<p>الطرف الثاني السادة / {b("second_party_name", True)} سجل تجاري رقم ( {b("second_party_cr")} ) مصدره {b("second_party_cr_city")} وفروعها في {b("second_party_branches")}</p>
<p>ويمثلها السيد / {b("second_party_rep_name", True)} الجنسية {b("second_party_rep_nationality")} هوية رقم ( {b("second_party_rep_id")} ) بصفته {b("second_party_rep_title")} وعنوانه {b("second_party_address")}</p>"""),
        ("capacity", """<p class="c">وهما بكامل الأهلية اللازمة لإجراء التصرفات :</p>"""),
        ("preamble", f"""<p class="h">التمهيد :</p>
<p>حيث يرغب الطرف الثاني في الحصول على الفاكهة والخضار وتوريدها إلى موقعه الواقع في {b("supply_sites", True)}. وحيث تقدم الطرف الأول إلى الطرف الثاني بعرض أسعار الفاكهة والخضار وأرفق عرض الأسعار بهذا العقد. وحيث وافق الطرف الثاني على عرض الأسعار المقدم من الطرف الأول وأقر الطرف الأول بقدرته على توريد كامل الكميات وبمواصفاتها الموضحة في عرض الأسعار.</p>
<p class="c">عليه فقد اتفق الطرفان على إبرام هذا العقد وفقاً للشروط التالية :-</p>"""),
        ("first", """<p class="h">أولاً :</p>
<p class="c">تعتبر مقدمة هذا العقد وعرض الأسعار المبينة فيه لأصناف الفاكهة والخضار جزءاً لا يتجزأ منه وبناءً من بنوده.</p>"""),
        ("second", """<p class="h">ثانياً: الشروط العامة :</p>
<p>أ- يقر الطرف الأول بأن جميع الفاكهة والخضار التي سيتم توريدها مطابقة للمواصفات وجدول الكميات.</p>
<p>ب- جدول الكميات: يلتزم الطرف الثاني بتزويد الطرف الأول بجدول الكميات المطلوبة تأمينها يومياً ويكون التسليم حسب الوقت المتفق عليه.</p>
<p>ت- تعتبر البضائع المسلمة مطابقة للمواصفات والكميات بمجرد توقيع الطرف الثاني على استلامها.</p>
<p>ث- يحق للطرف الثاني رفض أي بضاعة تصل إلى موقعه غير مطابقة للمواصفات الواردة في جدول الكميات المسلمة للطرف الثاني في نفس يوم التسليم، وفي حال عدم مطابقتها يلتزم الطرف الأول بإرجاع البضائع مع تحمله كافة مصروفات الإرجاع ويلتزم بتوريد البضاعة البديلة المطلوبة وتكون مطابقة للمواصفات والكميات.</p>
<p>ج- تعتبر نماذج تسليم البضائع الموقعة والمختومة من قبل الطرف الثاني سندات أمر لصالح الطرف الأول بقيمة البضائع المسلمة له.</p>"""),
        ("third", f"""<p class="h">ثالثاً: قيمة العقد وطريقة السداد:</p>
<p>أ- إجمالي قيمة الفاكهة والخضار حسب عرض الأسعار المرفق مع هذا العقد. يتم دفع إجمالي الفواتير من قبل الطرف الثاني للطرف الأول بعد {b("payment_days_after_first_supply")} يوم من تاريخ أول توريد.</p>
<p>ب- يقر الطرفان أن جميع الأسعار الموضحة في هذا العقد وفي عرض الأسعار المرفق هي بالريال السعودي وأنها أسعار نهائية متفق عليها وغير قابلة للتعديل طيلة فترة العقد.</p>
<p>ت- يحق للطرف الأول إضافة أي ضرائب تفرضها حكومة خادم الحرمين الشريفين مستقبلاً على الأسعار وفق ما تفرضه الدولة ويكون ملزماً على الطرف الثاني أن يتم مخاطبته بتلك الزيادة رسمياً.</p>
<p>ث- يتم السداد خلال {b("payment_days_after_statement")} أيام من تاريخ إرسال كشف الحساب نهاية كل شهر كحد أقصى.</p>"""),
        ("fourth", """<p class="h">رابعاً: مدة العقد:</p>
<p class="c">اتفق الطرفان على أن مدة هذا العقد سنة كاملة ابتداءً من تاريخ توقيع هذا العقد.</p>"""),
        ("fifth", """<p class="h">خامساً: الجزاءات:</p>
<p>أ- في حالة عدم قدرة الطرف الأول بتأمين أي صنف من الأصناف الملتزم بتأمينها، فإنه يحق للطرف الثاني الحصول على غير مؤمن من أي مصادر أخرى، ويتحمل الطرف الأول فرق الأسعار خصماً من مستحقاته.</p>
<p>ب- في حال تأخر الطرف الثاني في سداد مستحقات الطرف الأول مدة أقصاها أسبوع من تاريخ رفع المطالبة، يحق للطرف الأول إيقاف التوريد دون الرجوع للطرف الثاني عليه بأي التزامات مالية أو إدارية، ويعاود التوريد بمجرد استلام المستحقات.</p>
<p>ت- إذا استمر التأخير أكثر من خمسة عشر يوماً، يحق للطرف الأول إلغاء العقد دون الرجوع للطرف الثاني مع ثبات مطالبة الطرف الأول بمستحقاته لدى الطرف الثاني، مع حق الطرف الأول بالمطالبة بالطريقة التي يراها مناسبة.</p>
<p class="c">ث- في حال رغبة أحد الطرفين إلغاء العقد يتم إبلاغ الطرف الآخر قبل الموعد بـ 30 يوماً.</p>"""),
        ("sixth", """<p class="h">سادساً: نسخ العقد:</p>
<p class="c">حرر هذا العقد باللغة العربية مكون من نسختين بيد كل طرف نسخة للتمشي بموجبه.</p>"""),
        ("seventh", """<p>سابعاً: فض النزاع: أي خلاف ينشأ بين الطرفين يتم الفصل فيه ودياً، وإذا تعذر الأمر لا قدر الله يتم إحالة الخلاف إلى جهة الاختصاص بالمملكة العربية السعودية للفصل فيه وعلى ذلك وقع هذا العقد.</p>"""),
        ("closing", f"""<p class="c">وعليه يتم السداد عبر حساب الشركة لدى بنك {b("bank_name")} ( {b("bank_account", True)} )</p>
<p class="c">والله الموفق،،،</p>"""),
        ("signatures", f"""<table class="sigs" width="100%"><tr>
<td width="50%"><p class="h">الطرف الأول</p><p>الاسم: {b("first_party_rep_name")}</p><p>التوقيع:</p><p>الختم:</p>{stamp_html}</td>
<td width="50%"><p class="h">الطرف الثاني</p><p>الاسم: {b("second_party_rep_name")}</p><p>التوقيع:</p><p>الختم:</p></td>
</tr></table>"""),
    ]


def _contract_body(data: dict[str, Any], blank: Callable[[str, bool], str], stamp_html: str = "") -> str:
    """The whole contract as HTML; ``blank(value, long)`` renders each blank."""
    return "\n".join(part for _key, part in contract_sections(data, blank, stamp_html))


def print_blank(value: str, long: bool) -> str:
    if not value:
        return _DOTS_LONG if long else _DOTS_SHORT
    return f'<span class="v">{html.escape(value)}</span>'


def stamp_html(data: dict[str, Any]) -> str:
    """The first party's company stamp, unless «طباعة الختم» is unticked."""
    if not data.get("show_stamp", True):
        return ""
    stamp_uri = company_stamp_data_uri(data.get("first_party_company") or {})
    return (f'<img src="{stamp_uri}" alt="" style="max-height:90px;max-width:130px;'
            'object-fit:contain;">' if stamp_uri else "")


def build_supply_contract_html(data: dict[str, Any]) -> str:
    """The contract for print / PDF: A4, the text flowing over its two pages."""
    body = _contract_body(data, print_blank, stamp_html(data))
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ max-width:740px; margin:0 auto; padding:8px 4px; color:#111; font-family:{_FONTS};
           font-size:14.5px; line-height:1.75; }}
  .rules {{ display:flex; justify-content:space-between; margin-bottom:10px; }}
  .rules span {{ width:34%; border-top:1.5px solid {_RED}; }}
  .ttl {{ text-align:center; color:{_GREEN}; font-weight:700; font-size:22px; margin:4px 0 16px; }}
  p {{ margin:0 0 6px; text-align:justify; }}
  p.c {{ text-align:center; }}
  p.h {{ text-align:center; font-weight:700; margin-top:10px; }}
  .v {{ font-weight:700; }}
  .sigs {{ margin-top:18px; border-collapse:collapse; page-break-inside:avoid; break-inside:avoid; }}
  .sigs td {{ vertical-align:top; text-align:center; }}
  .sigs p {{ text-align:center; margin-bottom:10px; }}
</style>
</head>
<body>
<div class="sheet">
  <div class="rules"><span></span><span></span></div>
  {body}
</div>
</body>
</html>"""


# The picker shown by «طباعة العقد»: the user's original layout first, then the
# five picked from the 2026-10-20 gallery (its numbers 2, 4, 9, 10 and 11).
SUPPLY_CONTRACT_TEMPLATE_OPTIONS: tuple[str, ...] = (
    "النموذج الأساسي",
    "الترويسة الخضراء",
    "الكحلي والذهبي",
    "العنابي الرسمي",
    "الخضار والفواكه",
    "البطاقات",
)


def supply_contract_builders() -> dict[int, Callable[[dict[str, Any]], str]]:
    """1-based picker choice → HTML builder, in the order of the options above."""
    from app.ui.screens.supply_contract_print_templates import (
        build_supply_contract_html_cards,
        build_supply_contract_html_fresh,
        build_supply_contract_html_green,
        build_supply_contract_html_maroon,
        build_supply_contract_html_navy,
    )

    return {
        1: build_supply_contract_html,
        2: build_supply_contract_html_green,
        3: build_supply_contract_html_navy,
        4: build_supply_contract_html_maroon,
        5: build_supply_contract_html_fresh,
        6: build_supply_contract_html_cards,
    }


def choose_supply_contract_builder(
    parent: QWidget | None,
) -> Callable[[dict[str, Any]], str] | None:
    """Ask which contract layout to print; its builder, or ``None`` if cancelled."""
    from app.ui.screens.saudi_invoice_print import choose_invoice_template

    choice = choose_invoice_template(
        parent, "طباعة عقد التوريد", SUPPLY_CONTRACT_TEMPLATE_OPTIONS, orientation="vertical",
    )
    if choice is None:
        return None
    return supply_contract_builders().get(choice, build_supply_contract_html)


def _page_layout() -> QPageLayout:
    """A4 portrait with print margins: the contract flows over its pages."""
    return QPageLayout(
        QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(16, 16, 16, 16),
        QPageLayout.Millimeter,
    )


def _default_pdf_name(data: dict[str, Any]) -> str:
    number = _text(data, "contract_number") or "contract"
    safe = "".join(ch for ch in number if ch.isalnum() or ch in ("-", "_")) or "contract"
    return f"عقد_توريد_{safe}.pdf"


class SupplyContractPreviewDialog(SaudiReceiptVoucherPreviewDialog):
    """The voucher preview window (PDF / print / close) showing the contract."""

    def __init__(
        self,
        data: dict[str, Any],
        parent: QWidget | None = None,
        html_builder: Callable[[dict[str, Any]], str] = build_supply_contract_html,
    ) -> None:
        super().__init__(data, parent=parent, html_builder=html_builder)
        self.setWindowTitle("معاينة عقد التوريد")

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ العقد PDF", _default_pdf_name(self._data), "PDF (*.pdf)"
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
                QMessageBox.information(self, "تم", f"تم تصدير العقد إلى:\n{file_path}")
            else:
                QMessageBox.warning(self, "تعذّر التصدير", "حدث خطأ أثناء إنشاء ملف PDF.")

        self.view.page().pdfPrintingFinished.connect(_finished)
        self.view.page().printToPdf(path, _page_layout())

    def _on_print(self) -> None:
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except Exception:  # noqa: BLE001
            QMessageBox.warning(self, "الطباعة", "خدمة الطباعة غير متاحة.")
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageLayout(_page_layout())
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.Accepted:
            return
        self._printer = printer  # keep a reference during async print
        self.view.print(printer)


__all__ = [
    "SECTION_KEYS",
    "SUPPLY_CONTRACT_TEMPLATE_OPTIONS",
    "SupplyContractPreviewDialog",
    "build_supply_contract_html",
    "choose_supply_contract_builder",
    "contract_sections",
    "print_blank",
    "stamp_html",
    "supply_contract_builders",
    "contract_date_text",
    "contract_day_name",
]
