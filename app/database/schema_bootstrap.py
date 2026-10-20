"""Automatic, idempotent full-schema bootstrap.

Runs the consolidated schema DDL in ``schema/full_schema.sql`` so that:

* a **fresh** database self-builds every table / sequence / index / constraint /
  trigger / function the application needs, and
* an **existing** database is left untouched — every statement is
  ``IF NOT EXISTS`` or guarded, so re-running it is a safe no-op that never
  changes data.

This is what lets a newly installed device work with **no manual migration
step**: the app runs this on startup and the installer runs it while
provisioning.

Adding a table or column later — the "no migrations" workflow
--------------------------------------------------------------
Edit ``schema/full_schema.sql`` and add an **idempotent** statement:

* new table  -> ``CREATE TABLE IF NOT EXISTS public.my_table (...);``
* new column -> ``ALTER TABLE public.my_table ADD COLUMN IF NOT EXISTS col TYPE;``
* new index  -> ``CREATE INDEX IF NOT EXISTS ... ;``

It then applies itself automatically on every device on the next launch. No
numbered migration files, no manual ``psql`` run. Complex one-off changes
(renames, type changes, data back-fills) still need a guarded ``DO $$ ... $$``
block, but they live in this same file.

Columns written only inside a CREATE TABLE
------------------------------------------
``CREATE TABLE IF NOT EXISTS`` is skipped whole when the table already exists,
so a column that was only added to the CREATE TABLE body (e.g. ``companies.stamp``)
never reached an older customer database — it failed at runtime with
``column "stamp" does not exist``. ``missing_columns_sql`` closes that gap: it
derives an ``ADD COLUMN IF NOT EXISTS`` for every column of every CREATE TABLE
in the file (plus a ``DROP NOT NULL`` where the file relaxed a column) and runs
them BEFORE the main script, so later indexes/constraints find them.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.database.db import Database

# schema/full_schema.sql sits next to this module (bundled as data in the frozen
# app via the same mechanism as app/database/migrations).
_SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema" / "full_schema.sql"

_CREATE_TABLE_RE = re.compile(
    r"^CREATE TABLE IF NOT EXISTS (public\.\w+) \((.*?)\n\);", re.S | re.M
)
# pg_dump 18 names NOT NULL constraints: ``col type CONSTRAINT x_not_null NOT NULL``.
_TRAILING_NOT_NULL_RE = re.compile(r"(\s+CONSTRAINT \w+)?\s+NOT NULL$")


def full_schema_sql() -> str:
    """Return the idempotent full-schema DDL text."""
    return _SCHEMA_SQL_PATH.read_text(encoding="utf-8")


def missing_columns_sql(schema_sql: str) -> str:
    """Back-fill script adding any CREATE TABLE column an existing table lacks.

    One guarded ``DO`` block per table: skipped while the table does not exist
    yet (the main script then creates it complete). Skipped per column:

    * ``CONSTRAINT`` lines — the main script adds constraints (guarded);
    * ``nextval(...)`` / ``GENERATED`` columns — identity/serial keys that exist
      since the table was created (a ``::regclass`` cast would also fail to
      parse if its sequence were missing).

    ``NOT NULL`` is kept only with a ``DEFAULT`` (existing rows get the default);
    without one it is dropped, since adding a NOT NULL column without a default
    to a table that has rows fails.

    Nullability drift is closed too: a column the file declares NULLABLE but an
    older table still has as NOT NULL gets ``DROP NOT NULL`` (e.g.
    ``sales_invoice_lines.product_id`` — migration 016 made it nullable for free
    lines, but that never reached old databases). Relaxing a constraint never
    touches data; primary-key columns are always ``NOT NULL`` in the file, so
    they are never relaxed.
    """
    blocks: list[str] = []
    for match in _CREATE_TABLE_RE.finditer(schema_sql):
        table, body = match.groups()
        alters: list[str] = []
        for raw in body.split("\n"):
            column = raw.strip().rstrip(",")
            if (
                not column
                or column.startswith("CONSTRAINT")
                or "nextval(" in column
                or " GENERATED " in column
            ):
                continue
            nullable = _TRAILING_NOT_NULL_RE.search(column) is None
            column = _TRAILING_NOT_NULL_RE.sub(
                " NOT NULL" if " DEFAULT " in column else "", column
            )
            alters.append(f"    ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column};")
            if nullable:
                name = column.split()[0]
                alters.append(
                    "    IF EXISTS (SELECT 1 FROM pg_attribute"
                    f" WHERE attrelid = '{table}'::regclass"
                    f" AND attname = '{name.strip(chr(34))}' AND attnotnull) THEN\n"
                    f"      ALTER TABLE {table} ALTER COLUMN {name} DROP NOT NULL;\n"
                    "    END IF;"
                )
        if alters:
            blocks.append(
                "DO $bf$ BEGIN\n"
                f"  IF to_regclass('{table}') IS NOT NULL THEN\n"
                + "\n".join(alters)
                + "\n  END IF;\nEND $bf$;"
            )
    return "\n\n".join(blocks)


def ensure_full_schema(db: Database | None = None) -> None:
    """Apply the idempotent full schema. Safe to run on every startup/provision.

    On a fresh database this creates the whole schema; on an existing one it
    first adds any columns an older version of a table lacks, then runs the
    (no-op) main script — nothing is dropped, no data is touched. Raises on a
    real database error (e.g. the server is unreachable) so callers can surface it.
    """
    db = db or Database()
    schema_sql = full_schema_sql()
    db.execute_script(missing_columns_sql(schema_sql))
    db.execute_script(schema_sql)
