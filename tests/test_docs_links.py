"""Every relative link in every Markdown file must resolve (keeps the bilingual docs consistent)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FILES = sorted(p for p in ROOT.rglob("*.md") if not any(part.startswith(".") or part in ("data", "reports")
                                                          for part in p.relative_to(ROOT).parts[:-1]))


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(path):
    broken = []
    for target in LINK.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        file_part = target.split("#", 1)[0]
        if file_part and not (path.parent / file_part).resolve().exists():
            broken.append(target)
    assert broken == [], f"{path.relative_to(ROOT)} has broken links: {broken}"


def test_every_spanish_doc_links_back_to_english():
    for path in [ROOT / "README.es.md", *sorted((ROOT / "docs" / "es").glob("*.md"))]:
        assert "[English](" in path.read_text(encoding="utf-8").split("\n\n", 2)[1], path
