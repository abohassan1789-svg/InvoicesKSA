"""«إظهار وصف الصنف»: the native Phase-1 invoice designs (النموذج الأول→السادس in
``saudi_invoice_print_phase1``) print each line's description in its own «الوصف»
column, right after the item-name column, only when the flag is ticked."""

from __future__ import annotations

import datetime
import re
from decimal import Decimal

import pytest

from app.ui.screens import saudi_invoice_print_phase1 as phase1

_BUILDERS = ["build_phase1_invoice_html"] + [f"build_phase1_invoice_html_v{v}" for v in range(2, 7)]

_DESC = "وصف خاص بالطباعة <b>&</b>"
_DESC_ESCAPED = "وصف خاص بالطباعة &lt;b&gt;&amp;&lt;/b&gt;"
_NAME = "صنف الاختبار"


def _line(n: int, description: str | None) -> dict:
    return {
        "code": f"C-{n}", "name": f"{_NAME} {n}", "unit": "حبة", "qty": Decimal("2"),
        "price": Decimal("10.00"), "before": Decimal("20.00"), "vat_amount": Decimal("3.00"),
        "vat_rate": Decimal("15.00"), "total": Decimal("23.00"), "description": description,
    }


def _data(show: bool | None, description: str | None = f"  {_DESC}  ", *, show_unit: bool = True,
          second: bool = False) -> dict:
    lines = [_line(1, description)]
    if second:
        lines.append(_line(2, None))
    data = {
        "invoice_number": "INV-1", "issue_datetime": datetime.datetime(2026, 1, 5, 10, 30),
        "payment_label": "نقدي",
        "seller": {"name": "البائع", "name_en": "Seller", "address": "الرياض", "vat": "300000000000003",
                   "cr": "1010101010", "logo": None, "stamp": None},
        "customer": {"name": "العميل", "vat": "311111111100003", "cr": "2020202020", "address": "جدة"},
        "lines": lines,
        "totals": {"subtotal": Decimal("20.00"), "discount": Decimal("0"), "taxable": Decimal("20.00"),
                   "vat": Decimal("3.00"), "total": Decimal("23.00")},
        "show_unit": show_unit, "show_stamp": False, "qr_payload": "AQ1URVNU",
    }
    if show is not None:
        data["show_description"] = show
    return data


def _row_cells(out: str, name: str) -> list[str]:
    """The ``<td>`` contents of the item row holding ``name``."""
    start = out.rindex("<tr", 0, out.index(name))
    row = out[start:out.index("</tr>", start)]
    return re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)


@pytest.mark.parametrize("fn", _BUILDERS)
@pytest.mark.parametrize("show_unit", [True, False])
def test_description_gets_its_own_column_after_the_name(fn, show_unit):
    on = getattr(phase1, fn)(_data(True, show_unit=show_unit, second=True))
    off = getattr(phase1, fn)(_data(False, show_unit=show_unit, second=True))
    assert 'class="line-desc"' not in on  # not under the name any more
    assert re.search(r"<th[^>]*>الوصف(<span|</th>)", on)
    cells = _row_cells(on, f"{_NAME} 1")
    i = next(k for k, c in enumerate(cells) if f"{_NAME} 1" in c)
    assert _DESC not in cells[i] and _DESC_ESCAPED not in cells[i]
    assert cells[i + 1] == _DESC_ESCAPED  # trimmed + escaped, in the very next cell
    # A line without a description still gets its (empty) cell: one extra column per row.
    cells2 = _row_cells(on, f"{_NAME} 2")
    j = next(k for k, c in enumerate(cells2) if f"{_NAME} 2" in c)
    assert cells2[j + 1] == ""
    assert len(cells) == len(_row_cells(off, f"{_NAME} 1")) + 1


@pytest.mark.parametrize("fn", _BUILDERS)
@pytest.mark.parametrize("show", [False, None])
def test_description_hidden_when_flag_off(fn, show):
    build = getattr(phase1, fn)
    out = build(_data(show))
    assert "وصف خاص بالطباعة" not in out
    assert not re.search(r"<th[^>]*>الوصف(<span|</th>)", out)
    no_desc = _data(show)
    no_desc["lines"][0].pop("description")
    assert out == build(no_desc)


@pytest.mark.parametrize("fn", _BUILDERS)
def test_flag_on_with_blank_descriptions_shows_an_empty_column(fn):
    build = getattr(phase1, fn)
    for blank in (None, "", "   "):
        out = build(_data(True, blank))
        assert re.search(r"<th[^>]*>الوصف(<span|</th>)", out)
        cells = _row_cells(out, f"{_NAME} 1")
        i = next(k for k, c in enumerate(cells) if f"{_NAME} 1" in c)
        assert cells[i + 1] == ""


@pytest.mark.parametrize("fn", _BUILDERS)
def test_empty_invoice_placeholder_spans_the_extra_column(fn):
    build = getattr(phase1, fn)
    off, on = _data(False), _data(True)
    off["lines"], on["lines"] = [], []
    span_off = int(re.search(r'colspan="(\d+)">لا توجد أصناف|colspan="(\d+)" style', build(off)).group(0)
                   .split('"')[1])
    span_on = int(re.search(r'colspan="(\d+)">لا توجد أصناف|colspan="(\d+)" style', build(on)).group(0)
                  .split('"')[1])
    assert span_on == span_off + 1


@pytest.mark.parametrize(
    ("fn", "keep"),
    [
        ("build_phase1_invoice_html_v2", ".lower { break-inside: avoid"),
        ("build_phase1_invoice_html_v3", ".paybox { break-inside: avoid"),
        ("build_phase1_invoice_html_v5", "table.tot, .sign { break-inside: avoid"),
    ],
)
def test_totals_block_kept_whole_only_with_the_column(fn, keep):
    build = getattr(phase1, fn)
    assert keep in build(_data(True))
    assert keep not in build(_data(False))
