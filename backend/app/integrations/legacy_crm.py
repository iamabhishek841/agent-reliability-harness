from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from backend.app.integrations.faults import IntegrationUnavailable, apply_faults


class LegacyCRMClient:
    def __init__(self, database_url: str, timeout_seconds: float = 4.0):
        self.database_url = database_url
        self.timeout_seconds = timeout_seconds

    def get_order_context(self, *, order_ref: str | None = None, customer_email: str | None = None) -> dict[str, Any]:
        stale_hours = apply_faults("legacy_crm", self.timeout_seconds)
        if not order_ref and not customer_email:
            raise IntegrationUnavailable("legacy_crm", "missing_identity", "An order reference or customer email is required")
        filters: list[str] = []
        params: list[str] = []
        if order_ref:
            filters.append("(o.order_ref = %s OR CAST(o.ord_pk AS text) = %s)")
            params.extend([order_ref, order_ref])
        if customer_email:
            filters.append("lower(c.email_addr) = lower(%s)")
            params.append(customer_email)
        query = f"""
            SELECT c.cust_id, c.full_nm, c.email_addr, c.updated_ts AS customer_updated_at,
                   o.ord_pk, o.order_ref, o.amount_cents, o.curr_cd, o.order_status,
                   o.order_placed_at, o.delivered_ts, o.updated_at AS order_updated_at,
                   o.product_flags,
                   (SELECT count(*) FROM refund_requests r
                    WHERE r.order_identifier = coalesce(o.order_ref, CAST(o.ord_pk AS text))) AS prior_refund_count
            FROM orders o
            JOIN customers c ON c.cust_id = o.customer_id
            WHERE {" AND ".join(filters)}
            ORDER BY o.updated_at DESC, c.updated_ts DESC
            LIMIT 3
        """
        try:
            with psycopg.connect(self.database_url, connect_timeout=max(1, int(self.timeout_seconds)), row_factory=dict_row) as connection:
                rows = connection.execute(query, params).fetchall()
        except psycopg.Error as exc:
            raise IntegrationUnavailable("legacy_crm", "database_error", str(exc)) from exc
        if not rows:
            return {"found": False, "source": "legacy_crm", "stale_hours": stale_hours}
        row = dict(rows[0])
        updated_at = row.get("order_updated_at")
        natural_age = 0.0
        if isinstance(updated_at, datetime):
            updated_at = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=UTC)
            natural_age = (datetime.now(UTC) - updated_at).total_seconds() / 3600
        return {"found": True, "source": "legacy_crm", "stale_hours": stale_hours, "source_age_hours": round(natural_age + stale_hours, 2), **row}

    def health(self) -> bool:
        try:
            with psycopg.connect(self.database_url, connect_timeout=2) as connection:
                return connection.execute("SELECT 1").fetchone() == (1,)
        except psycopg.Error:
            return False
