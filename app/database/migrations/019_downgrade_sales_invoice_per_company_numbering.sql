-- Migration 019 (DOWNGRADE): restore global Saudi sales-invoice numbering.
--
-- Rebuilds the table-wide unique index that migration 018 relied on. Because
-- per-company numbering allows the same number under different sellers, this
-- aborts (without changing anything) if such duplicates exist — they must be
-- resolved by hand before a global constraint can be re-imposed.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM sales_invoices
        GROUP BY invoice_number
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Cannot restore global invoice numbering: duplicate invoice numbers exist across sellers';
    END IF;
END $$;

DROP INDEX IF EXISTS uq_sales_invoices_company_number;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_invoices_invoice_number
    ON sales_invoices (invoice_number);

COMMIT;
