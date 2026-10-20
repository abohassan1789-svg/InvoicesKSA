-- Migration 023 (DOWNGRADE): reverse 023_add_supply_contract_show_stamp.sql.
--
-- Drops only the show_stamp column; the contracts themselves are untouched.

BEGIN;

ALTER TABLE public.supply_contracts DROP COLUMN IF EXISTS show_stamp;

COMMIT;
