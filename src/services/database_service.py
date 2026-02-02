import psycopg2

from src.core.constants import APP_NAME
from src.core.logging import get_logger

logger = get_logger(APP_NAME)


def ensure_pgvector_extension(database_url: str) -> None:
    """
    Ensures pgvector extension exists.
    Note: this requires privileges. In managed Postgres, you may need to enable it in the provider console.
    """
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("pgvector extension ensured")
    except Exception as exc:
        logger.error("Failed to ensure pgvector extension. Error=%s", exc)
        raise
    finally:
        if conn:
            conn.close()
