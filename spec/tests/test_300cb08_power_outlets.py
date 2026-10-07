"""The three 300CB08 panels export their sixteen outputs as power outlets (#806).

Each side's eight outputs are fed by that side's input and run through the
breaker position of the same number. These export each panel from the build
and read the committed files, in both trees, so a regression that only the
committed export held - #822's shape - fails here too.
"""
import pathlib

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
EXPORTS = ROOT / "library" / "exports"
MAN = pathlib.Path("device-types") / "Amphenol Network Solutions"
# device -> (export file, outlet type, label)
PANELS = {
    "300cb08": ("300CB08.yaml", "dc-terminal", None),
    "300cb08-c": ("300CB08-C.yaml", "other", "P40"),
    "300cb08-sc": ("300CB08-SC.yaml", "other", "P40"),
}


def want(kind, label):
    rows = []
    for side in "ab":
        for n in range(1, 9):
            row = {"name": f"output-{side}{n}", "type": kind}
            if label:
                row["label"] = label
            row["power_port"] = f"input-{side}"
            row["description"] = f"Through breaker position breaker-{side}{n}"
            rows.append(row)
    return rows


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    if not DIST.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    from portrayal.artifacts import Dist
    out = tmp_path_factory.mktemp("dcim")
    for name in PANELS:
        dx.export_device(Dist(str(DIST)), name, out, None)
    return out


def check(doc, name):
    fname, kind, label = PANELS[name]
    outlets = doc["power-outlets"]
    assert outlets == want(kind, label)
    assert [p["name"] for p in doc["power-ports"]] == ["input-a", "input-b"]
    assert sum(o["power_port"] == "input-a" for o in outlets) == 8
    assert sum(o["power_port"] == "input-b" for o in outlets) == 8
    bays = {b["position"]: b for b in doc["module-bays"]}
    for o in outlets:
        via = o["description"].rsplit(" ", 1)[-1]
        assert via in bays, (name, o)
        assert bays[via]["description"].endswith(f"; protects {o['name']}"), bays[via]
    assert not any("feed_leg" in o for o in outlets)


@pytest.mark.parametrize("tree", dx.TARGETS)
@pytest.mark.parametrize("name", sorted(PANELS))
def test_the_built_panel_exports_sixteen_fed_outlets(exported, tree, name):
    check(yaml.safe_load((exported / tree / MAN / PANELS[name][0]).read_text()), name)


@pytest.mark.parametrize("tree", dx.TARGETS)
@pytest.mark.parametrize("name", sorted(PANELS))
def test_the_committed_panel_exports_sixteen_fed_outlets(tree, name):
    check(yaml.safe_load((EXPORTS / tree / MAN / PANELS[name][0]).read_text()), name)


@pytest.mark.parametrize("name", sorted(PANELS))
def test_both_trees_carry_the_same_outlets(name):
    docs = [yaml.safe_load((EXPORTS / t / MAN / PANELS[name][0]).read_text())
            for t in dx.TARGETS]
    assert docs[0]["power-outlets"] == docs[1]["power-outlets"]
