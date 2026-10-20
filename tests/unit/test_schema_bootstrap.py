"""Guards for the automatic idempotent full-schema bootstrap.

These run without a database: they assert the *shipped* ``full_schema.sql`` is
safe to run repeatedly (every object is IF NOT EXISTS / guarded, no psql-only
meta-commands that would break the psycopg runtime path) and that
``ensure_full_schema`` feeds it through the DB's script runner. The live
apply-twice / no-data-loss behaviour was verified against real databases during
development.
"""

from __future__ import annotations

import re

from app.database import schema_bootstrap


CORE_TABLES = (
    "customers", "app_users", "roles", "permissions", "companies", "products",
    "receipt_vouchers", "cashier_invoices", "cashier_invoice_lines",
    "sales_invoices", "sales_invoice_lines", "sales_invoice_zatca_data",
)


def test_full_schema_sql_loads_and_covers_core_tables():
    sql = schema_bootstrap.full_schema_sql()
    assert sql.strip()
    for table in CORE_TABLES:
        assert f"public.{table}" in sql, f"missing schema for {table}"


def test_no_psql_meta_commands_leak_into_the_script():
    # pg_dump 18 emits \restrict / \unrestrict; psql tolerates them but psycopg
    # (the app's runtime) raises a syntax error. They must be stripped.
    for line in schema_bootstrap.full_schema_sql().splitlines():
        assert not line.lstrip().startswith("\\"), f"psql meta-command leaked: {line!r}"


def test_every_create_is_idempotent():
    sql = schema_bootstrap.full_schema_sql()
    assert not re.search(r"(?im)^\s*CREATE TABLE (?!IF NOT EXISTS)", sql), \
        "a CREATE TABLE is missing IF NOT EXISTS"
    assert not re.search(r"(?im)^\s*CREATE SEQUENCE (?!IF NOT EXISTS)", sql), \
        "a CREATE SEQUENCE is missing IF NOT EXISTS"
    assert not re.search(r"(?im)^\s*CREATE (UNIQUE )?INDEX (?!IF NOT EXISTS)", sql), \
        "a CREATE INDEX is missing IF NOT EXISTS"


def test_constraints_and_identity_and_triggers_are_guarded():
    sql = schema_bootstrap.full_schema_sql()
    # Every ADD CONSTRAINT sits inside its own pg_constraint-guarded DO block —
    # so the counts match exactly (a bare, unguarded one would break the balance).
    add_constraints = len(re.findall(r"\bADD CONSTRAINT\b", sql))
    guards = sql.count("FROM pg_constraint")
    assert add_constraints > 0 and add_constraints == guards, \
        f"{add_constraints} ADD CONSTRAINT vs {guards} guards — an unguarded one exists"
    # Identity columns are guarded via pg_attribute.attidentity.
    assert "attidentity" in sql
    # Triggers are dropped-if-exists before create (version-safe idempotency).
    assert "DROP TRIGGER IF EXISTS" in sql


def test_artifact_tables_are_excluded():
    sql = schema_bootstrap.full_schema_sql()
    assert "app_users_legacy" not in sql
    assert "backup_006" not in sql


def test_ensure_full_schema_backfills_columns_then_runs_the_script():
    calls: list[str] = []

    class FakeDB:
        def execute_script(self, sql: str) -> None:
            calls.append(sql)

    schema_bootstrap.ensure_full_schema(FakeDB())
    assert len(calls) == 2
    # Column back-fill runs first, so the main script's indexes/constraints
    # already find columns an older table lacked.
    assert "ADD COLUMN IF NOT EXISTS stamp bytea" in calls[0]
    assert "CREATE TABLE IF NOT EXISTS public.sales_invoices" in calls[1]


def test_backfill_covers_columns_that_only_live_in_create_table():
    # companies.stamp was only ever in the CREATE TABLE body, so an older
    # customer database never got it ("column "stamp" does not exist").
    sql = schema_bootstrap.missing_columns_sql(schema_bootstrap.full_schema_sql())
    for table, column in (
        ("companies", "stamp"), ("companies", "stamp_mime"),
        ("companies", "logo"), ("customers", "vat_number"),
        ("customers", "address"),
    ):
        assert f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS {column} " in sql
    # Each table is guarded so a not-yet-created table is simply skipped.
    assert "IF to_regclass('public.companies') IS NOT NULL THEN" in sql


def test_backfill_never_adds_a_bare_not_null_or_constraint():
    sql = schema_bootstrap.missing_columns_sql(schema_bootstrap.full_schema_sql())
    for line in sql.splitlines():
        if "ADD COLUMN" not in line:
            continue
        assert "CONSTRAINT" not in line, line
        assert "nextval(" not in line and " GENERATED " not in line, line
        if line.endswith(" NOT NULL;"):
            assert " DEFAULT " in line, f"NOT NULL without DEFAULT fails on a table with rows: {line}"


def test_backfill_parsing_of_a_pg_dump_18_table():
    sql = (
        "CREATE TABLE IF NOT EXISTS public.t (\n"
        "    id integer CONSTRAINT t_id_not_null NOT NULL,\n"
        "    code integer DEFAULT nextval('public.t_seq'::regclass) NOT NULL,\n"
        "    total numeric GENERATED ALWAYS AS ((a * b)) STORED,\n"
        "    flag boolean DEFAULT false CONSTRAINT t_flag_not_null NOT NULL,\n"
        "    note text,\n"
        "    CONSTRAINT ck_t CHECK ((id > 0))\n"
        ");"
    )
    out = schema_bootstrap.missing_columns_sql(sql)
    assert "ADD COLUMN IF NOT EXISTS id integer;" in out
    assert "ADD COLUMN IF NOT EXISTS flag boolean DEFAULT false NOT NULL;" in out
    assert "ADD COLUMN IF NOT EXISTS note text;" in out
    assert "code" not in out and "total" not in out and "ck_t" not in out
    # Nullable in the file -> relaxed on an old table; NOT NULL columns never are.
    assert "ALTER TABLE public.t ALTER COLUMN note DROP NOT NULL;" in out
    assert "ALTER COLUMN id DROP NOT NULL" not in out
    assert "ALTER COLUMN flag DROP NOT NULL" not in out


def test_backfill_relaxes_free_line_product_id():
    # Migration 016 made sales_invoice_lines.product_id nullable (free lines);
    # an older client database must get that through the bootstrap too.
    sql = schema_bootstrap.missing_columns_sql(schema_bootstrap.full_schema_sql())
    assert "ALTER TABLE public.sales_invoice_lines ALTER COLUMN product_id DROP NOT NULL;" in sql
