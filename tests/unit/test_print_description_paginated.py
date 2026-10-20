"""«إظهار وصف الصنف» on the fixed-sheet, self-paginating templates
(النماذج الثالث → الثامن).

Ticked, each template prints a «الوصف» COLUMN right after the item-name column,
carved out of the same table width. These templates split rows across 1056px
``overflow:hidden`` sheets using row-height *estimates*, so the description cell
must also be paid for in the estimate — otherwise the bottom rows of a sheet are
silently clipped. Unticked, nothing changes.
"""

from __future__ import annotations

import datetime
from decimal import Decimal as D

import pytest

from app.ui.screens import (
    saudi_invoice_print_v3 as v3,
    saudi_invoice_print_v4 as v4,
    saudi_invoice_print_v5 as v5,
    saudi_invoice_print_v6 as v6,
    saudi_invoice_print_v7 as v7,
    saudi_invoice_print_v8 as v8,
)
from app.ui.screens.saudi_invoice_print import with_print_descriptions

DESC = "وصف تجريبي DESCX للصنف — خامة عالية الجودة مقاس كبير لون أبيض مع ضمان سنتين من تاريخ التوريد"
NAME = "صنف رقم 1"

TEMPLATES = [
    ("v3", v3.build_invoice_html_v3, v3._row_height_v3),
    ("v4", v4.build_invoice_html_v4, v4._row_height_v4),
    ("v5", v5.build_invoice_html_v5, v5._row_height_v5),
    ("v6", v6.build_invoice_html_v6, v6._row_height_v6),
    ("v7", v7.build_invoice_html_v7, v7._row_height_v7),
    ("v8", v8.build_invoice_html_v8, v8._row_height_v8),
]
IDS = [t[0] for t in TEMPLATES]

# (default widths, «الوصف»-on widths, name index, description index, grid gap)
WIDTHS = {
    "v3": (v3._COL_WIDTHS, v3._COL_WIDTHS_DESC, v3._NAME_COLUMN, v3._DESC_COLUMN, 0),
    "v4": (tuple(w for _, w in v4._COLUMNS), tuple(w for _, w in v4._COLUMNS_DESC),
           v4._NAME_COLUMN, v4._DESC_COLUMN, 0),
    "v5": (tuple(w for *_, w in v5._COLUMNS), tuple(w for *_, w in v5._COLUMNS_DESC),
           v5._NAME_COLUMN, v5._DESC_COLUMN, 0),
    "v6": (v6._ITEM_COLS, v6._ITEM_COLS_DESC, 0, v6._DESC_COLUMN, 0),
    "v7": (v7._ITEM_COLS, v7._ITEM_COLS_DESC, 1, v7._DESC_COLUMN, 1),   # 1px grid gaps
    "v8": (v8._ITEM_COLS, v8._ITEM_COLS_DESC, 1, 2, 0),
}


def _data(n: int = 3, *, show: bool | None = None, desc: str = DESC, show_unit: bool = True) -> dict:
    lines = []
    for i in range(1, n + 1):
        lines.append(dict(code=f"C-{i}", name=f"صنف رقم {i}", qty=D(2), unit="حبة",
                          description=desc, price=D("10.00"), before=D("20.00"),
                          vat_amount=D("3.00"), vat_rate=D("15.00"), total=D("23.00")))
    data = {
        "invoice_number": "INV-1", "issue_datetime": datetime.datetime(2026, 1, 5, 10, 30),
        "payment_label": "نقدي",
        "seller": {"name": "البائع", "vat": "300000000000003", "cr": "1010101010", "address": "الرياض"},
        "customer": {"name": "العميل", "vat": "311111111100003", "cr": "2020202020", "address": "جدة"},
        "lines": lines,
        "totals": {"subtotal": D(20 * n), "discount": D(0), "taxable": D(20 * n),
                   "vat": D(3 * n), "total": D(23 * n)},
        "show_unit": show_unit,
        "qr_payload": "AQ1URVNU",
    }
    if show is not None:
        data["show_description"] = show
    return data


@pytest.mark.parametrize("tag,build,_h", TEMPLATES, ids=IDS)
def test_description_column_printed_only_when_ticked(tag, build, _h):
    on = build(_data(show=True))
    off = build(_data(show=False))
    assert "DESCX" in on
    if tag == "v7":
        # its item column is already headed «الوصف»; ticked, that head reads
        # «اسم الصنف» and the new column takes «الوصف»
        assert on.count('class="hcell"') == off.count('class="hcell"') + 1
        assert "اسم الصنف" in on and "اسم الصنف" not in off
    else:
        assert on.count("الوصف") > off.count("الوصف")     # the new column's head
    for html in (off, build(_data())):
        assert "DESCX" not in html


@pytest.mark.parametrize("tag,build,_h", TEMPLATES, ids=IDS)
def test_flag_off_matches_no_description_at_all(tag, build, _h):
    """Unticked, a line's description changes nothing in the output."""
    assert build(_data(show=False)) == build(_data(show=False, desc=""))


@pytest.mark.parametrize("tag,build,_h", TEMPLATES, ids=IDS)
def test_description_cell_sits_right_after_the_name_cell(tag, build, _h):
    html = build(_data(1, show=True))
    name_at = html.index(NAME)
    desc_at = html.index("DESCX", name_at)
    assert name_at < desc_at < html.index("حبة", name_at)     # name, description, unit


@pytest.mark.parametrize("tag,build,_h", TEMPLATES, ids=IDS)
def test_description_column_without_unit_column(tag, build, _h):
    html = build(_data(1, show=True, show_unit=False))
    assert "DESCX" in html and "حبة" not in html


@pytest.mark.parametrize("tag", IDS)
def test_table_width_kept_and_columns_wide_enough(tag):
    base, desc, name_i, desc_i, gap = WIDTHS[tag]
    assert len(desc) == len(base) + 1
    assert sum(desc) + gap * (len(desc) - 1) == sum(base) + gap * (len(base) - 1)
    assert desc[name_i] >= 70 and desc[desc_i] >= 90
    assert desc_i == name_i + 1


@pytest.mark.parametrize("tag,_b,height", TEMPLATES, ids=IDS)
def test_row_height_charges_the_description_cell(tag, _b, height):
    with_desc = with_print_descriptions(_data(1, show=True))[0]
    without = with_print_descriptions(_data(1, show=False))[0]
    blank = {**with_desc, "print_description": ""}

    assert with_desc["print_description"] and without["print_description"] == ""
    # column on: a long description is taller than the name alone, "" changes nothing
    assert height(with_desc, True) > height(without, True)
    assert height(blank, True) == height(without, True)
    longer = {**with_desc, "print_description": DESC + " " + DESC}
    assert height(longer, True) > height(with_desc, True)
    # column off: the legacy estimate, whatever the line carries
    assert height(with_desc) == height(without) == height(blank)
    assert height(with_desc, False) == height(without)


@pytest.mark.parametrize("tag,_b,height", TEMPLATES, ids=IDS)
def test_narrower_name_column_is_charged(tag, _b, height):
    """With the column on, the name wraps in its narrower column."""
    line = {"name": "اسم صنف طويل جدا يلتف على عدة أسطر داخل عمود الاسم الضيق " * 3,
            "code": "C-1", "print_description": ""}
    assert height(line, True) > height(line, False)


@pytest.mark.parametrize("tag,build,_h", TEMPLATES, ids=IDS)
def test_descriptions_push_rows_onto_more_sheets(tag, build, _h):
    """The paginator sees the taller rows: a long invoice with long descriptions
    runs onto more sheets ticked than unticked."""
    long_desc = DESC + " " + DESC
    off = build(_data(26, show=False, desc=long_desc)).count("<div data-sheet")
    on = build(_data(26, show=True, desc=long_desc)).count("<div data-sheet")
    assert on > off
