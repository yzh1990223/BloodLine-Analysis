"""Regression tests for repository governance hook scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_SYNC_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "doc-sync-check.sh"
SCHEMA_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "schema-migration-check.sh"


def _init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def _stage_file(repo: Path, relative_path: str, content: str = "sample\n") -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", relative_path], cwd=repo, check=True, capture_output=True, text=True)


def _run_script(repo: Path, script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_doc_sync_points_api_changes_to_specific_documents(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/api/routes_scan.py")

    completed = _run_script(repo, DOC_SYNC_SCRIPT)

    assert "docs/uat/" in completed.stdout
    assert "README.md" in completed.stdout


def test_doc_sync_points_lineage_service_changes_to_design_docs(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/services/lineage_query.py")

    completed = _run_script(repo, DOC_SYNC_SCRIPT)

    assert "docs/superpowers/specs/" in completed.stdout
    assert "docs/uat/" in completed.stdout


def test_schema_migration_points_model_changes_to_migration_and_design_docs(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/models.py")

    completed = _run_script(repo, SCHEMA_SCRIPT)

    assert "backend/alembic/versions/" in completed.stdout
    assert "docs/superpowers/specs/" in completed.stdout
