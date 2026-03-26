"""Helpers for loading Java source files from disk."""

from pathlib import Path


def read_java_source(path: Path) -> str:
    """Read a Java source file as UTF-8 text for parser consumption."""

    return path.read_text(encoding="utf-8")
