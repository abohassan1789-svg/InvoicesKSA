"""Phase-1 sales-invoice print template (المرحلة الأولى — النموذج الأول).

A standalone, Arabic-first (RTL) printable «فاتورة مبيعات» for the new
«مرحلة أولى» action on the Saudi sales-invoice screen. It is deliberately kept
**separate** from the eight Phase-2 templates (``saudi_invoice_print`` +
``saudi_invoice_print_v2..v8``): none of those files are modified here, and the
only layout borrowed from them is Phase-2's «النموذج الثامن», offered on the
Phase-1 picker as «النموذج السابع» with the Phase-1 tags 1–5 QR
(:func:`build_phase1_invoice_html_v7`). Otherwise only the small, shared,
side-effect-free helpers
(:func:`company_logo_data_uri`, :func:`qr_vector_data_uri`,
:func:`stamp_overlay_html`, money/qty formatters, the QR print size) are reused
so the QR and logo behave identically everywhere.

Design: the approved «النموذج السادس» warm-amber sheet, retitled to «فاتورة
مبيعات» (no «ضريبية»/«مبسطة»), with the seller's company data (name, VAT,
commercial registration, address) on one side of the header and the company
logo on the other. All party/line/total values come from the same
``_collect_preview_data`` dict every template already consumes, so preview,
print and PDF share one data shape.
"""

from __future__ import annotations

import datetime
import html
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QPageSize
from PySide6.QtWidgets import QMessageBox, QWidget

from app.services import saudi_zatca_generator as zatca_gen
from app.ui.screens.saudi_invoice_print import (
    _ASSETS_DIR,
    QR_PRINT_PX_V1,
    SaudiInvoicePreviewDialog,
    _money,
    _qty,
    build_invoice_html,
    company_logo_data_uri,
    export_invoice_to_pdf,
    qr_vector_data_uri,
    stamp_overlay_html,
    with_print_descriptions,
)
# «مرحلة أولى» now mirrors the Phase-2 picker exactly (user request 2026-08-22):
# the eight Phase-2 native layouts (النموذج الأول→الثامن) are offered in Phase-1
# too, each re-QR'd with the Phase-1 tags 1–5 code — see the
# :func:`build_phase1_p2_model1`…`_model7` wrappers below and the pre-existing
# :func:`build_phase1_invoice_html_v7` (which is Phase-2's النموذج الثامن).
from app.ui.screens.saudi_invoice_print_v2 import build_invoice_html_v2
from app.ui.screens.saudi_invoice_print_v3 import build_invoice_html_v3
from app.ui.screens.saudi_invoice_print_v4 import build_invoice_html_v4
from app.ui.screens.saudi_invoice_print_v5 import build_invoice_html_v5
from app.ui.screens.saudi_invoice_print_v6 import build_invoice_html_v6
from app.ui.screens.saudi_invoice_print_v7 import build_invoice_html_v7
from app.ui.screens.saudi_invoice_print_v8 import build_invoice_html_v8
from app.ui.screens.saudi_invoice_print_v9 import build_invoice_html_v9
from app.ui.screens.saudi_invoice_print_v10 import build_invoice_html_v10
from app.ui.screens.saudi_invoice_print_v11 import build_invoice_html_v11
from app.ui.screens.saudi_invoice_print_v12 import build_invoice_html_v12
from app.ui.screens.saudi_invoice_print_v13 import build_invoice_html_v13
from app.ui.screens.saudi_invoice_print_v14 import build_invoice_html_v14
from app.ui.screens.saudi_invoice_print_v15 import build_invoice_html_v15
from app.ui.screens.saudi_invoice_print_v16 import build_invoice_html_v16
from app.ui.screens.saudi_invoice_print_v17 import build_invoice_html_v17
from app.ui.screens.saudi_invoice_print_v18 import build_invoice_html_v18
from app.ui.screens.saudi_invoice_print_v19 import build_invoice_html_v19
from app.ui.screens.saudi_invoice_print_v20 import build_invoice_html_v20
from app.ui.screens.saudi_invoice_print_v21 import build_invoice_html_v21
from app.ui.screens.saudi_invoice_print_v22 import build_invoice_html_v22
from app.ui.screens.saudi_invoice_print_v23 import build_invoice_html_v23
from app.ui.screens.saudi_invoice_print_v24 import build_invoice_html_v24
from app.ui.screens.saudi_invoice_print_v25 import build_invoice_html_v25
from app.ui.screens.saudi_invoice_print_v26 import build_invoice_html_v26
from app.ui.screens.saudi_invoice_print_v27 import build_invoice_html_v27

# Warm-amber identity (النموذج السادس).
_BROWN = "#7c2d12"
_AMBER = "#b45309"
_PANEL = "#fdf6ec"
_LINE = "#e7cfa6"
_LINE_SOFT = "#f0e6d5"

# Static stylesheet. Kept as a plain (non f-string) constant so its CSS braces
# never have to be doubled, and so the font-family lives here once — not inline —
# avoiding the inline font-family quote trap that has silently killed typography
# on other templates. The .page table wrapper reproduces النموذج الأول's
# per-page margin technique so a long invoice paginates instead of clipping.
_CSS = """
  html, body { margin: 0; padding: 0; }
  body { background: #e9e9ea; -webkit-print-color-adjust: exact; print-color-adjust: exact;
    font-family: 'Tajawal', 'Cairo', 'Segoe UI', 'Tahoma', 'Arial', sans-serif; color: #241a10; }
  .sheet { box-sizing: border-box; width: 816px; min-height: 1056px; margin: 24px auto;
    background: #ffffff; padding: 0 44px; box-shadow: 0 6px 28px rgba(0,0,0,.16); direction: rtl; }
  tr, .keep { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .page { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .page > tbody > tr > td { padding: 0; vertical-align: top; }
  .page > thead > tr > td, .page > tfoot > tr > td { padding: 0; font-size: 0; line-height: 0; }
  .page-top { height: 30px; }
  .page-bottom { height: 44px; }

  .hdr { display: flex; justify-content: space-between; align-items: flex-start; gap: 26px; }
  .co-name { font-size: 27px; font-weight: 800; color: #7c2d12; letter-spacing: -.2px; }
  .co-lines { margin-top: 9px; display: grid; gap: 5px; font-size: 13.5px; }
  .co-lines .row { display: flex; gap: 7px; }
  .co-lines .k { color: #b45309; font-weight: 700; white-space: nowrap; }
  .co-lines .v { color: #3a2a1a; min-width: 0; overflow-wrap: anywhere; }
  .logo-box { flex: none; width: 165px; height: 135px; border: 1.5px solid #e7cfa6;
    border-radius: 16px; background: linear-gradient(160deg, #fdf7ec, #fbeed7);
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
  .logo-box svg { width: 58px; height: 58px; }
  .logo-box span { font-size: 12px; color: #b0855a; font-weight: 700; }
  .logo-img { max-height: 135px; max-width: 210px; width: auto; height: auto;
    object-fit: contain; display: block; }

  .rule { height: 2px; background: linear-gradient(90deg, #b45309, #e7cfa6 70%, transparent);
    margin: 18px 0 15px; }
  .title { text-align: center; margin-bottom: 16px; }
  .title h2 { display: inline-block; margin: 0; font-size: 24px; font-weight: 800; color: #7c2d12;
    letter-spacing: .5px; padding: 5px 34px; border: 1.5px solid #e7cfa6; border-radius: 26px;
    background: #fdf6ec; }

  .meta { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 7px 32px; font-size: 14px;
    margin-bottom: 16px; }
  .meta .cell { display: flex; gap: 8px; }
  .meta .k { color: #b45309; font-weight: 700; white-space: nowrap; }
  .meta .v { color: #241a10; min-width: 0; overflow-wrap: anywhere; }

  table.items { width: 100%; border-collapse: collapse; }
  table.items thead th { background: #fdf6ec; color: #7c2d12; font-size: 13.5px; font-weight: 800;
    padding: 9px 10px; border-top: 1.5px solid #e7cfa6; border-bottom: 1.5px solid #e7cfa6; }
  table.items tbody td { padding: 8px 10px; font-size: 13px; border-bottom: 1px solid #f0e6d5;
    vertical-align: middle; }
  .c-name { text-align: right; font-weight: 700; color: #1f150c; overflow-wrap: anywhere; }
  .c-num { text-align: center; font-variant-numeric: tabular-nums; }

  .sum { display: flex; justify-content: space-between; align-items: flex-end; gap: 22px;
    margin-top: 20px; }
  .qr-wrap { text-align: center; }
  .qr-wrap img { width: 150px; height: 150px; display: block; background: #ffffff; }
  .qr-wrap .cap { font-size: 11px; color: #b0855a; margin-top: 4px; }
  .tot { min-width: 54%; border: 1px solid #e7cfa6; border-radius: 9px; overflow: hidden; }
  .tot .line { display: flex; justify-content: space-between; padding: 8px 15px; font-size: 14px; }
  .tot .line:not(:last-child) { border-bottom: 1px solid #f0e6d5; }
  .tot .grand { background: #7c2d12; color: #ffffff; font-weight: 800; font-size: 16px; }

  .foot { margin-top: 24px; padding-top: 13px; border-top: 1px solid #f0e6d5;
    text-align: center; color: #a06a2a; font-size: 12.5px; }
  @media print {
    body { background: #ffffff; }
    .sheet { margin: 0; box-shadow: none; width: 100%; min-height: 0; }
  }
"""

# A simple hexagon-and-bars emblem, drawn only when the company has no stored
# logo, so the header stays balanced instead of leaving an empty gap.
_LOGO_PLACEHOLDER = (
    '<div class="logo-box">'
    '<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M24 4l17 10v20L24 44 7 34V14L24 4z" stroke="#b45309" stroke-width="2.4" '
    'stroke-linejoin="round"/>'
    '<path d="M24 14v20M15 19v14M33 19v14" stroke="#c9924e" stroke-width="2.4" '
    'stroke-linecap="round"/></svg>'
    "<span>شعار الشركة</span></div>"
)


def _phase1_qr_payload(data: dict[str, Any]) -> str | None:
    """Build the **Phase-1** QR: tags 1–5 ONLY (seller name, VAT number, timestamp,
    total incl. VAT, VAT amount).

    The Phase-1 «فاتورة مبيعات» must NOT carry the Phase-2 cryptographic tags
    (6–9: hash, signature, public key, stamp) — those are what make the ZATCA
    Fatoora app report «متوافق مع المرحلة الثانية». So this deliberately ignores
    any ``data["qr_payload"]`` (which the screen resolves as the full signed
    Phase-2 payload) and re-derives a clean tags 1–5 code from the invoice facts.
    """
    seller = data.get("seller") or {}
    totals = data.get("totals") or {}
    issued = data.get("issue_datetime")
    timestamp = issued if isinstance(issued, datetime.datetime) else datetime.datetime.now()
    try:
        return zatca_gen.build_qr(
            seller_name=str(seller.get("name") or ""),
            vat_number=str(seller.get("vat") or ""),
            timestamp=timestamp,
            total_with_vat=totals.get("total", 0),
            vat_total=totals.get("vat", 0),
        )
    except Exception:  # noqa: BLE001 - QR is best-effort; never block the print
        return None


def _phase1_qr_uri(data: dict[str, Any]) -> str | None:
    """QR data-URI for a Phase-1 layout.

    Default: the clean Phase-1 tags 1–5 code from :func:`_phase1_qr_payload`. But
    when one of these designs is reused from the **Phase-2** invoice screen
    (``data["use_phase2_qr"]`` set and the screen's signed payload present), print
    the full tags 1–9 payload instead, so the very same layout comes out «متوافق مع
    المرحلة الثانية». The Phase-1 «مرحلة أولى» flow never sets the flag, so it keeps
    its tags 1–5 code untouched.
    """
    if data.get("use_phase2_qr") and data.get("qr_payload"):
        return qr_vector_data_uri(data["qr_payload"])
    return qr_vector_data_uri(_phase1_qr_payload(data))


def _company_line(label: str, value: str) -> str:
    """One «key: value» row of the seller block, or ``""`` when value is empty."""
    value = (value or "").strip()
    if not value:
        return ""
    return (
        f'<div class="row"><span class="k">{html.escape(label)}:</span>'
        f'<span class="v">{html.escape(value)}</span></div>'
    )


def _meta_cell(label: str, value: str, span2: bool = False) -> str:
    span = ' style="grid-column: span 2;"' if span2 else ""
    return (
        f'<div class="cell"{span}><span class="k">{html.escape(label)}:</span>'
        f'<span class="v">{html.escape(value)}</span></div>'
    )


# «الوصف» rows run taller, and in these designs (النموذج الثاني/الثالث/الخامس) the
# QR + totals block — which has no `.keep` wrapper of its own — then splits across
# a page break (a render sweep over 1–35 lines showed it). With the column on, keep
# that block whole; never emitted for an unticked invoice, whose HTML is unchanged.
_DESC_KEEP_V2 = " .lower { break-inside: avoid; page-break-inside: avoid; }"
_DESC_KEEP_V3 = " .paybox { break-inside: avoid; page-break-inside: avoid; }"
_DESC_KEEP_V5 = (
    " table.tot, .sign { break-inside: avoid; page-break-inside: avoid; }"
    " table.it { table-layout: fixed; }"
)
# النموذج السادس's items table is auto-layout; with «الوصف» it is pinned to the
# header widths so the name/description columns are not squeezed.
_DESC_FIXED_V6 = " table.items { table-layout: fixed; }"


def _desc_cell(line: dict[str, Any], cls: str) -> str:
    """The «الوصف» cell (``print_description``, see :func:`with_print_descriptions`)
    styled with the name cell's ``cls``; empty for a line without a description."""
    return f'<td class="{cls}">{html.escape(str(line.get("print_description") or ""))}</td>'


def _item_rows(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """Item rows: الصنف (wraps + grows) · [الوصف] · الكمية · السعر · الإجمالي (before VAT)."""
    if not lines:
        return (
            f'<tr><td colspan="{6 if show_desc else 5}" style="text-align:center; padding:20px; color:#999; '
            'font-size:13px;">لا توجد أصناف</td></tr>'
        )
    rows: list[str] = []
    for line in lines:
        name = html.escape(str(line.get("name") or ""))
        unit_cell = (
            f'<td class="c-num">{html.escape(str(line.get("unit") or ""))}</td>'
            if show_unit
            else ""
        )
        rows.append(
            "<tr>"
            f'<td class="c-name">{name}</td>'
            f'{_desc_cell(line, "c-name") if show_desc else ""}'
            f'{unit_cell}'
            f'<td class="c-num">{_qty(line.get("qty"))}</td>'
            f'<td class="c-num">{_money(line.get("price"))}</td>'
            f'<td class="c-num">{_money(line.get("before"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def _discount_and_taxable(totals: dict[str, Any]) -> tuple[Any, Any]:
    """Return ``(discount_amount, taxable_after_discount)`` for a totals block.

    Tolerates legacy invoices saved before the invoice-level discount existed:
    when ``taxable`` is absent it falls back to ``subtotal - discount`` (and to
    ``subtotal`` if either value cannot be parsed).
    """
    subtotal = totals.get("subtotal", 0)
    discount = totals.get("discount", 0)
    taxable = totals.get("taxable")
    if taxable is None:
        try:
            taxable = Decimal(str(subtotal)) - Decimal(str(discount))
        except Exception:  # noqa: BLE001 - retain a printable legacy-invoice fallback
            taxable = subtotal
    return discount, taxable


def build_phase1_invoice_html(data: dict[str, Any]) -> str:
    """Build the printable «فاتورة مبيعات» HTML for the Phase-1 template."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))
    # «إظهار وصف الصنف»: a «الوصف» column right after الصنف, carved out of its width.
    show_desc = bool(data.get("show_description"))
    discount, taxable = _discount_and_taxable(totals)

    logo = company_logo_data_uri(seller)
    logo_html = (
        f'<img class="logo-img" src="{logo}" alt="logo">' if logo else _LOGO_PLACEHOLDER
    )
    # Phase-1 QR: tags 1–5 by default; the full signed tags 1–9 when this design
    # is rendered from the Phase-2 screen (see _phase1_qr_uri).
    qr = _phase1_qr_uri(data)

    company_lines = "".join(
        (
            _company_line("الرقم الضريبي", str(seller.get("vat") or "")),
            _company_line("السجل التجاري", str(seller.get("cr") or "")),
            _company_line("العنوان", str(seller.get("address") or "")),
        )
    )

    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        issue_date = issued.strftime("%d-%m-%Y")
    else:
        issue_date = str(issued or "")

    customer_name = str(customer.get("name") or "").strip() or "عميل نقدي"
    meta_html = "".join(
        (
            _meta_cell("رقم الفاتورة", str(data.get("invoice_number") or "")),
            _meta_cell("التاريخ", issue_date),
            _meta_cell("طريقة الدفع", str(data.get("payment_label") or "")),
            _meta_cell("العميل", customer_name),
            _meta_cell("الرقم الضريبي للعميل", str(customer.get("vat") or "")),
            _meta_cell("السجل التجاري للعميل", str(customer.get("cr") or "")),
            _meta_cell("عنوان العميل", str(customer.get("address") or ""), span2=True),
        )
    )

    stamp_overlay = stamp_overlay_html(data)

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
  <div class="sheet">
  <table class="page">
    <thead><tr><td class="page-top"></td></tr></thead>
    <tfoot><tr><td class="page-bottom"></td></tr></tfoot>
    <tbody><tr><td>

    <div class="hdr">
      <div class="company">
        <div class="co-name">{html.escape(str(seller.get("name") or ""))}</div>
        <div class="co-lines">{company_lines}</div>
      </div>
      {logo_html}
    </div>

    <div class="rule"></div>
    <div class="title"><h2>فاتورة مبيعات</h2></div>

    <div class="meta">{meta_html}</div>

    <table class="items">
      <thead>
        <tr>
          {'<th style="width:22%;">الصنف</th><th style="width:18%;">الوصف</th>' if show_desc else '<th style="width:40%;">الصنف</th>'}
          {'<th style="width:12%;">الوحدة</th>' if show_unit else ''}
          <th style="width:14%;">الكمية</th>
          <th style="width:16%;">السعر</th>
          <th style="width:18%;">الإجمالي</th>
        </tr>
      </thead>
      <tbody>{_item_rows(lines, show_unit, show_desc)}</tbody>
    </table>

    <div class="keep">
      <div class="sum">
        <div class="qr-wrap"><img src="{qr}" alt="QR"><div class="cap">رمز الاستجابة السريعة</div></div>
        <div class="tot">
          <div class="line"><span>الإجمالي قبل الخصم</span><span>{_money(totals.get("subtotal", 0))}</span></div>
          <div class="line"><span>قيمة الخصم</span><span>{_money(discount)}</span></div>
          <div class="line"><span>الإجمالي بعد الخصم</span><span>{_money(taxable)}</span></div>
          <div class="line"><span>قيمة الضريبة</span><span>{_money(totals.get("vat", 0))}</span></div>
          <div class="line grand"><span>الإجمالي بعد الضريبة</span><span>{_money(totals.get("total", 0))} ريال</span></div>
        </div>
      </div>
      {stamp_overlay}
      <div class="foot">نشكر لكم تعاملكم معنا — {html.escape(str(seller.get("name") or ""))}</div>
    </div>

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


# ======================================================================
# Shared bits for the multi-column / 7-column templates (النموذج الثاني+الثالث)
# ======================================================================
# A monoline emblem inheriting its colour from the surrounding chip (currentColor),
# drawn only when the company has no stored logo.
_EMBLEM_SVG = (
    '<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M24 4l17 10v20L24 44 7 34V14L24 4z" stroke="currentColor" stroke-width="2.4" '
    'stroke-linejoin="round"/>'
    '<path d="M24 14v20M15 19v14M33 19v14" stroke="currentColor" stroke-width="2.2" '
    'stroke-linecap="round" opacity=".6"/></svg>'
)


def _logo_inner(seller: dict[str, Any]) -> str:
    """The logo chip's inner: the real DB logo if present, else the emblem."""
    uri = company_logo_data_uri(seller)
    if uri:
        return f'<img src="{uri}" alt="logo">'
    return _EMBLEM_SVG


def _item_rows_7(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """7-column rows: مسلسل · اسم الصنف · [الوصف] · الكمية · السعر · الإجمالي · الضريبة · بعد الضريبة."""
    if not lines:
        return f'<tr><td class="empty" colspan="{9 if show_desc else 8}">لا توجد أصناف</td></tr>'
    rows: list[str] = []
    for index, line in enumerate(lines, start=1):
        name = html.escape(str(line.get("name") or ""))
        unit_cell = (
            f"<td>{html.escape(str(line.get('unit') or ''))}</td>" if show_unit else ""
        )
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f'<td class="name">{name}</td>'
            f'{_desc_cell(line, "name") if show_desc else ""}'
            f"{unit_cell}"
            f"<td>{_qty(line.get('qty'))}</td>"
            f"<td>{_money(line.get('price'))}</td>"
            f"<td>{_money(line.get('before'))}</td>"
            f"<td>{_money(line.get('vat_amount'))}</td>"
            f"<td>{_money(line.get('total'))}</td>"
            "</tr>"
        )
    return "".join(rows)


def _phase1_ctx(data: dict[str, Any]) -> dict[str, str]:
    """Escaped, ready-to-embed strings shared by the 7-column templates."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))
    issued = data.get("issue_datetime")
    issue_date = (
        issued.strftime("%d-%m-%Y") if isinstance(issued, datetime.datetime) else str(issued or "")
    )
    _disc, _tax = _discount_and_taxable(totals)
    return {
        "co_name": html.escape(str(seller.get("name") or "")),
        "co_vat": html.escape(str(seller.get("vat") or "")),
        "co_cr": html.escape(str(seller.get("cr") or "")),
        "co_addr": html.escape(str(seller.get("address") or "")),
        "cu_name": html.escape(str(customer.get("name") or "").strip() or "عميل نقدي"),
        "cu_vat": html.escape(str(customer.get("vat") or "")),
        "cu_cr": html.escape(str(customer.get("cr") or "")),
        "cu_addr": html.escape(str(customer.get("address") or "")),
        "inv_no": html.escape(str(data.get("invoice_number") or "")),
        "inv_date": html.escape(issue_date),
        "pay": html.escape(str(data.get("payment_label") or "")),
        "rows": _item_rows_7(lines, show_unit, show_desc),
        "logo": _logo_inner(seller),
        "qr": _phase1_qr_uri(data),
        "t_before": _money(totals.get("subtotal", 0)),
        "t_discount": _money(_disc),
        "t_taxable": _money(_tax),
        "t_vat": _money(totals.get("vat", 0)),
        "t_after": _money(totals.get("total", 0)),
    }


# ---- النموذج الثاني : أزرق عصري — «فاتورة ضريبية» (مرجع: فاتورة15.05.2026.pdf) ----
# Approved by the user on 2026-08-06. The design was pixel-/geometry-measured off
# the reference PDF with PyMuPDF. It is laid out on the same 816×1056 Letter sheet
# every template prints through (the reference is A4, but the shared Phase-1
# preview/PDF/print pipeline pins Letter via `_page_layout`, so the vertical
# rhythm was trimmed to clear the shorter page). Kept as a plain (non f-string)
# constant so the CSS braces are never doubled and the font-family lives here once,
# never inline — the trap that has silently killed typography on other templates.
# The QR box is sized to QR_PRINT_PX_V1 (192px) so the printed code still scans.
_CSS_V2 = """
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: #EFF9FF; -webkit-print-color-adjust: exact; print-color-adjust: exact;
    font-family: 'Tajawal','Dubai','Cairo','Segoe UI','Tahoma','Arial',sans-serif; color: #243746; }

  /* Flowing sheet: a long invoice paginates instead of clipping. `keep`/`tr` never
     split a row or the totals block; the items table's real <thead> (the blue bar)
     is a table-header-group, so Chromium repeats it on every continuation page. The
     page-top/page-bottom spacers live in the OUTER table's <thead>/<tfoot>, so the
     pale print margin applies to every page (a zero-margin QPageLayout is handed to
     printToPdf, so a CSS @page margin would not win). */
  tr, .keep { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .page { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .page > tbody > tr > td { padding: 0; vertical-align: top; }
  .page > thead > tr > td, .page > tfoot > tr > td { padding: 0; font-size: 0; line-height: 0; }
  .page-top { height: 20px; }
  .page-bottom { height: 26px; }

  .card { background: #fff; border-radius: 24px; box-shadow: 0 10px 40px rgba(3,120,190,.10); }

  .header { background: linear-gradient(90deg, #0790C8 0%, #0079BF 100%);
    border-top-left-radius: 24px; border-top-right-radius: 24px;
    padding: 16px 30px; display: flex; align-items: center; justify-content: space-between; }
  .h-title { text-align: right; color: #fff; }
  .h-title .en { font-size: 12px; letter-spacing: 3px; font-weight: 600; opacity: .85; }
  .h-title .ar { font-size: 30px; font-weight: 800; margin-top: 2px; }
  .h-right { display: flex; align-items: center; gap: 16px; }
  .logo { width: 78px; height: 78px; border-radius: 20px; background: #fff; display: flex;
    align-items: center; justify-content: center; box-shadow: 0 6px 16px rgba(0,0,0,.15);
    overflow: hidden; color: #125FA8; }
  .logo img, .logo svg { max-width: 64px; max-height: 64px; width: auto; height: auto;
    object-fit: contain; display: block; }
  .metabox { background: rgba(255,255,255,.14); border-radius: 16px; padding: 12px 20px; min-width: 300px; }
  .metarow { display: flex; align-items: center; gap: 8px; color: #fff; font-size: 14px; padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,.28); }
  .metarow:last-child { border-bottom: none; }
  .metarow .lbl { font-weight: 600; opacity: .92; }
  .metarow .val { font-weight: 800; }

  .body { padding: 20px 30px 18px; }
  .parties { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; }
  .party { background: #F5FBFE; border: 1px solid #DCEBF6; border-radius: 18px; padding: 11px 16px 12px; }
  .party h3 { color: #0E7CC0; font-size: 16px; font-weight: 800; text-align: right; margin: 0 0 9px; }
  .prow { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
  .prow:last-child { margin-bottom: 0; }
  .prow .k { width: 96px; color: #65839A; font-size: 12.5px; font-weight: 600; text-align: right; flex: none; }
  .prow .v { flex: 1; min-width: 0; background: #fff; border: 1px solid #E1EDF5; border-radius: 11px;
    padding: 8px 12px; font-size: 12.5px; font-weight: 700; text-align: right;
    box-shadow: 0 2px 5px rgba(3,120,190,.05); white-space: normal; overflow-wrap: anywhere; }

  .items { margin-top: 16px; }
  .items table { width: 100%; border-collapse: separate; border-spacing: 0; table-layout: fixed; }
  .items thead th { background: #0891C9; color: #fff; font-size: 13px; font-weight: 700;
    padding: 12px 8px; white-space: nowrap; }
  .items thead th:first-child { border-top-right-radius: 12px; border-bottom-right-radius: 12px;
    text-align: right; padding-right: 18px; }
  .items thead th:last-child { border-top-left-radius: 12px; border-bottom-left-radius: 12px; }
  .items tbody td { font-size: 13px; font-weight: 600; padding: 7px 8px;
    border-bottom: 1px solid #EAF3FA; text-align: center; }
  .items tbody td.name { text-align: right; padding-right: 18px; font-weight: 700; line-height: 1.35;
    white-space: normal; overflow-wrap: anywhere; }
  .items tbody td.total { color: #0891C9; font-weight: 800; }
  .items tbody td.empty { color: #9bb3c4; padding: 22px 6px; text-align: center; border-bottom: none; }
  .items tbody tr:last-child td { border-bottom: none; }

  .lower { display: flex; gap: 26px; margin-top: 16px; align-items: flex-start; }
  .lower .rcol { flex: 1; }
  .qrbox { flex: none; width: 212px; height: 212px; border: 1px solid #DCEBF6; border-radius: 18px;
    padding: 10px; display: flex; align-items: center; justify-content: center; background: #fff;
    box-shadow: 0 4px 14px rgba(3,120,190,.08); }
  .qrbox img { width: 192px; height: 192px; display: block; background: #fff; }
  .payrow { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
  .payrow .k { color: #65839A; font-size: 13px; font-weight: 600; width: 96px; text-align: right; flex: none; }
  .payrow .v { flex: 1; background: #fff; border: 1px solid #E1EDF5; border-radius: 12px;
    padding: 11px 14px; text-align: right; font-weight: 700; font-size: 13px; box-shadow: 0 2px 6px rgba(3,120,190,.05); }
  .totrow { display: flex; align-items: center; justify-content: space-between; padding: 6px 4px;
    border-bottom: 1px solid #EAF3FA; }
  .totrow .k { color: #65839A; font-size: 13.5px; font-weight: 600; }
  .totrow .v { font-size: 14px; font-weight: 800; color: #243746; }
  .grand { padding: 9px 4px; }
  .grand .k { font-size: 17px; font-weight: 800; color: #243746; }
  .grand .v { font-size: 20px; font-weight: 800; color: #0891C9; }
  .paidrow { display: flex; align-items: center; gap: 12px; padding: 3px 0; }
  .paidrow .k { color: #65839A; font-size: 13px; font-weight: 600; flex: 1; text-align: right; }
  .paidrow .box { display: flex; align-items: center; gap: 8px; width: 200px; }
  .paidrow .field { flex: 1; background: #fff; border: 1px solid #E1EDF5; border-radius: 11px;
    padding: 8px 12px; text-align: right; font-weight: 800; font-size: 13px; }
  .paidrow .cur { color: #65839A; font-size: 12px; font-weight: 700; }

  @media print { [data-sheet] { margin: 0 !important; } .card { box-shadow: none; } }
"""

# Small calendar glyph for the date meta-row (inline SVG — no icon font dependency).
_CAL_SVG = (
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">'
    '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
    '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
)


def _single_vat_rate(lines: list[dict[str, Any]], totals: dict[str, Any]) -> str:
    """Best-effort single VAT-rate label (e.g. ``15``) for the header/totals."""
    rates = {str(ln.get("vat_rate")) for ln in lines if ln.get("vat_rate") not in (None, "")}
    if len(rates) == 1:
        try:
            return f"{Decimal(next(iter(rates))):g}"
        except Exception:  # noqa: BLE001
            pass
    try:
        base = Decimal(str(totals.get("subtotal", 0)))
        if base > 0:
            return f"{(Decimal(str(totals.get('vat', 0))) / base * 100).quantize(Decimal('1')):g}"
    except Exception:  # noqa: BLE001
        pass
    return "15"


def _item_rows_blue(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """5-column rows: اسم الصنف · [الوصف] · الوحدة · الكمية · سعر الوحدة · الإجمالي (قبل الضريبة)."""
    if not lines:
        return f'<tr class="keep"><td class="empty" colspan="{6 if show_desc else 5}">لا توجد أصناف</td></tr>'
    rows: list[str] = []
    for line in lines:
        name = html.escape(str(line.get("name") or ""))
        unit_cell = (
            f"<td>{html.escape(str(line.get('unit') or ''))}</td>" if show_unit else ""
        )
        rows.append(
            '<tr class="keep">'
            f'<td class="name">{name}</td>'
            f'{_desc_cell(line, "name") if show_desc else ""}'
            f"{unit_cell}"
            f"<td>{_qty(line.get('qty'))}</td>"
            f"<td>{_money(line.get('price'))}</td>"
            f'<td class="total">{_money(line.get("before"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def build_phase1_invoice_html_v2(data: dict[str, Any]) -> str:
    """النموذج الثاني: modern-blue «فاتورة ضريبية» (reference فاتورة15.05.2026.pdf)."""
    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))
    c = _phase1_ctx(data)
    lines = with_print_descriptions(data)
    totals = data.get("totals") or {}
    vat_rate = _single_vat_rate(lines, totals)
    inv_date = c["inv_date"].replace("-", "/")
    # المبلغ المسدد / المستحق follow the payment type (نوع الدفع):
    #   • نقدي  → paid = full invoice total, due = 0
    #   • آجل   → paid = 0,  due = full invoice total
    # Detected from the payment label the screen already puts in the data dict
    # ("نقدي" / "آجل"); anything not آجل is treated as paid-in-full (cash).
    pay_raw = str(data.get("payment_label") or "")
    is_credit = "آجل" in pay_raw or "اجل" in pay_raw
    if is_credit:
        paid_disp = _money(0)
        due_disp = c["t_after"]
    else:
        paid_disp = c["t_after"]
        due_disp = _money(0)
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>{_CSS_V2}{_DESC_KEEP_V2 if show_desc else ""}</style>
</head>
<body>

<div data-sheet style="width:816px; min-height:1056px; margin:24px auto; background:#EFF9FF; padding:0 22px; box-shadow:0 6px 28px rgba(0,0,0,.12);">
<table class="page">
  <thead><tr><td class="page-top"></td></tr></thead>
  <tfoot><tr><td class="page-bottom"></td></tr></tfoot>
  <tbody><tr><td>

  <div class="card">

    <!-- HEADER -->
    <div class="header">
      <div class="h-right">
        <div class="h-title">
          <div class="en">TAX INVOICE</div>
          <div class="ar">فاتورة ضريبية</div>
        </div>
        <div class="logo">{c["logo"]}</div>
      </div>
      <div class="metabox">
        <div class="metarow"><span class="lbl">رقم الفاتورة :</span><span style="flex:1"></span><span class="val">{c["inv_no"]}</span></div>
        <div class="metarow"><span class="lbl">التاريخ :</span><span style="flex:1"></span><span class="val">{inv_date}</span><span style="display:flex;">{_CAL_SVG}</span></div>
      </div>
    </div>

    <!-- BODY -->
    <div class="body">

      <div class="parties">
        <div class="party">
          <h3>بيانات العميل</h3>
          <div class="prow"><div class="k">الاسم</div><div class="v">{c["cu_name"]}</div></div>
          <div class="prow"><div class="k">الرقم الضريبي</div><div class="v">{c["cu_vat"]}</div></div>
          <div class="prow"><div class="k">السجل التجاري</div><div class="v">{c["cu_cr"]}</div></div>
          <div class="prow"><div class="k">العنوان</div><div class="v">{c["cu_addr"]}</div></div>
        </div>
        <div class="party">
          <h3>بيانات البائع</h3>
          <div class="prow"><div class="k">الاسم</div><div class="v">{c["co_name"]}</div></div>
          <div class="prow"><div class="k">الرقم الضريبي</div><div class="v">{c["co_vat"]}</div></div>
          <div class="prow"><div class="k">السجل التجاري</div><div class="v">{c["co_cr"]}</div></div>
          <div class="prow"><div class="k">العنوان</div><div class="v">{c["co_addr"]}</div></div>
        </div>
      </div>

      <div class="items">
        <table>
          <colgroup>
            {'<col style="width:22%"><col style="width:18%">' if show_desc else '<col style="width:40%">'}{'<col style="width:15%">' if show_unit else ''}<col style="width:15%"><col style="width:15%"><col style="width:15%">
          </colgroup>
          <thead>
            <tr>
              <th>المنتج / الخدمة</th>{'<th>الوصف</th>' if show_desc else ''}
              {'<th>الوحدة</th>' if show_unit else ''}
              <th>الكمية</th>
              <th>سعر الوحدة</th>
              <th>الإجمالي</th>
            </tr>
          </thead>
          <tbody>{_item_rows_blue(lines, show_unit, show_desc)}</tbody>
        </table>
      </div>

      <div class="lower">
        <div class="qrbox"><img src="{c["qr"]}" alt="QR"></div>
        <div class="rcol">
          <div class="payrow"><div class="k">طريقة الدفع</div><div class="v">{c["pay"]}</div></div>
          <div class="totrow"><div class="k">الإجمالي قبل الخصم</div><div class="v">ر.س {c["t_before"]}</div></div>
          <div class="totrow"><div class="k">قيمة الخصم</div><div class="v">ر.س {c["t_discount"]}</div></div>
          <div class="totrow"><div class="k">الإجمالي بعد الخصم</div><div class="v">ر.س {c["t_taxable"]}</div></div>
          <div class="totrow"><div class="k">ضريبة القيمة المضافة {vat_rate}%</div><div class="v">ر.س {c["t_vat"]}</div></div>
          <div class="totrow grand"><div class="k">الإجمالي بعد الضريبة</div><div class="v">ر.س {c["t_after"]}</div></div>
          <div class="paidrow"><div class="k">المبلغ المسدد</div><div class="box"><div class="field">{paid_disp}</div><div class="cur">ر.س</div></div></div>
          <div class="paidrow"><div class="k">المبلغ المستحق</div><div class="box"><div class="field">{due_disp}</div><div class="cur">ر.س</div></div></div>
        </div>
      </div>
      {stamp_overlay_html(data)}

    </div>
  </div>

  </td></tr></tbody>
</table>
</div>
</body>
</html>"""


# ---- النموذج الثالث : زمرّدي — single column, logo top-left, QR above the totals ----
_CSS_V3 = """
  html, body { margin: 0; padding: 0; }
  body { background: #e9e9ea; -webkit-print-color-adjust: exact; print-color-adjust: exact;
    font-family: 'Tajawal','Cairo','Segoe UI','Tahoma','Arial',sans-serif; color: #1c2530; }
  .sheet { box-sizing: border-box; width: 816px; min-height: 1056px; margin: 24px auto; background: #fff;
    box-shadow: 0 6px 28px rgba(0,0,0,.16); display: flex; flex-direction: column; direction: rtl;
    padding: 40px 44px 30px; }
  tr { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .head { display: flex; justify-content: space-between; align-items: center; gap: 24px; }
  .head .cname { font-size: 26px; font-weight: 800; color: #065f46; }
  .head .cmeta { margin-top: 7px; display: grid; gap: 3px; font-size: 12.5px; color: #334155; }
  .head .cmeta b { color: #059669; font-weight: 700; }
  .head .logo { flex: none; width: 130px; height: 112px; border-radius: 14px; background: #ecfdf5;
    border: 1.5px solid #a7f3d0; color: #059669; display: flex; align-items: center;
    justify-content: center; padding: 16px; }
  .head .logo img, .head .logo svg { max-width: 100%; max-height: 100%; object-fit: contain; }
  .rule { height: 2px; background: linear-gradient(90deg, #059669, #a7f3d0 70%, transparent); margin: 18px 0; }
  .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; font-size: 12.5px; margin-bottom: 16px; }
  .meta .f .k { font-weight: 700; color: #059669; }
  .meta .f .v { font-weight: 600; }
  table.items { width: 100%; border-collapse: collapse; }
  table.items th { background: #ecfdf5; color: #065f46; font-size: 11px; padding: 8px 4px;
    text-align: center; font-weight: 700; border-bottom: 2px solid #6ee7b7; }
  table.items td { font-size: 11.5px; padding: 7px 4px; text-align: center; border-bottom: 1px solid #eef6f1; }
  table.items td.name { text-align: right; font-weight: 600; overflow-wrap: anywhere; }
  table.items td.empty { color: #999; padding: 18px; }
  /* QR directly above the totals, both hugging the physical right edge */
  .paybox { margin-top: auto; padding-top: 18px; }
  .paybox .qrbox { width: 120px; margin-left: auto; }
  .paybox .qrbox img { display: block; width: 100%; background: #fff; }
  .paybox .cap { width: 120px; margin-left: auto; text-align: center; font-size: 9.5px;
    color: #059669; margin-top: 2px; }
  .paybox .totals { width: 60%; margin-left: auto; margin-top: 12px; border: 1px solid #d1fae5;
    border-radius: 8px; overflow: hidden; }
  .paybox .totals .t { display: flex; justify-content: space-between; padding: 8px 14px; font-size: 12.5px; }
  .paybox .totals .t:not(:last-child) { border-bottom: 1px solid #eef6f1; }
  .paybox .totals .t.s { color: #047857; }
  .paybox .totals .t.g { background: #065f46; color: #fff; font-weight: 800; font-size: 14px; }
  .foot { text-align: center; font-size: 10.5px; color: #7a8a82; padding-top: 16px; }
  @media print { body { background: #fff; } .sheet { margin: 0; box-shadow: none; width: 100%; } }
"""


def _v3_head_cells(show_unit: bool, show_desc: bool) -> str:
    """النموذج الثالث's item header cells. With «الوصف» on, 45% of the 22% name
    column would leave the name ~87px, so the name keeps 13.5% (~98px), الوصف gets
    11% and every other column gives up the 2.5 points pro rata (×0.968)."""
    if not show_desc:
        unit = '<th style="width:8%;">الوحدة</th>' if show_unit else ""
        return (
            '<th style="width:8%;">مسلسل</th><th style="width:22%;">اسم الصنف</th>'
            + unit
            + '<th style="width:9%;">الكمية</th>\n'
            '        <th style="width:12%;">السعر</th><th style="width:13%;">الإجمالي</th>'
            '<th style="width:12%;">الضريبة</th>\n'
            '        <th style="width:16%;">بعد الضريبة</th>'
        )
    unit = '<th style="width:7.7%;">الوحدة</th>' if show_unit else ""
    return (
        '<th style="width:7.7%;">مسلسل</th><th style="width:13.5%;">اسم الصنف</th>'
        '<th style="width:11%;">الوصف</th>'
        + unit
        + '<th style="width:8.7%;">الكمية</th>'
        '<th style="width:11.6%;">السعر</th><th style="width:12.6%;">الإجمالي</th>'
        '<th style="width:11.6%;">الضريبة</th><th style="width:15.6%;">بعد الضريبة</th>'
    )


def build_phase1_invoice_html_v3(data: dict[str, Any]) -> str:
    """النموذج الثالث: single-column emerald «فاتورة مبيعات» — logo top-left, QR above totals."""
    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))
    c = _phase1_ctx(data)
    totals = data.get("totals") or {}
    subtotal = totals.get("subtotal", 0)
    discount = totals.get("discount", 0)
    taxable = totals.get("taxable")
    if taxable is None:
        try:
            taxable = Decimal(str(subtotal)) - Decimal(str(discount))
        except Exception:  # noqa: BLE001 - retain a printable legacy-invoice fallback
            taxable = subtotal
    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>{_CSS_V3}{_DESC_KEEP_V3 if show_desc else ""}</style>
</head>
<body>
  <div class="sheet">
    <div class="head">
      <div>
        <div class="cname">{c["co_name"]}</div>
        <div class="cmeta">
          <span><b>الرقم الضريبي:</b> {c["co_vat"]}</span>
          <span><b>السجل التجاري:</b> {c["co_cr"]}</span>
          <span><b>العنوان:</b> {c["co_addr"]}</span>
        </div>
      </div>
      <div class="logo">{c["logo"]}</div>
    </div>
    <div class="rule"></div>
    <div class="meta">
      <div class="f"><span class="k">التاريخ:</span> <span class="v">{c["inv_date"]}</span></div>
      <div class="f"><span class="k">رقم الفاتورة:</span> <span class="v">{c["inv_no"]}</span></div>
      <div class="f"><span class="k">نوع الدفع:</span> <span class="v">{c["pay"]}</span></div>
      <div class="f"><span class="k">اسم العميل:</span> <span class="v">{c["cu_name"]}</span></div>
      <div class="f"><span class="k">الرقم الضريبي للعميل:</span> <span class="v">{c["cu_vat"]}</span></div>
      <div class="f"><span class="k">السجل التجاري للعميل:</span> <span class="v">{c["cu_cr"]}</span></div>
      <div class="f" style="grid-column: span 2;"><span class="k">عنوان العميل:</span> <span class="v">{c["cu_addr"]}</span></div>
    </div>
    <table class="items">
      <thead><tr>
        {_v3_head_cells(show_unit, show_desc)}
      </tr></thead>
      <tbody>{c["rows"]}</tbody>
    </table>
    <div class="paybox">
      <div class="qrbox"><img src="{c["qr"]}" alt="QR"></div>
      <div class="cap">رمز الاستجابة</div>
      <div class="totals">
        <div class="t s"><span>الإجمالي قبل الخصم</span><span>{_money(subtotal)}</span></div>
        <div class="t s"><span>قيمة الخصم</span><span>{_money(discount)}</span></div>
        <div class="t s"><span>الإجمالي بعد الخصم</span><span>{_money(taxable)}</span></div>
        <div class="t s"><span>قيمة الضريبة</span><span>{c["t_vat"]}</span></div>
        <div class="t g"><span>الإجمالي بعد الضريبة</span><span>{c["t_after"]} ريال</span></div>
      </div>
    </div>
    <div class="foot">نشكر لكم تعاملكم معنا — {c["co_name"]}</div>
  </div>
</body>
</html>"""


# ---- النموذج الرابع : أبيض/أسود ثنائي اللغة — «فاتورة ضريبية Tax Invoice» (مرجع: فاتوره01.10.2025.pdf) ----
# A minimal bilingual (Arabic/English) document, geometry-measured off the
# reference PDF with PyMuPDF: grid rules #cbd5e1 (slate-300), a single darker
# header rule #94a2b8, ArialMT throughout — so Arial is the primary family and NO
# web font is loaded (nothing to fail in a headless render). Plain-string CSS to
# dodge the brace-doubling + inline-font-family traps. Seven columns, matching the
# reference: serial, description, qty, price, taxable amount, VAT rate, line total.
_CSS_V4 = """
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: #ececee; color: #1f2937;
    font-family: Arial, 'Segoe UI', Tahoma, sans-serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  tr, .keep { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .page { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .page > tbody > tr > td { padding: 0; vertical-align: top; }
  .page > thead > tr > td, .page > tfoot > tr > td { padding: 0; font-size: 0; line-height: 0; }
  .page-top { height: 30px; }
  .page-bottom { height: 40px; }

  .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; }
  .co { text-align: right; direction: rtl; }
  .co .nm { font-size: 19px; font-weight: 700; color: #111827; }
  .co .ln { font-size: 12px; color: #374151; margin-top: 5px; line-height: 1.7; }
  .co .ln .lbl { color: #4b5563; }
  .brand { flex: none; }
  .brand img { max-width: 250px; max-height: 92px; width: auto; height: auto; object-fit: contain; display: block; }
  .brand svg { width: 120px; height: 84px; color: #94a2b8; }

  .hr { height: 1.5px; background: #94a2b8; margin: 14px 0 0; }
  .title { text-align: center; margin: 22px 0; font-size: 25px; font-weight: 700; color: #111827; direction: rtl; }
  .title .en { margin-inline-start: 8px; }

  table.info { width: 100%; border-collapse: collapse; direction: ltr; font-size: 12px; }
  table.info td { border: 1px solid #cbd5e1; padding: 5px 10px; }
  table.info .il { color: #6b7280; white-space: nowrap; width: 108px; text-align: left; }
  table.info .ir { color: #374151; white-space: nowrap; width: 150px; text-align: right; direction: rtl; }
  table.info .iv { color: #111827; text-align: center; direction: rtl; }
  table.meta { width: 100%; border-collapse: collapse; border-top: 0; font-size: 12px; direction: ltr; }
  table.meta td { border: 1px solid #cbd5e1; padding: 0; width: 50%; }
  table.meta .mc { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 5px 10px; min-height: 26px; }
  table.meta .mc .il { color: #6b7280; white-space: nowrap; }
  table.meta .mc .ir { color: #374151; direction: rtl; white-space: nowrap; }
  table.meta .mc .mv { color: #111827; flex: 1; text-align: center; }

  table.items { width: 100%; border-collapse: collapse; direction: rtl; margin-top: 18px; border: 1px solid #cbd5e1; }
  table.items thead th { border-bottom: 1px solid #cbd5e1; padding: 7px 6px; font-weight: 700;
    font-size: 12.5px; color: #111827; line-height: 1.45; vertical-align: middle; }
  table.items thead th .en { display: block; font-size: 10px; font-weight: 400; color: #6b7280; }
  table.items tbody td { border-top: 1px solid #cbd5e1; padding: 10px 6px; font-size: 12.5px; vertical-align: middle; }
  table.items tbody tr:first-child td { border-top: 0; }
  .c-idx { text-align: center; color: #6b7280; }
  .c-name { text-align: right; color: #111827; overflow-wrap: anywhere; line-height: 1.4; }
  .c-num { text-align: center; color: #1f2937; }
  .c-amt { text-align: center; color: #111827; font-weight: 700; }
  table.items td.empty { text-align: center; color: #9aa5b1; padding: 20px; }

  .lower { display: flex; direction: ltr; justify-content: space-between; align-items: flex-start; gap: 24px; margin-top: 22px; }
  .totals { flex: 1; max-width: 58%; }
  .trow { display: flex; align-items: center; gap: 10px; padding: 5px 2px; }
  .trow .amt { min-width: 96px; text-align: left; font-weight: 700; color: #111827; font-size: 13px; }
  .trow .cur { color: #6b7280; font-size: 11.5px; }
  .trow .lar { direction: rtl; color: #1f2937; font-size: 12.5px; }
  .trow .len { color: #6b7280; font-size: 11.5px; }
  .qrblk { flex: none; text-align: center; width: 152px; }
  .qrblk img { width: 122px; height: 122px; display: block; margin: 0 auto; background: #fff; }
  .qrblk .cap { font-size: 8px; color: #6b7280; margin-top: 5px; line-height: 1.55; direction: rtl; }
  .qrblk .cap .en { display: block; direction: ltr; color: #94a2b8; margin-top: 2px; }

  .sign { margin-top: 28px; direction: rtl; font-size: 15px; font-weight: 700; color: #111827; }
  @media print { body { background: #fff; } [data-sheet] { margin: 0 !important; box-shadow: none !important; } }
"""


def _item_rows_v4(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """7-column rows (RTL): # · المنتج · [الوصف] · الكمية · السعر · المبلغ الخاضع · القيمة المضافة% · المجموع."""
    if not lines:
        return f'<tr class="keep"><td class="empty" colspan="{9 if show_desc else 8}">لا توجد أصناف</td></tr>'
    rows: list[str] = []
    for index, line in enumerate(lines, start=1):
        name = html.escape(str(line.get("name") or ""))
        rate = line.get("vat_rate")
        try:
            rate_disp = f"{Decimal(str(rate)):g}%" if rate not in (None, "") else "15%"
        except Exception:  # noqa: BLE001
            rate_disp = "15%"
        unit_cell = (
            f'<td class="c-num">{html.escape(str(line.get("unit") or ""))}</td>'
            if show_unit
            else ""
        )
        rows.append(
            '<tr class="keep">'
            f'<td class="c-idx">{index}</td>'
            f'<td class="c-name">{name}</td>'
            f'{_desc_cell(line, "c-name") if show_desc else ""}'
            f'{unit_cell}'
            f'<td class="c-num">{_qty(line.get("qty"))}</td>'
            f'<td class="c-num">{_money(line.get("price"))}</td>'
            f'<td class="c-num">{_money(line.get("before"))}</td>'
            f'<td class="c-num">{rate_disp}</td>'
            f'<td class="c-amt">{_money(line.get("total"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def build_phase1_invoice_html_v4(data: dict[str, Any]) -> str:
    """النموذج الرابع: minimal bilingual «فاتورة ضريبية / Tax Invoice» (reference فاتوره01.10.2025.pdf)."""
    show_unit = bool(data.get("show_unit", True))
    # «التوقيع:» line under the totals — on by default; a print run may hide it.
    show_signature = bool(data.get("show_signature", True))
    show_desc = bool(data.get("show_description"))
    c = _phase1_ctx(data)
    seller = data.get("seller") or {}
    lines = with_print_descriptions(data)
    logo_uri = company_logo_data_uri(seller)
    brand_html = (
        f'<img src="{logo_uri}" alt="logo">' if logo_uri else _EMBLEM_SVG
    )
    # No dedicated due-date field on the screen — the reference shows it equal to
    # the issue date, so mirror that (a cash sale is due on issue).
    due_date = c["inv_date"]
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_CSS_V4}</style>
</head>
<body>

<div data-sheet style="width:816px; min-height:1056px; margin:24px auto; background:#ffffff; padding:0 40px; box-shadow:0 6px 28px rgba(0,0,0,.12);">
<table class="page">
  <thead><tr><td class="page-top"></td></tr></thead>
  <tfoot><tr><td class="page-bottom"></td></tr></tfoot>
  <tbody><tr><td>

  <!-- HEADER -->
  <div class="top">
    <div class="co">
      <div class="nm">{c["co_name"]}</div>
      <div class="ln">{c["co_addr"]}</div>
      <div class="ln"><span class="lbl">رقم السجل التجاري:</span> {c["co_cr"]}</div>
      <div class="ln"><span class="lbl">رقم التسجيل الضريبي:</span> {c["co_vat"]}</div>
    </div>
    <div class="brand">{brand_html}</div>
  </div>
  <div class="hr"></div>

  <!-- TITLE -->
  <div class="title">فاتورة ضريبية<span class="en">Tax Invoice</span></div>

  <!-- CUSTOMER + META -->
  <table class="info">
    <tbody>
      <tr><td class="il">Customer</td><td class="iv" colspan="2">{c["cu_name"]}</td><td class="ir">العميل</td></tr>
      <tr><td class="il">Address</td><td class="iv" colspan="2">{c["cu_addr"]}</td><td class="ir">العنوان</td></tr>
      <tr><td class="il">VAT number</td><td class="iv" colspan="2">{c["cu_vat"]}</td><td class="ir">رقم التسجيل الضريبي</td></tr>
    </tbody>
  </table>
  <table class="meta">
    <tbody>
      <tr>
        <td><div class="mc"><span class="il">Invoice number</span><span class="mv">{c["inv_no"]}</span><span class="ir">رقم الفاتورة</span></div></td>
        <td><div class="mc"><span class="il">Date</span><span class="mv">{c["inv_date"]}</span><span class="ir">التاريخ</span></div></td>
      </tr>
      <tr>
        <td><div class="mc"><span class="il">Due date</span><span class="mv">{due_date}</span><span class="ir">تاريخ الإستحقاق</span></div></td>
        <td><div class="mc"></div></td>
      </tr>
    </tbody>
  </table>

  <!-- ITEMS -->
  <table class="items">
    <colgroup>
      <col style="width:5%">{'<col style="width:15%"><col style="width:12%">' if show_desc else '<col style="width:27%">'}{'<col style="width:11%">' if show_unit else ''}<col style="width:11%"><col style="width:17%"><col style="width:12%"><col style="width:17%">
    </colgroup>
    <thead>
      <tr>
        <th># <span class="en">Item</span></th>
        {'<th>المنتج<span class="en">Product</span></th><th>الوصف<span class="en">Description</span></th>' if show_desc else '<th>المنتج / الوصف<span class="en">Description</span></th>'}
        {'<th>الوحدة<span class="en">Unit</span></th>' if show_unit else ''}
        <th>الكمية<span class="en">Qty</span></th>
        <th>السعر<span class="en">Price</span></th>
        <th>المبلغ الخاضع للضريبة<span class="en">Taxable amount</span></th>
        <th>القيمة المضافة<span class="en">VAT</span></th>
        <th>المجموع<span class="en">Amount</span></th>
      </tr>
    </thead>
    <tbody>{_item_rows_v4(lines, show_unit, show_desc)}</tbody>
  </table>

  <!-- TOTALS + QR -->
  <div class="lower">
    <div class="totals">
      <div class="trow"><span class="amt">{c["t_before"]}</span><span class="cur">SAR</span><span class="lar">المجموع الفرعي</span><span class="len">Subtotal</span></div>
      <div class="trow"><span class="amt">{c["t_vat"]}</span><span class="cur">SAR</span><span class="lar">إجمالي ضريبة القيمة المضافة</span><span class="len">Total VAT</span></div>
      <div class="trow grand"><span class="amt">{c["t_after"]}</span><span class="cur">SAR</span><span class="lar">المجموع شامل القيمة المضافة</span><span class="len">Total including VAT</span></div>
    </div>
    <div class="qrblk">
      <img src="{c["qr"]}" alt="QR">
      <div class="cap">رمز الإستجابة السريعة مشفّر بحسب متطلبات هيئة الزكاة والضريبة والجمارك للفوترة الإلكترونية<span class="en">This QR code is encoded as per ZATCA e-invoicing requirements</span></div>
    </div>
  </div>

  <!-- SIGNATURE + STAMP -->
  {'<div class="sign">التوقيع:</div>' if show_signature else ''}
  {stamp_overlay_html(data)}

  </td></tr></tbody>
</table>
</div>
</body>
</html>"""


# ---- النموذج الخامس : كلاسيك عنابي رسمي — «فاتورة ضريبية» (تصميم جديد، معتمد 2026-08-06) ----
# A formal, document-style layout: centred crest-like header with a double
# burgundy rule, a bordered bilingual info grid, a fully-ruled items table and a
# burgundy grand-total bar, closed by a signature/stamp line. Serif family
# ('Traditional Arabic' first — a classic naskh present on Windows, the app's
# host) for the official feel. Plain-string CSS (no brace-doubling / inline-font
# traps); QR is the Phase-1 tags-1..5 code from _phase1_ctx.
_CSS_V5 = """
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: #ececee; color: #2b1a1d;
    font-family: 'Traditional Arabic','Amiri','Times New Roman','Sakkal Majalla',serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  tr, .keep { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .page { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .page > tbody > tr > td { padding: 0; vertical-align: top; }
  .page > thead > tr > td, .page > tfoot > tr > td { padding: 0; font-size: 0; line-height: 0; }
  .page-top { height: 30px; }
  .page-bottom { height: 40px; }

  .hd { display: flex; justify-content: space-between; align-items: center; gap: 24px;
    border-bottom: 3px double #7a1f2b; padding-bottom: 14px; }
  .hd .co { text-align: right; }
  .hd .co .nm { font-size: 28px; font-weight: 800; color: #7a1f2b; }
  .hd .co .ln { font-size: 14px; color: #5a4448; margin-top: 4px; }
  .hd .logo { flex: none; }
  .hd .logo img { max-height: 90px; max-width: 220px; width: auto; height: auto; object-fit: contain; display: block; }
  .hd .logo .ph { width: 150px; height: 82px; border: 2px solid #d9b8bd; border-radius: 6px;
    display: flex; align-items: center; justify-content: center; color: #b98b93; font-weight: 800; letter-spacing: 3px; }

  .title { text-align: center; margin: 20px 0; }
  .title span { display: inline-block; border: 2px solid #7a1f2b; color: #7a1f2b; font-size: 22px; font-weight: 800; padding: 6px 44px; }

  table.info { width: 100%; border-collapse: collapse; margin: 8px 0 22px; font-size: 14px; }
  table.info td { border: 1px solid #d9b8bd; padding: 8px 12px; }
  table.info .k { background: #f7eef0; color: #7a1f2b; font-weight: 700; width: 132px; white-space: nowrap; }
  table.info .v { text-align: center; }
  /* Invoice no. / date / payment: a narrower label and a fixed, non-wrapping value
     column so the date (dd-mm-yyyy) prints on one line (user, 2026-10-03). */
  table.info .k2 { width: 92px; padding-left: 8px; padding-right: 8px; }
  table.info .v2 { width: 122px; white-space: nowrap; }

  table.it { width: 100%; border-collapse: collapse; }
  table.it thead th { background: #7a1f2b; color: #fff; font-size: 14px; font-weight: 700; padding: 10px 8px; border: 1px solid #7a1f2b; }
  table.it tbody td { padding: 9px 8px; font-size: 13.5px; text-align: center; border: 1px solid #d9b8bd; vertical-align: middle; }
  table.it td.nm { text-align: right; font-weight: 700; overflow-wrap: anywhere; }
  table.it td.idx { width: 36px; color: #7a1f2b; font-weight: 700; }
  table.it td.tot { font-weight: 800; color: #7a1f2b; }
  table.it td.empty { text-align: center; color: #9a8a8d; padding: 20px; }

  table.tot { width: 340px; margin-inline-start: auto; margin-top: 18px; border-collapse: collapse; }
  table.tot td { border: 1px solid #d9b8bd; padding: 9px 14px; font-size: 14px; }
  table.tot .k { background: #f7eef0; color: #7a1f2b; font-weight: 700; }
  table.tot .val { text-align: center; }
  table.tot .g td { background: #7a1f2b; color: #fff; font-weight: 800; font-size: 15.5px; }

  .sign { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 28px; }
  .sign .qr { text-align: center; }
  .sign .qr img { width: 128px; height: 128px; background: #fff; }
  .sign .qr .cap { font-size: 10px; color: #9a8a8d; margin-top: 4px; }
  .sign .s { font-size: 16px; font-weight: 700; color: #2b1a1d; }
  @media print { body { background: #fff; } [data-sheet] { margin: 0 !important; box-shadow: none !important; } }
"""


def _item_rows_v5(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """7-column rows: # · الصنف · [الوصف] · الكمية · السعر · قبل الضريبة · الضريبة · الإجمالي."""
    if not lines:
        return f'<tr class="keep"><td class="empty" colspan="{9 if show_desc else 8}">لا توجد أصناف</td></tr>'
    rows: list[str] = []
    for index, line in enumerate(lines, start=1):
        name = html.escape(str(line.get("name") or ""))
        unit_cell = (
            f'<td>{html.escape(str(line.get("unit") or ""))}</td>' if show_unit else ""
        )
        rows.append(
            '<tr class="keep">'
            f'<td class="idx">{index}</td>'
            f'<td class="nm">{name}</td>'
            f'{_desc_cell(line, "nm") if show_desc else ""}'
            f'{unit_cell}'
            f'<td>{_qty(line.get("qty"))}</td>'
            f'<td>{_money(line.get("price"))}</td>'
            f'<td>{_money(line.get("before"))}</td>'
            f'<td>{_money(line.get("vat_amount"))}</td>'
            f'<td class="tot">{_money(line.get("total"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def _v5_cols(show_unit: bool, show_desc: bool) -> str:
    """النموذج الخامس's <col>s. Unticked, the colgroup sizes 7 of the 8 columns, so
    الصنف and the last (الإجمالي) column share the slack (الصنف ≈ 172px with الوحدة).
    With «الوصف» the table switches to a fixed layout (``_DESC_KEEP_V5``) and all
    nine columns but الصنف get border-box widths: 45% of the old name width would
    leave الصنف < 90px, so the numeric columns give up a little too (الصنف ≈ 98px,
    الوصف 80px with الوحدة; ≈ 120px / 100px without it)."""
    if not show_desc:
        unit = '<col style="width:66px">' if show_unit else ""
        return (
            f'<col style="width:38px"><col>{unit}<col style="width:92px"><col style="width:104px">'
            '<col style="width:92px"><col style="width:104px">'
        )
    if show_unit:
        return (
            '<col style="width:38px"><col><col style="width:80px"><col style="width:62px">'
            '<col style="width:70px"><col style="width:92px"><col style="width:96px">'
            '<col style="width:88px"><col style="width:100px">'
        )
    return (
        '<col style="width:38px"><col><col style="width:100px"><col style="width:76px">'
        '<col style="width:96px"><col style="width:98px"><col style="width:92px"><col style="width:104px">'
    )


def build_phase1_invoice_html_v5(data: dict[str, Any]) -> str:
    """النموذج الخامس: formal burgundy «فاتورة ضريبية» (new design, chosen 2026-08-06)."""
    show_unit = bool(data.get("show_unit", True))
    # «التوقيع والختم» caption beside the QR — on by default; a print run may hide it.
    show_signature = bool(data.get("show_signature", True))
    show_desc = bool(data.get("show_description"))
    cols = _v5_cols(show_unit, show_desc)
    c = _phase1_ctx(data)
    seller = data.get("seller") or {}
    lines = with_print_descriptions(data)
    logo_uri = company_logo_data_uri(seller)
    logo_inner = f'<img src="{logo_uri}" alt="logo">' if logo_uri else '<div class="ph">شعار</div>'
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_CSS_V5}{_DESC_KEEP_V5 if show_desc else ""}</style>
</head>
<body>

<div data-sheet style="width:816px; min-height:1056px; margin:24px auto; background:#ffffff; padding:0 46px; box-shadow:0 6px 28px rgba(0,0,0,.12);">
<table class="page">
  <thead><tr><td class="page-top"></td></tr></thead>
  <tfoot><tr><td class="page-bottom"></td></tr></tfoot>
  <tbody><tr><td>

  <!-- HEADER : company info (right) + logo (left) -->
  <div class="hd">
    <div class="co">
      <div class="nm">{c["co_name"]}</div>
      <div class="ln">{c["co_addr"]}</div>
      <div class="ln">السجل التجاري: {c["co_cr"]} — الرقم الضريبي: {c["co_vat"]}</div>
    </div>
    <div class="logo">{logo_inner}</div>
  </div>

  <!-- TITLE -->
  <div class="title"><span>فاتورة ضريبية</span></div>

  <!-- INFO -->
  <table class="info">
    <tbody>
      <tr><td class="k">العميل</td><td class="v">{c["cu_name"]}</td><td class="k k2">رقم الفاتورة</td><td class="v v2">{c["inv_no"]}</td></tr>
      <tr><td class="k">الرقم الضريبي</td><td class="v">{c["cu_vat"]}</td><td class="k k2">التاريخ</td><td class="v v2">{c["inv_date"]}</td></tr>
      <tr><td class="k">العنوان</td><td class="v">{c["cu_addr"]}</td><td class="k k2">طريقة الدفع</td><td class="v v2">{c["pay"]}</td></tr>
    </tbody>
  </table>

  <!-- ITEMS -->
  <table class="it">
    <colgroup>
      {cols}
    </colgroup>
    <thead>
      <tr>
        <th>#</th><th>الصنف</th>{'<th>الوصف</th>' if show_desc else ''}{'<th>الوحدة</th>' if show_unit else ''}<th>الكمية</th><th>السعر</th><th>قبل الضريبة</th><th>الضريبة</th><th>الإجمالي</th>
      </tr>
    </thead>
    <tbody>{_item_rows_v5(lines, show_unit, show_desc)}</tbody>
  </table>

  <!-- TOTALS -->
  <table class="tot">
    <tbody>
      <tr><td class="k">المجموع قبل الضريبة</td><td class="val">{c["t_before"]}</td></tr>
      <tr><td class="k">ضريبة القيمة المضافة 15%</td><td class="val">{c["t_vat"]}</td></tr>
      <tr class="g"><td>الإجمالي شامل الضريبة</td><td class="val">{c["t_after"]} ريال</td></tr>
    </tbody>
  </table>

  <!-- SIGNATURE + QR + STAMP -->
  <div class="sign">
    <div class="qr"><img src="{c["qr"]}" alt="QR"><div class="cap">رمز الاستجابة السريعة</div></div>
    {'<div class="s">التوقيع والختم: ................</div>' if show_signature else ''}
  </div>
  {stamp_overlay_html(data)}

  </td></tr></tbody>
</table>
</div>
</body>
</html>"""


# ---- النموذج السادس : أزرق سماوي «طبق الأصل» — «فاتورة ضريبية» (مرجع: مؤسسة ثوابت الرواسي) ----
# A faithful reproduction of the customer's own scanned «فاتورة ضريبية»: the QR at
# the top-left, the big azure title at the top-right, a split band (a white seller
# panel beside a solid-azure meta panel carrying رقم الفاتورة / التاريخ / وقت
# الفاتورة), the «المبلغ المستحق» hero, a 5-column items table (الصنف · الكمية ·
# السعر · ضريبة القيمة المضافة · المبلغ), the totals block and a soft azure corner
# flourish painted as a background gradient (no positioned element — so it never
# disturbs pagination). Plain-string CSS (no brace-doubling, font-family lives here
# once — never inline) and the same paginating .page table wrapper as النموذج الأول
# so a long invoice flows onto extra pages instead of clipping.
_AZURE = "#2F98E8"
_CSS_V6 = """
  html, body { margin: 0; padding: 0; }
  body { background: #e9edf1; -webkit-print-color-adjust: exact; print-color-adjust: exact;
    font-family: 'Tajawal','Cairo','Segoe UI','Tahoma','Arial',sans-serif; color: #1c2733; }
  .sheet { box-sizing: border-box; width: 816px; min-height: 1056px; margin: 24px auto; background: #ffffff;
    padding: 0 44px; box-shadow: 0 6px 28px rgba(0,0,0,.16); direction: rtl;
    background-image: radial-gradient(circle 150px at 100% 100%, rgba(47,152,232,.15) 0 99%, rgba(255,255,255,0) 100%);
    background-repeat: no-repeat; }
  tr, .keep { break-inside: avoid; page-break-inside: avoid; }
  thead { display: table-header-group; }
  .page { width: 100%; table-layout: fixed; border-collapse: collapse; }
  .page > tbody > tr > td { padding: 0; vertical-align: top; }
  .page > thead > tr > td, .page > tfoot > tr > td { padding: 0; font-size: 0; line-height: 0; }
  .page-top { height: 30px; }
  .page-bottom { height: 44px; }

  .hdr { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
  .inv-title { font-size: 40px; font-weight: 800; color: #111111; line-height: 1; }
  .qr-box img { width: 120px; height: 120px; display: block; background: #ffffff; }

  .band { display: flex; margin: 18px 0 8px; border-radius: 10px; overflow: hidden; border: 1px solid #e3e9ef; }
  .band .seller { flex: 1; padding: 14px 18px; background: #ffffff; }
  .band .seller .k { color: #2F98E8; font-size: 13px; font-weight: 700; }
  .band .seller .v { color: #23303c; font-size: 14px; font-weight: 700; margin-bottom: 5px; }
  .band .meta { flex: 1.25; background: #2F98E8; color: #ffffff; display: flex; justify-content: space-around;
    text-align: center; padding: 16px 10px; gap: 8px; }
  .band .meta .lbl { font-size: 12.5px; opacity: .92; margin-bottom: 10px; }
  .band .meta .val { font-size: 16px; font-weight: 800; }

  .buyer { font-size: 13.5px; margin: 10px 2px 0; }
  /* Each buyer field on its OWN line — a long address must never wrap mid-label
     («السجل / التجاري» split) the way an inline « · »-joined line does. */
  .buyer .brow { display: flex; gap: 6px; padding: 2px 0; align-items: baseline; }
  .buyer .k { color: #23303c; font-weight: 700; white-space: nowrap; flex: none; }
  .buyer .v { color: #23303c; font-weight: 700; overflow-wrap: anywhere; }

  .due { text-align: left; margin: 22px 0 4px; font-size: 20px; font-weight: 700; color: #23303c; }
  .amount { text-align: left; color: #2F98E8; margin-bottom: 10px; }
  .amount .cur { font-size: 16px; font-weight: 700; }
  .amount .big { font-size: 38px; font-weight: 800; letter-spacing: .5px; }

  table.items { width: 100%; border-collapse: collapse; margin-top: 6px; }
  table.items thead th { color: #2F98E8; font-size: 13px; font-weight: 800; padding: 10px 8px;
    border-bottom: 2px solid #2F98E8; white-space: nowrap; text-align: center; }
  table.items thead th:first-child { text-align: right; }
  table.items tbody td { padding: 11px 8px; font-size: 13px; border-bottom: 1px solid #e6ecf2; text-align: center; }
  .c-name { text-align: right; font-weight: 700; color: #1f2a35; overflow-wrap: anywhere; }
  .c-num { font-variant-numeric: tabular-nums; }
  .c-vat .rate { color: #2F98E8; font-size: 11px; }
  table.items td.empty { text-align: center; color: #9aa5b1; padding: 20px; }

  /* Totals block hugs the physical LEFT edge (margin-right:auto absorbs the slack
     on the right, pushing the box left) — like the reference «الرواسي» invoice. */
  .totals { width: 58%; margin-top: 18px; margin-left: 0; margin-right: auto; display: grid; gap: 8px; }
  .totals .row { display: flex; justify-content: space-between; font-size: 13.5px; }
  .totals .k { color: #2F98E8; font-weight: 700; }
  .totals .grand { font-size: 16px; border-top: 1px solid #e6ecf2; padding-top: 8px; }
  .totals .grand .k, .totals .grand .v { font-weight: 800; }

  .foot { margin-top: 26px; padding-top: 12px; border-top: 1px solid #eef2f6; text-align: center;
    color: #7d93a6; font-size: 12px; }
  @media print {
    body { background: #ffffff; }
    .sheet { margin: 0; box-shadow: none; width: 100%; min-height: 0; }
  }
"""


def _item_rows_v6(lines: list[dict[str, Any]], show_unit: bool = True, show_desc: bool = False) -> str:
    """5-column rows: الصنف (wraps + grows) · [الوصف] · الكمية · السعر · ضريبة القيمة المضافة · المبلغ."""
    if not lines:
        return f'<tr><td class="empty" colspan="{7 if show_desc else 6}">لا توجد أصناف</td></tr>'
    rows: list[str] = []
    for line in lines:
        name = html.escape(str(line.get("name") or ""))
        rate = line.get("vat_rate")
        try:
            rate_disp = f'<span class="rate">{Decimal(str(rate)):g}%</span>' if rate not in (None, "") else ""
        except Exception:  # noqa: BLE001
            rate_disp = ""
        unit_cell = (
            f'<td class="c-num">{html.escape(str(line.get("unit") or ""))}</td>'
            if show_unit
            else ""
        )
        rows.append(
            "<tr>"
            f'<td class="c-name">{name}</td>'
            f'{_desc_cell(line, "c-name") if show_desc else ""}'
            f'{unit_cell}'
            f'<td class="c-num">{_qty(line.get("qty"))}</td>'
            f'<td class="c-num">{_money(line.get("price"))}</td>'
            f'<td class="c-num c-vat">{_money(line.get("vat_amount"))} {rate_disp}</td>'
            f'<td class="c-num">{_money(line.get("total"))}</td>'
            "</tr>"
        )
    return "".join(rows)


def _v6_head_cells(show_unit: bool, show_desc: bool) -> str:
    """النموذج السادس's item header cells. With «الوصف» on, «الصنف \\ الوصف» becomes
    «الصنف» (16.5%) + its own right-aligned «الوصف» (13.5%, 45% of the old 30%), and
    the table switches to a fixed layout (``_DESC_FIXED_V6``) so those widths hold;
    the numeric columns are re-balanced so the nowrap «ضريبة القيمة المضافة» header
    (~150px) still fits."""
    if not show_desc:
        unit = '<th style="width:10%;">الوحدة</th>' if show_unit else ""
        return (
            '<th style="width:30%;">الصنف \\ الوصف</th>\n'
            f"          {unit}\n"
            '          <th style="width:12%;">الكمية</th>\n'
            '          <th style="width:16%;">السعر</th>\n'
            '          <th style="width:16%;">ضريبة القيمة المضافة</th>\n'
            '          <th style="width:16%;">المبلغ</th>'
        )
    unit = '<th style="width:8%;">الوحدة</th>' if show_unit else ""
    return (
        '<th style="width:16.5%;">الصنف</th><th style="width:13.5%; text-align:right;">الوصف</th>'
        + unit
        + '<th style="width:9%;">الكمية</th><th style="width:14%;">السعر</th>'
        '<th style="width:21%;">ضريبة القيمة المضافة</th><th style="width:18%;">المبلغ</th>'
    )


def build_phase1_invoice_html_v6(data: dict[str, Any]) -> str:
    """النموذج السادس: faithful azure «فاتورة ضريبية» (reference مؤسسة ثوابت الرواسي)."""
    seller = data.get("seller") or {}
    customer = data.get("customer") or {}
    totals = data.get("totals") or {}
    lines = with_print_descriptions(data)
    show_unit = bool(data.get("show_unit", True))
    show_desc = bool(data.get("show_description"))
    qr = _phase1_qr_uri(data)

    issued = data.get("issue_datetime")
    if isinstance(issued, datetime.datetime):
        issue_date = issued.strftime("%Y/%m/%d")
        issue_time = issued.strftime("%H:%M:%S")
    else:
        issue_date = str(issued or "")
        issue_time = ""

    co_name = html.escape(str(seller.get("name") or ""))
    co_vat = html.escape(str(seller.get("vat") or ""))
    co_addr = html.escape(str(seller.get("address") or "")) or "—"
    cu_name = html.escape(str(customer.get("name") or "").strip() or "عميل نقدي")
    cu_vat = html.escape(str(customer.get("vat") or ""))
    cu_cr = html.escape(str(customer.get("cr") or ""))
    cu_addr = html.escape(str(customer.get("address") or ""))
    inv_no = html.escape(str(data.get("invoice_number") or ""))

    def _brow(label: str, value: str) -> str:
        return f'<div class="brow"><span class="k">{label}</span><span class="v">{value}</span></div>'

    buyer_rows = [_brow("فوتر إلى:", cu_name)]
    if cu_addr:
        buyer_rows.append(_brow("العنوان:", cu_addr))
    if cu_cr:
        buyer_rows.append(_brow("السجل التجاري:", cu_cr))
    if cu_vat:
        buyer_rows.append(_brow("الرقم الضريبي:", cu_vat))
    buyer_html = "".join(buyer_rows)

    stamp_overlay = stamp_overlay_html(data)

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>{_CSS_V6}{_DESC_FIXED_V6 if show_desc else ""}</style>
</head>
<body>
  <div class="sheet">
  <table class="page">
    <thead><tr><td class="page-top"></td></tr></thead>
    <tfoot><tr><td class="page-bottom"></td></tr></tfoot>
    <tbody><tr><td>

    <div class="hdr">
      <div class="inv-title">فاتورة ضريبية</div>
      <div class="qr-box"><img src="{qr}" alt="QR"></div>
    </div>

    <div class="band">
      <div class="seller">
        <div class="k">فوتر من:</div><div class="v">{co_name}</div>
        <div class="k">العنوان: <span class="v" style="font-weight:700;">{co_addr}</span></div>
        <div class="k">التسجيل الضريبي:</div><div class="v">{co_vat}</div>
      </div>
      <div class="meta">
        <div><div class="lbl">رقم الفاتورة</div><div class="val">{inv_no}</div></div>
        <div><div class="lbl">التاريخ</div><div class="val">{issue_date}</div></div>
        <div><div class="lbl">وقت الفاتورة</div><div class="val">{issue_time}</div></div>
      </div>
    </div>

    <div class="buyer">{buyer_html}</div>

    <div class="due">المبلغ المستحق</div>
    <div class="amount"><span class="cur">ر.س SAR</span> <span class="big">{_money(totals.get("total", 0))}</span></div>

    <table class="items">
      <thead>
        <tr>
          {_v6_head_cells(show_unit, show_desc)}
        </tr>
      </thead>
      <tbody>{_item_rows_v6(lines, show_unit, show_desc)}</tbody>
    </table>

    <div class="keep">
      <div class="totals">
        <div class="row"><span class="k">إجمالي المبلغ</span><span>{_money(totals.get("subtotal", 0))} ر.س</span></div>
        <div class="row"><span class="k">إجمالي القيمة المضافة</span><span>{_money(totals.get("vat", 0))} ر.س</span></div>
        <div class="row grand"><span class="k">الإجمالي بالضريبة</span><span class="v">{_money(totals.get("total", 0))} ر.س</span></div>
      </div>
      {stamp_overlay}
      <div class="foot">نشكر لكم تعاملكم معنا — {co_name}</div>
    </div>

    </td></tr></tbody>
  </table>
  </div>
</body>
</html>"""


# ======================================================================
# Phase-2's «النموذج الثامن», reused as Phase-1's «النموذج السابع»
# ======================================================================
# The mirror image of the three wrappers below: the Phase-2 navy-accent layout
# (:mod:`saudi_invoice_print_v8`) is also offered on the «مرحلة أولى» picker, at
# the user's request. The ONLY difference when printed from here is the QR — the
# Phase-1 sheet must carry the clean tags 1–5 code, never the signed tags 1–9
# payload the Phase-2 screen resolves into ``data["qr_payload"]``. Overwriting
# that one key is enough: :func:`build_invoice_html_v8` reads the QR from it and
# takes everything else from the same ``_collect_preview_data`` dict.

def build_phase1_invoice_html_v7(data: dict[str, Any]) -> str:
    """Phase-2 «النموذج الثامن» layout with the Phase-1 (tags 1–5) QR."""
    return build_invoice_html_v8({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_mutakamila(data: dict[str, Any]) -> str:
    """«المتكاملة» layout (Phase-2 :func:`build_invoice_html_v9`) with the Phase-1
    (tags 1–5) QR — same plain black-on-white design, Phase-1 QR payload."""
    return build_invoice_html_v9({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_alesnad(data: dict[str, Any]) -> str:
    """«الإسناد الماسي» layout (Phase-2 :func:`build_invoice_html_v10`) with the
    Phase-1 (tags 1–5) QR — same branded design, Phase-1 QR payload."""
    return build_invoice_html_v10({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_aqaseem(data: dict[str, Any]) -> str:
    """«اقاسيم» layout (Phase-2 :func:`build_invoice_html_v11`) with the Phase-1
    (tags 1–5) QR — same fixed-brand design, Phase-1 QR payload."""
    return build_invoice_html_v11({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_khutoot(data: dict[str, Any]) -> str:
    """«الخطوط السعودية» layout (Phase-2 :func:`build_invoice_html_v12`) with the
    Phase-1 (tags 1–5) QR — same fixed-brand design, Phase-1 QR payload."""
    return build_invoice_html_v12({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_mawsim(data: dict[str, Any]) -> str:
    """«مواسم الفاكهة» layout (Phase-2 :func:`build_invoice_html_v13`) with the
    Phase-1 (tags 1–5) QR — same fixed-brand replica, Phase-1 QR payload."""
    return build_invoice_html_v13({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_atyaf(data: dict[str, Any]) -> str:
    """«نموذج أطياف» (fixed-brand نهلة الخليج header/footer, :func:`build_invoice_html_v14`)
    with the Phase-1 tags 1–5 QR in place of the signed Phase-2 payload."""
    return build_invoice_html_v14({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_drob(data: dict[str, Any]) -> str:
    """«دروب الاتحاد» (Daftra-style layout replica, :func:`build_invoice_html_v15`;
    live seller/buyer/logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v15({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_gharbia(data: dict[str, Any]) -> str:
    """«إنتار الغربيا» (layout replica, :func:`build_invoice_html_v16`; live
    seller/buyer/logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v16({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_modi(data: dict[str, Any]) -> str:
    """«موضي عقيل» (Zoho-style layout replica, :func:`build_invoice_html_v17`; live
    seller/buyer/logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v17({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_mig(data: dict[str, Any]) -> str:
    """«ميج السعودية» (Zoho-style layout replica, :func:`build_invoice_html_v18`;
    live seller/buyer/logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v18({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_amal(data: dict[str, Any]) -> str:
    """«الامل الناجح» (Odoo-style layout replica, :func:`build_invoice_html_v19`;
    live seller/buyer; the source has no logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v19({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_qasr(data: dict[str, Any]) -> str:
    """«قصر نصار» (layout replica, :func:`build_invoice_html_v20`; live seller/buyer/logo)
    with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v20({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_nawafidh(data: dict[str, Any]) -> str:
    """«نوافذ» (Daftra-style layout replica, :func:`build_invoice_html_v21`; live
    seller/buyer/logo) with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v21({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_cards(data: dict[str, Any]) -> str:
    """«النموذج الخامس عشر» — «البطاقات» (:func:`build_invoice_html_v22`) with the
    Phase-1 tags 1–5 QR."""
    return build_invoice_html_v22({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_stripe(data: dict[str, Any]) -> str:
    """«النموذج السادس عشر» — «الشريط القطري» (:func:`build_invoice_html_v23`) with
    the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v23({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_hero(data: dict[str, Any]) -> str:
    """«النموذج السابع عشر» — «الإجمالي أولًا» (:func:`build_invoice_html_v24`) with
    the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v24({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_boarding(data: dict[str, Any]) -> str:
    """«النموذج الثامن عشر» — «بطاقة الصعود» (:func:`build_invoice_html_v25`) with
    the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v25({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_mirror(data: dict[str, Any]) -> str:
    """«النموذج التاسع عشر» — «المرآة ثنائية اللغة» (:func:`build_invoice_html_v26`)
    with the Phase-1 tags 1–5 QR."""
    return build_invoice_html_v26({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_invoice_timeline(data: dict[str, Any]) -> str:
    """«النموذج العشرون» — «الخط الزمني» (:func:`build_invoice_html_v27`) with the
    Phase-1 tags 1–5 QR."""
    return build_invoice_html_v27({**data, "qr_payload": _phase1_qr_payload(data)})


# ----------------------------------------------------------------------
# Phase-2 native layouts (النموذج الأول → الثامن) reused inside «مرحلة أولى»
# ----------------------------------------------------------------------
# Full-mirror request (2026-08-22): the Phase-1 picker offers the SAME list as the
# Phase-2 picker. These wrappers render each Phase-2 native layout with the Phase-1
# tags 1–5 QR (النموذج الثامن already has one: build_phase1_invoice_html_v7). Every
# Phase-2 builder reads its QR from data["qr_payload"], so swapping that one key is
# all it takes; the layout, fonts and data binding are byte-for-byte the Phase-2
# originals.
def build_phase1_p2_model1(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج الأول» (Phase-2 :func:`build_invoice_html`) بـQR م‑1."""
    return build_invoice_html({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model2(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج الثاني» (Phase-2 :func:`build_invoice_html_v2`) بـQR م‑1."""
    return build_invoice_html_v2({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model3(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج الثالث» (Phase-2 :func:`build_invoice_html_v3`) بـQR م‑1."""
    return build_invoice_html_v3({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model4(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج الرابع» (Phase-2 :func:`build_invoice_html_v4`) بـQR م‑1."""
    return build_invoice_html_v4({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model5(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج الخامس» (Phase-2 :func:`build_invoice_html_v5`) بـQR م‑1."""
    return build_invoice_html_v5({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model6(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج السادس» (Phase-2 :func:`build_invoice_html_v6`) بـQR م‑1."""
    return build_invoice_html_v6({**data, "qr_payload": _phase1_qr_payload(data)})


def build_phase1_p2_model7(data: dict[str, Any]) -> str:
    """المرحلة‑1: «النموذج السابع» (Phase-2 :func:`build_invoice_html_v7`) بـQR م‑1."""
    return build_invoice_html_v7({**data, "qr_payload": _phase1_qr_payload(data)})


# ======================================================================
# Phase-1 template roster — a FULL MIRROR of the Phase-2 picker
# ======================================================================
# User request 2026-08-22 («تطابق كامل»): «مرحلة أولى» must offer the exact same
# 14-template list as the Phase-2 invoice screen, in the same order and with the
# same names — the ONLY difference per template is the QR (Phase-1 = tags 1–5,
# Phase-2 = tags 1–9). So the mapping below lines up index-for-index with
# ``SaudiSalesInvoicePage._choose_invoice_builder``:
#   1‑8  → Phase-2 native layouts v1..v8, re-QR'd for Phase-1
#   9‑11 → the three native Phase-1 designs (build_phase1_invoice_html/_v2/_v3),
#          which are Phase-2's النموذج التاسع/العاشر/الحادي عشر
#   (الخطوط السعودية, formerly 12, hidden per user request 2026-10-17)
# المتكاملة/الإسناد الماسي/اقاسيم أُخفيت من المُنتقي بناءً على طلب المستخدم؛
# دوالها ما زالت معرّفة أعلاه ويمكن إعادة إدراجها. Indices 1‑11 are the Phase-2
# mirror. The three original Phase-1-only designs
# (build_phase1_invoice_html_v4/_v5/_v6) sit at the end as النموذج
# الخامس عشر/السادس عشر/السابع عشر (now indices 12‑14); they use the native
# Phase-1 tags 1–5 QR by default, so no wrapper is needed.
PHASE1_TEMPLATE_OPTIONS: tuple[str, ...] = (
    "النموذج الأول",
    "النموذج الثاني",
    "النموذج الثالث",
    "النموذج الرابع",
    "النموذج الخامس",
    "النموذج السادس",
    "النموذج السابع",
    "النموذج الثامن",
    "النموذج التاسع",
    "النموذج العاشر",
    "النموذج الحادي عشر",
    # المتكاملة/الإسناد الماسي/اقاسيم أُخفيت من المُنتقي بناءً على طلب المستخدم؛
    # دوال البناء (build_phase1_invoice_mutakamila/alesnad/aqaseem) ما زالت معرّفة
    # أعلاه ويمكن إعادة إدراجها لاحقًا. «الخطوط السعودية» أُخفيت كذلك (طلب
    # 2026-10-17)؛ build_phase1_invoice_khutoot ما زالت معرّفة.
    # The three Phase-1-only designs re-added as new options at the end (user
    # request 2026-08-22) — they are not part of the Phase-2 mirror above.
    # كانت تسمّى الخامس عشر/السادس عشر/السابع عشر؛ أُعيدت تسميتها الثاني عشر/
    # الثالث عشر/الرابع عشر كي يمشي الترقيم متتاليًا (طلب 2026-10-17) — الاسم فقط.
    "النموذج الثاني عشر",
    "النموذج الثالث عشر",
    "النموذج الرابع عشر",
    # «مواسم الفاكهة» و«دروب الاتحاد»/«إنتار الغربيا»/«موضي عقيل»/«ميج السعودية»/
    # «الامل الناجح»/«قصر نصار»/«نوافذ» أُخفيت من المُنتقي بناءً على طلب المستخدم
    # (2026-10-17)؛ دوالها (build_phase1_invoice_mawsim/drob/gharbia/modi/mig/amal/
    # qasr/nawafidh) ما زالت معرّفة أعلاه ويمكن إعادة إدراجها لاحقًا.
    # «نموذج أطياف» (build_phase1_invoice_atyaf) أُخفي كذلك (طلب 2026-10-17)، ثم
    # أُعيد في آخر القائمة باسم «نهلة الخليج» (طلب 2026-10-20).
    # ثلاثة تصاميم جديدة اختارها المستخدم من معرض الموك أب (2026-10-18) — نفس
    # نماذج المرحلة الثانية ١٥–١٧ بالضبط، الفرق الوحيد QR المرحلة الأولى.
    "النموذج الخامس عشر",   # «البطاقات»
    "النموذج السادس عشر",   # «الشريط القطري»
    "النموذج السابع عشر",   # «الإجمالي أولًا»
    # ثلاثة أخرى من معرض الموك أب الثاني (2026-10-18)، بنفس الشرط.
    "النموذج الثامن عشر",   # «بطاقة الصعود»
    "النموذج التاسع عشر",   # «المرآة ثنائية اللغة»
    "النموذج العشرون",      # «الخط الزمني»
    # «نهلة الخليج» (= «نموذج أطياف» سابقًا، v14) أُعيد إظهاره في المرحلتين بناءً على
    # طلب المستخدم (2026-10-20)؛ هنا بـ QR المرحلة الأولى (تاجات ١–٥).
    "نهلة الخليج",
)

# 1-based template index -> its HTML builder (None = reserved / not built yet).
_PHASE1_BUILDERS: dict[int, Callable[[dict[str, Any]], str]] = {
    1: build_phase1_p2_model1,        # Phase-2 v1
    2: build_phase1_p2_model2,        # Phase-2 v2
    3: build_phase1_p2_model3,        # Phase-2 v3
    4: build_phase1_p2_model4,        # Phase-2 v4
    5: build_phase1_p2_model5,        # Phase-2 v5
    6: build_phase1_p2_model6,        # Phase-2 v6
    7: build_phase1_p2_model7,        # Phase-2 v7
    8: build_phase1_invoice_html_v7,  # Phase-2 v8 (pre-existing wrapper)
    9: build_phase1_invoice_html,     # native Phase-1 design 1 (= Phase-2 التاسع)
    10: build_phase1_invoice_html_v2,  # native Phase-1 design 2 (= Phase-2 العاشر)
    11: build_phase1_invoice_html_v3,  # native Phase-1 design 3 (= Phase-2 الحادي عشر)
    # المتكاملة/الإسناد الماسي/اقاسيم أُخفيت من المُنتقي (طلب المستخدم) — أُزيلت من
    # الخريطة كي تتطابق الفهارس مع القائمة المعروضة.
    # الخطوط السعودية (khutoot) أُخفيت كذلك (طلب 2026-10-17).
    # Phase-1-only designs restored as new options (not in the Phase-2 mirror).
    12: build_phase1_invoice_html_v4,
    13: build_phase1_invoice_html_v5,
    14: build_phase1_invoice_html_v6,
    # مواسم الفاكهة/أطياف/دروب/إنتار/موضي/ميج/الامل/قصر نصار/نوافذ أُخفيت (طلب
    # 2026-10-17) — أُزيلت من الخريطة كي تتطابق الفهارس مع القائمة المعروضة.
    15: build_phase1_invoice_cards,    # v22 «البطاقات», Phase-1 QR
    16: build_phase1_invoice_stripe,   # v23 «الشريط القطري», Phase-1 QR
    17: build_phase1_invoice_hero,     # v24 «الإجمالي أولًا», Phase-1 QR
    18: build_phase1_invoice_boarding, # v25 «بطاقة الصعود», Phase-1 QR
    19: build_phase1_invoice_mirror,   # v26 «المرآة ثنائية اللغة», Phase-1 QR
    20: build_phase1_invoice_timeline, # v27 «الخط الزمني», Phase-1 QR
    21: build_phase1_invoice_atyaf,    # v14 «نهلة الخليج», Phase-1 QR
}


def phase1_builder_for(choice: int | None) -> "Callable[[dict[str, Any]], str] | None":
    """Return the HTML builder for a 1-based template choice, or ``None`` if the
    choice is out of range. The Phase-1 roster mirrors the 14 Phase-2 templates."""
    if choice is None:
        return None
    return _PHASE1_BUILDERS.get(choice)


# ======================================================================
# The first three Phase-1 designs, reused inside the Phase-2 invoice screen
# ======================================================================
# النموذج الأول/الثاني/الثالث of «مرحلة أولى» are also offered on the Phase-2 screen
# (user request). The ONLY difference when printed from Phase-2 is the QR: it must
# carry the full signed tags 1–9 payload, not Phase-1's tags 1–5. These thin
# wrappers flip the ``use_phase2_qr`` switch that :func:`_phase1_qr_uri` reads; the
# layout, fonts and data binding are byte-for-byte the Phase-1 originals.

def build_phase1_design1_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج الأول» layout with the Phase-2 signed (tags 1–9) QR."""
    return build_phase1_invoice_html({**data, "use_phase2_qr": True})


def build_phase1_design2_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج الثاني» layout with the Phase-2 signed (tags 1–9) QR."""
    return build_phase1_invoice_html_v2({**data, "use_phase2_qr": True})


def build_phase1_design3_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج الثالث» layout with the Phase-2 signed (tags 1–9) QR."""
    return build_phase1_invoice_html_v3({**data, "use_phase2_qr": True})


def build_phase1_model15_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج الخامس عشر» (build_phase1_invoice_html_v4) copied to the
    Phase-2 screen as «النموذج الثاني عشر»: same layout, Phase-2 signed (tags 1–9)
    QR. Only the QR switch flips; the layout, fonts and data binding are the
    byte-for-byte Phase-1 original."""
    return build_phase1_invoice_html_v4({**data, "use_phase2_qr": True})


def build_phase1_model16_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج الثالث عشر» (formerly السادس عشر, build_phase1_invoice_html_v5)
    copied to the Phase-2 screen under the same name (2026-10-17, so both pickers
    offer the same 14): same layout, Phase-2 signed (tags 1–9) QR. Only the QR
    switch flips; the layout, fonts and data binding are the byte-for-byte
    Phase-1 original."""
    return build_phase1_invoice_html_v5({**data, "use_phase2_qr": True})


def build_phase1_model17_phase2(data: dict[str, Any]) -> str:
    """Phase-1 «النموذج السابع عشر» (now «الرابع عشر», build_phase1_invoice_html_v6)
    copied to the Phase-2 screen as «النموذج الرابع عشر»: same layout, Phase-2 signed (tags 1–9)
    QR. Only the QR switch flips; the layout, fonts and data binding are the
    byte-for-byte Phase-1 original."""
    return build_phase1_invoice_html_v6({**data, "use_phase2_qr": True})


# ======================================================================
# The three «مرحلة أولى» actions (preview / print / PDF)
# ======================================================================
def preview_phase1_invoice(
    parent: QWidget,
    data: dict[str, Any],
    html_builder: Callable[[dict[str, Any]], str] = build_phase1_invoice_html,
) -> None:
    """Open the shared preview window rendering the chosen Phase-1 template."""
    dialog = SaudiInvoicePreviewDialog(data, parent=parent, html_builder=html_builder)
    dialog.exec()


def export_phase1_invoice_pdf(
    parent: QWidget,
    data: dict[str, Any],
    html_builder: Callable[[dict[str, Any]], str] = build_phase1_invoice_html,
) -> None:
    """Ask for a path and export the chosen Phase-1 template straight to a PDF."""
    export_invoice_to_pdf(parent, data, html_builder=html_builder)


def print_phase1_invoice(
    parent: QWidget,
    data: dict[str, Any],
    html_builder: Callable[[dict[str, Any]], str] = build_phase1_invoice_html,
) -> None:
    """Render the chosen Phase-1 template off-screen and send it to a printer."""
    try:
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except Exception:  # noqa: BLE001 - print support may be unavailable
        QMessageBox.warning(parent, "الطباعة", "خدمة الطباعة غير متاحة.")
        return

    view = QWebEngineView(parent)
    # Keep a reference on the parent so the view survives the async print.
    holder = getattr(parent, "_phase1_print_views", None)
    if holder is None:
        holder = []
        parent._phase1_print_views = holder  # type: ignore[attr-defined]
    holder.append(view)

    def _cleanup() -> None:
        try:
            holder.remove(view)
        except ValueError:
            pass
        view.deleteLater()

    def _on_load(ok: bool) -> None:
        if not ok:
            _cleanup()
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.Letter))
        dialog = QPrintDialog(printer, parent)
        if dialog.exec() != QPrintDialog.Accepted:
            _cleanup()
            return

        def _done(success: bool) -> None:  # noqa: ARG001
            try:
                view.printFinished.disconnect(_done)
            except (RuntimeError, TypeError):
                pass
            _cleanup()

        view.printFinished.connect(_done)
        # Let fonts/layout settle before handing the page to the printer.
        QTimer.singleShot(150, lambda: view.print(printer))

    view.loadFinished.connect(_on_load)
    view.setHtml(html_builder(data), QUrl.fromLocalFile(str(_ASSETS_DIR) + "/"))
