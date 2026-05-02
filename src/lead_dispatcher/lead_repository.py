from .database import get_connection


def fetch_leads(limit: int):
    query = """
        SELECT id, full_name, phone
        FROM leads
        WHERE phone IS NOT NULL
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "name": r[1],
            "phone": r[2],
        }
        for r in rows
    ]