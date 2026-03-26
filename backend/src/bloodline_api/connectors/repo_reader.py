"""Helpers for reading Kettle repository exports from disk."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


def read_repo_root(path: Path) -> ET.Element:
    """Parse a `.repo` XML export and return its root element."""

    return ET.parse(path).getroot()
