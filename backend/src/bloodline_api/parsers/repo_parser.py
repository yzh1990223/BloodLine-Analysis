from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bloodline_api.connectors.repo_reader import read_repo_root
from bloodline_api.parsers.sql_table_extractor import extract_tables


@dataclass(slots=True)
class NamedObject:
    name: str


@dataclass(slots=True)
class RepoParseResult:
    jobs: list[NamedObject] = field(default_factory=list)
    transformations: list[NamedObject] = field(default_factory=list)
    step_reads: dict[str, list[str]] = field(default_factory=dict)
    step_writes: dict[str, list[str]] = field(default_factory=dict)


class RepoParser:
    def parse_file(self, path: Path) -> RepoParseResult:
        root = read_repo_root(path)
        result = RepoParseResult()

        for job in root.findall(".//job"):
            name = job.findtext("name", default="unknown_job").strip()
            result.jobs.append(NamedObject(name=name))

        for transformation in root.findall(".//transformation"):
            name = transformation.findtext("name")
            if name is None:
                continue
            result.transformations.append(NamedObject(name=name.strip()))

        for step in root.findall(".//step"):
            step_name = step.findtext("name", default="unknown_step").strip()
            sql = step.findtext("sql", default="").strip()
            if not sql:
                continue

            reads, writes = extract_tables(sql)
            if reads:
                result.step_reads[step_name] = sorted(reads)
            if writes:
                result.step_writes[step_name] = sorted(writes)

        return result
