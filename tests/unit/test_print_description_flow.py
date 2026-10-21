"""«إظهار وصف الصنف»: the flow-layout invoice templates add a description column
right after the item-name column only when the flag is ticked."""

from __future__ import annotations

import datetime
import importlib
import re
from decimal import Decimal

import pytest

# (module, builder, title of the new column's header)
_BUILDERS = [
    ("saudi_invoice_print", "build_invoice_html", "الوصف"),
    ("saudi_invoice_print_v2", "build_invoice_html_v2", "وصف الصنف"),
    ("saudi_invoice_print_v9", "build_invoice_html_v9", "الوصف"),
    ("saudi_invoice_print_v10", "build_invoice_html_v10", "وصف الصنف"),
    ("saudi_invoice_print_v11", "build_invoice_html_v11", "الوصف"),
    ("saudi_invoice_print_v12", "build_invoice_html_v12", "الوصف"),
    ("saudi_invoice_print_v13", "build_invoice_html_v13", "ITEM DESCRIPTION"),
    ("saudi_invoice_print_v14", "build_invoice_html_v14", "وصف الصنف"),
    ("saudi_invoice_print_v15", "build_invoice_html_v15", "الوصف"),
    ("saudi_invoice_print_v16", "build_invoice_html_v16", "وصف الصنف"),
    ("saudi_invoice_print_v18", "build_invoice_html_v18", "الوصف"),
    ("saudi_invoice_print_v19", "build_invoice_html_v19", "الوصف"),
    ("saudi_invoice_print_v28", "build_invoice_html_v28", "وصف الصنف"),
    ("saudi_invoice_print_v29", "build_invoice_html_v29", "وصف الصنف"),
]
_IDS = [fn for _m, fn, _t in _BUILDERS]

_DESC = "وصف خاص بالطباعة <b>&</b>"
_DESC_ESCAPED = "وصف خاص بالطباعة &lt;b&gt;&amp;&lt;/b&gt;"


def _line(no: int, description: str | None) -> dict:
    line = {
        "code": f"C-{no}", "name": f"صنف الاختبار {no}", "unit": "حبة", "qty": Decimal("2"),
        "price": Decimal("10.00"), "before": Decimal("20.00"), "vat_amount": Decimal("3.00"),
        "vat_rate": Decimal("15.00"), "total": Decimal("23.00"),
    }
    if description is not None:
        line["description"] = description
    return line


def _data(show: bool | None, lines: list[dict] | None = None) -> dict:
    data = {
        "invoice_number": "INV-1", "issue_datetime": datetime.datetime(2026, 1, 5, 10, 30),
        "payment_label": "نقدي",
        "seller": {"name": "البائع", "name_en": "Seller", "address": "الرياض", "vat": "300000000000003",
                   "cr": "1010101010", "logo": None, "stamp": None},
        "customer": {"name": "العميل", "vat": "311111111100003", "cr": "2020202020", "address": "جدة"},
        "lines": lines if lines is not None else [_line(1, f"  {_DESC}  "), _line(2, None)],
        "totals": {"subtotal": Decimal("40.00"), "discount": Decimal("0"), "taxable": Decimal("40.00"),
                   "vat": Decimal("6.00"), "total": Decimal("46.00")},
        "show_unit": True, "show_stamp": False, "qr_payload": "AQ1URVNU",
    }
    if show is not None:
        data["show_description"] = show
    return data


def _build(mod: str, fn: str):
    return getattr(importlib.import_module(f"app.ui.screens.{mod}"), fn)


@pytest.mark.parametrize(("mod", "fn", "title"), _BUILDERS, ids=_IDS)
def test_description_column_when_flag_on(mod, fn, title):
    build = _build(mod, fn)
    on = build(_data(True))
    off = build(_data(False))
    assert _DESC_ESCAPED in on
    assert 'class="line-desc"' not in on
    # Its own header, and its own cell: the name cell closes before the description.
    assert on.count(title) > off.count(title)
    between = on[on.index("صنف الاختبار 1"):on.index("وصف خاص بالطباعة")]
    assert re.search(r"</(td|div)>", between)


@pytest.mark.parametrize(("mod", "fn", "title"), _BUILDERS, ids=_IDS)
def test_description_column_with_flag_on_and_no_descriptions(mod, fn, title):
    build = _build(mod, fn)
    on = build(_data(True, [_line(1, None), _line(2, "")]))
    assert on.count(title) > build(_data(False, [_line(1, None)])).count(title)
    assert "صنف الاختبار 2" in on


@pytest.mark.parametrize(("mod", "fn", "title"), _BUILDERS, ids=_IDS)
@pytest.mark.parametrize("show", [False, None])
def test_no_description_column_when_flag_off(mod, fn, title, show):
    build = _build(mod, fn)
    out = build(_data(show))
    assert "وصف خاص بالطباعة" not in out
    assert out == build(_data(show, [_line(1, None), _line(2, None)]))
