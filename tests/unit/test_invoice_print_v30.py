"""«بنشر» (v30) — the replica of the user's «بنشر المشاري» price quotation, printed
as a tax invoice: live data binding, the national-address rows read from the
free-text address, the QR size, the stamp and pagination."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

from app.ui.screens.saudi_invoice_print import QR_PRINT_PX
from app.ui.screens.saudi_invoice_print_v30 import build_invoice_html_v30, national_address


def _line(code: str, name: str, qty: int, price: str) -> dict:
    before = Decimal(qty) * Decimal(price)
    vat = (before * Decimal("0.15")).quantize(Decimal("0.01"))
    return {"code": code, "name": name, "unit": "حبة", "qty": Decimal(qty), "price": Decimal(price),
            "before": before, "vat_rate": Decimal("15"), "vat_amount": vat, "total": before + vat}


def _data(n: int = 16, **over) -> dict:
    lines = [_line(f"{23210 + i}", "زيت شل هيلكس 20w50", 48, "12.15") for i in range(n)]
    sub = sum(ln["before"] for ln in lines)
    vat = sum(ln["vat_amount"] for ln in lines)
    data = {
        "invoice_number": "4000060", "issue_datetime": datetime.datetime(2026, 7, 7, 10, 0),
        "payment_label": "شبكة",
        "seller": {"name": "بنشر المشاري لخدمات السيارات",
                   "name_en": "Publishing Al -Mashari For Auto Services",
                   "address": "علي بن ابي طالب - حي الخالدية - الوجه 48721 - مبنى 6576 - رقم إضافي 4375",
                   "address_en": "Ali Bin Abi Talib St, Al Khalidiyah, Al Wajh",
                   "vat": "301158779400003", "cr": "3550123456",
                   "logo": b"\x89PNG-logo", "logo_mime": "image/png",
                   "stamp": b"\x89PNG-stamp", "stamp_mime": "image/png"},
        "customer": {"name": "شركة النقيب للإنارة الحديثة",
                     "address": "2779 بامحرز، البلد، جدة 22233، 6234، المملكة العربية السعودية",
                     "vat": "311103749200003", "phone": "0501234567"},
        "lines": lines,
        "totals": {"subtotal": sub, "discount": Decimal("0"), "discount_rate": Decimal("0"),
                   "taxable": sub, "vat": vat, "total": sub + vat},
        "show_unit": True, "show_description": False, "show_stamp": True,
        "qr_payload": "AQZzZWxsZXI=", "printed_by": "مدير النظام",
        "printed_at": "2026/10/11 20:38:19",
    }
    data.update(over)
    return data


def test_prints_the_live_invoice_like_the_source():
    html = build_invoice_html_v30(_data(12))
    for needle in (
        "Publishing Al -Mashari For Auto Services", "Ali Bin Abi Talib St, Al Khalidiyah, Al Wajh",
        "CR No : 3550123456", "VAT No : 301158779400003", "بنشر المشاري لخدمات السيارات",
        "السجل التجاري : <bdi>3550123456</bdi>", "الرقم الضريبي : <bdi>301158779400003</bdi>",
        'alt="logo"', '<span dir="ltr"><span dir="rtl">فاتورة ضريبية</span> - Tax Invoice</span>',
        "Branch", "الفرع", "Note", "البيان", "رصيد العميل", ">2026/07/07<", "رقم الفاتورة",
        ">4000060<", "طريقة الدفع", ">شبكة<",
        "المشتري", "البائع", "اسم العميل", "<bdi>شركة النقيب للإنارة الحديثة</bdi>",
        "<bdi>311103749200003</bdi>", ">SA<", "<bdi>جدة</bdi>", "<bdi>بامحرز</bdi>", "<bdi>البلد</bdi>",
        "<bdi>22233</bdi>", "<bdi>6234</bdi>", "<bdi>2779</bdi>", "<bdi>0501234567</bdi>",
        "<bdi>المملكة العربية السعودية</bdi>", "<bdi>الوجه</bdi>", "<bdi>علي بن ابي طالب</bdi>",
        "<bdi>الخالدية</bdi>", "<bdi>48721</bdi>", "<bdi>4375</bdi>", "<bdi>6576</bdi>", "رقم التواصل",
        "م.س", "S.N", "Product Code", "Product Name", "Location", "QTY", "Price", "Taxable<br>Amount",
        "Discount", "Total With<br>Tax", ">23210<", ">48<", ">12.15<", ">583.20<", ">%15<", ">87.48<",
        ">670.68<", ">576<", "Total Taxable Amount", "الاجمالي شامل الضريبة", 'alt="QR"',
        'data-company-stamp="1"', "تاريخ الطباعة", "2026/10/11 20:38:19", "طباعة بواسطة", "مدير النظام",
    ):
        assert needle in html, needle
    assert html.count("data-sheet") == 1   # twelve rows + the QR band fill one page
    assert ">حبة<" not in html              # the source has no unit column


def test_national_address_reads_labels_numbers_and_order():
    assert national_address("المدارس - حي البغدادية الغربية\nجدة - 22232 - المملكة العربية السعودية") == {
        "country": "المملكة العربية السعودية", "city": "جدة", "street": "المدارس",
        "district": "البغدادية الغربية", "postal": "22232", "additional": "", "building": ""}
    got = national_address("الرياض، شارع العليا، الرمز البريدي: 12211، رقم المبنى 7788")
    assert (got["city"], got["street"], got["postal"], got["building"], got["district"]) == (
        "الرياض", "العليا", "12211", "7788", "")
    assert national_address("")["city"] == ""


def test_qr_is_the_shared_print_size():
    tag = next(t for t in re.findall(r"<img[^>]*>", build_invoice_html_v30(_data())) if 'alt="QR"' in t)
    assert f"width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px" in tag


def test_stamp_only_when_ticked_and_stored():
    assert "data-company-stamp" not in build_invoice_html_v30(_data(show_stamp=False))
    seller = {**_data()["seller"], "stamp": None}
    assert "data-company-stamp" not in build_invoice_html_v30(_data(seller=seller))


def test_missing_cr_drops_its_header_lines():
    seller = {**_data()["seller"], "cr": ""}
    html = build_invoice_html_v30(_data(seller=seller))
    assert "CR No" not in html and "السجل التجاري" not in html


def test_long_invoice_paginates_with_totals_on_the_last_page():
    html = build_invoice_html_v30(_data(40))
    sheets = html.split("<div data-sheet")[1:]
    assert len(sheets) > 1
    assert html.count('<span dir="ltr"><span dir="rtl">فاتورة ضريبية</span> - Tax Invoice</span>') == len(sheets)     # header repeats
    assert all("Total Taxable Amount" not in s and 'alt="QR"' not in s for s in sheets[:-1])
    assert "Total Taxable Amount" in sheets[-1] and 'alt="QR"' in sheets[-1]
    assert f"{len(sheets)}&nbsp;)" in sheets[0]
    assert html.count('<td class="c-no">') == 40
