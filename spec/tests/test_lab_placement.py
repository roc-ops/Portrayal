"""Lab placement: rack-face parts on a host, the lab schema, and its checks.

docs/cable-managers-design.md section 6. A lab places library devices in one
rack. A `rack` device takes the units it spans; a `rack-face` part (the
FHD-CMP5DR cable manager) bolts to the rail face over a unit it shares, and is
placed `on` a host at a `unit` of it, or at an `ru`, on a `face`. labs.json
carries every placement with its position resolved.

One failing lab per check (section 12), each the passing lab with one thing
broken, so a check that stops firing fails here rather than passing quietly.
"""
import copy
import json
import pathlib
import sys

import pytest

from portrayal import labs, labs_index, libwalk, lint
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
ROADM = LIB / "labs/roadm-ring-demo/lab.yaml"

# fhd-4ufce is a 4U fibre enclosure, fhd-1ufce a 1U one, fhd-cmp5dr the 0U
# rack-face D-ring manager that shares a rack unit with either.
GOOD = {
    "format": 1, "kind": "lab", "name": "cable-manager-placement",
    "rack": {"height-ru": 42},
    "devices": [
        {"id": "enc-4u", "ref": "fhd-4ufce", "ru": 10},
        {"id": "enc-1u", "ref": "fhd-1ufce", "ru": 20},
        {"id": "mgr-a", "ref": "fhd-cmp5dr", "on": "enc-4u", "face": "front", "unit": 3},
        {"id": "mgr-b", "ref": "fhd-cmp5dr", "on": "enc-4u", "face": "rear", "unit": 3},
        {"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u"},
        {"id": "mgr-d", "ref": "fhd-cmp5dr", "ru": 30, "face": "front"},
    ],
    "links": [],
}


def lab(**changes):
    """GOOD with placements replaced (by id) or added; None removes one."""
    d = copy.deepcopy(GOOD)
    by_id = {p["id"]: i for i, p in enumerate(d["devices"])}
    for pid, p in changes.items():
        pid = pid.replace("_", "-")
        if pid in by_id:
            d["devices"][by_id[pid]] = p
        else:
            d["devices"].append(p)
    d["devices"] = [p for p in d["devices"] if p is not None]
    return d


def run(d):
    found, placed = labs.check(d, [LIB])
    return found, {p["id"]: p for p in placed}


def errors(d):
    return [(code, msg) for code, sev, msg in run(d)[0] if sev == "error"]


# ---- the passing lab ---------------------------------------------------------

def test_the_good_lab_validates_and_raises_nothing():
    assert labs.schema_errors(GOOD) == []
    found, _ = run(GOOD)
    assert found == []


def test_positions_are_resolved_to_rack_units_faces_and_hosts():
    _, p = run(GOOD)
    # rack devices: their own ru, the front, no host
    assert (p["enc-4u"]["ru"], p["enc-4u"]["face"], p["enc-4u"]["host"]) == (10, "front", None)
    assert p["enc-4u"]["mount"] == "rack" and p["enc-4u"]["unit"] is None
    # unit 3 of a 4U host at ru 10 is rack unit 12, counted the way the rack counts
    assert (p["mgr-a"]["ru"], p["mgr-a"]["face"], p["mgr-a"]["host"], p["mgr-a"]["unit"]) \
        == (12, "front", "enc-4u", 3)
    assert (p["mgr-b"]["ru"], p["mgr-b"]["face"]) == (12, "rear")
    assert p["mgr-a"]["mount"] == "rack-face"
    # unit defaults to 1, face to front
    assert (p["mgr-c"]["ru"], p["mgr-c"]["face"], p["mgr-c"]["host"], p["mgr-c"]["unit"]) \
        == (20, "front", "enc-1u", 1)
    # by ru with nothing behind it: no host
    assert (p["mgr-d"]["ru"], p["mgr-d"]["host"]) == (30, None)


def test_every_key_the_lab_wrote_is_kept():
    _, p = run(GOOD)
    for src in GOOD["devices"]:
        for k, v in src.items():
            assert p[src["id"]][k] == v, (src["id"], k)


def test_the_library_lab_passes_the_schema_and_every_check():
    files = libwalk.iter_labs([LIB])
    assert ROADM in files, "the walk found no lab; this test proved nothing"
    for f in files:
        d = load_yaml(f)
        assert labs.schema_errors(d) == [], f
        found, placed = labs.check(d, [LIB])
        assert found == [], (f, found)
        assert all(p["ru"] is not None and p["mount"] == "rack" for p in placed)


# ---- one failing lab per check -----------------------------------------------

FAILING = {
    "L139 a ref that is no device":
        ("L139", lab(enc_1u={"id": "enc-1u", "ref": "fhd-9ufce", "ru": 20},
                     mgr_c=None)),
    "L139 an on that names no placement":
        ("L139", lab(mgr_c={"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-2u"})),
    "L139 an id used twice":
        ("L139", lab(dup={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 25})),
    "L139 a cfg the device does not have":
        ("L139", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 20, "cfg": "no-such"})),
    "L140 face on a rack device":
        ("L140", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 20, "face": "rear"})),
    "L140 a rack device placed on another":
        ("L140", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "on": "enc-4u"},
                     mgr_c=None)),
    "L140 a rack-face part with on and ru":
        ("L140", lab(mgr_c={"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u", "ru": 20})),
    "L140 a rack-face part with neither":
        ("L140", lab(mgr_d={"id": "mgr-d", "ref": "fhd-cmp5dr", "face": "front"})),
    "L140 a unit with no host":
        ("L140", lab(mgr_d={"id": "mgr-d", "ref": "fhd-cmp5dr", "ru": 30, "unit": 1})),
    "L141 a unit beyond the host's height":
        ("L141", lab(mgr_a={"id": "mgr-a", "ref": "fhd-cmp5dr", "on": "enc-4u", "unit": 5})),
    "L141 a host that is itself rack-face":
        ("L141", lab(mgr_c={"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "mgr-d"})),
    "L142 two rack devices overlapping":
        ("L142", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 13}, mgr_c=None)),
    "L142 two rack-face parts on one unit and face":
        ("L142", lab(mgr_b={"id": "mgr-b", "ref": "fhd-cmp5dr", "on": "enc-4u",
                            "face": "front", "unit": 3})),
    "L153 a side on a rack-face part as wide as the rack":
        ("L153", lab(mgr_c={"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u", "side": "left"})),
    "L153 a side on a rack device":
        ("L153", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 20, "side": "right"})),
    "L142 a device outside the rack":
        ("L142", lab(enc_1u={"id": "enc-1u", "ref": "fhd-1ufce", "ru": 43}, mgr_c=None)),
}


@pytest.mark.parametrize("case", sorted(FAILING))
def test_each_check_fails_its_lab(case):
    code, d = FAILING[case]
    assert labs.schema_errors(d) == [], "the fixture should fail the check, not the schema"
    got = errors(d)
    assert [c for c, _ in got] == [code], got


def test_a_rack_face_part_by_ru_over_a_host_is_reported_with_it():
    d = lab(mgr_d={"id": "mgr-d", "ref": "fhd-cmp5dr", "ru": 11, "face": "rear"})
    found, p = run(d)
    assert [(c, s) for c, s, _ in found] == [("L143", "warning")]
    assert "enc-4u" in found[0][2] and "unit: 2" in found[0][2]
    assert (p["mgr-d"]["ru"], p["mgr-d"]["host"], p["mgr-d"]["unit"]) == (11, "enc-4u", 2)


@pytest.mark.parametrize("bad", [
    {"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u", "face": "top"},
    {"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u", "unit": 0},
    {"id": "mgr-c", "ref": "fhd-cmp5dr", "on": "enc-1u", "side": "middle"},
    {"id": "mgr-c", "on": "enc-1u"},
])
def test_the_schema_rejects_a_malformed_placement(bad):
    assert labs.schema_errors(lab(mgr_c=bad))


# ---- the two callers ---------------------------------------------------------

def test_lint_reports_the_checks_under_their_codes():
    path = "library/labs/x/lab.yaml"
    with lint.collecting() as found:
        lint.lint_lab(path, FAILING["L141 a unit beyond the host's height"][1], [LIB])
        lint.lint_lab(path, lab(mgr_d={"id": "mgr-d", "ref": "fhd-cmp5dr", "ru": 11}), [LIB])
    assert len(found.errors) == 1 and "[L141]" in found.errors[0]
    assert len(found.warnings) == 1 and "[L143]" in found.warnings[0]


def _index(tmp_path, monkeypatch, d):
    (tmp_path / "lib/labs/t").mkdir(parents=True)
    (tmp_path / "lib/labs/t/lab.yaml").write_text(json.dumps(d))
    out = tmp_path / "dist"
    monkeypatch.setattr(sys, "argv", ["labs_index", "--library", str(tmp_path / "lib"),
                                      "--library", str(LIB), "--out", str(out)])
    return labs_index.main(), out / "labs.json"


def test_labs_json_carries_resolved_positions(tmp_path, monkeypatch):
    rc, out = _index(tmp_path, monkeypatch, GOOD)
    assert rc == 0
    got = {l["name"]: l for l in json.loads(out.read_text())["labs"]}
    mgr = {p["id"]: p for p in got["cable-manager-placement"]["devices"]}["mgr-a"]
    assert {k: mgr[k] for k in ("ru", "face", "host", "unit", "mount", "on")} == \
        {"ru": 12, "face": "front", "host": "enc-4u", "unit": 3, "mount": "rack-face",
         "on": "enc-4u"}
    # the lab already in the library keeps every field it had
    roadm = got["roadm-ring-demo"]
    src = load_yaml(ROADM)
    assert set(roadm) == {"name", "title", "description", "rack", "devices", "links"}
    assert roadm["links"] == src["links"] and roadm["rack"] == src["rack"]
    for a, b in zip(roadm["devices"], src["devices"]):
        assert {k: a[k] for k in b} == b


def test_labs_index_refuses_a_lab_that_fails_a_check(tmp_path, monkeypatch, capsys):
    rc, out = _index(tmp_path, monkeypatch, FAILING["L142 two rack devices overlapping"][1])
    assert rc == 1 and not out.exists()
    assert "[L142]" in capsys.readouterr().out
