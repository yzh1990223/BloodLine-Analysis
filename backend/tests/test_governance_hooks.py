"""Regression tests for repository governance hook scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_SYNC_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "doc-sync-check.sh"
SCHEMA_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "schema-migration-check.sh"
POST_COMMIT_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "post-commit"
ISSUE_LINK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "issue-link-check.sh"
SET_ISSUE_REF_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "set-issue-ref.sh"
COMMIT_MSG_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "commit-msg"


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


def test_post_commit_suggests_incident_experience_after_fix_commit(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/services/example.py")
    subprocess.run(["git", "commit", "-m", "fix: 修复路径处理"], cwd=repo, check=True, capture_output=True, text=True)

    completed = subprocess.run(
        ["bash", str(POST_COMMIT_SCRIPT)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "incident" in completed.stdout
    assert "docs/experience/README.md" in completed.stdout


def test_post_commit_suggests_governance_experience_after_hook_commit(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "scripts/hooks/example.sh")
    subprocess.run(["git", "commit", "-m", "chore: 调整治理脚本"], cwd=repo, check=True, capture_output=True, text=True)

    completed = subprocess.run(
        ["bash", str(POST_COMMIT_SCRIPT)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "governance" in completed.stdout
    assert "experience-closure-foundation.md" in completed.stdout


def test_issue_link_allows_docs_only_change_without_issue(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "docs/notes/example.md")

    completed = _run_script(repo, ISSUE_LINK_SCRIPT)

    assert completed.returncode == 0


def test_issue_link_blocks_nontrivial_change_without_issue(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "frontend/src/pages/example.tsx")

    completed = subprocess.run(
        ["bash", str(ISSUE_LINK_SCRIPT)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "必须关联 GitHub Task/Issue" in completed.stdout


def test_issue_link_passes_after_setting_issue_ref(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "frontend/src/pages/example.tsx")
    subprocess.run(
        ["bash", str(SET_ISSUE_REF_SCRIPT), "12"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    completed = _run_script(repo, ISSUE_LINK_SCRIPT)

    assert "已检测到关联 Issue" in completed.stdout


def test_commit_msg_requires_issue_reference_for_nontrivial_change(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/services/example.py")
    message_file = repo / "COMMIT_EDITMSG"
    message_file.write_text("feat: 增加循环边次数\n", encoding="utf-8")

    completed = subprocess.run(
        ["bash", str(COMMIT_MSG_SCRIPT), str(message_file)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "必须在提交信息中包含关联 Issue" in completed.stdout


def test_commit_msg_requires_matching_issue_reference_when_issue_is_bound(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _stage_file(repo, "backend/src/bloodline_api/services/example.py")
    subprocess.run(
        ["bash", str(SET_ISSUE_REF_SCRIPT), "12"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    message_file = repo / "COMMIT_EDITMSG"
    message_file.write_text("feat: 增加循环边次数 #13\n", encoding="utf-8")

    completed = subprocess.run(
        ["bash", str(COMMIT_MSG_SCRIPT), str(message_file)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "当前仓库已关联 Issue #12" in completed.stdout
