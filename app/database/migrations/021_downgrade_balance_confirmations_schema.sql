-- Migration 021 (DOWNGRADE): reverse 021_create_balance_confirmations_schema.sql.
--
-- Removes ONLY the objects migration 021 created. Dropping the table discards
-- the saved confirmations; no other table or data is affected. Safe to re-run.

BEGIN;

DROP TRIGGER IF EXISTS trg_balance_confirmations_set_updated_at ON balance_confirmations;

-- Indexes go with the table; the sequence is OWNED BY the number column.
DROP TABLE IF EXISTS balance_confirmations;

DROP SEQUENCE IF EXISTS balance_confirmation_number_seq;

DROP FUNCTION IF EXISTS balance_confirmations_set_updated_at();

COMMIT;
