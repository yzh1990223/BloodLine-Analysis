from pathlib import Path


def test_backend_package_exists():
    assert Path("src/bloodline_api/__init__.py").exists()


def test_frontend_package_manifest_exists():
    assert Path("../frontend/package.json").exists()
