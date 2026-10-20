-- full_schema.sql — AUTO-GENERATED idempotent schema bootstrap.
-- Source: pg_dump --schema-only of the reference InvPhase2 database, made
-- safe to run repeatedly. Runs on app startup and installer provisioning so
-- a fresh database self-builds and an existing one gains only what it lacks.
-- To add a table/column later: add an idempotent statement (CREATE TABLE IF
-- NOT EXISTS / ALTER TABLE ... ADD COLUMN IF NOT EXISTS) — no migration files.

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';

CREATE OR REPLACE FUNCTION public.cashier_invoice_lines_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.cashier_invoices_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.companies_normalize() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.name_ar := btrim(NEW.name_ar);
    NEW.commercial_registration := NULLIF(btrim(NEW.commercial_registration), '');
    NEW.vat_number := btrim(NEW.vat_number);
    NEW.name_en := NULLIF(btrim(NEW.name_en), '');
    NEW.address_ar := NULLIF(btrim(NEW.address_ar), '');
    NEW.address_en := NULLIF(btrim(NEW.address_en), '');
    IF TG_OP = 'UPDATE' THEN
        NEW.updated_at := now();
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.products_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.receipt_vouchers_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.sales_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.app_users (
    id integer NOT NULL,
    username character varying(60) CONSTRAINT app_users_username_not_null1 NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(120),
    email character varying(120),
    phone character varying(40),
    role_id integer,
    language character varying(10) DEFAULT 'ar'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    full_access boolean DEFAULT false NOT NULL,
    notes text,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS public.app_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.app_users_id_seq OWNED BY public.app_users.id;

CREATE TABLE IF NOT EXISTS public.backup_logs (
    id integer NOT NULL,
    backup_type character varying(20) NOT NULL,
    file_name character varying(255),
    file_path text,
    status character varying(20) NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer
);

CREATE SEQUENCE IF NOT EXISTS public.backup_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.backup_logs_id_seq OWNED BY public.backup_logs.id;

CREATE TABLE IF NOT EXISTS public.case_statuses (
    case_status_id integer NOT NULL,
    case_status_name character varying(90)
);

CREATE SEQUENCE IF NOT EXISTS public.case_statuses_case_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.case_statuses_case_status_id_seq OWNED BY public.case_statuses.case_status_id;

CREATE TABLE IF NOT EXISTS public.cashier_invoice_lines (
    id integer NOT NULL,
    cashier_invoice_id integer NOT NULL,
    line_number integer NOT NULL,
    product_id integer NOT NULL,
    product_code_snapshot character varying(100),
    product_name_snapshot character varying(255),
    quantity numeric(18,6) DEFAULT 1 NOT NULL,
    unit_price numeric(18,6) DEFAULT 0 NOT NULL,
    line_subtotal numeric(18,2) DEFAULT 0 NOT NULL,
    vat_rate numeric(5,2) DEFAULT 15.00 NOT NULL,
    vat_amount numeric(18,2) DEFAULT 0 NOT NULL,
    line_total numeric(18,2) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_cashier_invoice_lines_line_number_positive CHECK ((line_number > 0)),
    CONSTRAINT ck_cashier_invoice_lines_line_subtotal_non_negative CHECK ((line_subtotal >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoice_lines_line_total_non_negative CHECK ((line_total >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoice_lines_quantity_positive CHECK ((quantity > (0)::numeric)),
    CONSTRAINT ck_cashier_invoice_lines_unit_price_non_negative CHECK ((unit_price >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoice_lines_vat_amount_non_negative CHECK ((vat_amount >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoice_lines_vat_rate_range CHECK (((vat_rate >= (0)::numeric) AND (vat_rate <= (100)::numeric)))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.cashier_invoice_lines'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.cashier_invoice_lines ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cashier_invoice_lines_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.cashier_invoices (
    id integer NOT NULL,
    invoice_number character varying(100) NOT NULL,
    invoice_uuid uuid,
    invoice_date date DEFAULT CURRENT_DATE NOT NULL,
    invoice_time time without time zone DEFAULT LOCALTIME NOT NULL,
    invoice_datetime timestamp with time zone DEFAULT now() NOT NULL,
    customer_id integer,
    company_id integer NOT NULL,
    branch_id integer,
    created_by_user_id integer,
    invoice_status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    invoice_type character varying(20) DEFAULT 'SIMPLIFIED'::character varying NOT NULL,
    currency_code character(3) DEFAULT 'SAR'::bpchar NOT NULL,
    subtotal numeric(18,2) DEFAULT 0 NOT NULL,
    vat_amount numeric(18,2) DEFAULT 0 NOT NULL,
    grand_total numeric(18,2) DEFAULT 0 NOT NULL,
    notes text,
    seller_name_snapshot character varying(255),
    seller_vat_number_snapshot character varying(15),
    seller_commercial_registration_snapshot character varying(50),
    seller_address_snapshot text,
    buyer_name_snapshot character varying(255),
    buyer_vat_number_snapshot character varying(15),
    zatca_icv bigint,
    zatca_previous_invoice_hash text,
    zatca_invoice_hash text,
    zatca_qr_base64 text,
    zatca_xml text,
    zatca_signed_xml text,
    zatca_cryptographic_stamp text,
    zatca_public_key text,
    zatca_signature text,
    zatca_status character varying(30) DEFAULT 'NOT_GENERATED'::character varying NOT NULL,
    zatca_response text,
    zatca_reported_at timestamp with time zone,
    print_count integer DEFAULT 0 NOT NULL,
    last_printed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_cashier_invoices_grand_total_non_negative CHECK ((grand_total >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoices_invoice_number_not_blank CHECK ((char_length(btrim((invoice_number)::text)) > 0)),
    CONSTRAINT ck_cashier_invoices_invoice_status CHECK (((invoice_status)::text = ANY ((ARRAY['DRAFT'::character varying, 'ISSUED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT ck_cashier_invoices_invoice_type CHECK (((invoice_type)::text = 'SIMPLIFIED'::text)),
    CONSTRAINT ck_cashier_invoices_print_count_non_negative CHECK ((print_count >= 0)),
    CONSTRAINT ck_cashier_invoices_subtotal_non_negative CHECK ((subtotal >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoices_vat_amount_non_negative CHECK ((vat_amount >= (0)::numeric)),
    CONSTRAINT ck_cashier_invoices_zatca_status CHECK (((zatca_status)::text = ANY ((ARRAY['NOT_GENERATED'::character varying, 'READY'::character varying, 'PENDING'::character varying, 'REPORTED'::character varying, 'ACCEPTED'::character varying, 'ACCEPTED_WITH_WARNINGS'::character varying, 'REJECTED'::character varying, 'FAILED'::character varying])::text[])))
);

CREATE SEQUENCE IF NOT EXISTS public.cashier_invoice_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.cashier_invoice_number_seq OWNED BY public.cashier_invoices.invoice_number;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.cashier_invoices'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.cashier_invoices ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.cashier_invoices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.companies (
    id integer NOT NULL,
    name_ar character varying(255) NOT NULL,
    name_en character varying(255),
    commercial_registration character varying(50),
    vat_number character varying(50) NOT NULL,
    address_ar text,
    address_en text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    logo bytea,
    logo_mime character varying(64),
    stamp bytea,
    stamp_mime character varying(64),
    CONSTRAINT ck_companies_name_ar_not_blank CHECK ((char_length(btrim((name_ar)::text)) > 0)),
    CONSTRAINT ck_companies_vat_number_not_blank CHECK ((char_length(btrim((vat_number)::text)) > 0))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.companies'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.companies ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.companies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.company_settings (
    company_name_ar character varying(80),
    general_manager_name character varying(80),
    email_address character varying(25),
    mobile_number character varying(25),
    website_url character varying(60),
    address character varying(80),
    commercial_registry_number character varying(25),
    tax_number character varying(25),
    image_path character varying(255),
    company_name_en character varying(80),
    civil_defense_license_number character varying(50),
    civil_defense_license_start_date timestamp without time zone,
    civil_defense_license_end_date timestamp without time zone,
    municipality_license_number character varying(50),
    municipality_license_start_date timestamp without time zone,
    municipality_license_end_date timestamp without time zone
);

CREATE SEQUENCE IF NOT EXISTS public.crm_attachment_code_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.crm_attachments (
    id integer NOT NULL,
    attachment_code character varying(40) NOT NULL,
    entity_type character varying(60) DEFAULT 'Other'::character varying NOT NULL,
    entity_id integer,
    title character varying(200) NOT NULL,
    category character varying(60),
    original_file_name character varying(255) NOT NULL,
    file_extension character varying(20),
    mime_type character varying(120),
    file_size bigint DEFAULT 0 NOT NULL,
    file_hash character varying(64),
    file_data bytea NOT NULL,
    notes text,
    tags text,
    is_favorite boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer,
    updated_by integer
);

CREATE SEQUENCE IF NOT EXISTS public.crm_attachments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.crm_attachments_id_seq OWNED BY public.crm_attachments.id;

CREATE TABLE IF NOT EXISTS public.customers (
    customer_id integer NOT NULL,
    phone_number character varying(40),
    customer_name character varying(100),
    place_area_feddan integer,
    area_number character varying(30),
    building character varying(30),
    unit_number character varying(30),
    floor_number character varying(60),
    installment_duration_years integer,
    remaining_installments integer,
    installment_amount integer,
    legacy_area_number_2 character varying(30),
    vat_number character varying(50),
    cr character varying(50),
    address text
);

CREATE SEQUENCE IF NOT EXISTS public.customers_customer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.customers_customer_id_seq OWNED BY public.customers.customer_id;

CREATE TABLE IF NOT EXISTS public.daily_followups (
    daily_followup_id integer NOT NULL,
    sequence_number integer DEFAULT 0,
    follow_up_date timestamp without time zone,
    customer_id integer,
    employee_id integer,
    case_status_id integer,
    notes character varying(150),
    follow_up_month smallint,
    follow_up_year smallint,
    legacy_month_year_code character varying(243),
    contact_count integer DEFAULT 1,
    installment_duration_years double precision,
    remaining_installments double precision,
    installment_amount double precision,
    installment_type character varying(50),
    buyer_name character varying(90),
    buyer_phone_number character varying(90),
    unit_sale_amount double precision,
    seller_commission_amount double precision,
    buyer_commission_amount double precision
);

CREATE SEQUENCE IF NOT EXISTS public.daily_followups_daily_followup_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.daily_followups_daily_followup_id_seq OWNED BY public.daily_followups.daily_followup_id;

CREATE TABLE IF NOT EXISTS public.employees (
    employee_id integer NOT NULL,
    phone_number character varying(40) NOT NULL,
    employee_name character varying(100),
    governorate character varying(100),
    district_center character varying(100),
    village character varying(100)
);

CREATE SEQUENCE IF NOT EXISTS public.employees_employee_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.employees_employee_id_seq OWNED BY public.employees.employee_id;

CREATE TABLE IF NOT EXISTS public.permissions (
    id integer NOT NULL,
    permission_code character varying(150) NOT NULL,
    permission_type character varying(20) NOT NULL,
    module_code character varying(50),
    module_name_ar character varying(120),
    module_name_en character varying(120),
    category_ar character varying(120),
    category_en character varying(120),
    target_code character varying(80),
    target_name_ar character varying(150),
    target_name_en character varying(150),
    action_code character varying(40),
    action_name_ar character varying(80),
    action_name_en character varying(80),
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;

CREATE TABLE IF NOT EXISTS public.places (
    place_id integer NOT NULL,
    place_number character varying(50)
);

CREATE SEQUENCE IF NOT EXISTS public.places_place_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.places_place_id_seq OWNED BY public.places.place_id;

CREATE TABLE IF NOT EXISTS public.products (
    id integer NOT NULL,
    item_code character varying(50) NOT NULL,
    item_name character varying(200) NOT NULL,
    quantity numeric(18,3) DEFAULT 0 NOT NULL,
    price numeric(18,2) DEFAULT 0 NOT NULL,
    total numeric(23,5) GENERATED ALWAYS AS ((quantity * price)) STORED,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_products_item_name_not_blank CHECK ((char_length(btrim((item_name)::text)) > 0)),
    CONSTRAINT ck_products_price_non_negative CHECK ((price >= (0)::numeric)),
    CONSTRAINT ck_products_quantity_non_negative CHECK ((quantity >= (0)::numeric))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.products'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.products ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.products_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE SEQUENCE IF NOT EXISTS public.products_item_code_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.products_item_code_seq OWNED BY public.products.item_code;

-- كود الصنف is user-editable and may be alphanumeric (e.g. "W-119"), so it is
-- text, not an integer. On an EXISTING database whose products.item_code is still
-- integer, convert it to varchar(50) in place (data preserved as its digits' text)
-- and switch the auto-default to the sequence cast to text. Guarded so it runs at
-- most once and is a no-op on a fresh/already-text database.
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'products'
      AND column_name = 'item_code' AND data_type = 'integer'
  ) THEN
    ALTER TABLE public.products ALTER COLUMN item_code DROP DEFAULT;
    ALTER TABLE public.products
        ALTER COLUMN item_code TYPE character varying(50) USING item_code::text;
    ALTER TABLE public.products
        ALTER COLUMN item_code SET DEFAULT nextval('public.products_item_code_seq'::regclass)::text;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.receipt_vouchers (
    id integer NOT NULL,
    voucher_number character varying(30) NOT NULL,
    voucher_date date DEFAULT CURRENT_DATE NOT NULL,
    customer_id integer NOT NULL,
    company_id integer NOT NULL,
    payment_type character varying(20) NOT NULL,
    amount numeric(18,2) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by integer,
    updated_by integer,
    CONSTRAINT ck_receipt_vouchers_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ck_receipt_vouchers_payment_type CHECK (((payment_type)::text = ANY ((ARRAY['cash'::character varying, 'bank_transfer'::character varying])::text[]))),
    CONSTRAINT ck_receipt_vouchers_voucher_number_not_blank CHECK ((char_length(btrim((voucher_number)::text)) > 0))
);

CREATE SEQUENCE IF NOT EXISTS public.receipt_voucher_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.receipt_voucher_number_seq OWNED BY public.receipt_vouchers.voucher_number;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.receipt_vouchers'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.receipt_vouchers ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.receipt_vouchers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.role_permissions (
    id integer NOT NULL,
    role_id integer NOT NULL,
    permission_id integer NOT NULL,
    allowed boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS public.role_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.role_permissions_id_seq OWNED BY public.role_permissions.id;

CREATE TABLE IF NOT EXISTS public.roles (
    id integer NOT NULL,
    role_code character varying(50) NOT NULL,
    role_name_ar character varying(120),
    role_name_en character varying(120),
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;

CREATE TABLE IF NOT EXISTS public.sales_invoice_audit_logs (
    id bigint NOT NULL,
    invoice_id bigint,
    invoice_number_snapshot character varying(100),
    seller_company_id_snapshot bigint,
    action character varying(50) NOT NULL,
    old_status character varying(30),
    new_status character varying(30),
    performed_by integer,
    batch_id uuid,
    details jsonb,
    previous_log_hash text,
    log_hash text,
    performed_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.sales_invoice_audit_logs'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.sales_invoice_audit_logs ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.sales_invoice_audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.sales_invoice_lines (
    id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    line_number integer NOT NULL,
    product_id integer,
    product_code_snapshot character varying(100) NOT NULL,
    product_name_snapshot character varying(255) NOT NULL,
    unit_code character varying(20) DEFAULT 'PCE'::character varying NOT NULL,
    item_description character varying(500),
    quantity numeric(18,6) NOT NULL,
    unit_price numeric(18,6) NOT NULL,
    line_amount_before_vat numeric(18,2) NOT NULL,
    vat_category_code character varying(10) DEFAULT 'S'::character varying NOT NULL,
    vat_rate numeric(5,2) DEFAULT 15.00 NOT NULL,
    vat_amount numeric(18,2) NOT NULL,
    line_total_including_vat numeric(18,2) NOT NULL,
    tax_exemption_reason_code character varying(100),
    tax_exemption_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_sales_invoice_lines_line_amount_before_vat_nonnegative CHECK ((line_amount_before_vat >= (0)::numeric)),
    CONSTRAINT ck_sales_invoice_lines_line_number_positive CHECK ((line_number > 0)),
    CONSTRAINT ck_sales_invoice_lines_line_total_including_vat_nonnegative CHECK ((line_total_including_vat >= (0)::numeric)),
    CONSTRAINT ck_sales_invoice_lines_line_total_matches_components CHECK ((line_total_including_vat = (line_amount_before_vat + vat_amount))),
    CONSTRAINT ck_sales_invoice_lines_quantity_positive CHECK ((quantity > (0)::numeric)),
    CONSTRAINT ck_sales_invoice_lines_unit_price_nonnegative CHECK ((unit_price >= (0)::numeric)),
    CONSTRAINT ck_sales_invoice_lines_vat_amount_nonnegative CHECK ((vat_amount >= (0)::numeric)),
    CONSTRAINT ck_sales_invoice_lines_vat_rate_nonnegative CHECK ((vat_rate >= (0)::numeric))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.sales_invoice_lines'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.sales_invoice_lines ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.sales_invoice_lines_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE SEQUENCE IF NOT EXISTS public.sales_invoice_number_seq
    START WITH 50001
    INCREMENT BY 1
    MINVALUE 50001
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.sales_invoice_zatca_data (
    invoice_id bigint NOT NULL,
    device_id bigint,
    uuid uuid,
    invoice_counter_value bigint,
    previous_invoice_hash text,
    invoice_hash text,
    cryptographic_stamp text,
    public_key_snapshot text,
    digital_signature text,
    qr_code_base64 text,
    generated_xml bytea,
    cleared_xml bytea,
    xml_file_name character varying(500),
    xml_file_path text,
    schema_version character varying(30),
    integration_operation character varying(20),
    integration_status character varying(30) DEFAULT 'not_generated'::character varying NOT NULL,
    zatca_request_id character varying(255),
    zatca_response jsonb,
    validation_warnings jsonb,
    validation_errors jsonb,
    xml_generated_at timestamp with time zone,
    submitted_at timestamp with time zone,
    accepted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_sales_invoice_zatca_data_integration_operation_valid CHECK (((integration_operation IS NULL) OR ((integration_operation)::text = ANY ((ARRAY['clearance'::character varying, 'reporting'::character varying])::text[])))),
    CONSTRAINT ck_sales_invoice_zatca_data_integration_status_valid CHECK (((integration_status)::text = ANY ((ARRAY['not_generated'::character varying, 'generated'::character varying, 'pending'::character varying, 'cleared'::character varying, 'reported'::character varying, 'warning'::character varying, 'rejected'::character varying, 'failed'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS public.sales_invoice_zatca_submissions (
    id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    operation character varying(20) NOT NULL,
    attempt_number integer NOT NULL,
    request_id character varying(255),
    request_payload_hash text,
    http_status_code integer,
    request_metadata jsonb,
    response_payload jsonb,
    warnings jsonb,
    errors jsonb,
    is_success boolean DEFAULT false NOT NULL,
    requested_at timestamp with time zone NOT NULL,
    responded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_sales_invoice_zatca_submissions_attempt_number_positive CHECK ((attempt_number > 0)),
    CONSTRAINT ck_sales_invoice_zatca_submissions_operation_valid CHECK (((operation)::text = ANY ((ARRAY['clearance'::character varying, 'reporting'::character varying, 'compliance'::character varying])::text[])))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.sales_invoice_zatca_submissions'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.sales_invoice_zatca_submissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.sales_invoice_zatca_submissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.sales_invoices (
    id bigint NOT NULL,
    invoice_number character varying(100) NOT NULL,
    issue_datetime timestamp with time zone DEFAULT now() NOT NULL,
    seller_company_id integer NOT NULL,
    seller_name_ar_snapshot character varying(255) NOT NULL,
    seller_name_en_snapshot character varying(255),
    seller_vat_number_snapshot character varying(15) NOT NULL,
    customer_id integer NOT NULL,
    customer_name_snapshot character varying(255) NOT NULL,
    customer_vat_number_snapshot character varying(15),
    customer_address_snapshot text,
    payment_type character varying(20) NOT NULL,
    notes text,
    invoice_currency_code character(3) DEFAULT 'SAR'::bpchar NOT NULL,
    tax_currency_code character(3) DEFAULT 'SAR'::bpchar NOT NULL,
    subtotal_before_vat numeric(18,2) DEFAULT 0 NOT NULL,
    invoice_discount_rate numeric(5,2) DEFAULT 0 NOT NULL,
    invoice_discount_amount numeric(18,2) DEFAULT 0 NOT NULL,
    subtotal_after_discount numeric(18,2) DEFAULT 0 NOT NULL,
    vat_total numeric(18,2) DEFAULT 0 NOT NULL,
    total_including_vat numeric(18,2) DEFAULT 0 NOT NULL,
    document_status character varying(30) DEFAULT 'draft'::character varying NOT NULL,
    approved_at timestamp with time zone,
    approved_by integer,
    created_by integer,
    updated_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    row_version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_sales_invoices_document_status_valid CHECK (((document_status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying])::text[]))),
    CONSTRAINT ck_sales_invoices_invoice_number_not_blank CHECK ((char_length(btrim((invoice_number)::text)) > 0)),
    CONSTRAINT ck_sales_invoices_payment_type_valid CHECK (((payment_type)::text = ANY ((ARRAY['cash'::character varying, 'credit'::character varying])::text[]))),
    CONSTRAINT ck_sales_invoices_subtotal_before_vat_nonnegative CHECK ((subtotal_before_vat >= (0)::numeric)),
    CONSTRAINT ck_sales_invoices_invoice_discount_rate_range CHECK ((invoice_discount_rate >= (0)::numeric) AND (invoice_discount_rate <= (100)::numeric)),
    CONSTRAINT ck_sales_invoices_invoice_discount_amount_nonnegative CHECK ((invoice_discount_amount >= (0)::numeric)),
    CONSTRAINT ck_sales_invoices_subtotal_after_discount_nonnegative CHECK ((subtotal_after_discount >= (0)::numeric)),
    CONSTRAINT ck_sales_invoices_subtotal_after_discount_matches_components CHECK ((subtotal_after_discount = (subtotal_before_vat - invoice_discount_amount))),
    CONSTRAINT ck_sales_invoices_total_including_vat_nonnegative CHECK ((total_including_vat >= (0)::numeric)),
    CONSTRAINT ck_sales_invoices_total_matches_components CHECK ((total_including_vat = (subtotal_after_discount + vat_total))),
    CONSTRAINT ck_sales_invoices_vat_total_nonnegative CHECK ((vat_total >= (0)::numeric))
);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'public.sales_invoices'::regclass AND attname = 'id' AND attidentity <> '') THEN
    ALTER TABLE public.sales_invoices ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.sales_invoices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.user_login_logs (
    id integer NOT NULL,
    user_id integer,
    username character varying(60),
    login_time timestamp with time zone DEFAULT now() NOT NULL,
    logout_time timestamp with time zone,
    status character varying(20),
    ip_address character varying(60),
    device_name character varying(120),
    notes text
);

CREATE SEQUENCE IF NOT EXISTS public.user_login_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.user_login_logs_id_seq OWNED BY public.user_login_logs.id;

CREATE TABLE IF NOT EXISTS public.user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL,
    allowed boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS public.user_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.user_permissions_id_seq OWNED BY public.user_permissions.id;

ALTER TABLE ONLY public.app_users ALTER COLUMN id SET DEFAULT nextval('public.app_users_id_seq'::regclass);

ALTER TABLE ONLY public.backup_logs ALTER COLUMN id SET DEFAULT nextval('public.backup_logs_id_seq'::regclass);

ALTER TABLE ONLY public.case_statuses ALTER COLUMN case_status_id SET DEFAULT nextval('public.case_statuses_case_status_id_seq'::regclass);

ALTER TABLE ONLY public.cashier_invoices ALTER COLUMN invoice_number SET DEFAULT ('CINV-'::text || to_char(nextval('public.cashier_invoice_number_seq'::regclass), 'FM000000'::text));

ALTER TABLE ONLY public.crm_attachments ALTER COLUMN id SET DEFAULT nextval('public.crm_attachments_id_seq'::regclass);

ALTER TABLE ONLY public.customers ALTER COLUMN customer_id SET DEFAULT nextval('public.customers_customer_id_seq'::regclass);

ALTER TABLE ONLY public.daily_followups ALTER COLUMN daily_followup_id SET DEFAULT nextval('public.daily_followups_daily_followup_id_seq'::regclass);

ALTER TABLE ONLY public.employees ALTER COLUMN employee_id SET DEFAULT nextval('public.employees_employee_id_seq'::regclass);

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);

ALTER TABLE ONLY public.places ALTER COLUMN place_id SET DEFAULT nextval('public.places_place_id_seq'::regclass);

ALTER TABLE ONLY public.products ALTER COLUMN item_code SET DEFAULT nextval('public.products_item_code_seq'::regclass)::text;

ALTER TABLE ONLY public.receipt_vouchers ALTER COLUMN voucher_number SET DEFAULT ('PA-'::text || to_char(nextval('public.receipt_voucher_number_seq'::regclass), 'FM000'::text));

ALTER TABLE ONLY public.role_permissions ALTER COLUMN id SET DEFAULT nextval('public.role_permissions_id_seq'::regclass);

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);

ALTER TABLE ONLY public.user_login_logs ALTER COLUMN id SET DEFAULT nextval('public.user_login_logs_id_seq'::regclass);

ALTER TABLE ONLY public.user_permissions ALTER COLUMN id SET DEFAULT nextval('public.user_permissions_id_seq'::regclass);

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'app_users_pkey1' AND conrelid = 'public.app_users'::regclass) THEN
    ALTER TABLE ONLY public.app_users ADD CONSTRAINT app_users_pkey1 PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'app_users_username_key' AND conrelid = 'public.app_users'::regclass) THEN
    ALTER TABLE ONLY public.app_users ADD CONSTRAINT app_users_username_key UNIQUE (username);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'backup_logs_pkey' AND conrelid = 'public.backup_logs'::regclass) THEN
    ALTER TABLE ONLY public.backup_logs ADD CONSTRAINT backup_logs_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_statuses_pkey' AND conrelid = 'public.case_statuses'::regclass) THEN
    ALTER TABLE ONLY public.case_statuses ADD CONSTRAINT case_statuses_pkey PRIMARY KEY (case_status_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cashier_invoice_lines_pkey' AND conrelid = 'public.cashier_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoice_lines ADD CONSTRAINT cashier_invoice_lines_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'cashier_invoices_pkey' AND conrelid = 'public.cashier_invoices'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoices ADD CONSTRAINT cashier_invoices_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'companies_pkey' AND conrelid = 'public.companies'::regclass) THEN
    ALTER TABLE ONLY public.companies ADD CONSTRAINT companies_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'crm_attachments_pkey' AND conrelid = 'public.crm_attachments'::regclass) THEN
    ALTER TABLE ONLY public.crm_attachments ADD CONSTRAINT crm_attachments_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'customers_pkey' AND conrelid = 'public.customers'::regclass) THEN
    ALTER TABLE ONLY public.customers ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'daily_followups_pkey' AND conrelid = 'public.daily_followups'::regclass) THEN
    ALTER TABLE ONLY public.daily_followups ADD CONSTRAINT daily_followups_pkey PRIMARY KEY (daily_followup_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'employees_pkey' AND conrelid = 'public.employees'::regclass) THEN
    ALTER TABLE ONLY public.employees ADD CONSTRAINT employees_pkey PRIMARY KEY (employee_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'permissions_permission_code_key' AND conrelid = 'public.permissions'::regclass) THEN
    ALTER TABLE ONLY public.permissions ADD CONSTRAINT permissions_permission_code_key UNIQUE (permission_code);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'permissions_pkey' AND conrelid = 'public.permissions'::regclass) THEN
    ALTER TABLE ONLY public.permissions ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_sales_invoice_audit_logs' AND conrelid = 'public.sales_invoice_audit_logs'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_audit_logs ADD CONSTRAINT pk_sales_invoice_audit_logs PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_sales_invoice_lines' AND conrelid = 'public.sales_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_lines ADD CONSTRAINT pk_sales_invoice_lines PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_sales_invoice_zatca_data' AND conrelid = 'public.sales_invoice_zatca_data'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_data ADD CONSTRAINT pk_sales_invoice_zatca_data PRIMARY KEY (invoice_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_sales_invoice_zatca_submissions' AND conrelid = 'public.sales_invoice_zatca_submissions'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_submissions ADD CONSTRAINT pk_sales_invoice_zatca_submissions PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pk_sales_invoices' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT pk_sales_invoices PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'places_pkey' AND conrelid = 'public.places'::regclass) THEN
    ALTER TABLE ONLY public.places ADD CONSTRAINT places_pkey PRIMARY KEY (place_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'products_pkey' AND conrelid = 'public.products'::regclass) THEN
    ALTER TABLE ONLY public.products ADD CONSTRAINT products_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'receipt_vouchers_pkey' AND conrelid = 'public.receipt_vouchers'::regclass) THEN
    ALTER TABLE ONLY public.receipt_vouchers ADD CONSTRAINT receipt_vouchers_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'role_permissions_pkey' AND conrelid = 'public.role_permissions'::regclass) THEN
    ALTER TABLE ONLY public.role_permissions ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'role_permissions_role_id_permission_id_key' AND conrelid = 'public.role_permissions'::regclass) THEN
    ALTER TABLE ONLY public.role_permissions ADD CONSTRAINT role_permissions_role_id_permission_id_key UNIQUE (role_id, permission_id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'roles_pkey' AND conrelid = 'public.roles'::regclass) THEN
    ALTER TABLE ONLY public.roles ADD CONSTRAINT roles_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'roles_role_code_key' AND conrelid = 'public.roles'::regclass) THEN
    ALTER TABLE ONLY public.roles ADD CONSTRAINT roles_role_code_key UNIQUE (role_code);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cashier_invoice_lines_invoice_line' AND conrelid = 'public.cashier_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoice_lines ADD CONSTRAINT uq_cashier_invoice_lines_invoice_line UNIQUE (cashier_invoice_id, line_number);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_sales_invoice_lines_invoice_line' AND conrelid = 'public.sales_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_lines ADD CONSTRAINT uq_sales_invoice_lines_invoice_line UNIQUE (invoice_id, line_number);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_sales_invoice_zatca_data_uuid' AND conrelid = 'public.sales_invoice_zatca_data'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_data ADD CONSTRAINT uq_sales_invoice_zatca_data_uuid UNIQUE (uuid);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_sales_invoice_zatca_submissions_attempt' AND conrelid = 'public.sales_invoice_zatca_submissions'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_submissions ADD CONSTRAINT uq_sales_invoice_zatca_submissions_attempt UNIQUE (invoice_id, operation, attempt_number);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_login_logs_pkey' AND conrelid = 'public.user_login_logs'::regclass) THEN
    ALTER TABLE ONLY public.user_login_logs ADD CONSTRAINT user_login_logs_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_permissions_pkey' AND conrelid = 'public.user_permissions'::regclass) THEN
    ALTER TABLE ONLY public.user_permissions ADD CONSTRAINT user_permissions_pkey PRIMARY KEY (id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_permissions_user_id_permission_id_key' AND conrelid = 'public.user_permissions'::regclass) THEN
    ALTER TABLE ONLY public.user_permissions ADD CONSTRAINT user_permissions_user_id_permission_id_key UNIQUE (user_id, permission_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_backup_logs_backup_type ON public.backup_logs USING btree (backup_type);

CREATE INDEX IF NOT EXISTS idx_backup_logs_created_at ON public.backup_logs USING btree (created_at);

CREATE INDEX IF NOT EXISTS idx_backup_logs_status ON public.backup_logs USING btree (status);

CREATE INDEX IF NOT EXISTS idx_case_statuses_name ON public.case_statuses USING btree (case_status_name);

CREATE INDEX IF NOT EXISTS idx_cashier_invoice_lines_cashier_invoice_id ON public.cashier_invoice_lines USING btree (cashier_invoice_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoice_lines_product_id ON public.cashier_invoice_lines USING btree (product_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_branch_id ON public.cashier_invoices USING btree (branch_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_company_id ON public.cashier_invoices USING btree (company_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_created_by_user_id ON public.cashier_invoices USING btree (created_by_user_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_customer_id ON public.cashier_invoices USING btree (customer_id);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_invoice_date ON public.cashier_invoices USING btree (invoice_date);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_invoice_status ON public.cashier_invoices USING btree (invoice_status);

CREATE INDEX IF NOT EXISTS idx_cashier_invoices_zatca_status ON public.cashier_invoices USING btree (zatca_status);

CREATE INDEX IF NOT EXISTS idx_companies_name_ar ON public.companies USING btree (name_ar);

CREATE INDEX IF NOT EXISTS idx_companies_name_ar_trgm ON public.companies USING gin (name_ar public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_crm_attachments_category ON public.crm_attachments USING btree (category);

CREATE UNIQUE INDEX IF NOT EXISTS idx_crm_attachments_code ON public.crm_attachments USING btree (attachment_code);

CREATE INDEX IF NOT EXISTS idx_crm_attachments_created_at ON public.crm_attachments USING btree (created_at);

CREATE INDEX IF NOT EXISTS idx_crm_attachments_entity_id ON public.crm_attachments USING btree (entity_id);

CREATE INDEX IF NOT EXISTS idx_crm_attachments_entity_type ON public.crm_attachments USING btree (entity_type);

CREATE INDEX IF NOT EXISTS idx_crm_attachments_file_hash ON public.crm_attachments USING btree (file_hash);

CREATE INDEX IF NOT EXISTS idx_customers_area_number ON public.customers USING btree (area_number);

CREATE INDEX IF NOT EXISTS idx_customers_name ON public.customers USING btree (customer_name);

CREATE INDEX IF NOT EXISTS idx_customers_name_trgm ON public.customers USING gin (customer_name public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customers_phone_number ON public.customers USING btree (phone_number);

CREATE INDEX IF NOT EXISTS idx_customers_phone_trgm ON public.customers USING gin (phone_number public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_customers_vat_number ON public.customers USING btree (vat_number);

CREATE INDEX IF NOT EXISTS idx_daily_followups_buyer_name ON public.daily_followups USING btree (buyer_name);

CREATE INDEX IF NOT EXISTS idx_daily_followups_case_status_id ON public.daily_followups USING btree (case_status_id);

CREATE INDEX IF NOT EXISTS idx_daily_followups_customer_id ON public.daily_followups USING btree (customer_id);

CREATE INDEX IF NOT EXISTS idx_daily_followups_customer_name ON public.daily_followups USING btree (buyer_name);

CREATE INDEX IF NOT EXISTS idx_daily_followups_employee_id ON public.daily_followups USING btree (employee_id);

CREATE INDEX IF NOT EXISTS idx_daily_followups_follow_up_date ON public.daily_followups USING btree (follow_up_date);

CREATE INDEX IF NOT EXISTS idx_daily_followups_notes_trgm ON public.daily_followups USING gin (notes public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_daily_followups_year_month ON public.daily_followups USING btree (follow_up_year, follow_up_month);

CREATE INDEX IF NOT EXISTS idx_employees_name ON public.employees USING btree (employee_name);

CREATE INDEX IF NOT EXISTS idx_employees_name_trgm ON public.employees USING gin (employee_name public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_employees_phone ON public.employees USING btree (phone_number);

CREATE INDEX IF NOT EXISTS idx_login_logs_user ON public.user_login_logs USING btree (user_id);

CREATE INDEX IF NOT EXISTS idx_permissions_active ON public.permissions USING btree (is_active);

CREATE INDEX IF NOT EXISTS idx_places_number ON public.places USING btree (place_number);

CREATE INDEX IF NOT EXISTS idx_products_item_name ON public.products USING btree (item_name);

CREATE INDEX IF NOT EXISTS idx_products_item_name_trgm ON public.products USING gin (item_name public.gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_receipt_vouchers_company_id ON public.receipt_vouchers USING btree (company_id);

CREATE INDEX IF NOT EXISTS idx_receipt_vouchers_customer_id ON public.receipt_vouchers USING btree (customer_id);

CREATE INDEX IF NOT EXISTS idx_receipt_vouchers_payment_type ON public.receipt_vouchers USING btree (payment_type);

CREATE INDEX IF NOT EXISTS idx_receipt_vouchers_voucher_date ON public.receipt_vouchers USING btree (voucher_date);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON public.role_permissions USING btree (role_id);

CREATE INDEX IF NOT EXISTS idx_user_permissions_user ON public.user_permissions USING btree (user_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_audit_logs_action ON public.sales_invoice_audit_logs USING btree (action);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_audit_logs_batch_id ON public.sales_invoice_audit_logs USING btree (batch_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_audit_logs_invoice_id ON public.sales_invoice_audit_logs USING btree (invoice_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_audit_logs_performed_at ON public.sales_invoice_audit_logs USING btree (performed_at);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_audit_logs_performed_by ON public.sales_invoice_audit_logs USING btree (performed_by);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_lines_invoice_id ON public.sales_invoice_lines USING btree (invoice_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_lines_product_id ON public.sales_invoice_lines USING btree (product_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_data_device_counter ON public.sales_invoice_zatca_data USING btree (device_id, invoice_counter_value);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_data_integration_status ON public.sales_invoice_zatca_data USING btree (integration_status);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_data_invoice_hash ON public.sales_invoice_zatca_data USING btree (invoice_hash);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_data_submitted_at ON public.sales_invoice_zatca_data USING btree (submitted_at);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_submissions_invoice_id ON public.sales_invoice_zatca_submissions USING btree (invoice_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_submissions_is_success ON public.sales_invoice_zatca_submissions USING btree (is_success);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_submissions_operation ON public.sales_invoice_zatca_submissions USING btree (operation);

CREATE INDEX IF NOT EXISTS ix_sales_invoice_zatca_submissions_requested_at ON public.sales_invoice_zatca_submissions USING btree (requested_at);

CREATE INDEX IF NOT EXISTS ix_sales_invoices_company_status_issued ON public.sales_invoices USING btree (seller_company_id, document_status, issue_datetime);

CREATE INDEX IF NOT EXISTS ix_sales_invoices_customer_id ON public.sales_invoices USING btree (customer_id);

CREATE INDEX IF NOT EXISTS ix_sales_invoices_document_status ON public.sales_invoices USING btree (document_status);

CREATE INDEX IF NOT EXISTS ix_sales_invoices_issue_datetime ON public.sales_invoices USING btree (issue_datetime);

CREATE INDEX IF NOT EXISTS ix_sales_invoices_seller_company_id ON public.sales_invoices USING btree (seller_company_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cashier_invoices_invoice_number ON public.cashier_invoices USING btree (invoice_number);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cashier_invoices_invoice_uuid ON public.cashier_invoices USING btree (invoice_uuid);

-- السجل التجاري is optional (2026-09-29): an existing DB loses the old NOT NULL via the
-- bootstrap back-fill and this drops its not-blank CHECK. Blank is stored as NULL
-- (companies_normalize), so several companies without a CR never collide below.
ALTER TABLE public.companies DROP CONSTRAINT IF EXISTS ck_companies_commercial_registration_not_blank;

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_commercial_registration ON public.companies USING btree (commercial_registration);

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_vat_number ON public.companies USING btree (vat_number);

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_item_code ON public.products USING btree (item_code);

CREATE UNIQUE INDEX IF NOT EXISTS uq_receipt_vouchers_voucher_number ON public.receipt_vouchers USING btree (voucher_number);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_invoice_audit_logs_log_hash ON public.sales_invoice_audit_logs USING btree (log_hash) WHERE (log_hash IS NOT NULL);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_invoice_zatca_device_counter ON public.sales_invoice_zatca_data USING btree (device_id, invoice_counter_value) WHERE ((device_id IS NOT NULL) AND (invoice_counter_value IS NOT NULL));

-- Sales-invoice numbering is PER-COMPANY (each seller restarts from 1), so the
-- invoice number is unique only within a seller company, never table-wide. Drop
-- the older global unique index if it is still present, then create the
-- composite one. (A table-wide index is stricter than the composite, so no
-- existing rows can ever conflict when switching.)
DROP INDEX IF EXISTS public.uq_sales_invoices_invoice_number;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_invoices_company_number ON public.sales_invoices USING btree (seller_company_id, invoice_number);

DROP TRIGGER IF EXISTS trg_cashier_invoice_lines_set_updated_at ON public.cashier_invoice_lines;
CREATE TRIGGER trg_cashier_invoice_lines_set_updated_at BEFORE UPDATE ON public.cashier_invoice_lines FOR EACH ROW EXECUTE FUNCTION public.cashier_invoice_lines_set_updated_at();

DROP TRIGGER IF EXISTS trg_cashier_invoices_set_updated_at ON public.cashier_invoices;
CREATE TRIGGER trg_cashier_invoices_set_updated_at BEFORE UPDATE ON public.cashier_invoices FOR EACH ROW EXECUTE FUNCTION public.cashier_invoices_set_updated_at();

DROP TRIGGER IF EXISTS trg_companies_normalize ON public.companies;
CREATE TRIGGER trg_companies_normalize BEFORE INSERT OR UPDATE ON public.companies FOR EACH ROW EXECUTE FUNCTION public.companies_normalize();

DROP TRIGGER IF EXISTS trg_products_set_updated_at ON public.products;
CREATE TRIGGER trg_products_set_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.products_set_updated_at();

DROP TRIGGER IF EXISTS trg_receipt_vouchers_set_updated_at ON public.receipt_vouchers;
CREATE TRIGGER trg_receipt_vouchers_set_updated_at BEFORE UPDATE ON public.receipt_vouchers FOR EACH ROW EXECUTE FUNCTION public.receipt_vouchers_set_updated_at();

DROP TRIGGER IF EXISTS trg_sales_invoice_lines_updated_at ON public.sales_invoice_lines;
CREATE TRIGGER trg_sales_invoice_lines_updated_at BEFORE UPDATE ON public.sales_invoice_lines FOR EACH ROW EXECUTE FUNCTION public.sales_set_updated_at();

DROP TRIGGER IF EXISTS trg_sales_invoice_zatca_data_updated_at ON public.sales_invoice_zatca_data;
CREATE TRIGGER trg_sales_invoice_zatca_data_updated_at BEFORE UPDATE ON public.sales_invoice_zatca_data FOR EACH ROW EXECUTE FUNCTION public.sales_set_updated_at();

DROP TRIGGER IF EXISTS trg_sales_invoices_updated_at ON public.sales_invoices;
CREATE TRIGGER trg_sales_invoices_updated_at BEFORE UPDATE ON public.sales_invoices FOR EACH ROW EXECUTE FUNCTION public.sales_set_updated_at();

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'app_users_role_id_fkey' AND conrelid = 'public.app_users'::regclass) THEN
    ALTER TABLE ONLY public.app_users ADD CONSTRAINT app_users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cashier_invoice_lines_invoice' AND conrelid = 'public.cashier_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoice_lines ADD CONSTRAINT fk_cashier_invoice_lines_invoice FOREIGN KEY (cashier_invoice_id) REFERENCES public.cashier_invoices(id) ON UPDATE CASCADE ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cashier_invoice_lines_product' AND conrelid = 'public.cashier_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoice_lines ADD CONSTRAINT fk_cashier_invoice_lines_product FOREIGN KEY (product_id) REFERENCES public.products(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cashier_invoices_company' AND conrelid = 'public.cashier_invoices'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoices ADD CONSTRAINT fk_cashier_invoices_company FOREIGN KEY (company_id) REFERENCES public.companies(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cashier_invoices_created_by_user' AND conrelid = 'public.cashier_invoices'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoices ADD CONSTRAINT fk_cashier_invoices_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cashier_invoices_customer' AND conrelid = 'public.cashier_invoices'::regclass) THEN
    ALTER TABLE ONLY public.cashier_invoices ADD CONSTRAINT fk_cashier_invoices_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_daily_followups_case_status' AND conrelid = 'public.daily_followups'::regclass) THEN
    ALTER TABLE ONLY public.daily_followups ADD CONSTRAINT fk_daily_followups_case_status FOREIGN KEY (case_status_id) REFERENCES public.case_statuses(case_status_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_daily_followups_customer' AND conrelid = 'public.daily_followups'::regclass) THEN
    ALTER TABLE ONLY public.daily_followups ADD CONSTRAINT fk_daily_followups_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_daily_followups_employee' AND conrelid = 'public.daily_followups'::regclass) THEN
    ALTER TABLE ONLY public.daily_followups ADD CONSTRAINT fk_daily_followups_employee FOREIGN KEY (employee_id) REFERENCES public.employees(employee_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_receipt_vouchers_company' AND conrelid = 'public.receipt_vouchers'::regclass) THEN
    ALTER TABLE ONLY public.receipt_vouchers ADD CONSTRAINT fk_receipt_vouchers_company FOREIGN KEY (company_id) REFERENCES public.companies(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_receipt_vouchers_created_by' AND conrelid = 'public.receipt_vouchers'::regclass) THEN
    ALTER TABLE ONLY public.receipt_vouchers ADD CONSTRAINT fk_receipt_vouchers_created_by FOREIGN KEY (created_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_receipt_vouchers_customer' AND conrelid = 'public.receipt_vouchers'::regclass) THEN
    ALTER TABLE ONLY public.receipt_vouchers ADD CONSTRAINT fk_receipt_vouchers_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_receipt_vouchers_updated_by' AND conrelid = 'public.receipt_vouchers'::regclass) THEN
    ALTER TABLE ONLY public.receipt_vouchers ADD CONSTRAINT fk_receipt_vouchers_updated_by FOREIGN KEY (updated_by) REFERENCES public.app_users(id) ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_audit_logs_invoice_id_sales_invoices' AND conrelid = 'public.sales_invoice_audit_logs'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_audit_logs ADD CONSTRAINT fk_sales_invoice_audit_logs_invoice_id_sales_invoices FOREIGN KEY (invoice_id) REFERENCES public.sales_invoices(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_audit_logs_performed_by_app_users' AND conrelid = 'public.sales_invoice_audit_logs'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_audit_logs ADD CONSTRAINT fk_sales_invoice_audit_logs_performed_by_app_users FOREIGN KEY (performed_by) REFERENCES public.app_users(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_lines_invoice_id_sales_invoices' AND conrelid = 'public.sales_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_lines ADD CONSTRAINT fk_sales_invoice_lines_invoice_id_sales_invoices FOREIGN KEY (invoice_id) REFERENCES public.sales_invoices(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_lines_product_id_products' AND conrelid = 'public.sales_invoice_lines'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_lines ADD CONSTRAINT fk_sales_invoice_lines_product_id_products FOREIGN KEY (product_id) REFERENCES public.products(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_zatca_data_invoice_id_sales_invoices' AND conrelid = 'public.sales_invoice_zatca_data'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_data ADD CONSTRAINT fk_sales_invoice_zatca_data_invoice_id_sales_invoices FOREIGN KEY (invoice_id) REFERENCES public.sales_invoices(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoice_zatca_submissions_invoice_id_sales_invoices' AND conrelid = 'public.sales_invoice_zatca_submissions'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoice_zatca_submissions ADD CONSTRAINT fk_sales_invoice_zatca_submissions_invoice_id_sales_invoices FOREIGN KEY (invoice_id) REFERENCES public.sales_invoices(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoices_approved_by_app_users' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT fk_sales_invoices_approved_by_app_users FOREIGN KEY (approved_by) REFERENCES public.app_users(id) ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoices_created_by_app_users' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT fk_sales_invoices_created_by_app_users FOREIGN KEY (created_by) REFERENCES public.app_users(id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoices_customer_id_customers' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT fk_sales_invoices_customer_id_customers FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoices_seller_company_id_companies' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT fk_sales_invoices_seller_company_id_companies FOREIGN KEY (seller_company_id) REFERENCES public.companies(id) ON UPDATE CASCADE ON DELETE RESTRICT;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_invoices_updated_by_app_users' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE ONLY public.sales_invoices ADD CONSTRAINT fk_sales_invoices_updated_by_app_users FOREIGN KEY (updated_by) REFERENCES public.app_users(id);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'role_permissions_permission_id_fkey' AND conrelid = 'public.role_permissions'::regclass) THEN
    ALTER TABLE ONLY public.role_permissions ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'role_permissions_role_id_fkey' AND conrelid = 'public.role_permissions'::regclass) THEN
    ALTER TABLE ONLY public.role_permissions ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_login_logs_user_id_fkey' AND conrelid = 'public.user_login_logs'::regclass) THEN
    ALTER TABLE ONLY public.user_login_logs ADD CONSTRAINT user_login_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_permissions_permission_id_fkey' AND conrelid = 'public.user_permissions'::regclass) THEN
    ALTER TABLE ONLY public.user_permissions ADD CONSTRAINT user_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_permissions_user_id_fkey' AND conrelid = 'public.user_permissions'::regclass) THEN
    ALTER TABLE ONLY public.user_permissions ADD CONSTRAINT user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Self-healing sequence resync (runs on every startup)
--
-- Identity / serial id columns are declared GENERATED BY DEFAULT, which lets a
-- restore — or any explicit-id INSERT — write rows without advancing the
-- backing sequence. The next auto-generated id then collides with a row that
-- already exists, e.g.:
--     duplicate key value violates unique constraint "pk_sales_invoice_audit_logs"
--     DETAIL: Key (id)=(225) already exists.
-- Restoring a *.sql backup with psql/pg_restore is the usual trigger, because
-- the dumped INSERTs carry explicit ids but do not touch the sequences.
--
-- This block realigns every *owned* sequence to its table's MAX(id) on each
-- startup, so the condition can never persist. It only ever moves a sequence
-- forward (GREATEST with the current last_value), so it is safe on a live /
-- shared LAN server and is a no-op once everything is already aligned.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r        RECORD;
    max_id   BIGINT;
    last_val BIGINT;
BEGIN
    FOR r IN
        SELECT
            n.nspname AS schema_name,
            t.relname AS table_name,
            a.attname AS column_name,
            pg_get_serial_sequence(format('%I.%I', n.nspname, t.relname), a.attname) AS seq
        FROM pg_class     t
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped
        WHERE t.relkind = 'r'
          AND n.nspname = 'public'
          -- Only true integer id columns. Text/varchar columns can also own a
          -- sequence (e.g. cashier_invoices.invoice_number, which formats a
          -- numeric string from its sequence); those have their own dedicated
          -- resync logic and MUST be skipped here — MAX(text) vs 0 would raise
          -- "COALESCE types text and integer cannot be matched".
          AND a.atttypid IN ('smallint'::regtype, 'integer'::regtype, 'bigint'::regtype)
          AND pg_get_serial_sequence(format('%I.%I', n.nspname, t.relname), a.attname) IS NOT NULL
    LOOP
        EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I.%I',
                       r.column_name, r.schema_name, r.table_name)
        INTO max_id;

        IF max_id > 0 THEN
            SELECT COALESCE(last_value, 0) INTO last_val
            FROM pg_sequences
            WHERE schemaname   = split_part(r.seq, '.', 1)
              AND sequencename = split_part(r.seq, '.', 2);

            -- setval(..., true) means the *next* value is GREATEST + 1, which is
            -- guaranteed to be past every existing id and never below last_val.
            PERFORM setval(r.seq, GREATEST(max_id, COALESCE(last_val, 0)), true);
        END IF;
    END LOOP;
END $$;

--
-- Name: units; Type: TABLE (وحدات المنتجات / units of measure master)
--
-- Three user-facing columns as requested:
--   * unit_id   = رقم تلقائي (numeric auto primary key, assigned by the DB sequence)
--   * unit_code = كود الوحدة (text code UN-1001, UN-1002, ... via a dedicated sequence)
--   * unit_name = اسم الوحدة
-- Idempotent (IF NOT EXISTS / guarded) exactly like every other object in this file.
--

CREATE OR REPLACE FUNCTION public.units_set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.units (
    unit_id integer NOT NULL,
    unit_code character varying(20) NOT NULL,
    unit_name character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_units_unit_code_not_blank CHECK ((char_length(btrim((unit_code)::text)) > 0)),
    CONSTRAINT ck_units_unit_name_not_blank CHECK ((char_length(btrim((unit_name)::text)) > 0))
);

-- Numeric auto primary key (رقم تلقائي). Plain sequence + DEFAULT nextval so
-- save_record's "INSERT ... RETURNING unit_id" gets a DB-assigned, concurrency
-- safe id (same approach as customers/places/case_statuses).
CREATE SEQUENCE IF NOT EXISTS public.units_unit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.units_unit_id_seq OWNED BY public.units.unit_id;

-- Unit code sequence: starts at 1001 so the first code is UN-1001, then UN-1002…
-- (mirrors the receipt-voucher 'PA-' auto-number pattern; concurrency-safe, never MAX+1).
CREATE SEQUENCE IF NOT EXISTS public.units_unit_code_seq
    START WITH 1001
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.units_unit_code_seq OWNED BY public.units.unit_code;

ALTER TABLE ONLY public.units ALTER COLUMN unit_id SET DEFAULT nextval('public.units_unit_id_seq'::regclass);

ALTER TABLE ONLY public.units ALTER COLUMN unit_code SET DEFAULT ('UN-'::text || to_char(nextval('public.units_unit_code_seq'::regclass), 'FM0000'::text));

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'units_pkey' AND conrelid = 'public.units'::regclass) THEN
    ALTER TABLE ONLY public.units ADD CONSTRAINT units_pkey PRIMARY KEY (unit_id);
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_units_unit_code ON public.units USING btree (unit_code);

CREATE INDEX IF NOT EXISTS idx_units_unit_name ON public.units USING btree (unit_name);

DROP TRIGGER IF EXISTS trg_units_set_updated_at ON public.units;
CREATE TRIGGER trg_units_set_updated_at BEFORE UPDATE ON public.units FOR EACH ROW EXECUTE FUNCTION public.units_set_updated_at();

--
-- sales_invoice_lines.unit_name: user-facing unit label (اسم الوحدة) chosen
-- from the units master. Separate from unit_code (the ZATCA UOM code, e.g. PCE)
-- so the e-invoice XML is never affected. Nullable; snapshot text like
-- product_name_snapshot. ADD COLUMN IF NOT EXISTS so existing DBs get it too.
--
ALTER TABLE public.sales_invoice_lines ADD COLUMN IF NOT EXISTS unit_name character varying(120);

--
-- sales_invoice_lines.item_description: free-text line description (وصف الصنف),
-- typed per line on the invoice screen and printed by templates that have a
-- «الوصف / Description» column (e.g. «موضي عقيل»). Optional; never sent to ZATCA.
--
ALTER TABLE public.sales_invoice_lines ADD COLUMN IF NOT EXISTS item_description character varying(500);

-- Invoice-level percentage discount.  Defaults preserve every historical invoice:
-- 0% discount, no discount amount, and the old pre-tax subtotal as its tax base.
ALTER TABLE public.sales_invoices
    ADD COLUMN IF NOT EXISTS invoice_discount_rate numeric(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS invoice_discount_amount numeric(18,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS subtotal_after_discount numeric(18,2) NOT NULL DEFAULT 0;

UPDATE public.sales_invoices
   SET subtotal_after_discount = subtotal_before_vat - invoice_discount_amount
 WHERE subtotal_after_discount <> subtotal_before_vat - invoice_discount_amount;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sales_invoices_invoice_discount_rate_range' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE public.sales_invoices ADD CONSTRAINT ck_sales_invoices_invoice_discount_rate_range CHECK (invoice_discount_rate >= 0 AND invoice_discount_rate <= 100);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sales_invoices_invoice_discount_amount_nonnegative' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE public.sales_invoices ADD CONSTRAINT ck_sales_invoices_invoice_discount_amount_nonnegative CHECK (invoice_discount_amount >= 0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sales_invoices_subtotal_after_discount_nonnegative' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE public.sales_invoices ADD CONSTRAINT ck_sales_invoices_subtotal_after_discount_nonnegative CHECK (subtotal_after_discount >= 0);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sales_invoices_subtotal_after_discount_matches_components' AND conrelid = 'public.sales_invoices'::regclass) THEN
    ALTER TABLE public.sales_invoices ADD CONSTRAINT ck_sales_invoices_subtotal_after_discount_matches_components CHECK (subtotal_after_discount = subtotal_before_vat - invoice_discount_amount);
  END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sales_invoices_total_matches_components' AND conrelid = 'public.sales_invoices'::regclass AND pg_get_constraintdef(oid) NOT LIKE '%subtotal_after_discount%') THEN
    ALTER TABLE public.sales_invoices DROP CONSTRAINT ck_sales_invoices_total_matches_components;
    ALTER TABLE public.sales_invoices ADD CONSTRAINT ck_sales_invoices_total_matches_components CHECK (total_including_vat = subtotal_after_discount + vat_total);
  END IF;
END $$;

--
-- balance_confirmations: «مصادقة على الرصيد» — one row per balance-confirmation
-- letter sent to a customer. ``balance`` (with the invoices/receipts totals it
-- came from) is a snapshot of the customer's statement balance as of
-- ``confirmation_date``, for one company (``company_id``) or for every company
-- (``company_id`` NULL = «كل الشركات»). confirmation_number defaults to BC-001,
-- BC-002, ... from its own sequence (atomic, never MAX+1); a manual number is
-- allowed and the UNIQUE index is the final guard.
--
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
