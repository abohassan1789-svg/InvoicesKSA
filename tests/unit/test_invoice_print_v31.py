"""«ثمار اليرموك» (v31) — the replica of the user's «شركة ثمار اليرموك» tax invoice:
live data binding, the paid / due rows, the QR size, the stamp and pagination."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

from app.ui.screens.saudi_invoice_print import QR_PRINT_PX
from app.ui.screens.saudi_invoice_print_v31 import address_lines, build_invoice_html_v31


def _line(code: str, name: str, qty: int, price: str) -> dict:
    before = Decimal(qty) * Decimal(price)
    vat = (before * Decimal("0.15")).quantize(Decimal("0.01"))
    return {"code": code, "name": name, "unit": "حبة", "qty": Decimal(qty), "price": Decimal(price),
            "before": before, "vat_rate": Decimal("15"), "vat_amount": vat, "total": before + vat}


def _data(n: int = 1, **over) -> dict:
    lines = [_line("002", "شمام صغير", 88, "22.00") for _ in range(n)]
    sub = sum(ln["before"] for ln in lines)
    vat = sum(ln["vat_amount"] for ln in lines)
    data = {
        "invoice_number": "INV/2026/00762", "issue_datetime": datetime.datetime(2026, 9, 12, 14, 2, 8),
        "payment_label": "نقدي",
        "seller": {"name": "شركة ثمار اليرموك", "address": "الطريق الدائرى الجنوبى\nالعزيزية\nالرياض RUH 14512",
                   "vat": "314705190500003", "cr": "7053944927",
                   "logo": b"\x89PNG-logo", "logo_mime": "image/png",
                   "stamp": b"\x89PNG-stamp", "stamp_mime": "image/png"},
        "customer": {"name": "شركة نورة حزام سعيد الثبيتى للتجارة", "address": "شارع يحيى بن سعيد، حى العزيزية، الرياض",
                     "vat": "312289268700003", "cr": ""},
        "lines": lines,
        "totals": {"subtotal": sub, "discount": Decimal("0"), "taxable": sub, "vat": vat, "total": sub + vat},
        "show_unit": True, "show_description": False, "show_stamp": True, "qr_payload": "AQZzZWxsZXI=",
    }
    data.update(over)
    return data


def test_prints_the_live_invoice_like_the_source():
    html = build_invoice_html_v31(_data())
    for needle in (
        "شركة ثمار اليرموك", "الطريق الدائرى الجنوبى", "Saudi Arabia", 'alt="logo"', "فاتورة ضريبية", "TAX INVOICE",
        "INV/2026/00762", "الرقم الضريبي | VAT", "314705190500003", "السجل التجاري | CR", "7053944927",
        "تاريخ فاتورة العميل | Invoice Date", "تاريخ الاستحقاق | Due date", "تاريخ التوريد | Supply Date",
        "2026-09-12", "العميل | Bill to", "شركة نورة حزام سعيد الثبيتى للتجارة", "شارع يحيى بن سعيد",
        "VAT 312289268700003", "وصف السلعة او الخدمة", "Description", "Quantity", "Unit Price", "Taxes",
        "VAT Amount", "Total Excl. VAT", "Total Incl. VAT", "[002] <bdi>شمام صغير</bdi>", ">88.00<", "15%",
        "1,936.00", "290.40", "2,226.40", "Invoice Taxable Amount | المبلغ الخاضع للضريبة",
        "VAT Total Amount | إجمالي ضريبة القيمة المضافة", "Invoice Gross Total (Inclusive of VAT)",
        "Paid on 2026-09-12", "Amount Due", "Payment Communication", "في هذا الحساب", "on this account: <b>SA2080000510608010699851</b>", "مصرف الراجحى", 'alt="QR"', 'data-company-stamp="1"',
        "14:02:08 2026-09-12", 'alt="SAR"',
    ):
        assert needle in html, needle
    assert html.count("data-sheet") == 1
    assert "السجل التجاري | <bdi" not in html          # the buyer has no CR → no CR line


def test_credit_invoice_has_no_paid_row_and_owes_the_total():
    html = build_invoice_html_v31(_data(payment_label="آجل"))
    assert "Paid on" not in html
    due = html.split('class="due"')[1].split("</tr>")[0]
    assert "2,226.40" in due


def test_buyer_cr_gets_its_own_line_and_discount_its_own_row():
    customer = {**_data()["customer"], "cr": "4030000000"}
    totals = {**_data()["totals"], "discount": Decimal("10.00")}
    html = build_invoice_html_v31(_data(customer=customer, totals=totals))
    assert "CR 4030000000" in html and "Discount | الخصم" in html


def test_qr_is_the_shared_print_size():
    tag = next(t for t in re.findall(r"<img[^>]*>", build_invoice_html_v31(_data())) if 'alt="QR"' in t)
    assert f"width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px" in tag


def test_stamp_only_when_ticked_and_stored():
    assert "data-company-stamp" not in build_invoice_html_v31(_data(show_stamp=False))
    seller = {**_data()["seller"], "stamp": None}
    assert "data-company-stamp" not in build_invoice_html_v31(_data(seller=seller))


def test_long_invoice_paginates_with_the_totals_on_the_last_page():
    html = build_invoice_html_v31(_data(40))
    sheets = html.split("<div data-sheet")[1:]
    assert len(sheets) > 1
    assert html.count("TAX INVOICE") == len(sheets)          # header repeats
    assert all("Amount Due" not in s and 'alt="QR"' not in s for s in sheets[:-1])
    assert "Amount Due" in sheets[-1] and 'alt="QR"' in sheets[-1]
    assert f"· 1 / {len(sheets)}" in sheets[0]
    assert html.count('<td class="c-desc">') == 40


def test_address_lines_split_and_fold():
    assert address_lines("الرياض، حي النخيل، شارع العليا", 4) == ["الرياض", "حي النخيل", "شارع العليا"]
    assert address_lines("أ\nب\nج\nد\nهـ", 3) == ["أ", "ب", "ج، د، هـ"]
    assert address_lines("جدة - المملكة العربية السعودية", 4) == ["جدة"]
    assert address_lines("", 4) == []
