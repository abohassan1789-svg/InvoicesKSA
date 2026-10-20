"""The five extra supply-contract print layouts the user picked (2026-10-20).

From the 15-design gallery the user chose 2, 4, 9, 10 and 11; they sit next to
the original layout in the «طباعة العقد» picker:

* ``build_supply_contract_html_green``  — «الترويسة الخضراء»: green letterhead
  band with the first party's logo, name, CR and the contract number;
* ``build_supply_contract_html_navy``   — «الكحلي والذهبي»: navy band with a
  gold rule, clause headings flush right behind a gold bar;
* ``build_supply_contract_html_maroon`` — «العنابي الرسمي»: logo and name over a
  maroon rule, the title in a full-width maroon bar;
* ``build_supply_contract_html_fresh``  — «الخضار والفواكه»: a fresh green /
  orange header with a small fruit drawing;
* ``build_supply_contract_html_cards``  — «البطاقات»: every part of the contract
  in its own card, the two parties side by side.

All of them print the same text as ``build_supply_contract_html``
(``contract_sections``): same clauses, same blanks, and the first party's stamp
only when ``show_stamp`` is on. The letterhead uses the first party's company
(``data["first_party_company"]``) for the logo, falling back to a letter tile.
"""

from __future__ import annotations

import html
from typing import Any

from app.ui.screens.saudi_invoice_print import company_logo_data_uri
from app.ui.screens.saudi_invoice_print_v28 import _FONTS, _font_face_css
from app.ui.screens.supply_contract_print import (
    contract_date_text,
    contract_sections,
    print_blank,
    stamp_html,
)

_FRUIT_SVG = (
    '<svg width="54" height="54" viewBox="0 0 44 44" aria-hidden="true">'
    '<circle cx="16" cy="26" r="11" fill="#F97316"/>'
    '<path d="M16 15c0-5 3-9 8-10-1 5-4 8-8 10z" fill="#65A30D"/>'
    '<circle cx="31" cy="27" r="9" fill="#DC2626"/>'
    '<path d="M31 18c1-4 4-6 8-6-1 4-4 6-8 6z" fill="#4D7C0F"/></svg>'
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value).strip())


def _logo(data: dict[str, Any], tile_bg: str, tile_fg: str, size: int = 56) -> str:
    """The first party's logo, or a tile with the first letter of its name."""
    uri = company_logo_data_uri(data.get("first_party_company") or {})
    if uri:
        return (f'<img src="{uri}" alt="" style="max-height:{size}px;max-width:{size * 3}px;'
                'object-fit:contain;">')
    name = str(data.get("first_party_name") or "").strip()
    letter = _esc(name.replace("شركة", "").replace("مؤسسة", "").strip()[:1] or "ع")
    return (f'<span style="display:inline-grid;place-items:center;width:{size}px;height:{size}px;'
            f'border-radius:9px;background:{tile_bg};color:{tile_fg};font-weight:700;'
            f'font-size:{size // 2}px;">{letter}</span>')


def _ident(data: dict[str, Any]) -> dict[str, str]:
    return {
        "name": _esc(data.get("first_party_name")),
        "cr": _esc(data.get("first_party_cr")),
        "address": _esc(data.get("first_party_address")),
        "number": _esc(data.get("contract_number")),
        "date": _esc(contract_date_text(data.get("contract_date"))),
    }


def _page(css: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  {_font_face_css()}
  html, body {{ margin:0; padding:0; background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  .sheet {{ max-width:740px; margin:0 auto; padding:0 4px 8px; color:#111; font-family:{_FONTS};
           font-size:14.5px; line-height:1.75; }}
  p {{ margin:0 0 6px; text-align:justify; }}
  p.c {{ text-align:center; }}
  p.h {{ text-align:center; font-weight:700; margin-top:10px; }}
  .v {{ font-weight:700; }}
  .ttl {{ text-align:center; font-weight:700; font-size:22px; margin:4px 0 16px; }}
  .num {{ direction:ltr; unicode-bidi:isolate; }}
  .sigs {{ margin-top:18px; border-collapse:collapse; page-break-inside:avoid; break-inside:avoid; }}
  .sigs td {{ vertical-align:top; text-align:center; }}
  .sigs p {{ text-align:center; margin-bottom:10px; }}
  {css}
</style>
</head>
<body>
<div class="sheet">
{body}
</div>
</body>
</html>"""


def _body(data: dict[str, Any]) -> str:
    return "\n".join(part for _key, part in contract_sections(data, print_blank, stamp_html(data)))


# --------------------------------------------------------------------------- #
# 2 · الترويسة الخضراء
# --------------------------------------------------------------------------- #
def build_supply_contract_html_green(data: dict[str, Any]) -> str:
    i = _ident(data)
    band = f"""<div class="band">{_logo(data, "rgba(255,255,255,.18)", "#fff")}
  <div class="who"><b>{i["name"]}</b><small>سجل تجاري <span class="num">{i["cr"]}</span> · {i["address"]}</small></div>
  <div class="no">رقم العقد<br><b class="num">{i["number"]}</b></div></div>"""
    css = """
  .band { display:flex; align-items:center; gap:14px; background:#137A38; color:#fff; border-radius:6px;
          padding:14px 20px; margin-bottom:16px; }
  .band .who b { display:block; font-size:19px; }
  .band .who small { font-size:12px; opacity:.9; }
  .band .no { margin-right:auto; text-align:left; font-size:12px; }
  .band .no b { font-size:15px; }
  .ttl { color:#137A38; border-bottom:2px solid #137A38; display:table; margin:4px auto 16px; padding:0 18px 2px; }
  p.h { color:#137A38; }"""
    return _page(css, band + _body(data))


# --------------------------------------------------------------------------- #
# 4 · الكحلي والذهبي
# --------------------------------------------------------------------------- #
def build_supply_contract_html_navy(data: dict[str, Any]) -> str:
    i = _ident(data)
    band = f"""<div class="band">{_logo(data, "#C9A227", "#0B2545")}
  <div><b>{i["name"]}</b><small>عقد رقم <span class="num">{i["number"]}</span> · <span class="num">{i["date"]}</span>م</small></div></div>"""
    css = """
  .band { display:flex; align-items:center; gap:14px; background:#0B2545; color:#fff; border-radius:6px 6px 0 0;
          border-bottom:5px solid #C9A227; padding:16px 20px 13px; margin-bottom:18px; }
  .band b { display:block; font-size:19px; }
  .band small { color:#CBD5E1; font-size:12px; }
  .ttl { color:#0B2545; }
  .ttl::after { content:""; display:block; width:80px; height:3px; background:#C9A227; margin:6px auto 0; }
  p.h { color:#0B2545; text-align:right; border-right:5px solid #C9A227; padding-right:10px; }
  .sigs p.h { text-align:center; border:none; padding:0; }"""
    return _page(css, band + _body(data))


# --------------------------------------------------------------------------- #
# 9 · العنابي الرسمي
# --------------------------------------------------------------------------- #
def build_supply_contract_html_maroon(data: dict[str, Any]) -> str:
    i = _ident(data)
    top = f"""<div class="top">{_logo(data, "#7F1D1D", "#fff")}<b>{i["name"]}</b>
  <span class="no">رقم العقد: <span class="num">{i["number"]}</span></span></div>"""
    css = """
  .top { display:flex; align-items:center; gap:14px; border-bottom:3px solid #7F1D1D; padding:6px 0 10px; margin-bottom:14px; }
  .top b { font-size:20px; color:#7F1D1D; }
  .top .no { margin-right:auto; color:#7F1D1D; font-size:13px; }
  .ttl { background:#7F1D1D; color:#fff; border-radius:4px; padding:6px; }
  p.h { color:#7F1D1D; }"""
    return _page(css, top + _body(data))


# --------------------------------------------------------------------------- #
# 10 · الخضار والفواكه
# --------------------------------------------------------------------------- #
def build_supply_contract_html_fresh(data: dict[str, Any]) -> str:
    i = _ident(data)
    uri = company_logo_data_uri(data.get("first_party_company") or {})
    mark = _logo(data, "#65A30D", "#fff") if uri else _FRUIT_SVG
    hero = f"""<div class="hero">{mark}<div><b>{i["name"]}</b><small>توريد الخضار والفواكه الطازجة</small></div>
  <span class="no">عقد رقم<br><b class="num">{i["number"]}</b></span></div>"""
    css = """
  .hero { display:flex; align-items:center; gap:14px; background:linear-gradient(135deg,#ECFCCB,#FEF3C7);
          border-bottom:4px solid #65A30D; border-radius:6px 6px 0 0; padding:14px 20px; margin-bottom:16px; }
  .hero b { display:block; font-size:19px; color:#365314; }
  .hero small { color:#92400E; font-size:12px; }
  .hero .no { margin-right:auto; text-align:left; color:#365314; font-size:12px; }
  .hero .no b { font-size:15px; }
  .ttl { color:#65A30D; }
  p.h { color:#C2410C; }"""
    return _page(css, hero + _body(data))


# --------------------------------------------------------------------------- #
# 11 · البطاقات
# --------------------------------------------------------------------------- #
def build_supply_contract_html_cards(data: dict[str, Any]) -> str:
    i = _ident(data)

    def b(key: str, long: bool = False) -> str:
        value = data.get(key)
        return print_blank("" if value is None else str(value).strip(), long)

    sections = dict(contract_sections(data, print_blank, stamp_html(data)))
    first = f"""<div class="box"><p class="h">الطرف الأول</p>
  <p>السادة / {b("first_party_name", True)}</p>
  <p>سجل تجاري رقم ( {b("first_party_cr")} ) مصدرها {b("first_party_cr_city")}</p>
  <p>ويمثلها السيد / {b("first_party_rep_name", True)}</p>
  <p>الجنسية {b("first_party_rep_nationality")} · سجل مدني ( {b("first_party_rep_id")} )</p>
  <p>بصفته {b("first_party_rep_title")} وعنوانها {b("first_party_address")}</p></div>"""
    second = f"""<div class="box"><p class="h">الطرف الثاني</p>
  <p>السادة / {b("second_party_name", True)}</p>
  <p>سجل تجاري رقم ( {b("second_party_cr")} ) مصدره {b("second_party_cr_city")} وفروعها في {b("second_party_branches")}</p>
  <p>ويمثلها السيد / {b("second_party_rep_name", True)}</p>
  <p>الجنسية {b("second_party_rep_nationality")} · هوية رقم ( {b("second_party_rep_id")} )</p>
  <p>بصفته {b("second_party_rep_title")} وعنوانه {b("second_party_address")}</p></div>"""
    boxed = "".join(
        f'<div class="box">{sections[key]}</div>'
        for key in ("preamble", "first", "second", "third", "fourth", "fifth", "sixth", "seventh")
    )
    body = f"""{sections["title"]}
<div class="meta"><span>رقم العقد: <b class="num">{i["number"]}</b></span><span>التاريخ: <b class="num">{i["date"]}</b>م</span></div>
<div class="box">{sections["opening"]}</div>
<div class="two">{first}{second}</div>
<div class="box">{sections["capacity"]}</div>
{boxed}
<div class="box">{sections["closing"]}</div>
{sections["signatures"]}"""
    css = """
  .sheet { background:#F8FAFC; padding:10px 12px; font-size:13.5px; line-height:1.7; }
  .ttl { color:#1D4ED8; }
  .meta { display:flex; justify-content:space-between; font-size:13px; color:#475569; margin-bottom:10px; }
  .meta b { color:#111; }
  .box { background:#fff; border:1px solid #E2E8F0; border-radius:9px; padding:8px 14px; margin-bottom:8px; }
  .box p.h { break-after:avoid; page-break-after:avoid; }
  .box p.h { text-align:right; color:#1D4ED8; margin:0 0 4px; }
  .two { display:grid; grid-template-columns:1fr 1fr; gap:8px; break-inside:avoid; page-break-inside:avoid; }
  .two .box p { text-align:right; margin-bottom:3px; }
  .sigs { background:#fff; border:1px solid #E2E8F0; border-radius:9px; }
  .sigs td { padding:10px; }
  .sigs p.h { color:#1D4ED8; text-align:center; }"""
    return _page(css, body)


__all__ = [
    "build_supply_contract_html_cards",
    "build_supply_contract_html_fresh",
    "build_supply_contract_html_green",
    "build_supply_contract_html_maroon",
    "build_supply_contract_html_navy",
]
