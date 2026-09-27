"""A configuration's airflow reaches the compiled index (#513).

Airflow was already a field: `chassis.airflow`, and `configurations.*.airflow`
wherever a build differs from its chassis (L91). The drawing carried the
resolved answer as `data-airflow` on each per-configuration SVG root, and the
DCIM export carried it too - but `<device>.configs.json`, the file a page reads
to list a device's builds, did not. A page filtering builds by airflow was left
parsing `ac-b2f` out of a name or "exhaust airflow" out of a description.

These pin the index to the drawing: both come from `manifest.config_airflow`,
so for every configuration that states airflow, the index's `airflow` is the
SVG's `data-airflow`.

`null` IS NOT ALWAYS AN ABSENT ATTRIBUTE. The SVG root also carries the flattened
`attrs:` bag, and a few devices keep a prose `airflow` there ("front to back;
both listed SKUs are F"). Where nothing structured is stated, that prose is what
the drawing's `data-airflow` holds; a structured value always overwrites it. The
index does not promote prose into the field - a filter needs one of four words,
not a sentence - so there the drawing may carry the attrs prose and nothing
else.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from portrayal import attrsections

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
DIST = LIB / "dist"
RENDER = SPEC / "tools/portrayal/render.py"

# all four `ac|dc x f2b|b2f` builds, airflow stated per configuration - the
# device #513 names as its example
BOTH = LIB / "devices/edgecore/as7326-56x/device.yaml"
# airflow stated only on the chassis, as `side` - the library's own vocabulary
# passes through rather than being forced into front/back
SIDE = LIB / "devices/cisco/asr-9001/device.yaml"
# no configurations and no airflow anywhere: the synthesised `default` build
BARE = LIB / "devices/juniper/mx150/device.yaml"

VOCAB = {"front-to-back", "back-to-front", "side", "passive", None}
AIRFLOW_ATTR = re.compile(r'<svg\b[^>]*?\sdata-airflow="([^"]*)"')
SVG_ROOT = re.compile(r"<svg\b[^>]*>")


def render(device_yaml, tmp_path):
    r = subprocess.run([sys.executable, str(RENDER), str(device_yaml),
                        "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return yaml.safe_load(device_yaml.read_text())["name"]


def svg_airflows(outdir, device, cfg):
    """{data-airflow or None} across every face drawn for one configuration."""
    got = set()
    # through configs.json: a drawing shared with another configuration
    # carries that configuration's name, not this one's (#665)
    files = next(c["files"] for c in json.loads(
        (outdir / f"{device}.configs.json").read_text())["configs"] if c["name"] == cfg)
    for f in (outdir / n for n in files.values()):
        root = SVG_ROOT.search(f.read_text()).group(0)
        m = AIRFLOW_ATTR.search(root)
        got.add(m.group(1) if m else None)
    return got


def check_index_matches_drawings(outdir, device):
    """Every configs[] entry has `airflow`, in the library's vocabulary, equal
    to the data-airflow on each of its drawings (or, where `null`, the drawing
    carries at most the attrs-bag prose). Returns the number of
    configurations compared, so a caller can assert it measured something."""
    idx = json.loads((outdir / f"{device}.configs.json").read_text())
    n = 0
    for c in idx["configs"]:
        assert "airflow" in c, (device, c["name"])
        assert c["airflow"] in VOCAB, (device, c["name"], c["airflow"])
        drawn = svg_airflows(outdir, device, c["name"])
        assert drawn, f"{device}.{c['name']}: no per-configuration SVG to compare"
        if c["airflow"] is None:
            prose = attrsections.flatten(idx.get("attrs")).get("airflow")
            assert drawn == {prose}, (device, c["name"], prose, drawn)
        else:
            assert drawn == {c["airflow"]}, (device, c["name"], c["airflow"], drawn)
        n += 1
    return idx, n


def test_both_directions_resolve_per_configuration(tmp_path):
    name = render(BOTH, tmp_path)
    idx, n = check_index_matches_drawings(tmp_path, name)
    assert n == 4
    got = {c["name"]: c["airflow"] for c in idx["configs"]}
    assert got == {"ac-f2b": "front-to-back", "ac-b2f": "back-to-front",
                   "dc-f2b": "front-to-back", "dc-b2f": "back-to-front"}
    assert "airflow" in idx["chassis"]


def test_a_chassis_only_airflow_is_inherited_and_side_passes_through(tmp_path):
    name = render(SIDE, tmp_path)
    idx, n = check_index_matches_drawings(tmp_path, name)
    assert n >= 1
    assert idx["chassis"]["airflow"] == "side"
    assert {c["airflow"] for c in idx["configs"]} == {"side"}


def test_an_unstated_airflow_is_null_not_invented(tmp_path):
    name = render(BARE, tmp_path)
    idx, n = check_index_matches_drawings(tmp_path, name)
    assert n == 1
    assert idx["chassis"]["airflow"] is None
    assert idx["configs"][0]["airflow"] is None


@pytest.mark.skipif(not DIST.is_dir() or not any(DIST.glob("*.configs.json")),
                    reason="dist/ not built; run ./publish.sh --no-images")
def test_every_published_configuration_matches_its_drawing():
    """The whole library, against the build a consumer downloads."""
    indexes = sorted(DIST.glob("*.configs.json"))
    total = 0
    for f in indexes:
        _, n = check_index_matches_drawings(DIST, f.name[:-len(".configs.json")])
        total += n
    # a dist/ that exists but holds nothing would pass the loop vacuously
    assert total > 100, f"compared only {total} configurations across {len(indexes)} indexes"
