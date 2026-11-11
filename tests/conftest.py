from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from govkit import generator, pipeline
from govkit.db import connect

ROOT = Path(__file__).resolve().parents[1]
COPIED = ("governance", "contracts", "models", "examples")


def make_project(destination: Path) -> Path:
    for folder in COPIED:
        if (ROOT / folder).exists():
            shutil.copytree(ROOT / folder, destination / folder)
    (destination / "docs").mkdir(exist_ok=True)
    shutil.copy(ROOT / "docs" / "ci_history.yaml", destination / "docs" / "ci_history.yaml")
    return destination


@pytest.fixture(scope="session")
def project(tmp_path_factory):
    """Copy the governance artefacts to a temp folder and run the full pipeline once."""
    root = make_project(tmp_path_factory.mktemp("project"))
    mp = pytest.MonkeyPatch()
    mp.setenv("GOVKIT_HOME", str(root))
    mp.delenv("GOVKIT_DB", raising=False)
    generator.generate()
    con = connect()
    report = pipeline.run(con=con, log=lambda *_: None)
    yield {"root": root, "con": con, "report": report}
    con.close()
    mp.undo()


@pytest.fixture
def con(project):
    return project["con"]
