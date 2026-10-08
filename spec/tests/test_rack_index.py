"""rack.json, the rack catalogue the kit's rack/catalog.js reads: every
device's rack units, depth, mount, shell, stated cable capacity, and the ids a
cable route can pass through, per view of its default configuration."""
import json

import pytest

from portrayal import rack_index

FACE = """<svg xmlns="http://www.w3.org/2000/svg">
  <g id="guide-1" data-guide="ring" data-ref="fs/d-ring-snap-in@1:1.1.0"/>
  <rect id="guide-2-end" data-kind="ring"/>
  <rect id="guide--duct" data-class="guide"/>
  <path id="pass--window-1" data-class="pass"/>
  <g id="guide-3" data-group="guides" data-ref="fs/cmh-4drb1u-ring@1:1.1.0"/>
  <g id="port-1" data-group="ports" data-ref="x"/>
</svg>"""


def test_marked_reads_every_way_a_pathway_is_drawn(tmp_path):
    p = tmp_path / "face.svg"
    p.write_text(FACE)
    assert rack_index.marked(p) == (["duct", "guide-1", "guide-2", "guide-3"], ["window-1"])


def test_marked_on_a_missing_face_is_empty(tmp_path):
    assert rack_index.marked(tmp_path / "nope.svg") == ([], [])


def _dist(tmp_path, chassis, attrs=None, faces=None, device=None):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": [
        {"name": "mgr", "manufacturer": "FS.com", "model": "FHD-CMP5DR", "profile": "passive", **(device or {})}]}))
    (tmp_path / "mgr.configs.json").write_text(json.dumps({
        "chassis": chassis, "default": "base", "configs": [{"name": "base"}], "attrs": attrs or {}}))
    for view, text in (faces or {}).items():
        (tmp_path / f"mgr.base.{view}.svg").write_text(text)
    return tmp_path


def test_a_rack_face_sheet_with_a_capacity(tmp_path):
    d = _dist(tmp_path, {"w": 483, "h": 44, "d": 110, "ru": 1, "mount": "rack-face", "shell": "sheet"},
              {"performance": {"cable-capacity": 30, "cable-capacity-basis": "Cat6"}}, {"front": FACE})
    e = rack_index.build(d)["devices"]["mgr"]
    assert e["mount"] == "rack-face" and e["shell"] == "sheet" and e["ru"] == 1 and e["d"] == 110
    assert e["capacity"] == {"count": 30, "basis": "Cat6"}
    assert e["guides"] == {"front": ["duct", "guide-1", "guide-2", "guide-3"]}
    assert e["passes"] == {"front": ["window-1"]}


def test_a_rack_device_states_no_mount_and_derives_its_units(tmp_path):
    e = rack_index.build(_dist(tmp_path, {"w": 440, "h": 88.9, "d": 300, "mount": "rack"}))["devices"]["mgr"]
    assert "mount" not in e and "shell" not in e and "capacity" not in e and e["ru"] == 2


def test_the_file_states_its_format(tmp_path):
    assert rack_index.build(_dist(tmp_path, {"h": 44}))["format"] == 1


def test_a_shared_face_is_read_from_the_file_the_index_names(tmp_path):
    d = _dist(tmp_path, {"h": 44})
    idx = json.loads((d / "mgr.configs.json").read_text())
    idx["configs"] = [{"name": "base", "files": {"front": "other.base.front.svg"}}]
    (d / "mgr.configs.json").write_text(json.dumps(idx))
    (d / "other.base.front.svg").write_text(FACE)
    e = rack_index.build(d)["devices"]["mgr"]
    assert e["guides"] == {"front": ["duct", "guide-1", "guide-2", "guide-3"]}
    assert "rear" not in e["guides"]


def test_a_face_the_index_does_not_name_falls_back_to_the_conventional_file(tmp_path):
    d = _dist(tmp_path, {"h": 44}, faces={"front": FACE})
    assert rack_index.face_file({"configs": [{"name": "base"}]}, "mgr", "base", "front") == "mgr.base.front.svg"
    assert rack_index.build(d)["devices"]["mgr"]["guides"]["front"][0] == "duct"



@pytest.mark.parametrize("device, chassis, kind", [
    ({"profile": "server"}, {}, "server"),
    ({"profile": "power"}, {}, "pdu"),
    ({"profile": "passive"}, {"mount": "rack-face"}, "cable manager"),
    ({"profile": "optical"}, {"airflow": "passive"}, "patch panel"),
    ({"profile": "optical"}, {"airflow": "front-to-back"}, "optical"),
    ({"profile": "networking", "portfolio": {"family": "Aggregation Services Router"}}, {}, "router"),
    ({"profile": "networking", "portfolio": {"family": "Universal Routing Platform"}}, {}, "router"),
    ({"profile": "networking", "portfolio": {"family": "Leaf Switch"}}, {}, "switch"),
    ({"profile": "networking", "description": "1U top-of-rack switch, 48 x 25G"}, {}, "switch"),
    ({"profile": "networking", "description": "The 2RU Nokia 7750 SR-1 service router"}, {}, "router"),
    ({"profile": "networking", "portfolio": {"family": "PTP grandmaster"}}, {}, "network device"),
    ({"profile": "lab-bench"}, {}, "device"),
    ({}, {}, "device"),
])
def test_kind_is_a_plain_word_from_the_profile_and_the_vendors_own_words(device, chassis, kind):
    assert rack_index.kind_of(device, chassis) == kind


def test_every_device_carries_its_kind(tmp_path):
    d = _dist(tmp_path, {"h": 44, "airflow": "passive"}, device={"profile": "optical"})
    assert rack_index.build(d)["devices"]["mgr"]["kind"] == "patch panel"
    assert rack_index.build(d)["format"] == 1


def test_devices_json_carries_each_manifests_profile(tmp_path):
    """rack_index reads `profile` from devices.json, so the index must publish it."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, root / "spec/tools/portrayal/devices_index.py",
                        "--library", root / "library", "--out", tmp_path], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    devices = {x["name"]: x for x in json.loads((tmp_path / "devices.json").read_text())["devices"]}
    assert devices["r740xd"]["profile"] == "server"
    assert devices["fhd-cmp5dr"]["profile"] == "passive"
    assert devices["fhd-1ufce"]["profile"] == "optical"
    assert all(x["profile"] for x in devices.values())
