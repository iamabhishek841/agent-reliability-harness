import os

import psycopg
from psycopg.rows import dict_row

dsn = os.getenv("LEGACY_DATABASE_URL", "postgresql://legacy:legacy@localhost:5433/legacy_crm")
with psycopg.connect(dsn, row_factory=dict_row) as connection:
    print(dict(connection.execute("""
        SELECT (SELECT count(*) FROM customers) customers,
               (SELECT count(*) FROM orders) orders,
               (SELECT count(*) FROM refund_requests) refunds,
               (SELECT count(*) FROM customers c JOIN customers d ON lower(c.email_addr)=lower(d.email_addr) AND c.cust_id<d.cust_id) duplicate_pairs,
               (SELECT count(*) FROM orders WHERE order_ref IS NULL) missing_order_refs,
               (SELECT count(*) FROM refund_requests r LEFT JOIN orders o ON r.order_identifier=o.order_ref WHERE o.ord_pk IS NULL) orphan_refunds
    """).fetchone()))

