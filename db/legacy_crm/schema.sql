-- Deliberately inconsistent legacy schema. Do not normalize away the mismatch.
CREATE TABLE IF NOT EXISTS customers (
    cust_id BIGSERIAL PRIMARY KEY,
    full_nm VARCHAR(180),
    email_addr VARCHAR(320),
    phone_no VARCHAR(40),
    addr_line_1 TEXT,
    city_nm VARCHAR(120),
    state_cd VARCHAR(20),
    postal VARCHAR(24),
    active_flg CHAR(1) DEFAULT 'Y',
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_ts TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_customers_email_legacy ON customers (lower(email_addr));

CREATE TABLE IF NOT EXISTS orders (
    ord_pk BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(cust_id),
    order_ref VARCHAR(80), -- about 5% intentionally missing
    amount_cents INTEGER,
    curr_cd CHAR(3) DEFAULT 'USD',
    order_status VARCHAR(40),
    order_placed_at TIMESTAMPTZ,
    delivered_ts TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    product_flags JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_orders_order_ref ON orders(order_ref);

CREATE TABLE IF NOT EXISTS refund_requests (
    req_id BIGSERIAL PRIMARY KEY,
    order_identifier VARCHAR(80), -- text and deliberately not a foreign key
    cust_id BIGINT,
    requested_amt NUMERIC(12,2),
    reason_txt TEXT,
    request_status VARCHAR(30),
    created_dt TIMESTAMP,
    last_touch TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS seed_audit (
    seed_value INTEGER PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    customer_count INTEGER NOT NULL,
    order_count INTEGER NOT NULL,
    refund_count INTEGER NOT NULL
);

