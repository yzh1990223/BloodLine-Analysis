from pathlib import Path


def read_java_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")
