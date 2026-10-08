"""A contract carrying `superseded-by` is not exported as a module type.

A retired major stays in the library so a manifest pinning it still resolves
(#448), and the schema says a consumer offering parts must not offer it. Its
model is its successor's model, so before this the two wrote one file and
`sorted()` decided which survived - the OLD one, wherever a name tied and the
documents differed (#903: MIC-3D-4COC3-1OC12-CE would have gone back to eight
ports).

BUILT FIXTURES, NOT THE LIVE LIBRARY. Each test makes its own contracts from a
real module entry, renamed, so it measures the rule whether or not the library
happens to hold a retired module today. The build is read only for the
manufacturer join and the devices that `seating_depths` walks.
"""
import copy
import json
from pathlib import Path

import pytest

from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
TEMPLATE = "juniper/mpc7e-mrate@2"


def _dist():
    if not (DIST / "components.json").exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    from portrayal.artifacts import Dist
    return Dist(str(DIST))


class _With:
    """The real build, with `modules()` and ref lookup narrowed or extended to
    the fixture entries a test passes."""

    def __init__(self, dist, entries, keep_real=False):
        self._dist, self._entries = dist, list(entries)
        self._keep_real = keep_real
        self._by_ref = {_ref(c): c for c in self._entries}

    def modules(self):
        return (self._dist.modules() if self._keep_real else []) + self._entries

    def component_by_ref(self, ref):
        return self._by_ref.get(ref) or self._dist.component_by_ref(ref)

    def __getattr__(self, name):
        return getattr(self._dist, name)


def _ref(c):
    return f"{c['ns']}/{c['name']}@{str(c['major'])[1:]}"


def _fixture(dist, name, model, version="1.0.0", superseded_by=None):
    base = dist.component_by_ref(TEMPLATE)
    assert base is not None, f"{TEMPLATE} is the fixture's template and is not in the build"
    c = copy.deepcopy(base)
    c.update({"name": name, "major": "v1", "version": version})
    c["attrs"] = dict(c.get("attrs") or {}, model=model)
    c.pop("superseded-by", None)
    if superseded_by:
        c["superseded-by"] = superseded_by
    return c


def _written(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*.yaml"))


def test_the_index_carries_superseded_by_for_every_retired_contract():
    """The export can only skip what the index tells it about."""
    _dist()
    idx = {_ref(c): c for c in
           json.loads((DIST / "components.json").read_text())["components"]}
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
    old = _fixture(dist, "fixture-old", "FIXTURE-RETIRED", superseded_by="juniper/fixture-new@1")
    live = _fixture(dist, "fixture-live", "FIXTURE-LIVE")
    export_modules(_With(dist, [old, live]), str(tmp_path))
    files = _written(tmp_path)
    assert any("FIXTURE-LIVE" in f for f in files), files
    assert not any("FIXTURE-RETIRED" in f for f in files), files


def test_a_retired_major_does_not_change_its_successors_export(tmp_path):
    """Sorted FIRST and identical in what a DCIM reads, so without the skip it
    would collapse into the successor's file and put its own stamp there."""
    from portrayal.dcim_export import export_modules
    dist = _dist()
    old = _fixture(dist, "fixture-a", "FIXTURE-CARD", version="1.9.9",
                   superseded_by="juniper/fixture-b@1")
    new = _fixture(dist, "fixture-b", "FIXTURE-CARD", version="2.0.0")
    alone, both = tmp_path / "alone", tmp_path / "both"
    export_modules(_With(dist, [new]), str(alone))
    export_modules(_With(dist, [old, new]), str(both))
    files = _written(alone)
    assert files, "the live successor wrote nothing - this test measured nothing"
    assert files == _written(both)
    for f in files:
        text = (both / f).read_text()
        assert text == (alone / f).read_text(), f
        assert "(juniper/fixture-a)" not in text, f


def test_a_retired_carrier_passes_no_depth_to_what_its_bays_accept():
    """`seating_depths` keys a carrier by its MODEL, so a retired major shares
    the depth of the live carrier it was replaced by. Read through its bays, it
    would give the modules it accepted a depth no exported document has."""
    from portrayal.dcim_export import module_key, seating_depths
    dist = _dist()
    live = dist.component_by_ref("juniper/mpc1e-3d@3")
    assert live is not None, "juniper/mpc1e-3d@3 is the seated carrier this fixture copies"
    child = _fixture(dist, "fixture-child", "FIXTURE-CHILD")
    child.pop("bays", None)
    carrier = copy.deepcopy(live)
    carrier.update({"name": "fixture-carrier", "major": "v1",
                    "bays": {"b0": {"accepts": [_ref(child)]}}})
    seated = module_key(dist, carrier)
    assert seating_depths(dist).get(seated), \
        "the live carrier is seated nowhere - this test measured nothing"

    key = module_key(dist, child)
    assert key in seating_depths(_With(dist, [carrier, child], keep_real=True)), \
        "a LIVE carrier's bay passes no depth - the control failed"
    carrier["superseded-by"] = "juniper/mpc1e-3d@3"
    assert key not in seating_depths(_With(dist, [carrier, child], keep_real=True))
