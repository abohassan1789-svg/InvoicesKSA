"""The fourteen Customer Statement print templates (كشف حساب العميل).

Added 2026-07-16 with the templates themselves. These are string/logic checks over
the built HTML, so they run headless; the printed geometry, the A4 orientations
and the pagination were verified by exporting real PDFs through the production
QWebEngine path when the templates were written.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from app.ui.screens.customer_statement_print import (
    STATEMENT_TEMPLATE_OPTIONS,
    _BUILDERS,
    build_statement_html_v1,
    build_statement_html_v2,
    build_statement_html_v3,
    build_statement_html_v4,
    build_statement_html_v5,
    build_statement_html_v6,
    build_statement_html_v7,
    build_statement_html_v8,
    build_statement_html_v9,
    build_statement_html_v10,
    build_statement_html_v11,
    build_statement_html_v12,
    build_statement_html_v13,
    build_statement_html_v14,
    rows_with_balance,
)

BUILDERS = [
    ("النموذج الأول", build_statement_html_v1),
    ("النموذج الثاني", build_statement_html_v2),
    ("النموذج الثالث", build_statement_html_v3),
]
# Picked by the user 2026-10-18 from ten mock-ups. They share every rule the
# first three follow except «four columns only»: some carry a running balance.
NEW_BUILDERS = [
    ("النموذج الرابع", build_statement_html_v4),
    ("النموذج الخامس", build_statement_html_v5),
    ("النموذج السادس", build_statement_html_v6),
    ("النموذج السابع", build_statement_html_v7),
    ("النموذج الثامن", build_statement_html_v8),
]
# The second pick, same day, from another ten mock-ups.
SECOND_BUILDERS = [
    ("النموذج التاسع", build_statement_html_v9),
    ("النموذج العاشر", build_statement_html_v10),
    ("النموذج الحادي عشر", build_statement_html_v11),
    ("النموذج الثاني عشر", build_statement_html_v12),
    ("النموذج الثالث عشر", build_statement_html_v13),
]
# The third pick, 2026-10-20: the VAT statement mock-up, without its QR.
THIRD_BUILDERS = [
    ("النموذج الرابع عشر", build_statement_html_v14),
]
ALL_BUILDERS = BUILDERS + NEW_BUILDERS + SECOND_BUILDERS + THIRD_BUILDERS
# Every template but النموذج التاسع, which carries the identity in its side
# column instead of the three-column letterhead.
LETTERHEAD_BUILDERS = [b for b in ALL_BUILDERS if b[1] is not build_statement_html_v9]


def _header_labels(html_text: str) -> list[str]:
    """The table column headers — the <th> text — in document order."""
    return [h.strip() for h in re.findall(r"<th[^>]*>([^<]*)</th>", html_text)]

# An inline style attribute containing a font-family: the stacks carry double
# quotes, which close the attribute early and silently drop everything after it.
# This is the trap that cost النموذج الرابع its whole typography — see
# tests/unit/test_invoice_print_font_regression.py.
_INLINE_FONT_FAMILY = re.compile(r'style="[^"]*font-family:')


def _row(date: str, invoice: str, debit: str, credit: str, description: str) -> dict:
    return {
        "transaction_date": date,
        "customer_name": "شركة الريادة",
        "company_name": "شركة الشرارة المضيئة",
        "sales_invoice_number": invoice,
        "debit": Decimal(debit),
        "credit": Decimal(credit),
        "description": description,
    }


ROWS = [
    _row("2026-03-04", "985", "65550.00", "0.00", "فاتورة مبيعات آجلة رقم 985"),
    _row("2026-04-12", "-", "0.00", "20000.00", "سند قبض رقم PA-014"),
    _row("2026-05-20", "991", "12650.00", "0.00", "فاتورة مبيعات نقدية رقم 991"),
]


def _data(rows=None) -> dict:
    rows = ROWS if rows is None else rows
    debit = sum((r["debit"] for r in rows), Decimal("0"))
    credit = sum((r["credit"] for r in rows), Decimal("0"))
    return {
        "title": "كشف حساب العميل",
        "company_name": "شركة الشرارة المضيئة",
        "tax_number": "311474361800003",
        "customer_label": "شركة الريادة",
        "company_label": "الكل",
        "date_from_label": "2026-01-01",
        "date_to_label": "2026-07-16",
        "rows": rows,
        "summary": {
            "total_debit_label": f"{debit:,.2f}",
            "total_credit_label": f"{credit:,.2f}",
            "difference_label": f"{debit - credit:,.2f}",
        },
        "is_empty": not rows,
        "empty_message": "لا توجد حركات للعميل خلال الفترة المحددة",
        "company": COMPANY,
    }


# The letterhead the screen passes: a `companies` row, verbatim. `logo` is raw
# bytes in the database, so it is raw bytes here too — company_logo_data_uri does
# the base64/data-URI work and must be exercised on what it will really get.
COMPANY = {
    "id": 11,
    "name_ar": "شركة الشرارة المضيئة",
    "name_en": "Bright Spark Company",
    "commercial_registration": "4030492763",
    "vat_number": "311474361800003",
    "address_ar": "الرياض",
    "address_en": "Riadh",
    "logo": b"\x89PNG\r\n\x1a\nFAKE",
    "logo_mime": "image/png",
}


# ======================================================================
# The company letterhead (all three templates, 2026-07-17)
# ======================================================================
@pytest.mark.parametrize("label,build", ALL_BUILDERS)
def test_letterhead_prints_the_company_in_both_languages_with_its_logo(label, build) -> None:
    html = build(_data())
    assert "شركة الشرارة المضيئة" in html, f"{label}: no Arabic company name"
    assert "Bright Spark Company" in html, f"{label}: no English company name"
    assert "311474361800003" in html and "4030492763" in html
    # The logo is embedded from the row's bytes, not a path or a URL.
    assert "data:image/png;base64," in html


@pytest.mark.parametrize("label,build", LETTERHEAD_BUILDERS)
def test_letterhead_puts_arabic_right_english_left_and_the_logo_between(label, build) -> None:
    """Source order IS the layout here, so it is worth pinning.

    The document is `<html dir="rtl">`: grid items are placed right-to-left, so
    this same source order without `direction:ltr` on the track would print the
    English block on the *right*. The grid is what makes the requested
    «عربي يمين / إنجليزي شمال» true.
    """
    html = build(_data())
    assert "direction:ltr; display:grid" in html
    english = html.index("Bright Spark Company")
    logo = html.index("data:image/png;base64,")
    arabic = html.index("شركة الشرارة المضيئة")
    assert english < logo < arabic, f"{label}: letterhead columns out of order"


@pytest.mark.parametrize("label,build", ALL_BUILDERS)
def test_no_letterhead_when_the_filter_spans_every_company(label, build) -> None:
    """«الكل» has no single issuer, so the sheet must not claim one."""
    data = {**_data(), "company": None}
    html = build(data)
    assert "Bright Spark Company" not in html
    assert "data:image/png;base64," not in html
    assert "كشف حساب العميل" in html, f"{label}: dropped the title along with it"


def test_company_is_no_longer_a_row_among_the_details() -> None:
    # النموذج الثالث listed «اسم الشركة» / «الرقم الضريبي» in a tint box between the
    # header and the table. The user asked for it in the letterhead instead — and
    # only there.
    html = build_statement_html_v3(_data())
    assert "اسم الشركة" not in html
    assert html.count("311474361800003") == 2   # the letterhead's two languages


# ======================================================================
# A long customer name must not mangle the fields beside it
# ======================================================================
_LONG_NAME = "مؤسسة الشرارة المضيئة للمقاولات العامة والتشغيل والصيانة المحدودة"
_UNBROKEN_NAME = "م" * 90


@pytest.mark.parametrize("name", [_LONG_NAME, _UNBROKEN_NAME])
def test_third_templates_bar_keeps_the_period_whole_beside_a_long_name(name) -> None:
    """The bar was flex, so a long name starved the date fields.

    Measured on the printed PDF before this: «الفترة» broke mid-value across four
    lines («01-01-2026 / -2026 — / 17-07») and «تاريخ الإصدار» (since removed) was
    squeezed off the bar altogether. A grid with a fixed track for the period,
    `nowrap` on its value, and `minmax(0,1fr)` for the name is what confines the
    wrapping to the name's own column.
    """
    html = build_statement_html_v3({**_data(), "customer_label": name})
    bar = html.split('background:#1A2A6C; color:#fff; display:grid')[1].split("</div>")[0]
    # The name gets the only flexible track; the period gets its own and may not wrap.
    assert "grid-template-columns:minmax(0,1fr) auto" in bar
    assert bar.count("white-space:nowrap") == 1, "the period must be unwrappable"
    assert name in html


# ======================================================================
# «تاريخ الإصدار» — removed from all three (user, 2026-07-17)
# ======================================================================
@pytest.mark.parametrize("label,build", ALL_BUILDERS)
def test_no_template_stamps_an_issue_date(label, build) -> None:
    """None of the three may print when the sheet was produced.

    Note this is only about the *statement*: the invoice templates' «تاريخ الإصدار»
    is the invoice's own issue date, a required field on a tax invoice, and is a
    different thing entirely.
    """
    html = build(_data())
    assert "تاريخ الإصدار" not in html, f"النموذج {label} still stamps an issue date"


@pytest.mark.parametrize("label,build", ALL_BUILDERS)
def test_templates_do_not_read_issued_at_at_all(label, build) -> None:
    # The screen no longer sends the key. A template reaching for it again would
    # print an empty label rather than fail, so pin that none of them does.
    stamped = build({**_data(), "issued_at": "2026-07-16 10:30"})
    assert "2026-07-16 10:30" not in stamped


# ======================================================================
# The running balance (النموذج الثاني's one derived value)
# ======================================================================
def test_the_running_balance_is_a_cumulative_debit_minus_credit() -> None:
    balances = [balance for _row, balance in rows_with_balance(ROWS)]
    assert balances == [Decimal("65550.00"), Decimal("45550.00"), Decimal("58200.00")]


def test_the_final_running_balance_equals_the_reported_difference() -> None:
    """The balance column and the totals bar must never disagree.

    They are computed independently — the balance walks the rows, the difference
    comes from the service's own totals — so a reader comparing the last row to
    the closing figure is checking two separate calculations. If they can drift,
    the statement is worthless.
    """
    _row_, final = rows_with_balance(ROWS)[-1]
    summary = _data()["summary"]
    assert f"{final:,.2f}" == summary["difference_label"]


def test_the_running_balance_stays_decimal() -> None:
    # Money is Decimal throughout this codebase, never float — a float running
    # balance would print 0.1 + 0.2 artefacts on a tax document.
    for _row_, balance in rows_with_balance(ROWS):
        assert isinstance(balance, Decimal)


def test_the_balance_handles_an_empty_statement() -> None:
    assert rows_with_balance([]) == []


def test_the_balance_survives_rows_with_missing_money() -> None:
    # A defensive row (None debit/credit) must not raise mid-print.
    rows = [{"debit": None, "credit": None, "description": "x"}]
    assert rows_with_balance(rows) == [(rows[0], Decimal("0.00"))]


# ======================================================================
# Every template
# ======================================================================
@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_every_template_emits_a_full_document(label: str, builder) -> None:
    html = builder(_data())
    assert html.lstrip().startswith("<!DOCTYPE html>"), label
    assert 'dir="rtl"' in html, label


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_every_template_prints_the_movements_and_the_totals(label: str, builder) -> None:
    html = builder(_data())
    assert "65,550.00" in html, f"{label}: a movement is missing"
    assert "20,000.00" in html, f"{label}: a movement is missing"
    assert "78,200.00" in html, f"{label}: the debit total is missing"
    assert "58,200.00" in html, f"{label}: the difference is missing"
    assert "سند قبض رقم PA-014" in html, f"{label}: a description is missing"


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_every_template_repeats_its_header_across_pages(label: str, builder) -> None:
    """A statement's row count is unbounded, so it *will* paginate.

    ``display:table-header-group`` is what carries the column headers onto page 2
    and beyond; without it a long statement's later pages are unreadable columns
    of numbers. Verified against a real 4-page PDF when written.
    """
    html = builder(_data())
    assert "table-header-group" in html, f"{label}: headers would not repeat"
    assert "page-break-inside" in html, f"{label}: rows could split across the fold"


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_every_template_handles_the_empty_statement(label: str, builder) -> None:
    html = builder(_data(rows=[]))
    assert "لا توجد حركات للعميل خلال الفترة المحددة" in html, label


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_no_template_declares_a_font_inline(label: str, builder) -> None:
    offenders = _INLINE_FONT_FAMILY.findall(builder(_data()))
    assert not offenders, (
        f"{label}: {len(offenders)} inline style attribute(s) declare font-family. "
        f"The stack's double quotes end the attribute there and every later "
        f"declaration is dropped. Move the font to the <style> block."
    )


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_no_template_invents_an_opening_balance(label: str, builder) -> None:
    """The query reads nothing before the period, so there is no opening balance.

    Printing one would be a fabricated number on a financial document.
    """
    assert "الرصيد الافتتاحي" not in builder(_data()), label


@pytest.mark.parametrize("label, builder", ALL_BUILDERS, ids=[b[0] for b in ALL_BUILDERS])
def test_no_template_prints_a_static_page_number(label: str, builder) -> None:
    """«1 / 1» cannot be honest here: Chromium decides the page count at print
    time, and these statements really do run to several pages."""
    assert "1 / 1" not in builder(_data()), label


_EXPECTED_HEADERS = {
    "النموذج الأول": ["التاريخ", "البيان", "المدين", "الدائن"],
    "النموذج الثاني": ["التاريخ", "البيان", "مدين", "دائن"],
    "النموذج الثالث": ["التاريخ", "البيان", "المدين", "الدائن"],
}


@pytest.mark.parametrize("label, builder", BUILDERS, ids=[b[0] for b in BUILDERS])
def test_the_first_three_show_only_the_four_columns(label: str, builder) -> None:
    # User 2026-07-23: the statement carries exactly التاريخ / البيان / مدين / دائن.
    # اسم العميل, اسم الشركة, the movement-number column and النموذج الثاني's per-row
    # balance column were all removed.
    heads = _header_labels(builder(_data()))
    assert heads == _EXPECTED_HEADERS[label], f"{label}: columns are {heads}"
    for gone in ("اسم العميل", "اسم الشركة", "فاتورة المبيعات", "الفاتورة", "الرصيد"):
        assert gone not in heads, f"{label}: still has the «{gone}» column"


def test_v2_keeps_the_closing_balance_but_no_per_row_balance_column() -> None:
    # النموذج الثاني's per-row running-balance column is gone, but the account
    # balance survives as the «الرصيد المستحق» card and the dark closing row.
    html = build_statement_html_v2(_data())
    assert "الرصيد" not in _header_labels(html)          # no per-row balance column
    assert "الرصيد المستحق" in html                       # the summary card stays
    assert "الرصيد الختامي المستحق على العميل" in html    # and the closing total


@pytest.mark.parametrize("label,build", ALL_BUILDERS)
def test_a_company_without_a_logo_still_gets_a_letterhead(label, build) -> None:
    """Two of the six companies have no logo — the letterhead must degrade, not break.

    (This test used to assert no template *ever* emitted a logo, which was true
    only because the screen hard-coded `logo: ""`. The real requirement is that a
    missing logo produces no <img>, while the names and numbers still print.)
    """
    company = {**COMPANY, "logo": None, "logo_mime": None}
    html = build({**_data(), "company": company})
    assert 'alt="logo"' not in html
    assert "شركة الشرارة المضيئة" in html
    assert "Bright Spark Company" in html
    assert "كشف حساب العميل" in html


def test_v3_signature_is_the_one_shared_bottom_left_line() -> None:
    # النموذج الثالث's «توقيع المحاسب» rule was replaced by the same line the
    # receipt vouchers print, at the sheet's physical left.
    html = build_statement_html_v3(_data())
    assert "توقيع المحاسب" not in html
    assert html.count("التوقيع: .........") == 1
    signature_div = [c for c in html.split("<div ") if "التوقيع: ........." in c]
    assert len(signature_div) == 1
    assert "text-align:left" in signature_div[0]


def test_only_v3_carries_a_signature() -> None:
    # النموذج الأول/الثاني never printed one and must not gain one.
    for build in (build_statement_html_v1, build_statement_html_v2):
        assert "التوقيع" not in build(_data()), f"{build.__name__} grew a signature"


def test_orientation_is_declared_per_template() -> None:
    # النموذج الأول/الثاني stay landscape, النموذج الثالث is a portrait letterhead.
    # statement_page_layout() reads these.
    assert build_statement_html_v1.landscape is True
    assert build_statement_html_v2.landscape is True
    assert build_statement_html_v3.landscape is False
    assert build_statement_html_v4.landscape is False
    assert build_statement_html_v5.landscape is True
    assert build_statement_html_v6.landscape is False
    assert build_statement_html_v7.landscape is False
    assert build_statement_html_v8.landscape is False
    for build in (build_statement_html_v9, build_statement_html_v10, build_statement_html_v11,
                  build_statement_html_v12, build_statement_html_v13, build_statement_html_v14):
        assert build.landscape is False, build.__name__


def test_every_picker_option_has_a_builder() -> None:
    """A fourth option added to the picker without a builder would silently fall
    back to النموذج الأول — the exact bug the invoice dispatch test guards."""
    assert len(STATEMENT_TEMPLATE_OPTIONS) == len(_BUILDERS)
    assert sorted(_BUILDERS) == list(range(1, 15))
    for index, (_label, build) in enumerate(ALL_BUILDERS, start=1):
        assert _BUILDERS[index] is build


# ======================================================================
# النموذج الرابع → الثامن (2026-10-18)
# ======================================================================
def _ths(html_text: str) -> list[str]:
    """Every <th>'s text, nested markup (the bilingual sub-label) flattened."""
    return [re.sub(r"<[^>]+>", " ", h).split()[0] if re.sub(r"<[^>]+>", " ", h).split() else ""
            for h in re.findall(r"<th[^>]*>(.*?)</th>", html_text, flags=re.S)]


@pytest.mark.parametrize(
    "build, expected",
    [
        (build_statement_html_v4, ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"]),
        (build_statement_html_v6, ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"]),
        (build_statement_html_v7, ["التاريخ", "البيان", "مدين", "دائن"]),
        (build_statement_html_v8, ["م", "التاريخ", "البيان", "مدين", "دائن"]),
    ],
)
def test_new_templates_columns(build, expected) -> None:
    assert _ths(build(_data())) == expected


def test_v5_detail_table_carries_the_running_balance() -> None:
    heads = _ths(build_statement_html_v5(_data()))
    assert heads[-5:] == ["التاريخ", "البيان", "مدين", "دائن", "الرصيد"]


@pytest.mark.parametrize("build", [build_statement_html_v4, build_statement_html_v5,
                                   build_statement_html_v6])
def test_running_balance_templates_print_each_rows_balance(build) -> None:
    html = build(_data())
    # 65,550 → 45,550 → 58,200 (see the rows_with_balance tests above).
    for balance in ("65,550.00", "45,550.00", "58,200.00"):
        assert balance in html


def test_v4_groups_by_month_with_a_subtotal_each() -> None:
    html = build_statement_html_v4(_data())
    for month in ("مارس 2026", "أبريل 2026", "مايو 2026"):
        assert f"مجموع {month}" in html
    assert html.index("مجموع مارس 2026") < html.index("مجموع أبريل 2026") < html.index("مجموع مايو 2026")


def test_v5_monthly_net_is_debit_minus_credit() -> None:
    html = build_statement_html_v5(_data())
    assert "-20,000.00" in html          # April: a receipt only
    assert "الملخص الشهري" in html


def test_v7_aging_settles_the_oldest_debit_first() -> None:
    from app.ui.screens.customer_statement_print import _aging

    # As of 2026-07-16: the March invoice (65,550) is 134 days old and gets the
    # 20,000 receipt → 45,550 in «+90»; the May invoice (12,650) is 57 days → 31-60.
    buckets = _aging(_data())
    assert buckets == [Decimal("0"), Decimal("12650.00"), Decimal("0"), Decimal("45550.00")]
    assert sum(buckets) == Decimal("58200.00")     # == the reported difference


def test_v7_aging_is_empty_when_everything_is_paid() -> None:
    from app.ui.screens.customer_statement_print import _aging

    rows = [ROWS[0], _row("2026-03-05", "-", "0.00", "65550.00", "سند قبض رقم 1")]
    assert sum(_aging(_data(rows))) == Decimal("0")


def test_v8_statement_number_needs_a_single_customer() -> None:
    assert "ST-29678-202607" in build_statement_html_v8({**_data(), "customer_id": 29678})
    html = build_statement_html_v8({**_data(), "customer_id": None})
    assert "ST-" not in html


def test_v8_frame_repeats_on_every_printed_page() -> None:
    assert "position:fixed" in build_statement_html_v8(_data())


@pytest.mark.parametrize("label, build", NEW_BUILDERS[:4], ids=[b[0] for b in NEW_BUILDERS[:4]])
def test_new_templates_isolate_dates_inside_arabic_text(label, build) -> None:
    """Inside an Arabic run, bidi prints «2026-07-16» as «16-07-2026» — measured on
    the mock-up PDFs. Every period date in a sentence sits in its own LTR box.
    (النموذج الثامن prints each date alone in its own cell, so has no such run.)"""
    html = build(_data())
    assert 'direction:ltr;">2026-07-16</span>' in html, label


# ======================================================================
# النموذج التاسع → الثالث عشر (2026-10-18, second pick)
# ======================================================================
@pytest.mark.parametrize(
    "build, expected",
    [
        (build_statement_html_v9, ["التاريخ", "البيان", "مدين", "دائن"]),
        (build_statement_html_v10, ["التاريخ", "البيان", "مدين", "دائن"]),
        (build_statement_html_v11, ["التاريخ", "النوع", "البيان", "مدين", "دائن"]),
        (build_statement_html_v12, ["التاريخ", "اليوم", "البيان", "مدين", "دائن"]),
        (build_statement_html_v13, ["التاريخ", "البيان", "مدين", "دائن"]),
    ],
)
def test_second_pick_columns(build, expected) -> None:
    assert _ths(build(_data())) == expected


def test_v9_side_column_is_fixed_on_every_printed_page() -> None:
    html = build_statement_html_v9(_data())
    assert re.search(r"@media print \{[^@]*\.side \{ position:fixed;", html)


def test_v9_side_column_carries_the_full_identity() -> None:
    html = build_statement_html_v9(_data())
    for value in ("شركة الشرارة المضيئة", "Bright Spark Company", "311474361800003", "4030492763"):
        assert value in html


def test_v10_bottom_band_sits_on_every_page_edge() -> None:
    html = build_statement_html_v10(_data())
    assert ".diag-foot { position:fixed;" in html


def test_v11_counts_and_totals_each_movement_type() -> None:
    from app.ui.screens.customer_statement_print import _kind

    kinds = [_kind(r) for r in ROWS]
    assert kinds == ["invoice_credit", "receipt", "invoice_cash"]
    html = build_statement_html_v11(_data())
    assert "فاتورة آجلة · 1" in html and "سند قبض · 1" in html and "فاتورة نقدية · 1" in html


def test_v12_draws_one_calendar_per_month_and_names_the_weekday() -> None:
    html = build_statement_html_v12(_data())
    for month in ("مارس 2026", "أبريل 2026", "مايو 2026"):
        assert month in html
    # 2026-03-04 was a Wednesday, 2026-04-12 a Sunday, 2026-05-20 a Wednesday.
    body = html.split("<tbody>")[1]
    assert [w for w in ("أربعاء", "أحد", "أربعاء") if w in body] == ["أربعاء", "أحد", "أربعاء"]
    assert body.index("أربعاء") < body.index("أحد")


def test_v12_without_movements_draws_no_calendar() -> None:
    assert "يوم فيه فاتورة" not in build_statement_html_v12(_data(rows=[]))


def test_v13_spells_the_balance_in_words_once() -> None:
    html = build_statement_html_v13(_data())
    assert html.count("فقط ") == 1 and html.count("لا غير") == 1
    assert "ريالاً" in html


def test_v13_words_drop_the_sign_of_a_credit_balance() -> None:
    from app.ui.screens.customer_statement_print import _words

    assert _words({"difference_label": "-1,250.00"}) == _words({"difference_label": "1,250.00"})


# ======================================================================
# النموذج الرابع عشر (2026-10-20, third pick)
# ======================================================================
def test_v14_columns() -> None:
    assert _ths(build_statement_html_v14(_data())) == [
        "التاريخ", "المستند", "قبل", "ضريبة", "الإجمالي", "المسدد", "الرصيد"]


def test_v14_uses_the_stored_vat_split_when_given() -> None:
    rows = [dict(ROWS[0], source_type="sales_invoice", source_id=7)]
    data = _data(rows)
    # A stored split that is NOT total/1.15, so only the stored one can print it.
    data["vat_breakdown"] = {7: {"taxable": Decimal("60000.00"), "vat": Decimal("5550.00")}}
    html = build_statement_html_v14(data)
    assert "60,000.00" in html and "5,550.00" in html


def test_v14_splits_at_fifteen_percent_without_a_stored_split() -> None:
    html = build_statement_html_v14(_data())
    # 65,550.00 = 57,000.00 + 8,550.00 ; 12,650.00 = 11,000.00 + 1,650.00
    assert "57,000.00" in html and "8,550.00" in html
    assert "68,000.00" in html and "10,200.00" in html   # the VAT summary totals


def test_v14_receipts_carry_no_vat() -> None:
    html = build_statement_html_v14(_data([ROWS[1]]))   # a receipt alone
    assert re.search(r"عدد الفواتير الضريبية</td>.*?<span class=\"num\">0</span>", html, re.S)
    assert re.search(r"ضريبة القيمة المضافة 15٪</td>.*?<span class=\"num\">0.00</span>", html, re.S)


def test_v14_prints_both_parties_tax_identity() -> None:
    data = _data()
    data["customer"] = {"customer_name": "شركة الريادة", "vat_number": "310000000000003",
                        "cr": "1010101010", "address": "جدة"}
    html = build_statement_html_v14(data)
    assert "المورّد" in html and "العميل" in html
    assert "311474361800003" in html and "310000000000003" in html and "1010101010" in html


def test_v14_has_no_qr_code() -> None:
    html = build_statement_html_v14(_data())
    assert "QR" not in html and "qr" not in html.lower().replace("qrcode", "")
