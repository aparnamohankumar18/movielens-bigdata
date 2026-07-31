"""Credential-safe Azure SQL schema and bulk-write utilities."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence

import pyodbc

ALLOWED_TABLES = {
    "movies",
    "users",
}


def connection_string_from_env() -> str:
    required = {
        name: os.environ.get(name)
        for name in (
            "AZURE_SQL_SERVER",
            "AZURE_SQL_DATABASE",
            "AZURE_SQL_USERNAME",
            "AZURE_SQL_PASSWORD",
        )
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(f"missing required environment variables: {', '.join(missing)}")
    return (
        "DRIVER={FreeTDS};"
        f"SERVER={required['AZURE_SQL_SERVER']};PORT=1433;"
        f"DATABASE={required['AZURE_SQL_DATABASE']};"
        f"UID={required['AZURE_SQL_USERNAME']};PWD={required['AZURE_SQL_PASSWORD']};"
        "TDS_Version=auto;Encrypt=yes;"
    )


class AzureSqlLoader:
    def __init__(self, connection_string: str | None = None):
        self._connection_string = connection_string or connection_string_from_env()

    def connect(self):
        try:
            return pyodbc.connect(self._connection_string, timeout=30)
        except pyodbc.Error as exc:
            raise ConnectionError(
                f"Azure SQL connection failed ({type(exc).__name__}); credentials redacted"
            ) from None

    def validate_connection(self) -> bool:
        with self.connect() as connection:
            row = connection.cursor().execute("SELECT 1").fetchone()
        return bool(row and row[0] == 1)

    def ensure_schema(self, ddl_path: Path) -> None:
        sql = ddl_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.cursor().execute(sql)
            connection.commit()

    @staticmethod
    def _validate_table(table: str) -> str:
        if table not in ALLOWED_TABLES:
            raise ValueError(f"unsupported table: {table!r}")
        return table

    _MAX_PARAMS_PER_STATEMENT = 2000

    def write_rows(
        self, table: str, columns: Sequence[str], rows: Iterable[Sequence[object]]
    ) -> int:
        table = self._validate_table(table)
        if not columns or any(not re.fullmatch(r"[a-z][a-z0-9_]*", col) for col in columns):
            raise ValueError("columns must be non-empty lower_snake_case identifiers")
        materialized = list(rows)
        if not materialized:
            return 0
        identifiers = ", ".join(f"[{column}]" for column in columns)
        row_placeholder = "(" + ", ".join("?" for _ in columns) + ")"
        batch_size = max(1, self._MAX_PARAMS_PER_STATEMENT // len(columns))
        with self.connect() as connection:
            cursor = connection.cursor()
            for start in range(0, len(materialized), batch_size):
                batch = materialized[start : start + batch_size]
                values_clause = ", ".join(row_placeholder for _ in batch)
                statement = (
                    f"INSERT INTO dbo.[{table}] ({identifiers}) VALUES {values_clause}"
                )
                params = [value for row in batch for value in row]
                cursor.execute(statement, params)
            connection.commit()
        return len(materialized)

    def row_count(self, table: str) -> int:
        table = self._validate_table(table)
        with self.connect() as connection:
            row = connection.cursor().execute(
                f"SELECT COUNT_BIG(*) FROM dbo.[{table}]"
            ).fetchone()
        return int(row[0])

    def reconcile_count(self, table: str, expected: int) -> Mapping[str, object]:
        actual = self.row_count(table)
        return {
            "table": table,
            "expected": expected,
            "actual": actual,
            "matches": actual == expected,
        }


def loader_from_dotenv() -> AzureSqlLoader:
    """Load local development environment variables without logging values."""
    from dotenv import load_dotenv

    load_dotenv()
    return AzureSqlLoader()

