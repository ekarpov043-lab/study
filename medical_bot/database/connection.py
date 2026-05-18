import logging
import psycopg2
from psycopg2 import extras
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)

_conn = None


def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        try:
            _conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            _conn.autocommit = True
            logger.info(f"Connected to PostgreSQL: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            raise
    return _conn


def execute(query, params=None, fetchone=False, fetchall=False):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            return None
    except psycopg2.Error as e:
        logger.error(f"SQL error: {e} | Query: {query[:100]} | Params: {params}")
        raise
