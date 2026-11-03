"""The Celestica DS6000 states its airflow once, on the chassis.

The data sheet's order information prints three orders, each ending in its airflow word: the AC
and DC builds end `F2B`, the AC reverse-airflow build ends `B2F`. The reverse build states
`back-to-front` on its configuration, as the library does wherever a build differs; the chassis
states `front-to-back`, so the two other builds resolve to it without a second copy of the fact.

Pinned here: the resolved airflow of each build, the one home, the index's options, the
provenance entry's words, the compiled device (index, drawn faces, fan and supply stamps), the
committed device types and the lock. Each check that reads a compiled or written thing is a
function returning its problems, so a planted wrong value is shown to fail.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock, lint
from portrayal.manifest import config_airflow, device_options

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
DEVICE = LIB / "devices/celestica/ds6000/device.yaml"
RENDER = SPEC / "tools/portrayal/render.py"
EXPORTS = LIB / "exports"

F2B, B2F = "front-to-back", "back-to-front"
WANT = {"ac-f2b": F2B, "ac-b2f": B2F, "dc-f2b": F2B}
# fan and supply groups drawn in each build's rear face
GROUPS = {"ac-f2b": 9, "ac-b2f": 9, "dc-f2b": 5}
# part number -> the DCIM airflow word its device type carries
EXPORTED = {"R4087-F9004-A1": "front-to-rear", "R4087-F9005-A1": "front-to-rear",
            "R4087-F9013-A1": "rear-to-front"}

G_TAG = re.compile(r"<g\b[^>]*>")
CLASS = re.compile(r'\sdata-class="([^"]*)"')
STAMP = re.compile(r'\sdata-config-airflow="([^"]*)"')
ROOT_TAG = re.compile(r"<svg\b[^>]*>")
ROOT_AIRFLOW = re.compile(r'\sdata-airflow="([^"]*)"')


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(DEVICE.read_text())


def test_each_build_resolves_to_the_direction_its_order_line_ends_in(doc):
    got = {name: config_airflow(doc, cfg) for name, cfg in doc["configurations"].items()}
    assert got == WANT


def test_airflow_is_stated_once_on_the_chassis(doc):
    assert doc["chassis"].get("airflow") == F2B
    stated = {n: c.get("airflow") for n, c in doc["configurations"].items() if c.get("airflow")}
    assert stated == {"ac-b2f": B2F}
    with lint.collecting() as found:
        lint.lint_device_airflow_home(DEVICE, doc)
    assert not [e for e in found.errors if "[L91]" in e], found.errors


def test_the_index_offers_both_directions(doc):
    assert device_options(doc)["airflow"] == [B2F, F2B]


def test_the_provenance_entry_says_what_the_data_sheet_prints_and_what_it_does_not(doc):
    entry = doc["provenance"]["airflow"]
    assert entry["confidence"] == "datasheet"
    note = " ".join(entry["note"].split())
    for token in ("100725", "R4087-F9004-A1", "R4087-F9005-A1", "R4087-F9013-A1", "F2B", "B2F"):
        assert token in note, token
    assert "does not spell" in note
    assert "no DC back-to-front order" in note


def render_device(out):
    r = subprocess.run([sys.executable, str(RENDER), str(DEVICE), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((out / "ds6000.configs.json").read_text())


def drawn_problems(out, idx):
    """Problems in a compiled DS6000: the index's airflow, each face's root and every fan and
    supply stamp, against WANT; and the groups counted on the rear face."""
    problems = []
    if idx["chassis"].get("airflow") != F2B:
        problems.append(f"chassis.airflow is {idx['chassis'].get('airflow')!r}")
    for cfg in idx["configs"]:
        want = WANT[cfg["name"]]
        if cfg["airflow"] != want:
            problems.append(f"{cfg['name']}: configs[].airflow is {cfg['airflow']!r}")
        for face, name in cfg["files"].items():
            if not name.endswith(".svg"):
                continue
            text = (out / name).read_text()
            root = ROOT_AIRFLOW.search(ROOT_TAG.search(text).group(0))
            if (root.group(1) if root else None) != want:
                problems.append(f"{cfg['name']} {face}: root data-airflow is {root and root.group(1)!r}")
            groups = [g for g in G_TAG.findall(text)
                      if (CLASS.search(g) or [None, None])[1] in ("fan", "psu")]
            for g in groups:
                stamp = STAMP.search(g)
                if (stamp.group(1) if stamp else None) != want:
                    problems.append(f"{cfg['name']} {face}: a {CLASS.search(g).group(1)} says "
                                    f"{stamp and stamp.group(1)!r}")
            if face == "rear" and len(groups) != GROUPS[cfg["name"]]:
                problems.append(f"{cfg['name']} rear: {len(groups)} fan and supply groups")
    return problems


@pytest.mark.heavy
def test_the_compiled_device_states_its_direction_on_every_build(tmp_path):
    idx = render_device(tmp_path)
    assert {c["name"] for c in idx["configs"]} == set(WANT)
    assert drawn_problems(tmp_path, idx) == []
    # a planted wrong value is found: the index, a face's root and a stamp
    idx["configs"][0]["airflow"] = None
    assert any("configs[].airflow" in p for p in drawn_problems(tmp_path, idx))
    idx = render_device(tmp_path)
    rear = next(c for c in idx["configs"] if c["name"] == "ac-f2b")["files"]["rear"]
    text = (tmp_path / rear).read_text()
    (tmp_path / rear).write_text(text.replace('data-config-airflow="front-to-back"',
                                              'data-config-airflow="back-to-front"', 1))
    assert len(drawn_problems(tmp_path, idx)) == 1


def export_airflow(vendor_dir, part):
    return yaml.safe_load((vendor_dir / f"{part}.yaml").read_text()).get("airflow")


@pytest.mark.parametrize("dcim", ["netbox", "nautobot"])
def test_the_committed_device_types_carry_the_direction(dcim):
    folder = EXPORTS / dcim / "device-types/Celestica"
    assert {p: export_airflow(folder, p) for p in EXPORTED} == EXPORTED


def test_the_lock_agrees_with_the_device():
    found = [f for f in devicelock.check(LIB) if f[0] == "celestica/ds6000"]
    assert found == []
