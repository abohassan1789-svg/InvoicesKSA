-- Migration 020: invoice-level percentage discount before VAT.
-- Existing invoices remain unchanged: the new values default to zero and their
-- post-discount subtotal is initialized from the original subtotal.

BEGIN;

ALTER TABLE sales_invoices
    ADD COLUMN IF NOT EXISTS invoice_discount_rate numeric(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS invoice_discount_amount numeric(18,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS subtotal_after_discount numeric(18,2) NOT NULL DEFAULT 0;

UPDATE sales_invoices
   SET subtotal_after_discount = subtotal_before_vat - invoice_discount_amount
 WHERE subtotal_after_discount <> subtotal_before_vat - invoice_discount_amount;

ALTER TABLE sales_invoices
    DROP CONSTRAINT IF EXISTS ck_sales_invoices_total_matches_components;

ALTER TABLE sales_invoices
    ADD CONSTRAINT ck_sales_invoices_invoice_discount_rate_range
        CHECK (invoice_discount_rate >= 0 AND invoice_discount_rate <= 100),
    ADD CONSTRAINT ck_sales_invoices_invoice_discount_amount_nonnegative
        CHECK (invoice_discount_amount >= 0),
    ADD CONSTRAINT ck_sales_invoices_subtotal_after_discount_nonnegative
        CHECK (subtotal_after_discount >= 0),
    ADD CONSTRAINT ck_sales_invoices_subtotal_after_discount_matches_components
        CHECK (subtotal_after_discount = subtotal_before_vat - invoice_discount_amount),
    ADD CONSTRAINT ck_sales_invoices_total_matches_components
        CHECK (total_including_vat = subtotal_after_discount + vat_total);

COMMIT;
