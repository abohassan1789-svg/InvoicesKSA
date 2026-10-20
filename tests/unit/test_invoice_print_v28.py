"""«النموذج الثاني والعشرون» (v28) — the «زيادة البركة» replica: live data
binding, pagination, the stamp, and the company seed under tools/."""

from __future__ import annotations

import datetime
import importlib.util
from decimal import Decimal
from pathlib import Path

from app.ui.screens.saudi_invoice_print_v28 import build_invoice_html_v28

_ROOT = Path(__file__).resolve().parents[2]


def _line(name: str, qty: int, price: int) -> dict:
    before = Decimal(qty * price)
    return {"name": name, "unit": "حبة", "qty": Decimal(qty), "price": Decimal(price), "before": before,
            "vat_rate": Decimal("15"), "vat_amount": before * Decimal("0.15"),
            "total": before * Decimal("1.15"), "description": "وصف"}


def _data(n: int = 7, **over) -> dict:
    lines = [_line(f"صنف {i}", 10 + i, 30) for i in range(1, n + 1)]
    sub = sum(ln["before"] for ln in lines)
    data = {
        "invoice_number": "BAR-2026-001", "issue_datetime": datetime.datetime(2026, 9, 14, 13, 0),
        "payment_label": "نقدي",
        "seller": {"name": "شركة زيادة البركة التجارية", "address": "جدة - العزيزية\nالبلدية - 23334",
                   "vat": "311369317100003", "cr": "7009631370",
                   "stamp": b"\x89PNG-stamp", "stamp_mime": "image/png"},
        "customer": {"name": "مؤسسة الراقية للسبح والهدايا التجارية", "address": "مكة المكرمة - الشرائع - 21955",
                     "vat": "302069047900003", "cr": "7017919205"},
        "lines": lines,
        "totals": {"subtotal": sub, "discount": Decimal("0"), "discount_rate": Decimal("0"), "taxable": sub,
                   "vat": sub * Decimal("0.15"), "total": sub * Decimal("1.15")},
        "show_unit": True, "show_description": False, "show_stamp": True,
        "qr_payload": "AQZzZWxsZXI=",
    }
    data.update(over)
    return data


def test_prints_the_live_invoice_like_the_source():
    html = build_invoice_html_v28(_data())
    for needle in ("شركة زيادة البركة التجارية", "جدة - العزيزية - البلدية - 23334",
                   "الرقم الضريبي: ", "311369317100003", "السجل التجاري: ", "7009631370",
                   "<b>المشتري:</b> مؤسسة الراقية للسبح والهدايا التجارية", "302069047900003",
                   "السجل التجاري / الموحد: ", "7017919205", "BAR-2026-001",
                   "تاريخ الإصدار: ", "14/09/2026", "13:00", "بتوقيت السعودية",
                   "فاتورة ضريبية", "TAX INVOICE", 'alt="QR"', "البند", "سعر الوحدة", "قبل الضريبة",
                   "صنف 7", "حبة", "الإجمالي قبل الضريبة", "ضريبة القيمة المضافة",
                   "الإجمالي شامل الضريبة", " SAR", "العملة: الريال السعودي | سعر الوحدة قبل الضريبة",
                   "1 / 1", 'data-company-stamp="1"'):
        assert needle in html, needle
    assert html.count("data-sheet") == 1   # the source's seven items fit one page
    assert "الخصم" not in html


def test_stamp_only_when_ticked_and_stored():
    assert 'data-company-stamp' not in build_invoice_html_v28(_data(show_stamp=False))
    seller = {**_data()["seller"], "stamp": None}
    assert 'data-company-stamp' not in build_invoice_html_v28(_data(seller=seller))


def test_options_unit_description_discount():
    html = build_invoice_html_v28(_data(show_unit=False))
    assert ">الوحدة<" not in html and "حبة" not in html
    html = build_invoice_html_v28(_data(show_description=True))
    assert "وصف الصنف" in html
    totals = {**_data()["totals"], "discount": Decimal("50")}
    assert "الخصم" in build_invoice_html_v28(_data(totals=totals))


def test_long_invoice_paginates_with_totals_on_the_last_page():
    html = build_invoice_html_v28(_data(30))
    sheets = html.split("<div data-sheet")[1:]
    assert len(sheets) > 1
    assert html.count("فاتورة ضريبية") == len(sheets)        # header repeats
    assert f"{len(sheets)} / 1" in sheets[0] and f"{len(sheets)} / {len(sheets)}" in sheets[-1]
    assert all("الإجمالي شامل الضريبة" not in s for s in sheets[:-1])
    assert "الإجمالي شامل الضريبة" in sheets[-1] and "صنف 30" in sheets[-1]
    for i in range(1, 31):
        assert html.count(f">صنف {i}<") == 1


def test_company_seed_sql_matches_its_generator():
    spec = importlib.util.spec_from_file_location("barakah_gen", _ROOT / "tools/barakah_company/gen_sql.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    sql = (_ROOT / "tools/barakah_company/barakah_company.sql").read_text(encoding="utf-8")
    assert sql == gen.build_sql()
    for needle in ("شركة زيادة البركة التجارية", "311369317100003", "7009631370", "WHERE NOT EXISTS",
                   "stamp IS NULL", "image/png"):
        assert needle in sql
