"""«فاتورة مبسطة» — the sales invoice printed as an 80 mm thermal cashier receipt.

The «فاتورة مبسطة» toolbar button on the sales-invoice screen first asks which
of three receipt layouts to use, then opens a preview with طباعة / تصدير PDF.
The three layouts are the ones the user picked (2026-09-29) from ten mockups:

* النموذج الأول  — rounded decorative frame (mockup #10);
* النموذج الثاني — logo + dashed sections, each item on two lines (mockup #2);
* النموذج الثالث — compact / paper-saving, QR beside the totals (mockup #3).

Each builder consumes the very same ``data`` dict as every other invoice
template (``SaudiSalesInvoicePage._collect_preview_data``), so a draft prints
without saving. The QR is the Phase-1 code (tags 1–5) re-derived from the
invoice facts, like the «مرحلة أولى» templates — or, when the user picks
المرحلة الثانية first, the screen's signed Phase-2 QR. Black-on-white only — thermal
printers have no colour. The paper is 80 mm wide and the page is exactly as tall
as the receipt (measured after layout), so there is no blank tail or 2nd page.
"""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.common.saudi_invoice_style import si_icon, style_button
from app.ui.screens.cashier_receipt_print import _px_to_mm, _thermal_layout
from app.ui.screens.saudi_invoice_print import company_logo_data_uri
from app.ui.screens.saudi_invoice_print_phase1 import _phase1_qr_uri
from app.ui.screens.saudi_invoice_print_v3 import _unit_price

PAPER_MM = 80

# Asked first: which phase's QR the receipt carries. Both phases print the very
# same three layouts; المرحلة الثانية sets ``use_phase2_qr`` so the QR is the
# screen's full signed payload (tags 1–9) instead of the Phase-1 tags 1–5 code.
SIMPLIFIED_PHASE_OPTIONS: tuple[str, ...] = ("المرحلة الأولى", "المرحلة الثانية")

SIMPLIFIED_TEMPLATE_OPTIONS: tuple[str, ...] = (
    "النموذج الأول",
    "النموذج الثاني",
    "النموذج الثالث",
)


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------
def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def _m(value: Any) -> str:
    return f"{_d(value):,.2f}"


def _q(value: Any) -> str:
    text = format(_d(value).normalize(), "f")
    return text if text not in ("", "-0") else "0"


def _e(value: Any) -> str:
    """Escaped one-line text (company names are stored with line breaks)."""
    return escape(" ".join(str(value or "").split()))


class _Ctx:
    """Everything a layout needs, pre-formatted from the shared ``data`` dict."""

    def __init__(self, data: dict[str, Any]) -> None:
        seller = data.get("seller") or {}
        customer = data.get("customer") or {}
        totals = data.get("totals") or {}
        issued = data.get("issue_datetime")
        if not isinstance(issued, datetime.datetime):
            issued = datetime.datetime.now()
        self.number = _e(data.get("invoice_number"))
        self.date = issued.strftime("%d/%m/%Y")
        self.time = issued.strftime("%H:%M")
        self.payment = _e(data.get("payment_label"))
        self.seller = _e(seller.get("name"))
        self.seller_vat = _e(seller.get("vat"))
        self.seller_cr = _e(seller.get("cr"))
        self.seller_addr = _e(seller.get("address"))
        self.customer = _e(customer.get("name")) or "عميل نقدي"
        self.customer_vat = _e(customer.get("vat"))
        self.logo = company_logo_data_uri(seller)
        self.qr = _phase1_qr_uri(data)
        # The signed Phase-2 payload is ~4× denser: print it larger so each module
        # still spans several thermal dots and the code scans.
        self.phase2 = bool(data.get("use_phase2_qr") and data.get("qr_payload"))
        self.lines = [ln for ln in (data.get("lines") or []) if ln]
        self.subtotal = _m(totals.get("subtotal"))
        self.discount = _m(totals.get("discount"))
        self.has_discount = _d(totals.get("discount")) > 0
        self.vat = _m(totals.get("vat"))
        self.total = _m(totals.get("total"))

    def logo_html(self, height: str) -> str:
        if not self.logo:
            return ""
        return (f'<img src="{self.logo}" alt="" style="display:block; margin:0 auto 1.5mm; '
                f'max-height:{height}; max-width:30mm;">')

    def qr_size(self, size: str) -> str:
        return "38mm" if self.phase2 else size

    def qr_html(self, size: str) -> str:
        size = self.qr_size(size)
        return (f'<img src="{self.qr}" alt="QR" style="display:block; margin:0 auto; '
                f'width:{size}; height:{size};">')


_BASE_CSS = f"""
@page {{ size: {PAPER_MM}mm auto; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ background: #fff; font-family: Tahoma, Arial, "Segoe UI", sans-serif; color: #000;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.r {{ width: {PAPER_MM}mm; padding: 4mm 3.5mm 5mm; background: #fff; }}
.c {{ text-align: center; }}
.ltr {{ direction: ltr; unicode-bidi: embed; }}
table {{ width: 100%; border-collapse: collapse; }}
@media screen {{
  body {{ background: #e9eaec; padding: 12px 0; }}
  .r {{ margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,.18); }}
}}
"""


def _document(css: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_BASE_CSS}{css}</style></head>
<body><div class="r" dir="rtl">{body}</div></body></html>"""


def _items_table(c: _Ctx, header_css: str = "") -> str:
    rows = "".join(
        f'<tr><td class="n">{_e(ln.get("name"))}</td><td>{_q(ln.get("qty"))}</td>'
        f'<td>{_unit_price(ln.get("price"))}</td><td>{_m(ln.get("before"))}</td></tr>'
        for ln in c.lines
    )
    return (f'<table class="items"><tr{header_css}><th style="text-align:right">الصنف</th>'
            f"<th>الكمية</th><th>السعر</th><th>المبلغ</th></tr>{rows}</table>")


# ---------------------------------------------------------------------------
# النموذج الأول — rounded decorative frame
# ---------------------------------------------------------------------------
def build_simplified_invoice_html_1(data: dict[str, Any]) -> str:
    c = _Ctx(data)
    css = """
.frame { border:1.5px solid #000; border-radius:4mm; padding:3mm 2.5mm; }
.nm { text-align:center; font-size:15px; font-weight:800; line-height:1.3; }
.orn { text-align:center; font-size:10px; letter-spacing:2px; margin:1mm 0; }
.ttl { text-align:center; margin:1.5mm 0 2mm; }
.ttl span { border-top:1px solid #000; border-bottom:1px solid #000; padding:.8mm 4mm; font-size:12px; font-weight:800; }
.kv { display:flex; justify-content:space-between; gap:2mm; font-size:10.5px; margin:.7mm 0; }
.kv span:first-child { white-space:nowrap; }
.kv span:first-child::after { content:" :"; }
.items th { font-size:9.5px; border-bottom:1.5px solid #000; padding:1mm .3mm; }
.items td { font-size:10px; text-align:center; padding:1.2mm .3mm; }
.items td.n { text-align:right; }
.dbl { border-top:3px double #000; margin:2mm 0; }
.g { display:flex; justify-content:space-between; align-items:center; font-size:15px; font-weight:800;
     border:1.5px solid #000; border-radius:3mm; padding:1.5mm 2.5mm; margin-top:1.5mm; }
"""
    discount = (f'<div class="kv"><span>الخصم</span><span class="ltr">- {c.discount}</span></div>'
                if c.has_discount else "")
    cust_vat = (f'<div class="kv"><span>الرقم الضريبي للعميل</span><span class="ltr">{c.customer_vat}</span></div>'
                if c.customer_vat else "")
    body = f"""
<div class="frame">
{c.logo_html("14mm")}
<div class="nm">{c.seller}</div>
<div class="orn">✦ ✦ ✦</div>
<div class="c" style="font-size:9.5px;">الرقم الضريبي <span class="ltr">{c.seller_vat}</span></div>
<div class="ttl"><span>فاتورة ضريبية مبسطة</span></div>
<div class="kv"><span>رقم الفاتورة</span><b class="ltr">{c.number}</b></div>
<div class="kv"><span>التاريخ</span><span class="ltr">{c.date} {c.time}</span></div>
<div class="kv"><span>العميل</span><span>{c.customer}</span></div>
{cust_vat}
<div class="kv"><span>الدفع</span><span>{c.payment}</span></div>
<div class="dbl"></div>
{_items_table(c)}
<div class="dbl"></div>
<div class="kv"><span>قبل الضريبة</span><span class="ltr">{c.subtotal}</span></div>
{discount}
<div class="kv"><span>الضريبة 15%</span><span class="ltr">{c.vat}</span></div>
<div class="g"><span>الإجمالي</span><span class="ltr">{c.total}</span></div>
<div style="margin-top:3mm;">{c.qr_html("32mm")}</div>
<div class="orn" style="margin-top:2mm;">شكراً لزيارتكم ✦</div>
</div>
"""
    return _document(css, body)


# ---------------------------------------------------------------------------
# النموذج الثاني — logo + dashed sections, each item on two lines
# ---------------------------------------------------------------------------
def build_simplified_invoice_html_2(data: dict[str, Any]) -> str:
    c = _Ctx(data)
    css = """
.nm { text-align:center; font-size:14px; font-weight:800; line-height:1.35; }
.meta { text-align:center; font-size:9.5px; line-height:1.5; }
.title { text-align:center; font-size:15px; font-weight:800; margin-top:2mm; }
.title small { display:block; font-size:9px; letter-spacing:1px; font-weight:400; }
.sep { border-top:1px dashed #000; margin:2.2mm 0; }
.row { display:flex; justify-content:space-between; gap:2mm; font-size:10.5px; margin:.7mm 0; }
.row span:first-child { white-space:nowrap; }
.it { padding:1.2mm 0; border-bottom:1px dotted #888; }
.it .a { font-size:11px; font-weight:700; }
.it .b { display:flex; justify-content:space-between; font-size:10px; margin-top:.5mm; }
.row.g { font-size:15px; font-weight:800; border-top:1.5px solid #000; padding-top:1.5mm; margin-top:1.5mm; }
.thanks { text-align:center; font-size:10.5px; font-weight:700; margin-top:2mm; }
"""
    items = "".join(
        f'<div class="it"><div class="a">{_e(ln.get("name"))}</div><div class="b">'
        f'<span class="ltr">{_q(ln.get("qty"))} × {_unit_price(ln.get("price"))}</span>'
        f'<b class="ltr">{_m(ln.get("before"))}</b></div></div>'
        for ln in c.lines
    )
    cr = f' — س.ت: <span class="ltr">{c.seller_cr}</span>' if c.seller_cr else ""
    addr = f"{c.seller_addr}<br>" if c.seller_addr else ""
    discount = (f'<div class="row"><span>الخصم</span><span class="ltr">- {c.discount}</span></div>'
                if c.has_discount else "")
    cust_vat = (f'<div class="row"><span>الرقم الضريبي للعميل</span><span class="ltr">{c.customer_vat}</span></div>'
                if c.customer_vat else "")
    body = f"""
{c.logo_html("16mm")}
<div class="nm">{c.seller}</div>
<div class="meta">{addr}الرقم الضريبي: <span class="ltr">{c.seller_vat}</span>{cr}</div>
<div class="title">فاتورة ضريبية مبسطة<small>SIMPLIFIED TAX INVOICE</small></div>
<div class="sep"></div>
<div class="row"><span>رقم الفاتورة</span><b class="ltr">{c.number}</b></div>
<div class="row"><span>التاريخ</span><span class="ltr">{c.date} &nbsp;{c.time}</span></div>
<div class="row"><span>العميل</span><span>{c.customer}</span></div>
{cust_vat}
<div class="row"><span>طريقة الدفع</span><span>{c.payment}</span></div>
<div class="sep"></div>
{items}
<div class="sep"></div>
<div class="row"><span>الإجمالي قبل الضريبة</span><span class="ltr">{c.subtotal}</span></div>
{discount}
<div class="row"><span>ضريبة القيمة المضافة 15%</span><span class="ltr">{c.vat}</span></div>
<div class="row g"><span>الإجمالي</span><span class="ltr">{c.total} ر.س</span></div>
<div class="sep"></div>
{c.qr_html("34mm")}
<div class="thanks">شكراً لتعاملكم معنا</div>
"""
    return _document(css, body)


# ---------------------------------------------------------------------------
# النموذج الثالث — compact / paper-saving, QR beside the totals
# ---------------------------------------------------------------------------
def build_simplified_invoice_html_3(data: dict[str, Any]) -> str:
    c = _Ctx(data)
    css = """
.r { padding: 2.5mm 3mm 3mm; }
body { font-size:9.5px; line-height:1.35; }
.nm { text-align:center; font-size:12.5px; font-weight:800; }
.s { text-align:center; font-size:8.5px; }
.ln { border-top:1px solid #000; margin:1.3mm 0; }
.kv { display:flex; justify-content:space-between; gap:2mm; }
.items td, .items th { padding:.6mm .3mm; font-size:9px; text-align:center; }
.items th { border-bottom:1px solid #000; }
.items td.n { text-align:right; }
.g { font-size:12.5px; font-weight:800; }
.foot { display:flex; align-items:center; gap:2mm; }
"""
    addr = f" | {c.seller_addr}" if c.seller_addr else ""
    discount = (f'<div class="kv"><span>خصم</span><span class="ltr">-{c.discount}</span></div>'
                if c.has_discount else "")
    cust_vat = (f'<div class="kv"><span>الرقم الضريبي للعميل</span><span class="ltr">{c.customer_vat}</span></div>'
                if c.customer_vat else "")
    body = f"""
<div class="nm">{c.seller}</div>
<div class="s">ض: <span class="ltr">{c.seller_vat}</span>{addr}</div>
<div class="s" style="font-weight:700; font-size:10px; margin-top:.5mm;">فاتورة ضريبية مبسطة</div>
<div class="ln"></div>
<div class="kv"><span>فاتورة: <b class="ltr">{c.number}</b></span><span class="ltr">{c.date} {c.time}</span></div>
<div class="kv"><span>العميل: {c.customer}</span><span>{c.payment}</span></div>
{cust_vat}
<div class="ln"></div>
{_items_table(c)}
<div class="ln"></div>
<div class="foot">
  <img src="{c.qr}" alt="QR" style="width:{c.qr_size("24mm")}; height:{c.qr_size("24mm")};">
  <div style="flex:1;">
    <div class="kv"><span>المجموع</span><span class="ltr">{c.subtotal}</span></div>
    {discount}
    <div class="kv"><span>ضريبة 15%</span><span class="ltr">{c.vat}</span></div>
    <div class="kv g"><span>الإجمالي</span><span class="ltr">{c.total}</span></div>
  </div>
</div>
"""
    return _document(css, body)


_BUILDERS: dict[int, Callable[[dict[str, Any]], str]] = {
    1: build_simplified_invoice_html_1,
    2: build_simplified_invoice_html_2,
    3: build_simplified_invoice_html_3,
}


def simplified_builder_for(choice: int) -> Callable[[dict[str, Any]], str] | None:
    """The layout for a 1-based chooser index, or ``None`` for an unknown one."""
    return _BUILDERS.get(choice)


# ---------------------------------------------------------------------------
# Preview dialog: same HTML for the screen, the PDF and the thermal print
# ---------------------------------------------------------------------------
class SimplifiedInvoicePreviewDialog(QDialog):
    """Preview a «فاتورة مبسطة» with طباعة / تصدير PDF / إغلاق."""

    def __init__(
        self,
        data: dict[str, Any],
        html_builder: Callable[[dict[str, Any]], str],
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        from PySide6.QtWebEngineWidgets import QWebEngineView

        super().__init__(parent)
        self.data = data
        self._printer = None
        self.setWindowTitle(f"فاتورة مبسطة — {title}")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(460, 900)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.print_button = QPushButton("طباعة")
        self.print_button.setFixedHeight(36)
        self.print_button.setIcon(si_icon("fa5s.print", color="#FFFFFF"))
        style_button(self.print_button, "green")
        self.print_button.clicked.connect(self._on_print)

        self.pdf_button = QPushButton("تصدير PDF")
        self.pdf_button.setFixedHeight(36)
        self.pdf_button.setIcon(si_icon("fa5s.file-pdf", color="#FFFFFF"))
        style_button(self.pdf_button, "red")
        self.pdf_button.clicked.connect(self._on_export_pdf)

        close_button = QPushButton("إغلاق")
        close_button.setFixedHeight(36)
        close_button.setIcon(si_icon("fa5s.times", color="#374151"))
        style_button(close_button, "white")
        close_button.clicked.connect(self.reject)

        bar.addWidget(self.print_button)
        bar.addWidget(self.pdf_button)
        bar.addStretch(1)
        bar.addWidget(close_button)
        root.addLayout(bar)

        self.view = QWebEngineView(self)
        self.view.setStyleSheet("border:1px solid #E5E7EB; border-radius:8px;")
        self.view.setHtml(html_builder(data))
        root.addWidget(self.view, 1)

    def _measure_then(self, after: Callable[[float], None]) -> None:
        # The receipt's own height (not the grey screen backdrop around it).
        self.view.page().runJavaScript(
            "Math.ceil(document.querySelector('.r').getBoundingClientRect().height)",
            0,
            lambda px: after(_px_to_mm(float(px or 400)) + 1.0),
        )

    def _on_export_pdf(self) -> None:
        number = "".join(ch for ch in str(self.data.get("invoice_number") or "") if ch.isalnum() or ch in "-_")
        path, _ = QFileDialog.getSaveFileName(
            self, "حفظ الفاتورة المبسطة PDF", f"فاتورة_مبسطة_{number or 'جديدة'}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return

        def _do(height_mm: float) -> None:
            def _finished(file_path: str, success: bool) -> None:
                try:
                    self.view.page().pdfPrintingFinished.disconnect(_finished)
                except (RuntimeError, TypeError):
                    pass
                if success:
                    QMessageBox.information(self, "تم", f"تم تصدير الفاتورة المبسطة إلى:\n{file_path}")
                else:
                    QMessageBox.warning(self, "تعذّر التصدير", "حدث خطأ أثناء إنشاء ملف PDF.")

            self.view.page().pdfPrintingFinished.connect(_finished)
            self.view.page().printToPdf(path, _thermal_layout(PAPER_MM, height_mm))

        self._measure_then(_do)

    def _on_print(self) -> None:
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except Exception:  # noqa: BLE001 - print support may be unavailable
            QMessageBox.warning(self, "الطباعة", "خدمة الطباعة غير متاحة.")
            return

        def _do(height_mm: float) -> None:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageLayout(_thermal_layout(PAPER_MM, height_mm))
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.Accepted:
                return
            self._printer = printer  # keep alive for the async print

            def _done(success: bool) -> None:
                try:
                    self.view.printFinished.disconnect(_done)
                except (RuntimeError, TypeError):
                    pass
                if not success:
                    QMessageBox.warning(self, "تعذّر الطباعة", "لم تكتمل مهمة الطباعة.")

            self.view.printFinished.connect(_done)
            self.view.print(printer)

        self._measure_then(_do)


__all__ = [
    "SIMPLIFIED_PHASE_OPTIONS",
    "SIMPLIFIED_TEMPLATE_OPTIONS",
    "SimplifiedInvoicePreviewDialog",
    "build_simplified_invoice_html_1",
    "build_simplified_invoice_html_2",
    "build_simplified_invoice_html_3",
    "simplified_builder_for",
]
