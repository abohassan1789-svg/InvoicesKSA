"""Every template-picker choice must reach *its own* builder.

This mapping broke silently once already: ``on_preview`` and ``on_export_pdf``
each open-coded ``build_invoice_html if choice == 1 else build_invoice_html_v2``,
so picking النموذج الثالث quietly printed النموذج الثاني. The picker looked fine
and nothing failed — the wrong layout simply came out. The dispatch now lives in
one place (:meth:`SaudiSalesInvoicePage._choose_invoice_builder`); this pins it.

The picker dialog is patched out, so no window opens and the tests stay headless.
"""

from __future__ import annotations

import os
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from app.services.saudi_sales_invoice_service import SaudiSalesInvoiceService
from app.ui.screens import saudi_invoice_print
from app.ui.screens.saudi_invoice_print import (
    _DEFAULT_TEMPLATE_OPTIONS,
    build_invoice_html,
)
from app.ui.screens.saudi_invoice_print_v2 import build_invoice_html_v2
from app.ui.screens.saudi_invoice_print_v3 import build_invoice_html_v3
from app.ui.screens.saudi_invoice_print_v4 import build_invoice_html_v4
from app.ui.screens.saudi_invoice_print_v5 import build_invoice_html_v5
from app.ui.screens.saudi_invoice_print_v6 import build_invoice_html_v6
from app.ui.screens.saudi_invoice_print_v7 import build_invoice_html_v7
from app.ui.screens.saudi_invoice_print_v8 import build_invoice_html_v8
from app.ui.screens.saudi_invoice_print_v22 import build_invoice_html_v22
from app.ui.screens.saudi_invoice_print_v23 import build_invoice_html_v23
from app.ui.screens.saudi_invoice_print_v24 import build_invoice_html_v24
from app.ui.screens.saudi_invoice_print_v25 import build_invoice_html_v25
from app.ui.screens.saudi_invoice_print_v26 import build_invoice_html_v26
from app.ui.screens.saudi_invoice_print_v27 import build_invoice_html_v27
from app.ui.screens.saudi_invoice_print_v14 import build_invoice_html_v14
from app.ui.screens.saudi_invoice_print_phase1 import (
    build_phase1_design1_phase2,
    build_phase1_design2_phase2,
    build_phase1_design3_phase2,
    build_phase1_model15_phase2,
    build_phase1_model16_phase2,
    build_phase1_model17_phase2,
)
from app.ui.screens.saudi_sales_invoice_page import SaudiSalesInvoicePage

from tests.unit.test_saudi_sales_invoice_page import FakeRepo

_EXPECTED = {
    1: build_invoice_html,
    2: build_invoice_html_v2,
    3: build_invoice_html_v3,
    4: build_invoice_html_v4,
    5: build_invoice_html_v5,
    6: build_invoice_html_v6,
    7: build_invoice_html_v7,
    8: build_invoice_html_v8,
}

# Phase-2 picker tail after النماذج الأول→الثامن (user requests, 2026-09-16):
# 9‑11 = the three native مرحلة-أولى designs re-QR'd for Phase-2; 12‑13 = copies of
# مرحلة أولى «النموذج الخامس عشر/السابع عشر».
# المتكاملة/الإسناد الماسي/اقاسيم/الخطوط السعودية were hidden from THIS picker, and
# مواسم الفاكهة + the v15–v21 replicas (دروب الاتحاد…نوافذ) too (user 2026-10-17).
_PHASE2_EXTRA_OPTIONS = (
    "النموذج التاسع",
    "النموذج العاشر",
    "النموذج الحادي عشر",
    "النموذج الثاني عشر",
    "النموذج الثالث عشر",
    "النموذج الرابع عشر",
    "النموذج الخامس عشر",
    "النموذج السادس عشر",
    "النموذج السابع عشر",
    "النموذج الثامن عشر",
    "النموذج التاسع عشر",
    "النموذج العشرون",
    "نهلة الخليج",
)

_PHASE2_EXTRA_BUILDERS = {
    9: build_phase1_design1_phase2,
    10: build_phase1_design2_phase2,
    11: build_phase1_design3_phase2,
    12: build_phase1_model15_phase2,
    13: build_phase1_model16_phase2,
    14: build_phase1_model17_phase2,
    15: build_invoice_html_v22,
    16: build_invoice_html_v23,
    17: build_invoice_html_v24,
    18: build_invoice_html_v25,
    19: build_invoice_html_v26,
    20: build_invoice_html_v27,
    21: build_invoice_html_v14,  # «نهلة الخليج», re-shown 2026-10-20
}

# Hidden from BOTH pickers (Phase-2 and «مرحلة أولى») on 2026-10-17 —
# الخطوط السعودية/نموذج أطياف were only in «مرحلة أولى» and are hidden there too.
# (نموذج أطياف came back on 2026-10-20 under the name «نهلة الخليج», in both.)
_HIDDEN_REPLICAS = (
    "مواسم الفاكهة",
    "دروب الاتحاد",
    "إنتار الغربيا",
    "موضي عقيل",
    "ميج السعودية",
    "الامل الناجح",
    "قصر نصار",
    "نوافذ",
    "الخطوط السعودية",
    "نموذج أطياف",
)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def page(qapp):
    return SaudiSalesInvoicePage(service=SaudiSalesInvoiceService(repository=FakeRepo()))


def test_every_option_has_a_builder():
    """A new option in the picker without a builder falls back to النموذج الأول."""
    assert len(_DEFAULT_TEMPLATE_OPTIONS) == len(_EXPECTED)


@pytest.mark.parametrize("choice", sorted(_EXPECTED))
def test_choice_reaches_its_own_builder(page, monkeypatch, choice):
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda *a, **k: choice,
    )
    assert page._choose_invoice_builder("المعاينة") is _EXPECTED[choice]


@pytest.mark.parametrize("choice", sorted(_PHASE2_EXTRA_BUILDERS))
def test_phase2_extra_choice_reaches_its_own_builder(page, monkeypatch, choice):
    """Each Phase-2 tail option (9‑14) must reach its own builder, never fall back."""
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda *a, **k: choice,
    )
    assert page._choose_invoice_builder("المعاينة") is _PHASE2_EXTRA_BUILDERS[choice]


def test_phase2_picker_offers_exactly_the_expected_options(page, monkeypatch):
    """The Phase-2 picker = النماذج الأول→الثامن + the six-option tail, nothing else.

    Pins that المتكاملة/الإسناد الماسي/اقاسيم/الخطوط السعودية stay hidden here and
    that «النموذج الرابع عشر» (the ZATCA replica) is the last option."""
    captured = {}

    def capture_options(_parent, _label, options, **_kwargs):
        captured["options"] = tuple(options)
        return None

    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template", capture_options
    )

    assert page._choose_invoice_builder("المعاينة") is None
    assert captured["options"] == tuple(_DEFAULT_TEMPLATE_OPTIONS) + _PHASE2_EXTRA_OPTIONS
    assert len(captured["options"]) == len(_EXPECTED) + len(_PHASE2_EXTRA_BUILDERS)
    for hidden in ("المتكاملة", "الإسناد الماسي", "اقاسيم") + _HIDDEN_REPLICAS:
        assert hidden not in captured["options"]
    assert captured["options"][-1] == "نهلة الخليج"




def test_cancelling_the_picker_builds_nothing(page, monkeypatch):
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda *a, **k: None,
    )
    assert page._choose_invoice_builder("المعاينة") is None


# ======================================================================
# Receipt voucher (سند قبض) — printed from two different screens
# ======================================================================
from app.ui.screens.saudi_receipt_voucher_print import (  # noqa: E402
    VOUCHER_TEMPLATE_OPTIONS,
    build_receipt_voucher_html,
    build_receipt_voucher_html_v2,
    build_receipt_voucher_html_v3,
    build_receipt_voucher_html_v4,
    build_receipt_voucher_html_v5,
    build_receipt_voucher_html_v6,
    build_receipt_voucher_html_v7,
    build_receipt_voucher_html_v8,
    build_receipt_voucher_html_v9,
    choose_voucher_builder,
)
from app.ui.screens.saudi_receipt_voucher_print_v10 import build_receipt_voucher_html_v10  # noqa: E402
from app.ui.screens.saudi_receipt_voucher_print_v11 import build_receipt_voucher_html_v11  # noqa: E402
from app.ui.screens.saudi_receipt_voucher_print_v12 import build_receipt_voucher_html_v12  # noqa: E402
from app.ui.screens.saudi_voucher_print_phase1 import (  # noqa: E402
    build_phase1_voucher_html,
    build_phase1_voucher_html_v2,
    build_phase1_voucher_html_v4,
)

_VOUCHER_EXPECTED = {
    1: build_receipt_voucher_html,
    2: build_receipt_voucher_html_v2,
    3: build_receipt_voucher_html_v3,
    4: build_receipt_voucher_html_v4,
    5: build_receipt_voucher_html_v5,
    6: build_receipt_voucher_html_v6,
    7: build_receipt_voucher_html_v7,
    8: build_receipt_voucher_html_v8,
    9: build_receipt_voucher_html_v9,
    # النماذج العاشر/الحادي عشر/الثاني عشر = Phase-1 layouts reused in Phase-2.
    10: build_phase1_voucher_html,
    11: build_phase1_voucher_html_v2,
    12: build_phase1_voucher_html_v4,
    13: build_receipt_voucher_html_v10,  # «سند عقيل»
    14: build_receipt_voucher_html_v11,  # «سند الامل»
    15: build_receipt_voucher_html_v12,  # «سند القصر»
}


def test_every_voucher_option_has_a_builder():
    assert len(VOUCHER_TEMPLATE_OPTIONS) == len(_VOUCHER_EXPECTED)


@pytest.mark.parametrize("choice", sorted(_VOUCHER_EXPECTED))
def test_voucher_choice_reaches_its_own_builder(qapp, monkeypatch, choice):
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda *a, **k: choice,
    )
    assert choose_voucher_builder(None) is _VOUCHER_EXPECTED[choice]


def test_cancelling_the_voucher_picker_builds_nothing(qapp, monkeypatch):
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda *a, **k: None,
    )
    assert choose_voucher_builder(None) is None


# ======================================================================
# Phase-1 «مرحلة أولى» rosters (فواتير + سندات) — النموذج الأول → السادس
# ======================================================================
from app.ui.screens.saudi_invoice_print_phase1 import (  # noqa: E402
    PHASE1_TEMPLATE_OPTIONS,
    _PHASE1_BUILDERS,
    build_phase1_invoice_html,
    build_phase1_invoice_html_v2,
    build_phase1_invoice_html_v3,
    build_phase1_invoice_html_v7,
    build_phase1_p2_model1,
    build_phase1_p2_model6,
    phase1_builder_for,
)
from app.ui.screens.saudi_voucher_print_phase1 import (  # noqa: E402
    PHASE1_VOUCHER_TEMPLATE_OPTIONS,
    _PHASE1_VOUCHER_BUILDERS,
    build_phase1_voucher_html_v6,
    phase1_voucher_builder_for,
)


def test_phase1_rosters_are_complete():
    """Every «مرحلة أولى» picker label (invoice + voucher) must have a builder, so a
    new option can never silently fall through to «قيد الإنشاء». The invoice roster
    now mirrors the first 11 Phase-2 templates (المتكاملة/الإسناد الماسي/اقاسيم
    hidden per user request)."""
    assert len(PHASE1_TEMPLATE_OPTIONS) == len(_PHASE1_BUILDERS) == 21
    for hidden in _HIDDEN_REPLICAS:
        assert hidden not in PHASE1_TEMPLATE_OPTIONS
    assert len(PHASE1_VOUCHER_TEMPLATE_OPTIONS) == len(_PHASE1_VOUCHER_BUILDERS) == 12


def test_phase1_voucher_7to9_reuse_phase2_designs():
    """«سندات» مرحلة أولى now also offers Phase-2's النموذج السابع/الثامن/التاسع, as-is
    (vouchers carry no QR/phase distinction), appended after the six native ones."""
    from app.ui.screens.saudi_receipt_voucher_print import (
        build_receipt_voucher_html_v7,
        build_receipt_voucher_html_v8,
        build_receipt_voucher_html_v9,
    )

    assert PHASE1_VOUCHER_TEMPLATE_OPTIONS[6:9] == (
        "النموذج السابع",
        "النموذج الثامن",
        "النموذج التاسع",
    )
    assert phase1_voucher_builder_for(7) is build_receipt_voucher_html_v7
    assert phase1_voucher_builder_for(8) is build_receipt_voucher_html_v8
    assert phase1_voucher_builder_for(9) is build_receipt_voucher_html_v9


def test_phase1_invoice_roster_mirrors_phase2(page, monkeypatch):
    """The Phase-1 invoice picker's first 11 labels mirror the Phase-2 picker, in
    the same order; three Phase-1-only designs follow as extra options 12–14
    (المتكاملة/الإسناد الماسي/اقاسيم hidden per user request)."""
    phase2 = tuple(_DEFAULT_TEMPLATE_OPTIONS) + (
        "النموذج التاسع",
        "النموذج العاشر",
        "النموذج الحادي عشر",
    )
    assert PHASE1_TEMPLATE_OPTIONS[:11] == phase2
    assert PHASE1_TEMPLATE_OPTIONS[11:] == (
        "النموذج الثاني عشر",
        "النموذج الثالث عشر",
        "النموذج الرابع عشر",
        "النموذج الخامس عشر",
        "النموذج السادس عشر",
        "النموذج السابع عشر",
        "النموذج الثامن عشر",
        "النموذج التاسع عشر",
        "النموذج العشرون",
        "نهلة الخليج",
    )


def test_phase1_extra_designs_13to15_are_native_phase1(page):
    """النموذج الخامس عشر/السادس عشر/السابع عشر are the restored Phase-1-only designs
    (build_phase1_invoice_html_v4/_v5/_v6), reached from the Phase-1 picker."""
    from app.ui.screens.saudi_invoice_print_phase1 import (
        build_phase1_invoice_html_v4,
        build_phase1_invoice_html_v5,
        build_phase1_invoice_html_v6,
    )

    assert phase1_builder_for(12) is build_phase1_invoice_html_v4
    assert phase1_builder_for(13) is build_phase1_invoice_html_v5
    assert phase1_builder_for(14) is build_phase1_invoice_html_v6




















def test_phase1_first_template_is_phase2_v1_with_a_phase1_qr():
    """«النموذج الأول» of مرحلة أولى is Phase-2's النموذج الأول (build_invoice_html)
    re-QR'd — it must reach its own wrapper, never the Phase-2 builder directly."""
    from app.ui.screens import saudi_invoice_print

    assert PHASE1_TEMPLATE_OPTIONS[0] == "النموذج الأول"
    assert phase1_builder_for(1) is build_phase1_p2_model1
    assert build_phase1_p2_model1 is not saudi_invoice_print.build_invoice_html


def test_phase1_sixth_template_is_phase2_v6_with_a_phase1_qr():
    """Under the full mirror, النموذج السادس is Phase-2's v6 (not the old Phase-1
    design) re-QR'd; the voucher sixth is unchanged."""
    assert PHASE1_TEMPLATE_OPTIONS[5] == "النموذج السادس"
    assert phase1_builder_for(6) is build_phase1_p2_model6
    assert PHASE1_VOUCHER_TEMPLATE_OPTIONS[5] == "النموذج السادس"
    assert phase1_voucher_builder_for(6) is build_phase1_voucher_html_v6


def test_phase1_eighth_template_is_phase2_v8_with_a_phase1_qr():
    """«النموذج الثامن» of مرحلة أولى is Phase-2's النموذج الثامن re-QR'd.

    It must reach its own wrapper — never ``build_invoice_html_v8`` directly —
    because the wrapper is what replaces the signed tags 1–9 payload with the
    Phase-1 tags 1–5 code before the layout reads it.
    """
    from app.ui.screens import saudi_invoice_print_v8

    assert PHASE1_TEMPLATE_OPTIONS[7] == "النموذج الثامن"
    assert phase1_builder_for(8) is build_phase1_invoice_html_v7
    assert build_phase1_invoice_html_v7 is not saudi_invoice_print_v8.build_invoice_html_v8


def test_phase1_ninth_to_eleventh_are_native_phase1_designs():
    """النموذج التاسع/العاشر/الحادي عشر of مرحلة أولى are the three native Phase-1
    designs (build_phase1_invoice_html/_v2/_v3), matching Phase-2's positions 9–11."""
    assert PHASE1_TEMPLATE_OPTIONS[8] == "النموذج التاسع"
    assert phase1_builder_for(9) is build_phase1_invoice_html
    assert phase1_builder_for(10) is build_phase1_invoice_html_v2
    assert phase1_builder_for(11) is build_phase1_invoice_html_v3


def test_phase1_seventh_template_never_prints_the_signed_qr(monkeypatch):
    """The Phase-2 signed payload must not survive into the Phase-1 sheet."""
    from app.ui.screens import saudi_invoice_print_phase1 as phase1

    seen: dict[str, object] = {}
    monkeypatch.setattr(
        phase1, "build_invoice_html_v8", lambda data: seen.update(data) or ""
    )
    monkeypatch.setattr(phase1, "_phase1_qr_payload", lambda data: "TAGS-1-5")

    phase1.build_phase1_invoice_html_v7({"qr_payload": "SIGNED-TAGS-1-9", "seller": {}})
    assert seen["qr_payload"] == "TAGS-1-5"


def test_both_voucher_screens_share_one_dispatch():
    """Neither screen may re-open-code the option list or the builder map.

    They each used to carry their own copy, so a template added to one screen was
    silently missing from the other. Both must go through choose_voucher_builder.
    """
    import inspect

    from app.ui.screens import receipt_vouchers_screen, saudi_sales_invoice_page

    for module in (receipt_vouchers_screen, saudi_sales_invoice_page):
        src = inspect.getsource(module)
        assert "choose_voucher_builder" in src, f"{module.__name__} bypasses the shared dispatch"
        assert "build_receipt_voucher_html_v2" not in src, (
            f"{module.__name__} open-codes a voucher builder map again"
        )


def test_aqeel_voucher_in_both_pickers():
    """«سند عقيل» is the last option of BOTH voucher pickers and reaches the
    same builder (vouchers carry no QR, so Phase-1 needs no wrapper)."""
    assert VOUCHER_TEMPLATE_OPTIONS[12] == "سند عقيل"
    assert PHASE1_VOUCHER_TEMPLATE_OPTIONS[9] == "سند عقيل"
    assert phase1_voucher_builder_for(10) is build_receipt_voucher_html_v10


def test_amal_voucher_in_both_pickers():
    """«سند الامل» is the last option of BOTH voucher pickers, same builder."""
    assert VOUCHER_TEMPLATE_OPTIONS[13] == "سند الامل"
    assert PHASE1_VOUCHER_TEMPLATE_OPTIONS[10] == "سند الامل"
    assert phase1_voucher_builder_for(11) is build_receipt_voucher_html_v11


def test_qasr_voucher_in_both_pickers():
    """«سند القصر» is the last option of BOTH voucher pickers, same builder."""
    assert VOUCHER_TEMPLATE_OPTIONS[-1] == "سند القصر"
    assert PHASE1_VOUCHER_TEMPLATE_OPTIONS[-1] == "سند القصر"
    assert phase1_voucher_builder_for(12) is build_receipt_voucher_html_v12


@pytest.mark.parametrize("payment, ticked", [("نقدي", "cash"), ("شيك", "cheque"), ("تحويل", "transfer"), ("", None)])
def test_qasr_voucher_prints_live_data_and_ticks_the_method(payment, ticked):
    import datetime
    from decimal import Decimal

    html = build_receipt_voucher_html_v12({
        "number": "166", "issue_date": datetime.date(2026, 2, 3), "amount": Decimal("148000"),
        "received_from": "عميل تجريبي", "payment_type": payment, "purpose": "سداد فاتورة",
        "seller": {"name": "شركة البائع", "address": "الرياض"},
    })
    for needle in ("شركة البائع", "#166", "03/02/2026", "148,000", "عميل تجريبي", "ريال سعودي فقط لا غير",
                   "Received Voucher", "Recevied From Mr.", "Main Treasury", "سداد فاتورة", "أمين الصندوق"):
        assert needle in html, needle
    boxes = {key: f"{arabic}</span><span class=\"cb\">&#10003;" in html
             for key, arabic in (("cash", "نقداً"), ("cheque", "شيك"), ("transfer", "تحويل"))}
    assert boxes == {key: key == ticked for key in boxes}


def test_amal_voucher_prints_live_data():
    import datetime
    from decimal import Decimal

    html = build_receipt_voucher_html_v11({
        "number": "PYT51", "issue_date": datetime.date(2025, 10, 2), "amount": Decimal("27600"),
        "received_from": "عميل تجريبي", "reference": "INV136", "purpose": "دفعت نقدي",
        "seller": {"name": "شركة البائع", "address": "الرياض"},
    })
    for needle in ("سند قبض", "شركة البائع", "مستلم من", "عميل تجريبي", "PYT51", "2025-10-02",
                   "النقدية في الخزينة", "27,600.00", "INV136", "فاتورة مبيعات", "الوصف", "دفعت نقدي"):
        assert needle in html, needle


def test_aqeel_voucher_prints_live_data():
    import datetime
    from decimal import Decimal

    html = build_receipt_voucher_html_v10({
        "number": "113", "issue_date": datetime.date(2026, 2, 5), "amount": Decimal("105455"),
        "received_from": "عميل تجريبي", "received_from_code": "29673", "payment_type": "",
        "purpose": "سداد فواتير\nINV-0469",
        "seller": {"name": "شركة البائع", "cr": "7013655993", "vat": "310085953300003", "address": "الطائف"},
    })
    for needle in ("عملية دفع عميل", "#113", "2026/2/5", "105,455.00", "#29673</span> - عميل تجريبي",
                   "طريقة الدفع / </span>نقدي", "الخزنة الرئيسية", "سداد فواتير<br>INV-0469",
                   "Register Number : 7013655993", "Tax Number : 310085953300003",
                   "ريال سعودي لا غير.", "Accountant", "Manager"):
        assert needle in html, needle
    assert "فقط" not in html


def test_both_pickers_offer_the_same_names(page, monkeypatch):
    """Phase-2 and «مرحلة أولى» list the same 20 labels in the same order (2026-10-18);
    15‑20 are the new in-house designs (v22…v27); 12‑14 are the Phase-1 designs v4/v5/v6, re-QR'd with the signed tags 1–9 on Phase-2."""
    captured = {}
    monkeypatch.setattr(
        "app.ui.screens.saudi_invoice_print.choose_invoice_template",
        lambda _p, _l, options, **_k: captured.update(options=tuple(options)),
    )
    page._choose_invoice_builder("المعاينة")
    assert captured["options"] == PHASE1_TEMPLATE_OPTIONS
    assert len(PHASE1_TEMPLATE_OPTIONS) == 21


def test_phase2_model13_is_phase1_v5_with_the_signed_qr(monkeypatch):
    from app.ui.screens import saudi_invoice_print_phase1 as phase1

    seen = {}
    monkeypatch.setattr(phase1, "build_phase1_invoice_html_v5", lambda data: seen.update(data) or "")
    phase1.build_phase1_model16_phase2({"qr_payload": "SIGNED"})
    assert seen["use_phase2_qr"] is True


@pytest.mark.parametrize(
    "choice, wrapper_name, raw_name",
    [
        (15, "build_phase1_invoice_cards", "build_invoice_html_v22"),
        (16, "build_phase1_invoice_stripe", "build_invoice_html_v23"),
        (17, "build_phase1_invoice_hero", "build_invoice_html_v24"),
        (18, "build_phase1_invoice_boarding", "build_invoice_html_v25"),
        (19, "build_phase1_invoice_mirror", "build_invoice_html_v26"),
        (20, "build_phase1_invoice_timeline", "build_invoice_html_v27"),
        (21, "build_phase1_invoice_atyaf", "build_invoice_html_v14"),
    ],
)
def test_phase1_new_designs_swap_in_the_phase1_qr(monkeypatch, choice, wrapper_name, raw_name):
    """«مرحلة أولى» 15‑20 reach their own wrappers, which print the tags 1–5 QR
    instead of the Phase-2 signed payload (the only difference between phases)."""
    from app.ui.screens import saudi_invoice_print_phase1 as phase1

    wrapper = getattr(phase1, wrapper_name)
    assert phase1_builder_for(choice) is wrapper
    seen = {}
    monkeypatch.setattr(phase1, raw_name, lambda data: seen.update(data) or "")
    monkeypatch.setattr(phase1, "_phase1_qr_payload", lambda data: "TAGS-1-5")
    wrapper({"qr_payload": "SIGNED-TAGS-1-9", "seller": {}})
    assert seen["qr_payload"] == "TAGS-1-5"
