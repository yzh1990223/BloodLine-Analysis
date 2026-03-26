from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


def read_repo_root(path: Path) -> ET.Element:
    return ET.parse(path).getroot()
