"""«أفنان جيزان» (v29) — the replica of the user's 0352 invoice (شركة عبير النخبة →
شركة افنان جيزان للتجارة): live data binding, the bilingual header, the per-unit
VAT column, the amount in words, the QR size, the stamp and pagination."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

from app.ui.screens.saudi_invoice_print import QR_PRINT_PX
from app.ui.screens.saudi_invoice_print_v29 import amount_in_words_afnan, build_invoice_html_v29


def _line(code: str, qty: int, price: int) -> dict:
    before = Decimal(qty * price)
    return {"code": code, "name": "جلابيه نسائي راقي", "unit": "حبة", "qty": Decimal(qty),
            "price": Decimal(price), "before": before, "vat_rate": Decimal("15"),
            "vat_amount": before * Decimal("0.15"), "total": before * Decimal("1.15")}


def _data(n: int = 13, **over) -> dict:
    lines = [_line(f"01158{i:02d}", 8, 170 if i != 5 else 85) for i in range(1, n + 1)]
    sub = sum(ln["before"] for ln in lines)
    data = {
        "invoice_number": "0352", "issue_datetime": datetime.datetime(2026, 10, 17, 9, 36),
        "payment_label": "آجل",
        "seller": {"name": "شركة عبير النخبة", "name_en": "ABEER AL-NOKHBA COMPANY",
                   "address": "المدارس - حي البغدادية الغربية\nجدة - 22232 - المملكة العربية السعودية",
                   "address_en": "Al Madaris - Al Baghdadiyah Al Gharbiyah District\n"
                                 "Jeddah - 22232 - Kingdom of Saudi Arabia",
                   "vat": "314909764300003", "cr": "7054818195",
                   "logo": b"\x89PNG-logo", "logo_mime": "image/png",
                   "stamp": b"\x89PNG-stamp", "stamp_mime": "image/png"},
        "customer": {"name": "شركة افنان جيزان للتجارة",
                     "address": "جازان - حي الساحل - شارع فهد بن عبدالعزيز - المملكة العربية السعودية 82714",
                     "vat": "311371055800003", "phone": "+9660501040960"},
        "lines": lines,
        "totals": {"subtotal": sub, "discount": Decimal("0"), "discount_rate": Decimal("0"), "taxable": sub,
                   "vat": sub * Decimal("0.15"), "total": sub * Decimal("1.15")},
        "show_unit": True, "show_description": False, "show_stamp": True,
        "qr_payload": "AQZzZWxsZXI=",
    }
    data.update(over)
    return data


def test_prints_the_live_invoice_like_the_source():
    html = build_invoice_html_v29(_data())
    for needle in (
        "ABEER AL-NOKHBA COMPANY", "Al Madaris - Al Baghdadiyah Al Gharbiyah District",
        "CR No: 7054818195", "TRN: 314909764300003", ">ABEER AL-NOKHBA<",
        "شركة عبير النخبة", "جدة - 22232 - المملكة العربية السعودية",
        "رقم السجل التجاري: 7054818195", "الرقم الضريبي: 314909764300003",
        "فاتورة ضريبية – TAX INVOICE", "Bill to:", "شركة افنان جيزان للتجارة,",
        "شارع فهد بن عبدالعزيز", "رقم الجوال: +9660501040960", "Client VAT : 311371055800003",
        "Invoice No:", "رقم الفاتورة", ">0352<", "Invoice Date:", "17/10/2026 09:36 AM",
        "Invoice Type:", "Credit | آجل", "Paid By:", "طريقة الدفع", "نقدا",
        "رقم<br>No.", "الرمز<br>SKU", "الوصف<br>Description", "الكمية<br>Qty", "سعر<br>Rate",
        "المبلغ الإجمالي<br>Gross Amt.", ">VAT%<", "الضريبة<br>VAT", "الإجمالي<br>Net Amt.",
        ">0115801<", ">8.00<", ">170.00<", ">1,360.00<", ">15%<", ">VAT 25.50<", ">VAT 12.75<",
        ">1,564.00<", "Total Excl VAT (المجموع)", "Discount (خصم)", "VAT (الضريبة)",
        "Total with VAT (الإجمالي مع الضريبة)", "Outstanding Amount (المبلغ المستحق)", " ريال",
        "المبلغ بالحروف", "الختم", 'alt="logo"', 'data-company-stamp="1"', 'alt="QR"',
    ):
        assert needle in html, needle
    assert html.count("data-sheet") == 1   # the source's thirteen items fit one page
    assert ">حبة<" not in html              # the source has no unit column


def test_cash_invoice_type():
    assert "Cash | نقدي" in build_invoice_html_v29(_data(payment_label="نقدي"))


def test_qr_is_the_shared_print_size():
    tag = next(t for t in re.findall(r"<img[^>]*>", build_invoice_html_v29(_data())) if 'alt="QR"' in t)
    assert f"width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px" in tag


def test_amount_in_words_matches_the_source_wording():
    assert amount_in_words_afnan(Decimal("33091.25")) == (
        "ثلاثة وثلاثون ألف وواحد وتسعون ريال وخمسة وعشرون هللة فقط لا غير")
    assert amount_in_words_afnan(Decimal("100")) == "مائة ريال فقط لا غير"


def test_stamp_only_when_ticked_and_stored():
    assert "data-company-stamp" not in build_invoice_html_v29(_data(show_stamp=False))
    seller = {**_data()["seller"], "stamp": None}
    assert "data-company-stamp" not in build_invoice_html_v29(_data(seller=seller))


def test_optional_customer_lines_are_dropped():
    customer = {"name": "عميل نقدي", "address": "", "vat": "", "phone": ""}
    html = build_invoice_html_v29(_data(customer=customer))
    assert "رقم الجوال" not in html and "Client VAT" not in html


def test_long_invoice_paginates_with_totals_on_the_last_page():
    html = build_invoice_html_v29(_data(40))
    sheets = html.split("<div data-sheet")[1:]
    assert len(sheets) > 1
    assert html.count("TAX INVOICE") == len(sheets)          # header repeats
    assert all("Outstanding Amount" not in s for s in sheets[:-1])
    assert "Outstanding Amount" in sheets[-1] and "المبلغ بالحروف" in sheets[-1]
    assert f"1 / {len(sheets)}" in sheets[0]
    assert html.count('<td class="c-no">') == 40
