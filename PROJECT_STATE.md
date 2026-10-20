# CRM Project State

Last updated: 2026-09-19

## «مصادقة على الرصيد» Balance Confirmations Screen (added 2026-10-20)

A new CRM screen (sidebar: **مصادقة على الرصيد**, after سندات القبض), in the
«الخطوات الثلاث» layout the user picked (mock-up 5 of 10):

- Table `balance_confirmations` (id, confirmation_number BC-001… from
  `balance_confirmation_number_seq`, confirmation_date, customer_id, nullable
  company_id = «كل الشركات», total_debit / total_credit / balance snapshot,
  description). Added to `schema/full_schema.sql` (auto-applied on startup) and
  as migration `021_*` (+ downgrade).
- `ReviewDataService.customer_balance(customer, company|None, as_of)` uses the
  same movements as كشف حساب العميل (invoices − cash-invoice settlements −
  receipt vouchers, up to the date). `save_record` always recomputes the
  snapshot; the form never sends it.
- Screen `balance_confirmations_screen.py` (BaseCrudScreen): 1 العميل والتاريخ /
  2 مراجعة الرصيد (live, «عليكم»/«لكم») / 3 البيان والحفظ («حفظ وطباعة»), list below.
- Letter `balance_confirmation_print.py`: the user's sample letter (Gregorian +
  Hijri «حتى تاريخ», amount in words, 15-day note, tear-off reply), preview /
  PDF / print via the voucher preview dialog.
- Print layouts (picker on «طباعة مصادقة», 2026-10-20): النموذج الأساسي plus the
  user's gallery picks 1, 2, 13, 14 — «الترويسة الكحلية», «الإطار المزدوج الرسمي»,
  «الأخضر المؤسسي», «المقارنة الجانبية» (`balance_confirmation_print_templates.py`),
  all with the chosen company's logo and stamp (none for «كل الشركات»).
- Permission target `crm.balance_confirmations.*`. Tests:
  `tests/unit/test_balance_confirmations.py`.

## «النموذج الثاني والعشرون» — «زيادة البركة» Replica (added 2026-10-20)

A layout replica of the user's ``barakah-raqia-template-stamped.pdf`` (شركة زيادة
البركة التجارية → مؤسسة الراقية للسبح والهدايا), added as **option 22 of both
invoice pickers** under the name **«النموذج الثاني والعشرون»**:

- Module `saudi_invoice_print_v28.py` (`build_invoice_html_v28`): seller, buyer,
  items, totals and stamp all live from ``data``; fixed Letter sheets paginated
  via `invoice_pagination` (header repeats, totals + stamp on the last page,
  «n / i» counter in the footer). Arabic is Noto Naskh Arabic, embedded from the
  bundled `noto_naskh_arabic_*.woff2` assets (SIL OFL), so no internet is needed.
- Phase-2 (`_choose_invoice_builder`) → `build_invoice_html_v28` with the signed
  tags 1–9 QR; «مرحلة أولى» → `build_phase1_invoice_barakah` (tags 1–5 QR).
- Seller seed: `tools/barakah_company/barakah_company.sql` adds the company
  (CR 7009631370, VAT 311369317100003) with the stamp lifted from the PDF;
  idempotent.
- Tests: `tests/unit/test_invoice_print_v28.py`, dispatch tests (22 options),
  description-column test includes v28.

## «نهلة الخليج» Invoice Template Re-shown in Both Phases (added 2026-10-20)

The «نهلة الخليج التجارية» replica (`saudi_invoice_print_v14.py`, formerly
labelled «نموذج أطياف», hidden on 2026-10-17) is back as the **last option
(21) of both invoice pickers**, under the name **«نهلة الخليج»**:

- Phase-2 (`SaudiSalesInvoicePage._choose_invoice_builder`) →
  `build_invoice_html_v14` with the signed tags 1–9 QR.
- «مرحلة أولى» (`PHASE1_TEMPLATE_OPTIONS` / `_PHASE1_BUILDERS[21]`) →
  `build_phase1_invoice_atyaf` with the tags 1–5 QR.
- Both pickers still list the same labels in the same order (now 21).
- Tests: `tests/unit/test_invoice_template_dispatch.py` updated (21 options,
  new last label, Phase-1 QR swap for choice 21).

## «سندات» Receipt-Voucher Column in the Search Dialog (added 2026-09-19)

A third per-row PDF link column, **«سندات»**, exports a **Phase-2 receipt voucher
(سند قبض)** for the row's invoice — same click → template picker → PDF-to-file
flow as «تصدير» / «مرحلة أولى». Column order (visual left→right): «تصدير»,
«مرحلة أولى», «سندات»; «تصدير» stays last.

- UI (`app/ui/dialogs/saudi_invoice_dialogs.py`): sentinel `_VOUCHER_COL_KEY`
  («سندات») added to `_COLUMNS` just before «مرحلة أولى»; `_LINK_COL_KEYS` now
  drives the hug-content sizing for all three link columns generically. New
  `voucher_callback` arg + `_make_voucher_cell` / `_on_voucher_clicked`, sharing
  the same `_run_row_action`.
- Page (`app/ui/screens/saudi_sales_invoice_page.py`):
  - `export_saved_voucher(invoice_id, dialog_parent=None)` — load by id →
    `choose_voucher_builder` (`saudi_receipt_voucher_print`, the same roster as
    the toolbar «طباعة سند») → `export_receipt_voucher_to_pdf`.
  - `_collect_voucher_data` refactored to delegate to the new
    `_voucher_data_from_preview(inv)`, so the on-screen voucher and the by-id
    export share one reshape; the export feeds it `_preview_data_from_record`.
  - `open_search` now also passes `voucher_callback=self.export_saved_voucher`.
- Tests: `tests/unit/test_saudi_invoice_search_dialog.py` (voucher column
  placement, a link per row, click → voucher callback with row id, graceful
  no-callback) and the page fake dialog updated for the new kwarg. Full invoice
  suite: **190 passed, 1 skipped**.

## «مرحلة أولى» PDF Column in the Search Dialog (added 2026-09-19)

The Saudi invoice search dialog now has a second per-row PDF link column,
**«مرحلة أولى»**, sitting immediately to the right of the existing **«تصدير»**
column. It behaves identically — click a row's link → template picker → PDF saved
straight to a file, without loading the invoice onto the form — but offers the
**Phase-1** template roster instead of the Phase-2 one.

- UI (`app/ui/dialogs/saudi_invoice_dialogs.py` → `SaudiInvoiceSearchDialog`):
  - New sentinel column key `_PHASE1_COL_KEY` («مرحلة أولى»); «تصدير»
    (`_EXPORT_COL_KEY`) stays the **last** column, «مرحلة أولى» is the one before
    it. Both link columns `ResizeToContents`.
  - New `phase1_callback` constructor arg (the Phase-2 twin is `print_callback`).
    Each row renders a «PDF» `_PdfLinkLabel`; `_make_phase1_cell` /
    `_on_phase1_clicked` mirror the export ones, and both now share
    `_run_row_action` (defers a tick, guards a missing callback with the same
    «خدمة التصدير غير متاحة» notice).
- Page (`app/ui/screens/saudi_sales_invoice_page.py`):
  - `export_saved_invoice_phase1(invoice_id, dialog_parent=None)` — the Phase-1
    twin of `print_saved_invoice`: `service.load` by id → `choose_invoice_template`
    over `PHASE1_TEMPLATE_OPTIONS` → `phase1_builder_for` → `export_phase1_invoice_pdf`
    on `_preview_data_from_record(loaded)`. Reserved (unbuilt) templates show the
    same «قيد الإنشاء» notice as the toolbar «مرحلة أولى → فواتير» flow.
  - `open_search` now passes `phase1_callback=self.export_saved_invoice_phase1`.
- Tests: `tests/unit/test_saudi_invoice_search_dialog.py` (column placement, a
  link per row, click → Phase-1 callback with the row id, Phase-1/Phase-2 links
  independent, graceful no-callback) and the `SaudiInvoiceSearchDialog` fake in
  `tests/unit/test_saudi_sales_invoice_page.py` updated for the new kwarg. Full
  invoice suite: **186 passed, 1 skipped**.

## Inline Invoice-Number Edit in the Search Dialog (added 2026-09-19)

The Saudi invoice search dialog (بحث عن فاتورة، F1 / the toolbar search button)
now lets the user edit an invoice's number **directly in the results grid**,
without opening the invoice onto the form first.

- UI (`app/ui/dialogs/saudi_invoice_dialogs.py` → `SaudiInvoiceSearchDialog`):
  - Only the «رقم الفاتورة» cell (column 0) of a **مسودة** row is editable;
    double-click / F2 / Enter / start-typing opens the inline editor. Every other
    cell stays read-only, and an **مُصدَّرة** (approved) row's number cell is
    locked (with an explanatory tooltip).
  - Double-clicking the number column edits it; double-clicking **any other**
    column still opens the invoice, exactly like the «فتح» button.
  - Committing a changed value calls the service immediately. On success the cell
    and the row's carried record are updated in place (no re-query); on failure
    (duplicate, blank, approved, concurrency) an Arabic warning is shown and the
    cell reverts to the stored value. A no-op edit (same value) writes nothing.
  - Column 0 now carries the whole invoice record in `Qt.UserRole` (was just the
    id) so the inline editor can validate and revert; `_accept` reads
    `record["id"]`.
- Service (`app/services/saudi_sales_invoice_service.py` →
  `rename_invoice_number(invoice_id, new_number, *, user_id=None)`): a lightweight
  path that changes only the number. Draft-only; the new number must be unique
  **for the same seller company** (same rule as create/update — numbering is
  per-company); requires the `edit` permission; no-op when unchanged.
- Repository (`app/repositories/saudi_sales_invoice_repository.py` →
  `update_invoice_number(...)`): updates only `invoice_number`, bumps
  `row_version` + `updated_at`, guarded by `document_status = 'draft'`, and writes
  an `update` audit row. Lines and Phase-2 data are untouched.
- Tests: `tests/unit/test_saudi_invoice_search_dialog.py` (inline edit: editable
  vs locked cells, persist, no-op, blank/duplicate revert, double-click routing)
  and `tests/services/test_saudi_sales_invoice_service.py` (rename: success,
  blank, per-seller duplicate, cross-seller allowed, no-op, approved refused,
  missing). Full invoice suite (dialogs + page + service + repository):
  **189 passed, 1 skipped**.

## Automatic Schema Bootstrap + Installer v4.4.9 (added 2026-07-27)

## Automatic Schema Bootstrap + Installer v4.4.9 (added 2026-07-27)

The application and installer now build the database schema automatically, so a
fresh device works with **no manual migration step**, and future schema changes
no longer need numbered migration files.

- `app/database/schema/full_schema.sql` — one idempotent DDL file (every
  `CREATE TABLE/SEQUENCE/INDEX` is `IF NOT EXISTS`; constraints wrapped in a
  `pg_constraint`-guarded `DO $$` block; identity columns guarded via
  `pg_attribute.attidentity`; triggers `DROP ... IF EXISTS` + create; functions
  `CREATE OR REPLACE`). Generated from a `pg_dump --schema-only` of the reference
  `InvPhase2` DB, made idempotent by a transformer; two artifact tables
  (`app_users_legacy`, `backup_006_customers_area_code`) excluded.
- `app/database/schema_bootstrap.py` → `ensure_full_schema(db)` runs it via
  `Database.execute_script`. Wired into app startup (`review_window.py`
  `_bootstrap_security`) and the installer (`configure_cli.py` `_cmd_provision`),
  both before the existing security `ensure_schema` (now a redundant no-op).
- Adding a table/column later: add one idempotent statement to `full_schema.sql`
  (`CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) — it
  self-applies on every device at next launch. No numbered migrations.
- Traps fixed while generating it: pg_dump comment headers contain `;`; pg_dump
  18 emits `\restrict`/`\unrestrict` psql meta-commands that break psycopg;
  pg_dump's `set_config('search_path','')` blanked the shared connection's
  search_path and broke the security schema's unqualified DDL — all stripped.
- Bundling: `installer/PHASEINV2-app.spec` datas gains `app/database/schema`;
  `build_main_device.ps1` validates `full_schema.sql` is present in the bundle.
- Verification:
  - Idempotent across repeated applies (psql ×3, psycopg ×2), 24 base tables.
  - Safe no-op on a full copy of the live database — **zero data loss** (row
    counts identical before/after).
  - End-to-end `configure_cli provision` on a fresh DB: `ok:true`, 24 tables +
    `sales_invoices` + Admin + 104 permissions, idempotent on re-run.
  - `tests/unit/test_schema_bootstrap.py` (6 passed); full unit suite 758 passed
    (only the two pre-existing failures remain).
- Installer rebuilt to **v4.4.9**: `Successful compile (299.6 sec)`, all bundle
  checks incl. "full schema bundled (auto-provision)" pass. Output
  `D:\PHASEINV2\dist\PHASEINV2_MainDevice_Setup.exe` (~178 MB). Pre-build backup
  kept: `PHASEINV2_MainDevice_Setup_BACKUP_v4.4.8_20260727_120245.exe`.

## Main Device Installer v4.4.8 (added 2026-07-27)

The Main Device Windows installer was rebuilt to ship the latest code.

- Version bump: `installer/PHASEINV2-MainDevice.iss` `MyAppVersion` **4.4.7 → 4.4.8**
  (with a changelog comment block). `AppId` is unchanged, so it upgrades in place.
- Included updates (all code, bundled automatically by re-running the build):
  - **"حفظ وإرسال واتساب"** sales-invoice action (save → silent PDF export to a
    remembered folder → open the customer's WhatsApp Web chat and auto-send the
    PDF, PDF-only).
  - **Company-stamp print alignment** (stamp in-flow directly under the totals on
    all 8 templates, with pagination safety).
  - **Global sales-invoice numbering** (one editable, globally-unique automatic
    number, starting at 50001).
- Build: `powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_main_device.ps1`
  ran clean — PyInstaller froze `PHASEINV2.exe` + `phaseinv2-config.exe`, all
  bundle validations passed (PySide6, QtWebEngine, psycopg, cryptography,
  migrations, ZATCA assets, all 8 print templates, frozen-config smoke test), and
  Inno Setup reported `Successful compile (303.8 sec)`.
- Output: `D:\PHASEINV2\dist\PHASEINV2_MainDevice_Setup.exe` (v4.4.8, ~178 MB).
  - Pre-build backup of the previous installer kept in the same folder:
    `PHASEINV2_MainDevice_Setup_BACKUP_v4.4.7_20260727_110113.exe`.
  - Verified the bundle actually carries the new code: the WhatsApp button string
    is present in `_internal\app\ui\screens\saudi_sales_invoice_page.py`, and
    migrations 017 + 018 are present under `_internal\app\database\migrations\`.
- ⚠️ **The installer ships the migration `.sql` files but does NOT apply them.**
  On every customer device, `017_add_company_stamp.sql` and
  `018_create_sales_invoice_numbering.sql` must be run by hand against that
  device's PostgreSQL DB, or the stamp and global-numbering features raise raw
  Postgres errors. (The local `InvPhase2` DB already has both applied.)

## Saudi Invoice Print Stamp Alignment (added 2026-07-27)

The optional company stamp now prints directly below the totals at the physical
right in all eight Saudi sales-invoice templates.

- Shared presentation:
  - The stamp uses a bounded `140px × 100px` box with `object-fit: contain`.
  - It prints at full opacity with controlled saturation, contrast, and
    brightness enhancement.
  - A 10px gap separates it from the totals, and it remains in normal document
    flow rather than being pinned to the page edge.
- Pagination safety:
  - Templates v3-v8 reserve the stamp's 110px vertical footprint on the last
    page only when **إظهار الختم** is enabled and valid company stamp bytes
    exist.
  - Stamp-free, disabled-stamp, and missing-stamp invoices keep their previous
    pagination.
- Verification:
  - Changed Python modules compile successfully with Python 3.11.
  - Targeted invoice-print regression suite: **292 passed, 1 skipped**.
  - Direct generated-HTML inspection confirmed the approved stamp contract in
    **8/8** templates.

## Global Saudi Sales Invoice Numbering (added 2026-07-27)

Saudi sales invoices now receive one editable, globally unique automatic
number shared by all seller companies.

- Automatic sequence:
  - PostgreSQL sequence: `sales_invoice_number_seq`.
  - Empty-database first number: `50001`, then `50002`, `50003`, and so on.
  - The sequence is concurrency-safe and reservations may leave gaps when a
    user cancels a new invoice.
  - A saved manual ASCII-numeric value at or above `50001` advances the
    sequence forward when necessary. Lower and non-numeric manual values never
    move it backward.
- Global uniqueness:
  - Migration `018_create_sales_invoice_numbering.sql` replaces the old
    seller-scoped unique constraint/index with
    `uq_sales_invoices_invoice_number` on `invoice_number`.
  - The repository and service now reject a duplicate number regardless of
    seller company.
  - Historical duplicates cause the migration to abort without renumbering or
    deleting any rows.
- UI:
  - **New** reserves and displays the next number while keeping the field
    editable.
  - **Duplicate Invoice** preserves copied invoice content but reserves a new
    number.
  - If reservation fails, an Arabic warning is shown and the field remains
    editable for manual entry.
  - Existing approved-invoice read-only behavior is unchanged.
- Live database application:
  - Safety backup created at
    `Backups/backup_manual_20260727_015827.sql`.
  - Migration 018 applied successfully to `InvPhase2`.
  - Immediately after application, the verified state was
    `last_value = 50001`, `is_called = false`, zero invoice rows, and only the
    global unique index.
  - The first real draft was subsequently created with invoice number `50001`.
    The live sequence is now `last_value = 50001`, `is_called = true`, so the
    next automatic invoice number is `50002`.
- Tests:
  - New isolated migration coverage handles both a standalone legacy index and
    the constraint-owned index used by the live database.
  - Targeted migration/repository/service/UI verification: **157 passed**.
  - Changed Python modules compile successfully.
  - Full suite: **1085 passed, 10 skipped, 3 failed**. The remaining failures
    are unrelated: two Daily Follow-up smart-report debounce/dropdown tests and
    `test_skeleton_imports_settings` (`CRM` expected versus `InvPhase2`).

## Saudi Invoice Save + WhatsApp Fix (added 2026-07-27)

The Saudi sales-invoice toolbar action **"حفظ وإرسال واتساب"** was saving and
exporting the invoice, but automatic WhatsApp delivery could miss the intended
customer or send the simulated keystrokes to the wrong window.

- Root causes in `app/ui/screens/saudi_sales_invoice_page.py`:
  - When WhatsApp Web was already open, the code searched the existing chat
    list instead of navigating to the customer's `send?phone=` URL. A new
    customer with no previous conversation therefore could not be selected.
  - The delayed `Ctrl+V` and `Enter` keystrokes were sent globally without
    refocusing WhatsApp Web immediately beforehand, so they could land in the
    CRM or another active window.
- Fix:
  - `_send_invoice_via_whatsapp(...)` now always opens the normalized customer
    number through `open_whatsapp_web_multi(target, "")`, even when WhatsApp Web
    is already open.
  - The flow calls `focus_whatsapp_web_window()` immediately before pasting the
    exported PDF and before every automatic send attempt.
  - Save failure, missing/invalid phone, PDF export failure, and browser-open
    failure still stop the flow through their existing guarded branches.
- Regression coverage in `tests/unit/test_saudi_sales_invoice_page.py`:
  - `test_whatsapp_send_opens_the_customer_url_even_when_whatsapp_is_already_open`
  - `test_whatsapp_send_refocuses_web_before_paste_and_send`
- Verification:
  - WhatsApp/invoice targeted suite: **113 passed**.
  - Python compile check for the changed page and test: passed.
  - No live customer message was sent during verification; external delivery
    was intentionally represented by controlled test doubles.

## F5 Smart Customer Entry on Daily Follow-up (added 2026-06-25)

Quick customer selection from the Daily Follow-up screen (شاشة المتابعة
اليية).

- Service: `app/services/review_data_service.py` ->
  `ReviewDataService.search_customers(keyword, limit=100)`.
  - Partial case-insensitive (`ILIKE`) search across `customer_id` (code),
    `customer_name`, and `phone_number` (Arabic + English work; partial phone
    numbers work).
  - Empty keyword returns all customers (`ORDER BY customer_id ASC LIMIT`).
  - Non-empty keyword orders an **exact code match first**, then by
    `customer_id ASC`.
  - Capped at 100 rows for performance.
  - Documented limitation: the `customers` table currently has **no separate
    mobile column** (only `phone_number`) and **no active/inactive flag** per
    `app/database/migrations/001_create_core_schema.sql`. If those are added,
    only this method needs a small `WHERE`/column change — noted in its
    docstring. No schema change was needed or made.
- Reusable UI: `app/ui/dialogs/customer_lookup_dialog.py` ->
  `CustomerLookupDialog`.
  - Title "اختيار العميل / Select Customer"; RTL; search box on top, results
    table below with column headers كود العميل / اسم العميل / الهاتف.
  - Reuses theme helpers (`GREEN`, `_button_style`); no SQL in the UI.
  - Search is debounced 200ms via `QTimer`; Enter = accept highlighted row,
    double-click = accept, Esc = close; null phone/code handled through the
    service `COALESCE` + cell `"" if None` rendering; "لا يوجد عملاء" shown
    on no results. Reads `selected_customer_id` / `selected_customer`.
- Daily Follow-up wiring: `app/ui/screens/daily_followups_screen.py` ->
  `DailyFollowupsScreen`.
  - Binds **F5** (`QShortcut`) to `open_customer_lookup()` — non-conflicting
    with the existing F1 record lookup.
  - On selection: enters a fresh new record (`new_record()` resets manual
    fields + defaults `follow_up_date` today), then fills **only
    customer-related fields** via the existing `_load_customer(...,
    prefill_installments=False)` (customer code/id, name, phone, area, building,
    unit, floor). Installments and other follow-up/status fields stay empty.
  - Moves focus to the first manual follow-up field (`follow_up_date`).
- Tests: `tests/unit/test_review_data_service.py` adds 2 cases for
  `search_customers` (empty keyword params; keyword params include the exact
  code sort key). All targeted UI/service tests pass (18 passed in
  `tests/unit/`) — only the pre-existing `test_skeleton_imports_settings`
  `CRM` vs `crm` assertion still fails, unchanged by this work.

## Working Directory

Main application folder:

`D:\PHASEINV2\CRM_PYTHON_APP_STRUCTURE`

The parent folder `D:\PHASEINV2` also contains Access analysis, PostgreSQL
design output, installers, and other reference material. The runnable PySide6
application is under `CRM_PYTHON_APP_STRUCTURE`.

## Users & Permissions system (added 2026-06-25)

A dynamic users/roles/permissions system was added with login and enforcement.

- DB layer: `app/database/db.py` (`Database` psycopg helper),
  `app/models/security_models.py` (DDL: roles, app_users, permissions,
  role_permissions, user_permissions, user_login_logs — all `IF NOT EXISTS`),
  `app/repositories/security_repository.py` (all SQL + `ensure_schema()`),
  migration `app/database/migrations/004_create_security_schema.sql`.
- Security primitives: `app/security/password_hasher.py` (PBKDF2-SHA256),
  `app/security/session_context.py` (`SESSION` — current user + effective codes,
  permissive when no user is logged in).
- Services: `app/services/permission_registry.py` (central screen/report/action
  registry; permission code = `module_code.target_code.action_code`; reports are
  auto-discovered from `app/reports/*` via a `PERMISSION_TARGET` attr),
  `app/services/permissions_sync_service.py` (upsert + deactivate-missing, never
  deletes), `app/services/permission_service.py` (effective resolution + matrix
  + role/override editing), `app/services/auth_service.py` (authenticate, seed
  Admin/1 full-access, login logs, user CRUD with last-admin guard).
- UI: `app/ui/login_window.py`, `app/ui/screens/users_page.py`,
  `roles_page.py`, `user_permissions_page.py`.
- Integration: `app/ui/main_window.py` has a collapsible RTL tree section
  "المستخدمين والصلاحيات" with 3 children; opening any screen is gated by the
  `view` permission and unviewable menu items are hidden. `base_crud_screen.py`
  gates New/Edit/Save/Delete by create/edit/save/delete. `run_app()` now:
  ensure schema → seed Admin/1 → sync permissions → login → load effective
  permissions into `SESSION` → splash → main window.
- Default login: **Admin / 1** (full access). Tests:
  `tests/unit/test_permission_system.py` (8 passed, no DB needed).

## Current App Shape

- Entry point: `app/main.py` -> `app/ui/review_window.py:run_app()`
- Active review UI is now split by module (see "UI Structure" below).
- Active CRUD/data metadata service: `app/services/review_data_service.py`
- PostgreSQL schema/migration scripts: `app/database/migrations/`
- Old per-form placeholder stubs still exist under `app/ui/screens/` (e.g. `customer_screen.py`, `login_screen.py`); they are unused legacy scaffolding, not the active screens.

## UI Structure (refactored 2026-06-25)

The previous single-file UI (`review_window.py`, ~929 lines, all screens in one
`QTabWidget`) was split into per-module screen files behind a sidebar shell.
Layering is UI / business / database:

- Shell + navigation: `app/ui/main_window.py` -> `ReviewMainWindow`.
  - Owns only the sidebar/main menu; its central area stays empty (a hint).
  - Each sidebar button opens its module as a **separate, maximized top-level
    window** via `open_screen(key)` (`showMaximized()`). Windows are cached per
    module in `open_windows` and re-focused if already open.
  - `MODULES` registry + `SCREEN_BY_KEY` map each screen; add a module there to
    expose it.
- Per-module screens (`app/ui/screens/`), each its own class:
  - `customers_screen.py` -> `CustomersScreen`
  - `employees_screen.py` -> `EmployeesScreen`
  - `daily_followups_screen.py` -> `DailyFollowupsScreen`
  - `places_screen.py` -> `PlacesScreen`
  - `case_statuses_screen.py` -> `CaseStatusesScreen`
- Reusable CRUD page: `app/ui/screens/base_crud_screen.py` -> `BaseCrudScreen`
  (was `ReviewCrudPage`; each screen subclasses it with its `TableSpec`).
- F1 lookup dialog: `app/ui/dialogs/record_lookup_dialog.py` -> `RecordLookupDialog`.
- Shared UI helpers: `app/ui/common/theme.py` (colors, button style, delegate,
  layout maps) and `app/ui/common/lookup_filters.py` (pure, unit-tested
  `filter_lookup_rows` / `project_visible_columns`).
- `app/ui/review_window.py` is now a thin launcher (`run_app()`) that re-exports
  the moved names for backward compatibility, so existing imports/tests like
  `from app.ui.review_window import filter_lookup_rows` and `ReviewCrudPage`
  still work.
- All database access still goes only through `ReviewDataService`; no SQL was
  moved into the UI. Screen behavior is unchanged from the tabbed version.

### Startup performance

To avoid the lag when a screen (especially daily follow-ups) was opened for the
first time:

- `ReviewDataService` now reuses **one long-lived autocommit connection**
  instead of opening/closing a PostgreSQL connection per query. `connect()` is
  now a context manager that yields the shared connection and reconnects if it
  goes stale. This is the main fix for first-open lag.
- On launch, `run_app()` shows a loading splash (`app/ui/common/loading_splash.py`
  -> `LoadingSplash`) and calls `ReviewMainWindow.prewarm_all(...)` to build every
  screen up front (daily follow-ups first) with a progress bar. Only when all
  screens are ready is the maximized main window shown — so it opens ready to use
  with no first-click lag. Clicking a module then re-uses its prebuilt window.
- `BaseCrudScreen._fill_combo` bulk-loads combos with view updates/signals
  disabled so filling the full customer list does not repaint per item.

## Latest Customer Screen Changes

Files changed for the latest customer-screen request:

- `app/ui/review_window.py`
  - Hides the four unused customer form fields:
    - `installment_duration_years`
    - `remaining_installments`
    - `installment_amount`
    - `legacy_area_number_2`
  - Uses a customer-only area selector for `place_area_feddan`, populated from `places`.
  - Adds an F1 customer lookup dialog.
  - The F1 dialog now shows only the search field and the results table (the "الأعمدة" column show/hide section was removed per request). Search runs across all non-hidden columns; double-click loads a customer into the main form.
  - Lookup table rebuild is optimized: columns/headers are set once, and row repopulation runs with `setUpdatesEnabled(False)` + a single `setRowCount(...)` to avoid per-keystroke repaint lag on the full customer list.
  - Search is debounced with a 200ms single-shot `QTimer`: typing restarts the timer and the table only refilters/redraws once typing pauses, instead of on every keystroke.
  - Makes the customer list panel wider and input controls slightly shorter.
  - Form layout is label-beside-input on one row (label right, input to its left), labels left-aligned within a 90px column.
  - All Customer Data input text is right-aligned: `QLineEdit` and the area `QComboBox` use `setLayoutDirection(Qt.LeftToRight)` + `setAlignment(Qt.AlignRight | Qt.AlignVCenter)` so both Arabic and numeric values sit on the visual right (RTL inheritance would otherwise flip `AlignRight`). The combo is editable+read-only with a right-aligned `lineEdit()`, and a `_RightAlignDelegate` right-aligns the dropdown items.
  - Input text matches the labels: `font-size:14px; font-weight:900; color:#111827`.

- `app/services/review_data_service.py`
  - Adds `FieldSpec.hidden_on_form`.
  - Adds `list_places_for_selection()`.
  - Adds `next_id()`.
  - Makes customer IDs start at `1001` when the table is empty; otherwise uses `MAX(customer_id) + 1`.
  - Keeps hidden form fields out of update payloads so editing a customer does not clear existing hidden values.

- `app/database/migrations/003_renumber_customers_from_1001.sql`
  - Renumbers existing customers to start at `1001`.
  - Updates `daily_followups.customer_id` through a temporary ID map in the same transaction.

- `tests/unit/test_review_data_service.py`
  - Covers hidden customer fields and customer ID generation.

- `tests/unit/test_customer_lookup_filter.py`
  - Covers lookup search and visible-column projection helpers.

## Verification State (updated 2026-07-27)

Passing WhatsApp/invoice verification:

```powershell
& 'C:\Users\esraa\AppData\Local\Programs\Python\Python311\python.exe' -m pytest tests\unit\test_saudi_invoice_whatsapp.py tests\unit\test_saudi_sales_invoice_page.py -q
```

Result:

`113 passed`

Passing compile check:

```powershell
& 'C:\Users\esraa\AppData\Local\Programs\Python\Python311\python.exe' -m py_compile app\ui\screens\saudi_sales_invoice_page.py tests\unit\test_saudi_sales_invoice_page.py
```

Full-suite result:

```powershell
& 'C:\Users\esraa\AppData\Local\Programs\Python\Python311\python.exe' -m pytest -q
```

Latest result: **1085 passed, 10 skipped, 3 failed**. The failures are outside
the WhatsApp and automatic-numbering changes:

- `tests/unit/test_daily_followup_smart_report_screen.py::test_customer_name_dropdown_remote_searches_full_customer_lookup_after_debounce`
  did not observe the expected debounced remote-search call.
- `tests/unit/test_daily_followup_smart_report_screen.py::test_customer_name_partial_search_opens_dropdown_with_all_matching_names`
  observed the preloaded placeholder/customer IDs instead of the debounced
  remote-search results.
- `tests/unit/test_skeleton.py::test_skeleton_imports_settings` expects database
  name `"CRM"`, while the current configuration returns `"InvPhase2"`.

## Python Note

Use the explicit Python 3.11 executable shown above for verification in this
checkout. The Python 3.12 installation currently resolves its prefix to the
working directory and fails during startup with `ModuleNotFoundError:
No module named 'encodings'`. The first `python` command on `PATH` still points
to the obsolete Python 3.4 installation.

## Git / CodeRabbit Note

`D:\PHASEINV2\CRM_PYTHON_APP_STRUCTURE` is a Git repository on branch
`feature/daily-followup-smart-report`. The working tree contains many existing
modified and untracked files. In particular, the Saudi invoice page and its
unit-test file currently appear as untracked, so both must be included
explicitly in any future commit containing this WhatsApp fix.
