-- Migration 022 (UPGRADE): Supply Contracts schema (عقود التوريد).
--
-- Creates the standalone ``supply_contracts`` table: one row per fruit &
-- vegetable supply contract with the values typed into its blanks (both
-- parties, representatives, supply sites, payment days, bank account). The
-- contract clauses are fixed text in the print module, never stored.
-- contract_number defaults to CT-0001, CT-0002, ... from its own sequence.
--
-- Mirrors the block in app/database/schema/full_schema.sql (which is what new
-- and existing installs actually run on startup). Additive and idempotent: no
-- existing table or row is touched. Reverse with
-- 022_downgrade_supply_contracts_schema.sql.

BEGIN;

CREATE SEQUENCE IF NOT EXISTS public.supply_contract_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.supply_contracts (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contract_number character varying(30) DEFAULT ('CT-'::text || to_char(nextval('public.supply_contract_number_seq'::regclass), 'FM0000'::text)) NOT NULL,
    contract_date date DEFAULT CURRENT_DATE NOT NULL,
    first_party_company_id integer,
    first_party_name character varying(255) DEFAULT ''::character varying NOT NULL,
    first_party_cr character varying(50),
    first_party_cr_city character varying(100),
    first_party_address text,
    first_party_rep_name character varying(255),
    first_party_rep_nationality character varying(100),
    first_party_rep_id character varying(50),
    first_party_rep_title character varying(100),
    second_party_customer_id integer,
    second_party_name character varying(255) DEFAULT ''::character varying NOT NULL,
    second_party_cr character varying(50),
    second_party_cr_city character varying(100),
    second_party_branches text,
    second_party_address text,
    second_party_rep_name character varying(255),
    second_party_rep_nationality character varying(100),
    second_party_rep_id character varying(50),
    second_party_rep_title character varying(100),
    supply_sites text,
    payment_days_after_first_supply integer,
    payment_days_after_statement integer,
    bank_name character varying(255),
    bank_account character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer,
    updated_by integer,
    CONSTRAINT ck_supply_contracts_number_not_blank CHECK ((char_length(btrim((contract_number)::text)) > 0)),
    CONSTRAINT ck_supply_contracts_first_party_not_blank CHECK ((char_length(btrim((first_party_name)::text)) > 0)),
    CONSTRAINT ck_supply_contracts_second_party_not_blank CHECK ((char_length(btrim((second_party_name)::text)) > 0)),
    CONSTRAINT ck_supply_contracts_payment_days CHECK (((payment_days_after_first_supply IS NULL OR payment_days_after_first_supply >= 0) AND (payment_days_after_statement IS NULL OR payment_days_after_statement >= 0)))
);

ALTER SEQUENCE public.supply_contract_number_seq OWNED BY public.supply_contracts.contract_number;

CREATE UNIQUE INDEX IF NOT EXISTS uq_supply_contracts_number ON public.supply_contracts USING btree (contract_number);
CREATE INDEX IF NOT EXISTS idx_supply_contracts_date ON public.supply_contracts USING btree (contract_date);
CREATE INDEX IF NOT EXISTS idx_supply_contracts_first_party_company_id ON public.supply_contracts USING btree (first_party_company_id);
CREATE INDEX IF NOT EXISTS idx_supply_contracts_second_party_customer_id ON public.supply_contracts USING btree (second_party_customer_id);

CREATE OR REPLACE FUNCTION public.supply_contracts_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_supply_contracts_set_updated_at ON public.supply_contracts;
CREATE TRIGGER trg_supply_contracts_set_updated_at BEFORE UPDATE ON public.supply_contracts FOR EACH ROW EXECUTE FUNCTION public.supply_contracts_set_updated_at();

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_supply_contracts_first_party_company' AND conrelid = 'public.supply_contracts'::regclass) THEN
    ALTER TABLE ONLY public.supply_contracts ADD CONSTRAINT fk_supply_contracts_first_party_company FOREIGN KEY (first_party_company_id) REFERENCES public.companies(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_supply_contracts_second_party_customer' AND conrelid = 'public.supply_contracts'::regclass) THEN
    ALTER TABLE ONLY public.supply_contracts ADD CONSTRAINT fk_supply_contracts_second_party_customer FOREIGN KEY (second_party_customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_supply_contracts_created_by' AND conrelid = 'public.supply_contracts'::regclass) THEN
    ALTER TABLE ONLY public.supply_contracts ADD CONSTRAINT fk_supply_contracts_created_by FOREIGN KEY (created_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_supply_contracts_updated_by' AND conrelid = 'public.supply_contracts'::regclass) THEN
    ALTER TABLE ONLY public.supply_contracts ADD CONSTRAINT fk_supply_contracts_updated_by FOREIGN KEY (updated_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END $$;

COMMIT;
