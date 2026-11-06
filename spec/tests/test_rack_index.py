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
    # no source names the cable: said outright, as null (#1032)
    assert e["capacity"] == {"count": 30, "basis": "Cat6", "media": None}
    assert e["guides"] == {"front": ["duct", "guide-1", "guide-2", "guide-3"]}
    assert e["passes"] == {"front": ["window-1"]}


def test_a_pass_through_on_a_side_view_is_exported_and_a_guide_there_is_not(tmp_path):
    """P-0016: the CMH-4DRB1U's end walls each have a hole, declared on its
    left and right views. Only the top, front and rear views were read, so
    those never reached rack.json. A pass-through is read from the sides too;
    guides stay the three views they were (a side view's marks are not a
    pathway a route names)."""
    side = FACE.replace('id="pass--window-1"', 'id="pass--end-hole"')
    d = _dist(tmp_path, {"w": 440, "h": 44, "d": 88, "ru": 1, "mount": "rack-face"},
              faces={"front": FACE, "left": side, "right": side})
    e = rack_index.build(d)["devices"]["mgr"]
    assert e["passes"] == {"front": ["window-1"], "left": ["end-hole"], "right": ["end-hole"]}
    assert e["guides"] == {"front": ["duct", "guide-1", "guide-2", "guide-3"]}
    # a part with none on its sides gains no key
    (tmp_path / "none").mkdir()
    d = _dist(tmp_path / "none", {"w": 440, "h": 44, "d": 88, "ru": 1}, faces={"front": FACE, "left": FACE.replace("pass--window-1", "x")})
    assert rack_index.build(d)["devices"]["mgr"]["passes"] == {"front": ["window-1"]}


def test_a_capacity_carries_the_kind_of_cable_it_counts_only_where_the_device_states_it(tmp_path):
    """#1032: `cable-capacity-media` is what a rack tool compares the count
    with. The test above is the other half: a device that states none gets
    `media: null`, never a missing key, so a reader can tell it from a
    catalogue built before the key existed."""
    d = _dist(tmp_path, {"w": 483, "h": 44, "d": 110, "ru": 1, "mount": "rack-face"},
              {"performance": {"cable-capacity": 30, "cable-capacity-basis": "Cat6 24AWG", "cable-capacity-media": "cat6"}})
    assert rack_index.build(d)["devices"]["mgr"]["capacity"] == {"count": 30, "basis": "Cat6 24AWG", "media": "cat6"}


def test_an_estimated_capacity_is_marked_and_a_stated_one_never_is(tmp_path):
    """P-0027: `cable-capacity-estimated: true` marks a count the maker does not
    state. `rack.json` carries `estimated: true` for it and no key at all for a
    stated count, so every catalogue built before it reads as stated."""
    perf = {"cable-capacity": 54, "cable-capacity-basis": "ESTIMATE, not stated", "cable-capacity-media": "cat6"}
    mount = {"w": 483, "h": 44, "d": 110, "ru": 1, "mount": "rack-face"}
    est = rack_index.build(_dist(tmp_path, mount, {"performance": {**perf, "cable-capacity-estimated": True}}))
    assert est["devices"]["mgr"]["capacity"] == {"count": 54, "basis": "ESTIMATE, not stated", "media": "cat6", "estimated": True}
    (tmp_path / "s").mkdir()
    stated = rack_index.build(_dist(tmp_path / "s", mount, {"performance": perf}))
    assert "estimated" not in stated["devices"]["mgr"]["capacity"]


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


def test_the_default_ear_position_is_written_only_where_the_device_states_one(tmp_path):
    """P-0015: the kit's setbackOf reads `ears.default.at` and puts the front of a
    part that states it that far in front of the rail. rack.json is the only
    file it reads, so a position the part states has to reach it."""
    positions = [{"name": "recessed", "at": -25.4}, {"name": "proud", "at": 75.7, "default": True}]
    d = _dist(tmp_path, {"h": 44, "d": 174, "ears": {"positions": positions, "h": 40.0}})
    assert rack_index.build(d)["devices"]["mgr"]["ears"] == {"default": {"name": "proud", "at": 75.7}}
    # a position with no `at` is a name only: nothing to place by
    d = _dist(tmp_path, {"h": 44, "ears": {"positions": [{"name": "flush", "default": True}]}})
    assert "ears" not in rack_index.build(d)["devices"]["mgr"]
    # none is the default, no positions, `behind` alone, or no ears at all
    for ears in ({"positions": [{"name": "proud", "at": 40}]}, {"behind": True}, {}, None):
        d = _dist(tmp_path, {"h": 44, "ears": ears} if ears is not None else {"h": 44})
        assert "ears" not in rack_index.build(d)["devices"]["mgr"], ears


def test_the_default_ear_position_reaches_the_real_rack_json():
    """The FS managers whose source states a position carry it (two are read
    here); the one whose source states none (CMH-4DRB1U: no recess figure) and
    the rack-side verticals carry nothing."""
    from pathlib import Path
    built = Path(__file__).resolve().parents[2] / "library/dist/rack.json"
    if not built.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    devices = json.loads(built.read_text())["devices"]
    assert devices["cmh-dfd1u"]["ears"] == {"default": {"name": "proud", "at": 75.7}}
    assert devices["cmh-5dr1u"]["ears"]["default"]["at"] == 85.5
    assert "ears" not in devices["cmh-4drb1u"]
    assert not any("ears" in devices[n] for n in devices if n.startswith("cmv-"))


def _kit(ref, supply, configurations, motion="sliding"):
    """One row of `chassis.kits` as configs.json publishes it, the kit resolved inline."""
    return {"ref": ref, "supply": supply, "variant": None, "depth": None, "version": "1.0.0",
            "motion": motion, "travel": None, "install": None, "configurations": configurations,
            "parts": [], "accessories": []}


def test_the_default_kit_is_written_with_its_motion_and_depth_range(tmp_path):
    """The schema's rule: the site defaults to the `in-box` kit, then to the first
    listed. rack.json carries that kit's ref, motion and depth range, so a rack
    tool need not open the device's configs.json."""
    optional = _kit("acme/slide@1", "optional", [{"id": "four-post", "depth": [600, 800]}])
    in_box = _kit("acme/brackets@1", "in-box", [{"id": "four-post", "depth": [500, 700]}], motion="fixed")
    d = _dist(tmp_path, {"h": 44, "kits": [optional, in_box]})
    assert rack_index.build(d)["devices"]["mgr"]["kit"] == {
        "ref": "acme/brackets@1", "motion": "fixed", "depth": [500, 700]}
    # none in the box: the first listed
    (tmp_path / "b").mkdir()
    d = _dist(tmp_path / "b", {"h": 44, "kits": [optional, _kit("acme/other@1", "optional", [])]})
    assert rack_index.build(d)["devices"]["mgr"]["kit"]["ref"] == "acme/slide@1"
    # a range per hole type is published as the kit writes it
    (tmp_path / "c").mkdir()
    holes = {"square": [631, 868], "round": [617, 861]}
    d = _dist(tmp_path / "c", {"h": 44, "kits": [_kit("acme/slide@1", "in-box", [{"id": "four-post", "depth": holes}])]})
    assert rack_index.build(d)["devices"]["mgr"]["kit"]["depth"] == holes


def test_a_preset_with_no_range_is_published_with_no_depth_key(tmp_path):
    """A configuration may state a `preset` and no `depth`: factory setting known,
    range unknown. The key is absent, never null and never [preset, preset]."""
    kit = _kit("acme/rail@1", "in-box", [{"id": "four-post", "preset": 630}], motion="telescoping")
    e = rack_index.build(_dist(tmp_path, {"h": 44, "kits": [kit]}))["devices"]["mgr"]
    assert e["kit"] == {"ref": "acme/rail@1", "motion": "telescoping", "preset": 630}
    # a kit with several configurations has no default one: neither figure is written
    (tmp_path / "many").mkdir()
    bands = [{"id": "a", "depth": [600, 700]}, {"id": "b", "depth": [700, 800]}]
    e = rack_index.build(_dist(tmp_path / "many", {"h": 44, "kits": [_kit("acme/bands@1", "in-box", bands)]}))["devices"]["mgr"]
    assert e["kit"] == {"ref": "acme/bands@1", "motion": "sliding"}


def test_a_device_with_no_kit_has_no_kit_key(tmp_path):
    for chassis in ({"h": 44}, {"h": 44, "kits": []}, {"h": 44, "kits": None}):
        d = _dist(tmp_path, chassis)
        assert "kit" not in rack_index.build(d)["devices"]["mgr"], chassis


def test_a_kit_the_index_does_not_resolve_writes_no_key_and_does_not_crash(tmp_path):
    """A row that names a ref and nothing of the kit (no motion), or is not a row."""
    unresolved = {"ref": "acme/gone@1", "supply": "in-box", "variant": None, "depth": None}
    for kits in ([unresolved], ["acme/gone@1"], [None]):
        d = _dist(tmp_path, {"h": 44, "kits": kits})
        assert "kit" not in rack_index.build(d)["devices"]["mgr"], kits


def test_every_device_carries_its_kind(tmp_path):
    d = _dist(tmp_path, {"h": 44, "airflow": "passive"}, device={"profile": "optical"})
    assert rack_index.build(d)["devices"]["mgr"]["kind"] == "patch panel"
    assert rack_index.build(d)["format"] == 1


def test_devices_json_carries_each_manifests_profile():
    """rack_index reads `profile` from devices.json, so the built index must publish it."""
    from pathlib import Path
    built = Path(__file__).resolve().parents[2] / "library/dist/devices.json"
    if not built.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    devices = {x["name"]: x for x in json.loads(built.read_text())["devices"]}
    assert devices["r740xd"]["profile"] == "server"
    assert devices["fhd-cmp5dr"]["profile"] == "passive"
    assert devices["fhd-1ufce"]["profile"] == "optical"
    assert all(x["profile"] for x in devices.values())


def test_the_real_library_gets_a_plain_kind():
    """kind_of on the shipped manifests: a patch panel, a router and a cable manager."""
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "library/devices"
    def kind(name):
        d = yaml.safe_load((root / name / "device.yaml").read_text())
        return rack_index.kind_of(d, d.get("chassis") or {})
    assert kind("fs/fhd-1ufce") == "patch panel"
    assert kind("juniper/mx960") == "router"
    assert kind("fs/cmh-bs-dfdabs2u") == "cable manager"
