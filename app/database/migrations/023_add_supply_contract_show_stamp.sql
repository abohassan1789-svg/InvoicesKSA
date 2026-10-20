-- Migration 023 (UPGRADE): «طباعة الختم» on supply contracts.
--
-- Adds supply_contracts.show_stamp: whether the printed contract carries the
-- first party's company stamp. Defaults to true, so every existing contract
-- keeps printing its stamp. Mirrors the column in
-- app/database/schema/full_schema.sql (whose back-fill adds it on startup).
-- Reverse with 023_downgrade_supply_contract_show_stamp.sql.

BEGIN;

ALTER TABLE public.supply_contracts ADD COLUMN IF NOT EXISTS show_stamp boolean DEFAULT true NOT NULL;

COMMIT;
