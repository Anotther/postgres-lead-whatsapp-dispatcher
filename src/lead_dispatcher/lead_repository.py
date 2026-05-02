from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .database import get_connection
from .settings import settings

logger = logging.getLogger(__name__)


def fetch_leads(limit: int | None = None) -> list[dict[str, Any]]:
    query_path = Path(settings.lead_query_path)
    lead_limit = limit or settings.lead_limit

    logger.info("Fetching leads query_path=%s lead_limit=%s", query_path, lead_limit)

    with query_path.open("r", encoding="utf-8") as file:
        query = file.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, {"lead_limit": lead_limit})
            rows = cur.fetchall()
            columns = [column.name for column in cur.description]

    leads = [dict(zip(columns, row, strict=False)) for row in rows]
    logger.info("Leads fetched total=%s", len(leads))

    return leads
