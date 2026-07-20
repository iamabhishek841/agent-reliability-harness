#!/usr/bin/env python3
"""Reproducibly generate messy legacy CRM records with Faker."""

import argparse
import os
import random
from datetime import UTC, datetime, timedelta

from faker import Faker

SEED = 7301
BASE_CUSTOMERS = 110
DUPLICATES = 12
ORDER_COUNT = 140
REFUND_COUNT = 45


def database_url() -> str:
    if value := os.getenv("LEGACY_DATABASE_URL"):
        return value
    user = os.getenv("POSTGRES_USER", "legacy")
    database = os.getenv("POSTGRES_DB", "legacy_crm")
    return f"postgresql://{user}@/{database}?host=/var/run/postgresql"


def build_records(now: datetime):
    fake = Faker("en_US")
    Faker.seed(SEED)
    random.seed(SEED)
    customers = []
    for index in range(BASE_CUSTOMERS):
        name = fake.name()
        email = f"customer{index:03d}@example.test"
        created = now - timedelta(days=random.randint(60, 900))
        updated = now - timedelta(hours=random.choice([1, 2, 4, 8, 26, 35, 47]))
        customers.append((name, email, fake.phone_number()[:40], fake.street_address(), fake.city(), fake.state_abbr(), fake.postcode(), "Y", created, updated))
    for index in range(DUPLICATES):
        original = customers[index]
        customers.append((original[0].replace(" ", "  "), original[1].upper() if index % 2 else original[1], original[2], original[3], original[4], original[5], original[6], "Y", original[8] + timedelta(days=2), now - timedelta(hours=index + 1)))

    fixture_specs = [
        (1, "ORD-ELIGIBLE-001", 12000, "delivered", 18, 10, {}, 1),
        (2, "ORD-EXPIRED-001", 8500, "delivered", 55, 45, {}, 2),
        (3, "ORD-FINAL-001", 4900, "delivered", 12, 7, {"final_sale": True}, 1),
        (4, "ORD-HIGH-001", 150000, "delivered", 11, 5, {}, 1),
        (5, "ORD-NODATE-001", 7200, "delivered", 8, None, {}, 1),
        (6, "ORD-REFUNDED-001", 3300, "refunded", 15, 8, {}, 1),
        (7, "ORD-PENDING-001", 2400, "processing", 2, None, {}, 1),
        (8, "ORD-REGULATED-001", 18000, "delivered", 12, 6, {"regulated_item": True}, 1),
    ]
    orders = []
    for customer_id, ref, cents, status, placed_days, delivered_days, flags, updated_hours in fixture_specs:
        orders.append((customer_id, ref, cents, "USD", status, now - timedelta(days=placed_days), now - timedelta(days=delivered_days) if delivered_days is not None else None, now - timedelta(hours=updated_hours), flags))
    statuses = ["delivered", "completed", "processing", "cancelled", "fraud_review"]
    for index in range(len(fixture_specs), ORDER_COUNT):
        customer_id = random.randint(1, BASE_CUSTOMERS)
        missing_ref = index % 20 == 0
        placed_days = random.randint(3, 90)
        status = random.choices(statuses, weights=[55, 15, 15, 10, 5], k=1)[0]
        delivered = now - timedelta(days=max(1, placed_days - random.randint(1, 7))) if status in {"delivered", "completed"} else None
        flags = {"final_sale": True} if index % 29 == 0 else {}
        orders.append((customer_id, None if missing_ref else f"LEG-{100000 + index}", random.randint(1200, 175000), random.choice(["USD", "USD", "USD", "EUR"]), status, now - timedelta(days=placed_days), delivered, now - timedelta(hours=random.choice([1, 2, 6, 12, 27, 36, 48])), flags))

    refunds = [("ORD-REFUNDED-001", 6, 33.00, "duplicate shipment", "paid", now - timedelta(days=2), now - timedelta(hours=2))]
    for index in range(1, REFUND_COUNT):
        broken_reference = index % 11 == 0
        order_index = random.randint(8, ORDER_COUNT - 1)
        order_ref = f"ORPHAN-{index:03d}" if broken_reference else (orders[order_index][1] or str(order_index + 1))
        refunds.append((order_ref, random.randint(1, BASE_CUSTOMERS + DUPLICATES), round(random.uniform(12, 900), 2), fake.sentence(nb_words=6), random.choice(["new", "review", "denied", "paid"]), (now - timedelta(days=random.randint(1, 80))).replace(tzinfo=None), now - timedelta(hours=random.randint(1, 72))))
    return customers, orders, refunds


def seed(reset: bool = False) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    now = datetime.now(UTC).replace(microsecond=0)
    customers, orders, refunds = build_records(now)
    database_orders = [(*order[:-1], Jsonb(order[-1])) for order in orders]
    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            if reset:
                cursor.execute("TRUNCATE refund_requests, orders, customers, seed_audit RESTART IDENTITY CASCADE")
            elif cursor.execute("SELECT count(*) FROM seed_audit WHERE seed_value = %s", (SEED,)).fetchone()[0]:
                return {"customers": len(customers), "orders": len(orders), "refunds": len(refunds)}
            cursor.executemany("INSERT INTO customers (full_nm,email_addr,phone_no,addr_line_1,city_nm,state_cd,postal,active_flg,created_ts,updated_ts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", customers)
            cursor.executemany("INSERT INTO orders (customer_id,order_ref,amount_cents,curr_cd,order_status,order_placed_at,delivered_ts,updated_at,product_flags) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", database_orders)
            cursor.executemany("INSERT INTO refund_requests (order_identifier,cust_id,requested_amt,reason_txt,request_status,created_dt,last_touch) VALUES (%s,%s,%s,%s,%s,%s,%s)", refunds)
            cursor.execute("INSERT INTO seed_audit (seed_value,generated_at,customer_count,order_count,refund_count) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (seed_value) DO UPDATE SET generated_at=excluded.generated_at,customer_count=excluded.customer_count,order_count=excluded.order_count,refund_count=excluded.refund_count", (SEED, now, len(customers), len(orders), len(refunds)))
    return {"customers": len(customers), "orders": len(orders), "refunds": len(refunds)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    print(seed(reset=args.reset))
