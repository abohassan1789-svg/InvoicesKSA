-- Migration 021 (UPGRADE): Balance Confirmations schema (مصادقة على الرصيد).
--
-- Creates the standalone ``balance_confirmations`` table: one row per balance-
-- confirmation letter sent to a customer, with a snapshot of the customer's
-- statement balance (invoices − cash settlements − receipt vouchers) as of the
-- confirmation date, for one company or for every company (company_id NULL).
-- confirmation_number defaults to BC-001, BC-002, ... from its own sequence.
--
-- Mirrors the block in app/database/schema/full_schema.sql (which is what new
-- and existing installs actually run on startup). Additive and idempotent: no
-- existing table or row is touched. Reverse with
-- 021_downgrade_balance_confirmations_schema.sql.

BEGIN;

CREATE SEQUENCE IF NOT EXISTS public.balance_confirmation_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.balance_confirmations (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    confirmation_number character varying(30) DEFAULT ('BC-'::text || to_char(nextval('public.balance_confirmation_number_seq'::regclass), 'FM000'::text)) NOT NULL,
    confirmation_date date DEFAULT CURRENT_DATE NOT NULL,
    customer_id integer NOT NULL,
    company_id integer,
    total_debit numeric(18,2) DEFAULT 0 NOT NULL,
    total_credit numeric(18,2) DEFAULT 0 NOT NULL,
    balance numeric(18,2) DEFAULT 0 NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer,
    updated_by integer,
    CONSTRAINT ck_balance_confirmations_number_not_blank CHECK ((char_length(btrim((confirmation_number)::text)) > 0)),
    CONSTRAINT ck_balance_confirmations_balance_matches CHECK ((balance = (total_debit - total_credit)))
);

ALTER SEQUENCE public.balance_confirmation_number_seq OWNED BY public.balance_confirmations.confirmation_number;

CREATE UNIQUE INDEX IF NOT EXISTS uq_balance_confirmations_number ON public.balance_confirmations USING btree (confirmation_number);
CREATE INDEX IF NOT EXISTS idx_balance_confirmations_date ON public.balance_confirmations USING btree (confirmation_date);
CREATE INDEX IF NOT EXISTS idx_balance_confirmations_customer_id ON public.balance_confirmations USING btree (customer_id);
CREATE INDEX IF NOT EXISTS idx_balance_confirmations_company_id ON public.balance_confirmations USING btree (company_id);

CREATE OR REPLACE FUNCTION public.balance_confirmations_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_balance_confirmations_set_updated_at ON public.balance_confirmations;
CREATE TRIGGER trg_balance_confirmations_set_updated_at BEFORE UPDATE ON public.balance_confirmations FOR EACH ROW EXECUTE FUNCTION public.balance_confirmations_set_updated_at();

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_balance_confirmations_customer' AND conrelid = 'public.balance_confirmations'::regclass) THEN
    ALTER TABLE ONLY public.balance_confirmations ADD CONSTRAINT fk_balance_confirmations_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_balance_confirmations_company' AND conrelid = 'public.balance_confirmations'::regclass) THEN
    ALTER TABLE ONLY public.balance_confirmations ADD CONSTRAINT fk_balance_confirmations_company FOREIGN KEY (company_id) REFERENCES public.companies(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_balance_confirmations_created_by' AND conrelid = 'public.balance_confirmations'::regclass) THEN
    ALTER TABLE ONLY public.balance_confirmations ADD CONSTRAINT fk_balance_confirmations_created_by FOREIGN KEY (created_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_balance_confirmations_updated_by' AND conrelid = 'public.balance_confirmations'::regclass) THEN
    ALTER TABLE ONLY public.balance_confirmations ADD CONSTRAINT fk_balance_confirmations_updated_by FOREIGN KEY (updated_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END $$;

COMMIT;
