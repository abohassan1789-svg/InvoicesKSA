-- Migration 019 (UPGRADE): per-company Saudi sales-invoice numbering.
--
-- Reverses the "global shared numbering" of migration 018. Each seller company
-- now owns an independent 1-based sequence: numbers are computed on demand as
-- MAX(existing number for that company) + 1 (see
-- SaudiSalesInvoiceRepository.next_invoice_number), and uniqueness is scoped to
-- (seller_company_id, invoice_number) instead of the whole table.
--
-- The previous table-wide unique index is strictly stronger than the composite
-- one, so no existing row can conflict when switching. Existing invoice numbers
-- are never renumbered by this migration.

BEGIN;

-- Swap the global unique index for the per-company composite one.
DROP INDEX IF EXISTS uq_sales_invoices_invoice_number;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_invoices_company_number
    ON sales_invoices (seller_company_id, invoice_number);

-- The old shared sequence is no longer consulted (numbering is derived from the
-- table per company). It is left in place harmlessly; the downgrade re-seeds it.

COMMIT;
