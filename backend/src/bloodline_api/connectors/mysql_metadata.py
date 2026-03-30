"""Helpers for normalizing MySQL metadata loading inputs and boundaries."""

from __future__ import annotations

from dataclasses import dataclass

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
