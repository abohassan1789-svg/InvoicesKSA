-- Migration 022 (DOWNGRADE): reverse 022_create_supply_contracts_schema.sql.
--
-- Removes ONLY the objects migration 022 created. Dropping the table discards
-- the saved contracts; no other table or data is affected. Safe to re-run.

BEGIN;

DROP TRIGGER IF EXISTS trg_supply_contracts_set_updated_at ON supply_contracts;

-- Indexes go with the table; the sequence is OWNED BY the number column.
DROP TABLE IF EXISTS supply_contracts;

DROP SEQUENCE IF EXISTS supply_contract_number_seq;

DROP FUNCTION IF EXISTS supply_contracts_set_updated_at();

COMMIT;
