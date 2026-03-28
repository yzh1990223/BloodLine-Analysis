"""Parse Kettle `.repo` exports into job, transformation, and SQL step facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET
import re

from bloodline_api.connectors.repo_reader import read_repo_root
from bloodline_api.parsers.sql_table_extractor import extract_tables


@dataclass(slots=True)
class NamedObject:
    """Minimal named entity used for jobs and transformations."""

    name: str


@dataclass(slots=True)
class JobTransformationCall:
    """A job-level invocation of a transformation."""

    job_name: str
    transformation_name: str


@dataclass(slots=True, frozen=True)
class ObjectRef:
    """A lineage object touched by one repo actor, annotated with its object type."""

    name: str
    object_type: str


@dataclass(slots=True)
class RepoParseResult:
    """Normalized lineage facts extracted from one Kettle repository export."""

    jobs: list[NamedObject] = field(default_factory=list)
    transformations: list[NamedObject] = field(default_factory=list)
    job_transformation_calls: list[JobTransformationCall] = field(default_factory=list)
    step_reads: dict[str, list[ObjectRef]] = field(default_factory=dict)
    step_writes: dict[str, list[ObjectRef]] = field(default_factory=dict)
    job_reads: dict[str, list[ObjectRef]] = field(default_factory=dict)
    job_writes: dict[str, list[ObjectRef]] = field(default_factory=dict)


def _step_key(transformation_name: str, step_name: str) -> str:
    """Scope step keys by transformation to avoid cross-transformation collisions."""

    return f"{transformation_name}::{step_name}"


def _normalize_table_name(table_name: str) -> str:
    """Normalize repo table names to the same lowercase format as SQL extraction."""

    return table_name.strip().lower()


def _compose_table_name(schema_name: str, table_name: str) -> str | None:
    """Compose a physical table identifier from schema/table fields when present."""

    table_name = table_name.strip()
    if not table_name:
        return None

    schema_name = schema_name.strip()
    return _normalize_table_name(f"{schema_name}.{table_name}" if schema_name else table_name)


def _transformation_name(transformation: ET.Element) -> str | None:
    """Read a transformation name from either simplified or native Kettle export layouts."""

    name = transformation.findtext("name")
    if name is None:
        name = transformation.findtext("./info/name")
    if name is None:
        return None
    stripped = name.strip()
    return stripped or None


def _step_nodes(transformation: ET.Element) -> list[ET.Element]:
    """Return step elements from both simplified and native Kettle export layouts."""

    return transformation.findall("./steps/step") or transformation.findall("./step")


def _extract_sql_tables(sql: str) -> tuple[set[str], set[str]]:
    """Best-effort SQL extraction that skips malformed repo SQL placeholders."""

    try:
        reads, writes = extract_tables(sql)
        return (
            {_normalize_table_name(name) for name in reads},
            {_normalize_table_name(name) for name in writes},
        )
    except RecursionError:
        return set(), set()


def _job_entry_key(job_name: str, entry_name: str) -> str:
    """Scope job SQL entries by job name so multiple entries do not collide."""

    return f"{job_name}::{entry_name}"


def _truncate_target(sql: str) -> str | None:
    """Extract the target table from a TRUNCATE TABLE statement."""

    match = re.match(r"^\s*truncate\s+table\s+([^\s;]+)", sql, flags=re.IGNORECASE)
    if not match:
        return None
    return _normalize_table_name(match.group(1))


def _split_sql_statements(sql: str) -> list[str]:
    """Split one SQL blob into individual statements using semicolons."""

    statements = [statement.strip() for statement in sql.split(";")]
    return [statement for statement in statements if statement]


def _source_file_name(step: ET.Element) -> str | None:
    """Build a human-readable file source name from Kettle file input settings."""

    base_name = step.findtext("./file/name", default="").strip()
    filemask = step.findtext("./file/filemask", default="").strip()
    if base_name and filemask:
        return f"{base_name.rstrip('/')}/{filemask}"
    if base_name:
        return Path(base_name).name or base_name
    if filemask:
        return filemask
    return None


def _sorted_objects(items: set[ObjectRef]) -> list[ObjectRef]:
    """Return object refs in a stable order for deterministic tests and scans."""

    return sorted(items, key=lambda item: (item.object_type, item.name))


def _read_objects_for_step(step: ET.Element) -> set[ObjectRef]:
    """Extract read-side lineage objects from a repo step."""

    step_type = step.findtext("type", default="").strip()
    reads: set[ObjectRef] = set()
    sql = step.findtext("sql", default="").strip()

    if sql:
        sql_reads, _ = _extract_sql_tables(sql)
        reads.update(ObjectRef(name=name, object_type="data_table") for name in sql_reads)

    if step_type == "TableInput" and not reads:
        table_name = _compose_table_name(
            step.findtext("schema", default=""),
            step.findtext("table", default=""),
        )
        if table_name is not None:
            reads.add(ObjectRef(name=table_name, object_type="data_table"))

    if step_type == "AccessInput":
        if reads:
            reads = {ObjectRef(name=item.name, object_type="source_table") for item in reads}
        else:
            table_name = _normalize_table_name(step.findtext("table_name", default=""))
            if table_name:
                reads.add(ObjectRef(name=table_name, object_type="source_table"))

    if step_type in {"ExcelInput", "TextFileInput"}:
        file_name = _source_file_name(step)
        if file_name:
            reads.add(ObjectRef(name=file_name, object_type="source_file"))

    return reads


def _write_objects_for_step(step: ET.Element) -> set[ObjectRef]:
    """Extract write-side lineage objects from direct output steps or SQL mutations."""

    step_type = step.findtext("type", default="").strip()
    writes: set[ObjectRef] = set()
    sql = step.findtext("sql", default="").strip()

    if sql:
        _, sql_writes = _extract_sql_tables(sql)
        writes.update(ObjectRef(name=name, object_type="data_table") for name in sql_writes)

    if step_type == "TableOutput":
        table_name = _compose_table_name(
            step.findtext("schema", default=""),
            step.findtext("table", default=""),
        )
        if table_name is not None:
            writes.add(ObjectRef(name=table_name, object_type="data_table"))

    if step_type == "InsertUpdate":
        table_name = _compose_table_name(
            step.findtext("./lookup/schema", default=""),
            step.findtext("./lookup/table", default=""),
        )
        if table_name is not None:
            writes.add(ObjectRef(name=table_name, object_type="data_table"))

    return writes


def _job_sql_objects(entry: ET.Element) -> tuple[set[ObjectRef], set[ObjectRef]]:
    """Extract read/write objects from one SQL job entry, including multi-statement blobs."""

    sql = entry.findtext("sql", default="").strip()
    reads: set[ObjectRef] = set()
    writes: set[ObjectRef] = set()

    for statement in _split_sql_statements(sql):
        statement_reads, statement_writes = _extract_sql_tables(statement)
        reads.update(ObjectRef(name=name, object_type="data_table") for name in statement_reads)
        writes.update(ObjectRef(name=name, object_type="data_table") for name in statement_writes)
        truncate_target = _truncate_target(statement)
        if truncate_target is not None:
            writes.add(ObjectRef(name=truncate_target, object_type="data_table"))

    return reads, writes


class RepoParser:
    """Extract table-level lineage facts from a Kettle repository export."""

    def parse_file(self, path: Path) -> RepoParseResult:
        """Parse jobs, transformation calls, and SQL-bearing steps from a repo file."""

        root = read_repo_root(path)
        result = RepoParseResult()

        for job in root.findall(".//jobs/job"):
            name = job.findtext("name", default="unknown_job").strip()
            result.jobs.append(NamedObject(name=name))
            for transformation_ref in job.findall("./transformation"):
                transformation_name = (transformation_ref.text or "").strip()
                if transformation_name:
                    result.job_transformation_calls.append(
                        JobTransformationCall(
                            job_name=name,
                            transformation_name=transformation_name,
                        )
                    )
            for entry in job.findall("./entries/entry"):
                entry_type = entry.findtext("type", default="").strip()
                if entry_type == "TRANS":
                    transformation_name = entry.findtext("transname", default="").strip()
                    if transformation_name:
                        result.job_transformation_calls.append(
                            JobTransformationCall(
                                job_name=name,
                                transformation_name=transformation_name,
                            )
                        )
                if entry_type != "SQL":
                    continue
                entry_name = entry.findtext("name", default="unknown_sql_entry").strip()
                entry_key = _job_entry_key(name, entry_name)
                reads, writes = _job_sql_objects(entry)
                if reads:
                    result.job_reads[entry_key] = _sorted_objects(reads)
                if writes:
                    result.job_writes[entry_key] = _sorted_objects(writes)

        for transformation in root.findall(".//transformations/transformation"):
            transformation_name = _transformation_name(transformation)
            if transformation_name is None:
                continue
            result.transformations.append(NamedObject(name=transformation_name))

            for step in _step_nodes(transformation):
                step_name = step.findtext("name", default="unknown_step").strip()
                reads = _read_objects_for_step(step)
                writes = _write_objects_for_step(step)
                step_key = _step_key(transformation_name, step_name)
                if reads:
                    result.step_reads[step_key] = _sorted_objects(reads)
                if writes:
                    result.step_writes[step_key] = _sorted_objects(writes)

        return result
