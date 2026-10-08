"""A contract carrying `superseded-by` is not exported as a module type.

A retired major stays in the library so a manifest pinning it still resolves
(#448), and the schema says a consumer offering parts must not offer it. Its
model is its successor's model, so before this the two wrote one file and
`sorted()` decided which survived - the OLD one, wherever a name tied and the
documents differed (#903: MIC-3D-4COC3-1OC12-CE would have gone back to eight
ports).

These read library/dist, as the other export tests do.
"""
import json
from pathlib import Path

import pytest

from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def _dist():
    if not (DIST / "components.json").exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    from portrayal.artifacts import Dist
    return Dist(str(DIST))


class _Only:
    """The real build, with `modules()` narrowed to the entries a test names."""

    def __init__(self, dist, entries):
        self._dist, self._entries = dist, entries

    def modules(self):
        return list(self._entries)

    def __getattr__(self, name):
        return getattr(self._dist, name)


def _ref(c):
    return f"{c['ns']}/{c['name']}@{str(c['major'])[1:]}"


def _retired_pair(dist):
    """A retired module major and its live successor, both in the build."""
    for c in dist.modules():
        succ = c.get("superseded-by")
        if succ and dist.component_by_ref(succ) and not dist.component_by_ref(succ).get("superseded-by"):
            return c, dist.component_by_ref(succ)
    pytest.skip("no retired module with a live successor in this build")


def _written(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*.yaml"))


def test_the_index_carries_superseded_by_for_every_retired_contract():
    """The export can only skip what the index tells it about."""
    _dist()
    idx = {_ref(c): c for c in json.loads((DIST / "components.json").read_text())["components"]}
    retired = []
    for cf in sorted((ROOT / "library" / "components").glob("*/*/v*/contract.yaml")):
        data = load_yaml(cf) or {}
        if data.get("superseded-by"):
            ref = f"{cf.parents[2].name}/{cf.parents[1].name}@{cf.parent.name[1:]}"
            retired.append(ref)
            assert idx[ref].get("superseded-by") == data["superseded-by"], ref
    assert retired, "no contract carries superseded-by - this test measured nothing"


def test_a_retired_module_alone_writes_nothing(tmp_path):
    from portrayal.dcim_export import export_modules
    dist = _dist()
    old, _new = _retired_pair(dist)
    export_modules(_Only(dist, [old]), str(tmp_path))
    assert _written(tmp_path) == []


def test_a_retired_major_does_not_change_its_successors_export(tmp_path):
    """Listed FIRST, so without the skip it would win the collision or merge
    its stamp into the successor's document."""
    from portrayal.dcim_export import export_modules
    dist = _dist()
    old, new = _retired_pair(dist)
    alone, both = tmp_path / "alone", tmp_path / "both"
    export_modules(_Only(dist, [new]), str(alone))
    export_modules(_Only(dist, [old, new]), str(both))
    files = _written(alone)
    assert files, "the live successor wrote nothing - this test measured nothing"
    assert files == _written(both)
    for f in files:
        assert (alone / f).read_text() == (both / f).read_text(), f
