"""A configuration's `kind` reaches the compiled index.

#51 gave every configuration a `kind` - base, orderable, example or model - so a
consumer would stop guessing from the name which entry is the bare chassis,
which is a SKU and which is somebody's illustration. The source carried it and
`<device>.configs.json` did not, so a page reading the index saw `base`,
`ac` and `dc-populated` as three equal entries: the guessing #51 exists to
remove, one fetch further along (#66).

These pin the fact to the artifact. The index is where a browser reads a
device, and a second fetch of device.yaml is not something it should have to do
to learn what kind of configuration it is drawing.
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"

# three kinds on one device: a default orderable, a second orderable, and an
# example population that must never read as something you can buy
DEV = LIB / "devices/ufispace/s9510-28dc/device.yaml"
# declares no `configurations:` at all, so the renderer synthesises one
BARE = LIB / "devices/juniper/mx150/device.yaml"


def index_for(device_yaml, tmp_path):
    r = subprocess.run([sys.executable, str(RENDER), str(device_yaml),
                        "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    name = yaml.safe_load(device_yaml.read_text())["name"]
    return json.loads((tmp_path / f"{name}.configs.json").read_text())


def test_every_configuration_in_the_index_carries_its_kind(tmp_path):
    src = yaml.safe_load(DEV.read_text())["configurations"]
    idx = index_for(DEV, tmp_path)
    got = {c["name"]: c.get("kind") for c in idx["configs"]}
    want = {n: c["kind"] for n, c in src.items()}
    assert got == want, (got, want)
    # the three kinds this device declares are all distinguishable downstream
    assert set(got.values()) == {"orderable", "example"}
    assert got[idx["default"]] == "orderable"


def test_a_synthesised_configuration_says_it_has_no_kind(tmp_path):
    """A device with no `configurations:` gets one made up for it, named
    `default`. It declares no kind and the index must not invent one - `null`
    is the honest value, and a consumer can tell it from a declared `base`."""
    idx = index_for(BARE, tmp_path)
    assert [c["name"] for c in idx["configs"]] == ["default"]
    assert "kind" in idx["configs"][0]
    assert idx["configs"][0]["kind"] is None


def test_every_declared_configuration_in_the_library_has_a_kind():
    """The schema leaves `kind` optional, and 228 of 228 declare it. If one
    stops, the index carries `null` for a configuration a person wrote, which
    is the guessing coming back one device at a time."""
    missing = []
    for f in sorted(LIB.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for n, c in (d.get("configurations") or {}).items():
            if (c or {}).get("kind") not in ("base", "orderable", "example", "model"):
                missing.append(f"{f.parent.parent.name}/{f.parent.name}:{n}")
    assert not missing, missing
