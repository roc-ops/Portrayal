"""Each distinct drawing is written once, and `configs[].files` finds it (#665).

Configurations that differ only in a part a face cannot see draw that face
identically. Each used to write its own copy: the R740xd's 42 configurations
wrote 252 faces holding 35 distinct drawings, and with the source manifest in
every one of them that device alone was 46.5 MB - at the 50 MB a package on the
CDN may weigh. A drawing is now written once and `files` in
`<device>.configs.json` says which file each configuration's face is.

What is pinned is the published build: that every configuration's face
resolves to a file that exists, that every face on disk is some
configuration's, and that no two files hold the same drawing.
"""
import hashlib
import json
import pathlib
from collections import defaultdict

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def _indexes():
    found = sorted(DIST.glob("*.configs.json"))
    if not found:
        pytest.skip("library/dist not built - run ./build.sh")
    return [json.loads(p.read_text()) for p in found]


def _faces():
    """The per-configuration face files: <device>.<config>.<view>.svg."""
    return [p for p in DIST.glob("*.svg") if len(p.name.split(".")) == 4]


def test_every_configuration_names_a_file_for_every_face_it_draws():
    checked = 0
    for idx in _indexes():
        for c in idx["configs"]:
            files = c.get("files")
            assert files, f"{idx['device']}:{c['name']} lists no files"
            for view, name in files.items():
                assert view in idx["views"], f"{idx['device']}:{c['name']} files a non-face {view!r}"
                assert name.startswith(f"{idx['device']}.") and name.endswith(f".{view}.svg"), name
                assert (DIST / name).exists(), f"{idx['device']}:{c['name']} {view} -> missing {name}"
                checked += 1
    assert checked > 1000, f"only {checked} faces resolved; the build is not the library"


def test_every_face_on_disk_is_some_configurations():
    """A face nothing points at is left over from another build, and a
    consumer walking the directory would take it for a drawing."""
    named = {n for idx in _indexes() for c in idx["configs"] for n in c["files"].values()}
    orphans = sorted(p.name for p in _faces() if p.name not in named)
    assert not orphans, f"{len(orphans)} faces no configuration draws: {orphans[:5]}"


def test_no_two_files_hold_the_same_drawing():
    by_content = defaultdict(list)
    for p in _faces():
        by_content[hashlib.sha256(p.read_bytes()).hexdigest()].append(p.name)
    twins = [names for names in by_content.values() if len(names) > 1]
    assert not twins, f"{len(twins)} drawings written more than once: {twins[:3]}"


def test_a_face_does_not_say_which_configuration_it_is():
    """A shared drawing belongs to several, so it can name none of them."""
    said = [p.name for p in _faces() if 'data-config="' in p.read_text()[:4000]]
    assert not said, f"{len(said)} faces still carry data-config: {said[:5]}"


def test_the_r740xd_shares_its_faces():
    """The device that prompted this: 42 configurations, 6 faces each."""
    idx = json.loads((DIST / "r740xd.configs.json").read_text())
    drawn = sum(len(c["files"]) for c in idx["configs"])
    files = {n for c in idx["configs"] for n in c["files"].values()}
    assert drawn == 252, drawn
    assert len(files) < 60, f"{len(files)} files for 252 faces - nothing was shared"
    fronts = {c["files"]["front"] for c in idx["configs"]}
    assert len(fronts) == 2, f"the R740xd draws two fronts (SFF and LFF), not {len(fronts)}"
