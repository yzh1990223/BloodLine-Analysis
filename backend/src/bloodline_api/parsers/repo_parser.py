from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bloodline_api.connectors.repo_reader import read_repo_root
from bloodline_api.parsers.sql_table_extractor import extract_tables


@dataclass(slots=True)
class NamedObject:
    name: str


@dataclass(slots=True)
class JobTransformationCall:
    job_name: str
    transformation_name: str


@dataclass(slots=True)
class RepoParseResult:
    jobs: list[NamedObject] = field(default_factory=list)
    transformations: list[NamedObject] = field(default_factory=list)
    job_transformation_calls: list[JobTransformationCall] = field(default_factory=list)
    step_reads: dict[str, list[str]] = field(default_factory=dict)
    step_writes: dict[str, list[str]] = field(default_factory=dict)


def _step_key(transformation_name: str, step_name: str) -> str:
    return f"{transformation_name}::{step_name}"


class RepoParser:
    def parse_file(self, path: Path) -> RepoParseResult:
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

        for transformation in root.findall(".//transformations/transformation"):
            name = transformation.findtext("name")
            if name is None:
                continue
            transformation_name = name.strip()
            result.transformations.append(NamedObject(name=transformation_name))

            for step in transformation.findall("./steps/step"):
                step_name = step.findtext("name", default="unknown_step").strip()
                sql = step.findtext("sql", default="").strip()
                if not sql:
                    continue

                reads, writes = extract_tables(sql)
                step_key = _step_key(transformation_name, step_name)
                if reads:
                    result.step_reads[step_key] = sorted(reads)
                if writes:
                    result.step_writes[step_key] = sorted(writes)

        return result
