"""«النموذج الخامس عشر» → «النموذج العشرون» (v22…v27, chosen 2026-10-18 from the
two mock-up galleries) — they share :mod:`saudi_invoice_print_kit`, so the data
binding is pinned once here for all three."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from app.ui.screens.saudi_invoice_print_v22 import build_invoice_html_v22
from app.ui.screens.saudi_invoice_print_v23 import build_invoice_html_v23
from app.ui.screens.saudi_invoice_print_v24 import build_invoice_html_v24
from app.ui.screens.saudi_invoice_print_v25 import _city, build_invoice_html_v25
from app.ui.screens.saudi_invoice_print_v26 import build_invoice_html_v26
from app.ui.screens.saudi_invoice_print_v27 import build_invoice_html_v27

BUILDERS = [
    build_invoice_html_v22, build_invoice_html_v23, build_invoice_html_v24,
    build_invoice_html_v25, build_invoice_html_v26, build_invoice_html_v27,
]


def _data(**over):
    data = {
        "invoice_number": "125",
        "issue_datetime": datetime.datetime(2026, 10, 18, 10, 45),
        "payment_label": "آجل",
        "seller": {"name": "شركة البائع", "address": "الرياض\nحي العليا", "vat": "300000000000003", "cr": "1010000000"},
        "customer": {"name": "شركة العميل", "address": "جدة", "vat": "310000000000003", "cr": ""},
        "lines": [
            {"name": "رخام كرارا", "unit": "م²", "qty": Decimal("120"), "price": Decimal("85"),
             "before": Decimal("10200"), "vat_amount": Decimal("1530"), "vat_rate": Decimal("15"),
             "total": Decimal("11730"), "description": "مقاس 60×60"},
            {"name": "خدمة تركيب", "unit": "خدمة", "qty": Decimal("1"), "price": Decimal("2500"),
             "before": Decimal("2500"), "vat_amount": Decimal("375"), "vat_rate": Decimal("15"),
             "total": Decimal("2875"), "description": ""},
        ],
        "totals": {"subtotal": Decimal("12700"), "discount": Decimal("0"), "discount_rate": Decimal("0"),
                   "taxable": Decimal("12700"), "vat": Decimal("1905"), "total": Decimal("14605")},
        "show_unit": True, "show_description": True, "show_stamp": False,
        "qr_payload": "AQZzZWxsZXI=",
    }
    data.update(over)
    return data


@pytest.mark.parametrize("build", BUILDERS)
def test_prints_the_live_invoice(build):
    html = build(_data())
    for needle in ("شركة البائع", "شركة العميل", "300000000000003", "310000000000003", "1010000000",
                   "125", "2026-10-18", "10:45", "آجل", "رخام كرارا", "خدمة تركيب", "م²",
                   "11,730.00", "12,700.00", "1,905.00", "14,605.00",
                   "مقاس 60×60", "فاتورة ضريبية", 'alt="QR"', "حي العليا"):
        assert needle in html, needle
    # A customer with no CR prints no empty «السجل التجاري» line for them.
    assert html.count("السجل التجاري") <= html.count("1010000000")
    assert '<bdi dir="ltr"></bdi></div>' not in html


@pytest.mark.parametrize("build", BUILDERS)
def test_print_options_hide_unit_and_description(build):
    html = build(_data(show_unit=False, show_description=False))
    assert "الوحدة" not in html and "م²" not in html
    assert "مقاس 60×60" not in html


@pytest.mark.parametrize("build", BUILDERS)
def test_discount_row_only_when_there_is_a_discount(build):
    assert "الخصم" not in build(_data())
    totals = {**_data()["totals"], "discount": Decimal("635"), "discount_rate": Decimal("5")}
    html = build(_data(totals=totals))
    assert "الخصم" in html and "-635.00" in html and "5%" in html


@pytest.mark.parametrize("build", BUILDERS)
def test_totals_travel_with_the_last_item(build):
    """The last item and the closing block share one no-break tbody."""
    html = build(_data())
    summary = html.split('<tbody class="summary">', 1)[1]
    assert "خدمة تركيب" in summary and "رخام كرارا" not in summary
    assert "الإجمالي شامل الضريبة" in summary


@pytest.mark.parametrize("build", BUILDERS)
def test_missing_qr_payload_still_renders(build):
    """No payload → the shared placeholder QR (same as every other template)."""
    html = build(_data(qr_payload=None))
    assert "14,605.00" in html


@pytest.mark.parametrize("build", BUILDERS)
def test_long_text_is_escaped(build):
    html = build(_data(customer={"name": "<b>x</b>", "vat": "", "address": "", "cr": ""}))
    assert "<b>x</b>" not in html and "&lt;b&gt;x&lt;/b&gt;" in html


@pytest.mark.parametrize(
    "address, city",
    [("الرياض — حي العليا", "الرياض"), ("جدة، حي الروضة", "جدة"), ("الدمام\nشارع الملك", "الدمام"),
     ("مدينة الملك عبدالله الاقتصادية - رابغ", ""), ("", "")],
)
def test_boarding_pass_city_is_the_short_head_of_the_address(address, city):
    assert _city(address) == city


def test_boarding_pass_prints_both_cities():
    html = build_invoice_html_v25(_data(customer={"name": "ع", "vat": "", "cr": "", "address": "جدة — حي الروضة"}))
    assert '<div class="city">الرياض</div>' in html and '<div class="city">جدة</div>' in html


def test_mirror_prints_english_labels_and_payment():
    html = build_invoice_html_v26(_data(payment_label="نقدي"))
    for needle in ("TAX INVOICE", "Invoice No.", "VAT No. 300000000000003", "C.R. 1010000000",
                   "Cash", "Total incl. VAT", "Taxable Amount"):
        assert needle in html, needle


def test_timeline_stamp_slot_placeholder_without_stamp():
    assert "مكان الختم والتوقيع" in build_invoice_html_v27(_data())
