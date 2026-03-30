"""Helpers for normalizing MySQL metadata loading inputs and boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import bindparam
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url


class MySQLMetadataConfigurationError(ValueError):
    """Raised when a metadata request lacks a valid database scope."""


@dataclass(slots=True)
class MySQLMetadataRequest:
    """Normalized connector input for a single metadata load."""

    dsn: str
    databases: list[str]
    default_database: str | None


@dataclass(slots=True)
class MySQLMetadataColumn:
    """Column-level metadata returned by the connector."""

    column_name: str
    data_type: str
    ordinal_position: int
    is_nullable: bool
    column_comment: str | None = None


@dataclass(slots=True)
class MySQLMetadataObject:
    """Table or view metadata returned by the connector."""

    database_name: str
    object_name: str
    object_kind: str
    comment: str | None
    columns: list[MySQLMetadataColumn]


INFORMATION_SCHEMA_SQL = text(
    """
    SELECT
        c.table_schema AS database_name,
        c.table_name AS object_name,
        CASE
            WHEN t.table_type = 'VIEW' THEN 'view'
            ELSE 'table'
        END AS object_kind,
        t.table_comment AS comment,
        c.column_name AS column_name,
        c.data_type AS data_type,
        c.ordinal_position AS ordinal_position,
        c.is_nullable AS is_nullable,
        c.column_comment AS column_comment
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema
     AND t.table_name = c.table_name
    WHERE c.table_schema IN :schemas
    ORDER BY c.table_schema, c.table_name, c.ordinal_position
    """
).bindparams(bindparam("schemas", expanding=True))


def build_mysql_metadata_request(
    *,
    mysql_dsn: str | None,
    metadata_databases: list[str] | None,
) -> MySQLMetadataRequest | None:
    """Normalize metadata inputs and derive the effective database scope."""

    if not mysql_dsn:
        return None

    url = make_url(mysql_dsn)
    default_database = url.database
    normalized_databases = sorted({db.strip() for db in metadata_databases or [] if db and db.strip()})

    if not normalized_databases:
        if default_database:
            normalized_databases = [default_database]
        else:
            raise MySQLMetadataConfigurationError(
                "mysql_dsn 未提供默认库，必须显式传入 metadata_databases。"
            )

    return MySQLMetadataRequest(
        dsn=mysql_dsn,
        databases=normalized_databases,
        default_database=default_database,
    )


class MySQLMetadataLoader:
    """Load MySQL metadata from information_schema for the configured databases."""

    def __init__(
        self,
        row_fetcher: Callable[[MySQLMetadataRequest], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._row_fetcher = row_fetcher or self._fetch_rows

    def load(self, request: MySQLMetadataRequest) -> list[MySQLMetadataObject]:
        """Return grouped table/view metadata for the requested database scope."""

        grouped: dict[tuple[str, str, str, str | None], list[dict[str, Any]]] = {}
        for row in self._row_fetcher(request):
            key = (
                str(row["database_name"]),
                str(row["object_name"]),
                str(row["object_kind"]),
                row.get("comment"),
            )
            grouped.setdefault(key, []).append(row)

        objects: list[MySQLMetadataObject] = []
        for key in sorted(grouped.keys()):
            rows = sorted(grouped[key], key=lambda item: int(item["ordinal_position"]))
            objects.append(
                MySQLMetadataObject(
                    database_name=key[0],
                    object_name=key[1],
                    object_kind=key[2],
                    comment=key[3],
                    columns=[
                        MySQLMetadataColumn(
                            column_name=str(row["column_name"]),
                            data_type=str(row["data_type"]),
                            ordinal_position=int(row["ordinal_position"]),
                            is_nullable=str(row["is_nullable"]).upper() == "YES",
                            column_comment=row.get("column_comment"),
                        )
                        for row in rows
                    ],
                )
            )
        return objects

    def _fetch_rows(self, request: MySQLMetadataRequest) -> list[dict[str, Any]]:
        """Query information_schema using the normalized connector request."""

        engine = create_engine(request.dsn, future=True)
        try:
            with engine.connect() as connection:
                rows = connection.execute(INFORMATION_SCHEMA_SQL, {"schemas": request.databases}).mappings()
                return [dict(row) for row in rows]
        finally:
            engine.dispose()
