"""Printable Saudi tax-invoice document — **fourth template** (النموذج الرابع).

An *additional* invoice layout offered alongside النموذج الأول
(:mod:`app.ui.screens.saudi_invoice_print`), النموذج الثاني
(:mod:`app.ui.screens.saudi_invoice_print_v2`) and النموذج الثالث
(:mod:`app.ui.screens.saudi_invoice_print_v3`). It reproduces the approved
reference print supplied as ``نموذج جديد.pdf``: a fully right-to-left, minimal
layout — shaded «فاتورة ضريبية» title block top-left, logo top-right, four
blue-labelled meta rows, «مفوترة من / مفوترة إلى» party blocks over a grey rule,
a seven-column items table, then the QR and a label/value totals list.

Every coordinate below was measured off the reference PDF (Letter, 612.16 ×
792.06 pt) and converted to CSS pixels at 96 dpi (``pt × 4/3``), landing on the
same 816 × 1056 px design sheet the other templates use — so the existing
preview dialog and PDF exporter render it unchanged.

⚠️ Fonts are set through the ``<style>`` block, never through an inline
``style="… font-family:…"``. The font stacks contain double quotes, which close
the HTML attribute at the first one and silently drop every declaration after
it. This template used to do exactly that in eight places, and the whole page
consequently rendered as a single 12pt Arial in black: Calibri never applied,
the ``#1a2a6c`` label colour never applied, the title fell from 15.97pt to
12pt, and the items table from 9.99pt to 12pt — which also disabled
:func:`_fit_px` entirely. The eye could not see it because Arial and the
default sans are identical; only the extracted ``size`` showed it.

Long invoices paginate (user, 2026-07-23): the sheet holds seven item rows
beside the QR/totals band, and beyond that the rows run onto further sheets —
each a complete invoice page — with the band printed whole on the last one. It
used to be cut in half by the sheet's ``overflow:hidden`` instead. See
:mod:`app.ui.screens.invoice_pagination`.

Only :func:`build_invoice_html_v4` lives here — it consumes the very same
``data`` dict produced by
:meth:`SaudiSalesInvoicePage._collect_preview_data`.

Presentation only: no database access, no ZATCA cryptography.
"""

from __future__ import annotations

import datetime
import html
from decimal import Decimal
from typing import Any

from app.ui.screens.invoice_pagination import (
    FOOT_H,
    page_foot,
    paginate,
    row_height,
    sheet_style,
)
from app.ui.screens.saudi_invoice_print import (
    _asset_data_uri,
    _money,
    company_logo_data_uri,
    stamp_layout_reserve_px,
    stamp_overlay_html,
    QR_PRINT_PX,
    qr_vector_data_uri,
    with_print_descriptions,
)
from app.ui.screens.saudi_invoice_print_v2 import _vat_rate_display
from app.ui.screens.saudi_invoice_print_v3 import _fit_px, _rate, desc_cell_px, desc_estimate_text

# Design tokens measured off the reference PDF.
_GRID = "#242732"   # items-table border lines
_SHADE = "#deebf7"  # title block, party-label chips, table header fill
_LABEL = "#1a2a6c"  # the four meta labels — the only coloured text on the page
_RULE = "#d9d9d9"   # horizontal rule under the party blocks

_CALIBRI = 'Calibri, "Segoe UI", Arial, sans-serif'
_ARIAL = 'Arial, "Segoe UI", Tahoma, "Arial Unicode MS", sans-serif'

# Items-table columns in reading (right-to-left) order, widths in CSS px.
# Whole numbers (fractional tracks blur the grid lines) summing to exactly 730,
# the measured table width.
#
# Rebalanced away from the reference at the user's request. The reference gives
# قيمة الضريبة only 76px, which cannot hold 2,875,000.00 (77.8px) at the body
# font size, and leaves 375,000.00 with 2px of slack — so the figure ran into
# its own borders and read as if it had merged with the next column. الكمية,
# تفاصيل المنتج and % الضريبة were all far wider than their content needs, so
# their surplus went to the four money columns. Every money column now clears
# 12,345,678.90 with ~22px to spare, at one shared font size.
_COLUMNS: "tuple[tuple[str, int], ...]" = (
    ("تفاصيل المنتج", 78),
    ("الوحدة", 60),
    ("الكمية", 75),
    ("سعر الوحدة", 114),
    ("الإجمالى قبل الضريبة", 114),
    ("% الضريبة", 61),
    ("قيمة الضريبة", 114),
    ("الإجمالى شامل الضريبة", 114),
)

_NAME_COLUMN = 0  # تفاصيل المنتج — wraps and grows the row instead of shrinking
_UNIT_COLUMN = 1  # الوحدة — optional column, gated by data["show_unit"]
_META_PX = 15.97   # 11.98pt — labels, meta rows, totals
_TITLE_PX = 21.29  # 15.97pt — the «فاتورة ضريبية» title
_BODY_PX = 13.32  # the reference's own 9.99pt, shared by every items-table cell

# Measured table geometry, in CSS px. The sheet is RTL, so the table is placed
# by its RIGHT edge: the reference's right edge is at 577.0pt = 769.3px, which
# is 46.7px in from the 816px sheet.
_TABLE_RIGHT_MARGIN = 46.7
_HEAD_H = 38.3  # reference header row: 306.4..335.1pt = 28.7pt
_ROW_H = 47.9   # reference data row:   335.1..371.0pt = 35.9pt

# --- pagination (user, 2026-07-23) -----------------------------------------
# The sheet is a fixed 1056px with `overflow:hidden`, and the QR/totals band is
# the last thing on it — so on a nine-item invoice the band was pushed to
# y=1107 and Chromium sliced the QR in half. Nothing here compresses: rows keep
# the reference's 47.9px on every page and a long invoice simply runs onto more
# sheets, with the band whole on the last one.
_SHEET_H = 1056
_TABLE_TOP = 408.5      # the items block's own `top`
_BAND_GAP = 13.9        # table bottom -> QR/totals band
_BAND_H = QR_PRINT_PX   # the band is exactly as tall as the QR (see below)
_FOOT_H = FOOT_H     # the «صفحة x من y» strip, charged only when x/y > 1

_ROW_BUDGET = _SHEET_H - _TABLE_TOP - _HEAD_H                    # 609.2 -> 12 rows
_ROW_BUDGET_LAST = _ROW_BUDGET - _BAND_GAP - _BAND_H             # 379.3 ->  7 rows

# Name-column metrics, for the estimate of how tall a wrapping name makes a row:
# the column's 138px less its 3px cell padding each side, and the row's own
# padding (8.9 top / 2 bottom) plus its two 1px borders.
_NAME_W = _COLUMNS[_NAME_COLUMN][1] - 6
_NAME_LINE_H = 1.3
_ROW_CHROME = 8.9 + 2 + 2

# --- «الوصف» column (user, 2026-10-06) -------------------------------------
# With «إظهار وصف الصنف» ticked a «الوصف» column follows تفاصيل المنتج (to its
# left — the table is RTL). The table keeps its 730px: the name column keeps
# ≥ 70px and the description gets 100px, lent by the unit/qty/money columns
# (each money column still clears 1,234,567.89 at the body size). Unticked,
# _COLUMNS is used as-is.
_COLUMNS_DESC: "tuple[tuple[str, int], ...]" = (
    ("تفاصيل المنتج", 74),
    ("الوصف", 100),
    ("الوحدة", 52),
    ("الكمية", 62),
    ("سعر الوحدة", 96),
    ("الإجمالى قبل الضريبة", 96),
    ("% الضريبة", 58),
    ("قيمة الضريبة", 96),
    ("الإجمالى شامل الضريبة", 96),
)
_DESC_COLUMN = 1
_UNIT_COLUMN_DESC = 2
_HEAD_GROWTH_DESC = 1.0   # header-row growth allowance (measured +0.3px)
_NAME_W_DESC = _COLUMNS_DESC[_NAME_COLUMN][1] - 6
_DESC_W = _COLUMNS_DESC[_DESC_COLUMN][1] - 6


def _party_block(label: str, name: str, vat: str, address: str,
                 *, chip_left: float, chip_width: float, value_right: float) -> str:
    """One «مفوترة من / مفوترة إلى» block: a shaded chip plus three value rows."""
    rows = "".join(
        f'<div style="position:absolute; right:{value_right}px; top:{top}px; '
        f'max-width:240px; font-size:{_BODY_PX}px; line-height:1.25; '
        f'overflow-wrap:anywhere; word-break:break-word;">{value}</div>'
        for top, value in ((248.5, name), (277.2, vat), (306.0, address))
    )
    return (
        # The chip label is RIGHT-aligned in the reference (0.52pt of padding),
        # not centred — centring put it ~12pt out. The sheet is dir="rtl", so
        # flex-start is the right-hand edge.
        f'<div class="cal" style="position:absolute; left:{chip_left}px; top:236.9px; '
        f'width:{chip_width}px; height:23.1px; background:{_SHADE}; '
        f'display:flex; align-items:center; justify-content:flex-start; '
        f'padding-right:0.7px; font-size:{_META_PX}px;">{label}</div>'
        f"{rows}"
    )


def _meta_rows(rows: "tuple[tuple[str, str], ...]") -> str:
    """The four blue-labelled rows under the title block."""
    out = []
    for index, (label, value) in enumerate(rows):
        # 105.7, not 104.0: re-seated against the reference once the corrected
        # font sizes made the real ink positions measurable. Pitch 31.1 confirmed.
        top = 105.7 + index * 31.1
        out.append(
            f'<div class="lbl" style="position:absolute; right:415.3px; '
            f'top:{top + 2.1}px; font-size:{_META_PX}px; white-space:nowrap;">{label}</div>'
            f'<div style="position:absolute; right:540.4px; top:{top}px; '
            f'font-size:{_META_PX}px; white-space:nowrap;">{value}</div>'
        )
    return "".join(out)


def _colgroup_v4(show_unit: bool = True, columns=_COLUMNS, unit_col: int = _UNIT_COLUMN) -> str:
    return "".join(
        f'<col style="width:{w}px;">' for i, (_, w) in enumerate(columns) if show_unit or i != unit_col
    )


def _header_row(show_unit: bool = True, columns=_COLUMNS, unit_col: int = _UNIT_COLUMN) -> str:
    cells = "".join(
        # Tight line-height so the Arabic labels stay inside the reference's
        # 28.7pt header rather than forcing the row taller. The extra bottom
        # padding lifts the label ~1.9pt: the reference does not centre its
        # header text, it rides above the cell's middle.
        f'<th style="border:1px solid {_GRID}; background:{_SHADE}; padding:1px 3px 6px; '
        f'text-align:center; font-size:{_BODY_PX}px; '
        f'font-weight:700; line-height:1.15;">{label}</th>'
        for i, (label, _) in enumerate(columns)
        if show_unit or i != unit_col
    )
    return f'<tr style="height:{_HEAD_H}px;">{cells}</tr>'


def _item_rows_v4(lines: list[dict[str, Any]], show_unit: bool = True,
                  desc_column: bool = False) -> str:
    columns = _COLUMNS_DESC if desc_column else _COLUMNS
    unit_col = _UNIT_COLUMN_DESC if desc_column else _UNIT_COLUMN
    wrap_cols = (_NAME_COLUMN, _DESC_COLUMN) if desc_column else (_NAME_COLUMN,)
    rows: list[str] = []
    for line in lines:
        values = (
            html.escape(str(line.get("name") or "")),
            html.escape(str(line.get("unit") or "")),
            _money(line.get("qty")),
            _money(line.get("price")),
            _money(line.get("before")),
            _rate(line.get("vat_rate")),
            _money(line.get("vat_amount")),
            _money(line.get("total")),
        )
        if desc_column:
            values = (values[:_DESC_COLUMN]
                      + (html.escape(str(line.get("print_description") or "")),)
                      + values[_DESC_COLUMN:])
        cells = []
        for column, value in enumerate(values):
            if column == unit_col and not show_unit:
                continue
            width = columns[column][1]
            if column in wrap_cols:   # تفاصيل المنتج (and «الوصف» when printed)
                # Long names wrap and grow the row rather than shrinking their
                # own text, so the whole table keeps one font size.
                style = f"font-size:{_BODY_PX}px; line-height:1.3; word-wrap:break-word;"
            else:
                # Wide enough for any realistic figure; this guard only ever
                # engages to stop a freak value being silently clipped.
                style = (
                    f"font-size:{_fit_px(value, width, _BODY_PX)}px; white-space:nowrap;"
                )
            cells.append(
                # Top-aligned with the reference's own 8.9px inset: its 47.9px
                # row is far taller than 9.99pt text and it seats the figures
                # near the top, not centred. Top-aligning (rather than padding a
                # centred cell) also leaves a wrapped product name room to grow
                # inside the row instead of forcing it taller.
                f'<td style="border:1px solid {_GRID}; padding:8.9px 3px 2px; '
                f'vertical-align:top; text-align:center; {style}">{value}</td>'
            )
        rows.append(f'<tr style="height:{_ROW_H}px; background:#fff;">{"".join(cells)}</tr>')
    return "".join(rows)


# The reference does not space these rows evenly — the measured gaps are
# 28.7 / 30.2 / 27.2px. A uniform 28.7 left the third row 1.5px out, which only
# became visible once the font sizes were corrected.
_TOTALS_TOPS = (4.4, 33.1, 63.3, 90.5)


def _row_height_v4(line: dict[str, Any], desc_column: bool = False) -> float:
    """How tall this line's row will really be — see :mod:`invoice_pagination`.

    ``desc_column``: the «الوصف» column is printed — the name wraps in its
    narrower column and the description cell may be the taller one.
    """
    if not desc_column:
        return row_height(
            str(line.get("name") or ""),
            base=_ROW_H,
            width_px=_NAME_W,
            font_px=_BODY_PX,
            line_height=_NAME_LINE_H,
            chrome=_ROW_CHROME,
        )
    return max(
        row_height(desc_estimate_text(str(line.get("name") or "")), base=_ROW_H, width_px=_NAME_W_DESC,
                   font_px=_BODY_PX, line_height=_NAME_LINE_H, chrome=_ROW_CHROME),
        desc_cell_px(line, width_px=_DESC_W, font_px=_BODY_PX,
                     line_height=_NAME_LINE_H, chrome=_ROW_CHROME),
    )


def _totals_rows(rows: "tuple[tuple[str, str], ...]") -> str:
    out = []
    for index, (label, value) in enumerate(rows):
        top = _TOTALS_TOPS[index]
        out.append(
            f'<div class="cal" style="position:absolute; right:42.8px; top:{top}px; '
            f'font-size:{_META_PX}px; white-space:nowrap;">{label}</div>'
            f'<div style="position:absolute; right:223.6px; top:{top}px; '
            f'font-size:{_META_PX}px; white-space:nowrap;">{value}</div>'
        )
    return "".join(out)


def build_invoice_html_v4(data: dict[str, Any]) -> str:
    """Build the full printable invoice HTML for النموذج الرابع from live data."""
    # No fallback to the bundled default logo: a company with no stored logo prints
    # an empty logo slot, never someone else's brand (user request, 2026-09-14).
    logo = company_logo_data_uri(data.get("seller"))
    qr = qr_vector_data_uri(data.get("qr_payload"))

    invoice_number = html.escape(str(data.get("invoice_number") or ""))
    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        created = issued.strftime("%d-%m-%Y %H:%M:%S")
        issue_date = issued.strftime("%d-%m-%Y")
    else:
        created = issue_date = html.escape(str(issued or ""))

    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    # Lines with their resolved «وصف الصنف»; the same list feeds the paginator's
    # height estimate and the row renderer.
    lines = with_print_descriptions(data)

    # «الوحدة» column is optional; default on when the flag is absent (old
    # callers/tests). When off, the header th, the colgroup <col> and every body
    # <td> are dropped together and the fixed-layout table reclaims the width.
    show_unit = bool(data.get("show_unit", True))
    # «إظهار وصف الصنف»: print the «الوصف» column (see _COLUMNS_DESC).
    show_desc = bool(data.get("show_description"))
    if show_desc:
        table_head = (
            f'<colgroup>{_colgroup_v4(show_unit, _COLUMNS_DESC, _UNIT_COLUMN_DESC)}</colgroup>\n'
            f'      <thead>{_header_row(show_unit, _COLUMNS_DESC, _UNIT_COLUMN_DESC)}</thead>'
        )
    else:
        table_head = (
            f'<colgroup>{_colgroup_v4(show_unit)}</colgroup>\n'
            f'      <thead>{_header_row(show_unit)}</thead>'
        )

    location = html.escape(str(data.get("location") or "الموقع الرئيسي"))
    subtotal = totals.get("subtotal", 0)
    discount = totals.get("discount", 0)
    taxable = totals.get("taxable", Decimal(str(subtotal)) - Decimal(str(discount)))
    vat_total = totals.get("vat", 0)
    grand_total = totals.get("total", 0)
    vat_rate = _vat_rate_display(taxable, vat_total, lines)

    logo_html = (
        f'<img src="{logo}" alt="logo" style="position:absolute; left:574.4px; '
        f'top:55.1px; width:144px; height:143.5px; object-fit:contain;" />'
        if logo
        else ""
    )

    # ---- the page furniture, identical on every sheet ----------------------
    # Built once and interpolated into each page: a continuation page is a full
    # invoice page (title, logo, meta, both parties), not a bare table, so any
    # sheet of a multi-page invoice identifies the invoice it belongs to.
    header_html = f"""
  <!-- ============ TITLE BLOCK ============ -->
  <div class="cal" style="position:absolute; left:36px; top:55.1px; width:365.5px; height:38.3px; background:{_SHADE}; display:flex; align-items:center; justify-content:center; font-size:{_TITLE_PX}px;">فاتورة ضريبية</div>

  <!-- ============ LOGO ============ -->
  {logo_html}

  <!-- ============ META ROWS ============ -->
  {_meta_rows((
      ("رقم الفاتورة", invoice_number),
      ("تاريخ / وقت الإنشاء", created),
      ("تاريخ الإصدار", issue_date),
      ("الموقع", location),
  ))}

  <!-- ============ PARTY BLOCKS ============ -->
  {_party_block(
      "مفوترة من :",
      html.escape(str(seller.get("name") or "")),
      html.escape(str(seller.get("vat") or "")),
      html.escape(str(seller.get("address") or "")),
      chip_left=670.4, chip_width=97.9, value_right=154.9,
  )}
  {_party_block(
      "مفوترة إلى :",
      html.escape(str(customer.get("name") or "")),
      html.escape(str(customer.get("vat") or "")),
      html.escape(str(customer.get("address") or "")),
      chip_left=314.8, chip_width=88.3, value_right=512.3,
  )}

  <!-- ============ RULE ============ -->
  <div style="position:absolute; left:36px; top:380.1px; width:732.5px; height:2.5px; background:{_RULE};"></div>
"""

    # 13.9px, not the 11.6px measured off the reference's gap: correcting the
    # font sizes shortened the header row to its intended height, which lifted
    # this whole block (QR + totals) ~2.3px. Re-measured against the reference
    # and re-seated here — every totals row and the QR now land within 1.2pt.
    #
    # The band is as tall as the QR itself (QR_PRINT_PX). The totals rows are
    # right-anchored and the QR sits far left (55..271 vs totals from ~500), so
    # the two never meet. It prints on the LAST sheet only, and _ROW_BUDGET_LAST
    # guarantees that sheet's rows leave it the room it needs.
    band_html = f"""
    <div style="position:relative; margin-top:{_BAND_GAP}px; height:{_BAND_H}px;">
      <img src="{qr}" alt="QR" style="position:absolute; left:55.1px; top:0; width:{QR_PRINT_PX}px; height:{QR_PRINT_PX}px; background:#ffffff;" />
       {_totals_rows((
           ("إجمالي القيمة بدون الضريبة", _money(subtotal)),
           ("خصم الفاتورة", _money(discount)),
           (f"ضريبة القيمة المضافة {vat_rate}%", _money(vat_total)),
           ("الإجمالي شامل الضريبة", _money(grand_total)),
       ))}
    </div>"""

    # With «الوصف» on, the narrower money heads wrap to two lines and the header
    # row renders ~0.3px over its 38.3px design height; charge it to the budgets.
    head_extra = _HEAD_GROWTH_DESC if show_desc else 0
    pages = paginate(
        lines, (lambda ln: _row_height_v4(ln, True)) if show_desc else _row_height_v4,
        budget=_ROW_BUDGET - head_extra,
        budget_last=_ROW_BUDGET_LAST - stamp_layout_reserve_px(data) - head_extra,
        foot=_FOOT_H,
    )
    sheets = []
    for index, page_lines in enumerate(pages, start=1):
        last = index == len(pages)
        foot = page_foot(index, len(pages), sheet_h=_SHEET_H, colour="#5b5f6b")
        sheets.append(f"""
<div data-sheet dir="rtl" style="position:relative; width:816px; height:{_SHEET_H}px; margin:24px auto; background:#fff; font-weight:700; overflow:hidden; {sheet_style(last=last)}">
{header_html}
  <!-- ============ ITEMS TABLE + BOTTOM BAND ============ -->
  <div style="position:absolute; left:0; top:{_TABLE_TOP}px; width:816px;">

    <table style="margin-right:{_TABLE_RIGHT_MARGIN}px; width:730px; border-collapse:collapse; table-layout:fixed;">
      {table_head}
      <tbody>{_item_rows_v4(page_lines, show_unit, show_desc)}</tbody>
    </table>
{band_html + stamp_overlay_html(data) if last else ""}
  </div>
{foot}
</div>""")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    background: #53565a;
    font-family: {_ARIAL};
    color: #000;
    -webkit-font-smoothing: antialiased;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  /* Fonts live here, never inline: the stacks contain double quotes, which
     would close an inline style attribute and drop what follows. */
  .cal {{ font-family: {_CALIBRI}; }}
  .lbl {{ font-family: {_CALIBRI}; color: {_LABEL}; }}
  @media print {{
    body {{ background: #fff; }}
    [data-sheet] {{ box-shadow: none !important; margin: 0 !important; }}
  }}
</style>
</head>
<body>
{"".join(sheets)}
</body>
</html>"""


__all__ = ["build_invoice_html_v4"]
