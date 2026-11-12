"""MySQL connection: one shared engine (connection pool) for the whole app."""
import os
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv(Path(__file__).resolve().parent / ".env")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_CONNECTION_LIMIT = int(os.getenv("DB_CONNECTION_LIMIT", "10"))
# Tables the LLM must never see or query (secrets, tokens, biometric data)
BLOCKED_TABLES = {
    t.strip() for t in
    os.getenv("DB_BLOCKED_TABLES", "password_manager,activation_codes,faces").split(",")
    if t.strip()
}

# quote_plus because the user/password can contain characters like "@"
DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=DB_CONNECTION_LIMIT,
    max_overflow=0,
    pool_pre_ping=True,   # drop dead connections instead of failing the request
    pool_recycle=3600,
    connect_args={"connect_timeout": 10},
)


def check_connection() -> None:
    """Raises SQLAlchemyError if the database can't be reached."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def connect_on_startup() -> bool:
    """Try the connection once when the app starts; log the result instead of crashing."""
    try:
        check_connection()
        print(f"Database: connected to '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
        return True
    except SQLAlchemyError as e:
        print(f"Database: could not connect to '{DB_NAME}' on {DB_HOST}:{DB_PORT} -> {getattr(e, 'orig', e)}")
        return False


def get_tables() -> list[str]:
    return [t for t in inspect(engine).get_table_names() if t not in BLOCKED_TABLES]


@lru_cache(maxsize=1)
def get_schema_text() -> str:
    """Every table with its columns, primary key and foreign keys, as text for the LLM.

    Reads information_schema in 2 queries instead of ~3 inspector calls per table,
    which matters a lot when the MySQL server is remote.
    """
    with engine.connect() as conn:
        col_rows = conn.execute(text(
            "SELECT c.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE, c.COLUMN_KEY, c.COLUMN_COMMENT "
            "FROM information_schema.COLUMNS c "
            "JOIN information_schema.TABLES t "
            "  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME "
            "WHERE c.TABLE_SCHEMA = DATABASE() AND t.TABLE_TYPE = 'BASE TABLE' "
            "ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION"
        )).all()
        fk_rows = conn.execute(text(
            "SELECT TABLE_NAME, CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
            "FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL "
            "ORDER BY TABLE_NAME, CONSTRAINT_NAME, ORDINAL_POSITION"
        )).all()

    columns: dict[str, list[str]] = {}
    for table, name, col_type, key, comment in col_rows:
        if table in BLOCKED_TABLES:
            continue
        desc = f"{name} {col_type}" + (" PK" if key == "PRI" else "") + (f" -- {comment}" if comment else "")
        columns.setdefault(table, []).append(desc)

    fks: dict[tuple[str, str], list] = {}
    for table, constraint, col, ref_table, ref_col in fk_rows:
        if table in BLOCKED_TABLES or ref_table in BLOCKED_TABLES:
            continue
        fks.setdefault((table, constraint), [table, ref_table, [], []])
        fks[(table, constraint)][2].append(col)
        fks[(table, constraint)][3].append(ref_col)

    lines = []
    for table, cols in columns.items():
        lines.append(f"{table}({', '.join(cols)})")
        for t, ref_table, cols_from, cols_to in fks.values():
            if t == table:
                lines.append(f"  FK {table}.{','.join(cols_from)} -> {ref_table}.{','.join(cols_to)}")
    return "\n".join(lines)


# No SHOW / DESCRIBE: those would list the blocked tables (the LLM already has the schema)
READ_ONLY_START = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
SYSTEM_SCHEMAS = re.compile(r"\b(information_schema|performance_schema|mysql|sys)\s*`?\s*\.", re.IGNORECASE)


def run_select(sql: str, max_rows: int) -> tuple[list[str], list[tuple]]:
    """Run ONE read-only query written by the LLM. Returns (column names, rows)."""
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        raise ValueError("Only one SQL statement is allowed.")
    if not READ_ONLY_START.match(sql):
        raise ValueError("Only SELECT queries are allowed.")
    if SYSTEM_SCHEMAS.search(sql):
        raise ValueError("System schemas are not accessible; use the tables from the schema.")
    for table in BLOCKED_TABLES:
        if re.search(rf"\b{re.escape(table)}\b", sql, re.IGNORECASE):
            raise ValueError(f"Table '{table}' is not accessible.")
    with engine.connect() as conn:
        try:
            # exec_driver_sql, not text(): text() would treat '09:30:00' as bind params.
            # PyMySQL still %-formats the query, so a literal "%" (LIKE '%x%') must be doubled.
            result = conn.exec_driver_sql(sql.replace("%", "%%"))
            columns = list(result.keys())
            return columns, [tuple(row) for row in result.fetchmany(max_rows)]
        finally:
            conn.rollback()   # never keep anything the query might have changed


def fetch_rows(table: str, limit: int) -> tuple[list[str], list[tuple]]:
    """Read-only SELECT of a table's rows. Returns (column names, rows)."""
    if table not in get_tables():
        raise ValueError(f"Unknown table: {table}")
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM `{table}` LIMIT :n"), {"n": limit})
        return list(result.keys()), [tuple(row) for row in result]
