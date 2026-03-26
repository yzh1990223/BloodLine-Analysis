from pathlib import Path


def test_backend_package_exists():
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "backend/src/bloodline_api/__init__.py").exists()


def test_frontend_package_manifest_exists():
    repo_root = Path(__file__).resolve().parents[2]
    assert (repo_root / "frontend/package.json").exists()
