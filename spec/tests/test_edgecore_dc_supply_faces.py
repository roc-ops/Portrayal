"""The COR550, COR580 and CSR440 DC builds seat their own supply (not the AC face).

Each DC configuration used to seat the AC part and override its attributes. The
quick starts picture the DC supply's terminal end, so each device now has a DC
supply component of its own: `edgecore/cor550-psu-dc`, `edgecore/fsj033-610g`
and `edgecore/csr440-psu-dc`. Everything here pins a figure, a token or a
sentence this change writes, so a later edit has to say it is moving one.

A consumer that picks the AC or DC picture for a build reads the supply type
only from `attrs.input` of the supplies fitted in each configuration's bays,
accepts only `ac`, `dc` and `hvdc`, and ignores a configuration's `power:` list
and `component-attrs`. The DC configurations therefore seat the new parts
through `bays:`.
"""
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
EXPORT = SPEC / "tools/portrayal/dcim_export.py"

TOKENS = {"ac", "dc", "hvdc"}
TOL = 0.06

# device -> the view that carries the supplies, the two configurations, the bays,
# the AC and DC parts and the gap the change rewrites
DEVICES = {
    "cor550": dict(view="rear", ac_cfg="ac-f2b", dc_cfg="dc-f2b", bays=["psu-0", "psu-1"],
                   ac="edgecore/cor550-psu-ac@1", dc="edgecore/cor550-psu-dc@1",
                   gap="dc-supply-face", version="3.1.0"),
    "cor580": dict(view="rear", ac_cfg="ac-f2b", dc_cfg="dc48-f2b", bays=["psu-1", "psu-2"],
                   ac="common/psu-ac-1300@1", dc="edgecore/fsj033-610g@1",
                   gap="dc-psu-module", version="3.1.0"),
    "csr440": dict(view="front", ac_cfg="ac", dc_cfg="dc", bays=["psu-1", "psu-2"],
                   ac="edgecore/csr440-psu-ac@1", dc="edgecore/csr440-psu-dc@1",
                   gap="dc-power-supply", version="2.1.0"),
}

# the new parts: the figures each carries
PARTS = {
    "edgecore/cor550-psu-dc@1": dict(
        model=None, part=None, power_output=None, note="-48 - -60 VDC, 40 A max",
        size=(54.5, 40.8), ac="edgecore/cor550-psu-ac@1", poles=2, ground=0, studs=3),
    "edgecore/fsj033-610g@1": dict(
        model="FSJ033-610G", part="F0OEC9524003Z", power_output=1300,
        note="-40 V - -75 V, 40 A maximum",
        size=(57.0, 40.0), ac="common/psu-ac-1300@1", poles=2, ground=1, studs=0),
    "edgecore/csr440-psu-dc@1": dict(
        model="AS7535-28XB DC PSU", part=None, power_output=None,
        note="-44 - -60V, 15.5-9.6 A, per PS",
        size=(53.8, 39.4), ac="edgecore/csr440-psu-ac@1", poles=2, ground=1, studs=0),
}


def _load(p):
    return yaml.safe_load(pathlib.Path(p).read_text())


def _dir(ref):
    name, major = ref.split("@")
    return LIB / "components" / name / f"v{major}"


def _contract(ref):
    return _load(_dir(ref) / "contract.yaml")


def _skin(ref):
    return (_dir(ref) / "skins/default.svg").read_text()


def _device(name):
    return _load(LIB / "devices/edgecore" / name / "device.yaml")


def _layout(name):
    return _load(LIB / "devices/edgecore" / name / "layout.yaml")


def _bays(name, doc=None):
    doc = doc or _device(name)
    comp = doc["views"][DEVICES[name]["view"]]["components"]
    return {b["id"]: b for b in comp["bays"]}


def _fitted(name, cfg):
    """What each supply bay holds in a configuration: its own `bays:` entry, else the bay default."""
    doc = _device(name)
    c = doc["configurations"][cfg]
    bays = _bays(name, doc)
    return {i: (c.get("bays") or {}).get(i) or bays[i].get("default") for i in DEVICES[name]["bays"]}


def _words(s):
    return " ".join(str(s).split())


def _inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox - TOL and iy >= oy - TOL and ix + iw <= ox + ow + TOL and iy + ih <= oy + oh + TOL


# ---- the three new parts ------------------------------------------------------

@pytest.mark.parametrize("ref", PARTS)
def test_a_new_dc_supply_is_a_1_0_0_module_with_a_contract_and_one_skin(ref):
    c = _contract(ref)
    assert c["version"] == "1.0.0"
    assert c["kind"] == "module" and c["class"] == "psu"
    assert (_dir(ref) / "skins/default.svg").is_file()
    assert c["skins"] == ["default"]


@pytest.mark.parametrize("ref", PARTS)
def test_the_supply_states_a_dc_token_a_terminal_inlet_and_the_range_sentence(ref):
    a = _contract(ref)["attrs"]
    assert a["input"] == "dc"
    assert a["inlet"] == "dc-terminal"
    assert a["input-note"] == PARTS[ref]["note"]


@pytest.mark.parametrize("ref", PARTS)
def test_the_model_the_part_and_the_output_are_what_is_printed(ref):
    a = _contract(ref)["attrs"]
    want = PARTS[ref]
    assert a.get("model") == want["model"]
    assert a.get("part") == want["part"]
    assert a.get("power-output-w") == want["power_output"]
    if want["power_output"] is None:
        assert a["power-absent"] == "not-published"
    else:
        assert "power-absent" not in a


@pytest.mark.parametrize("ref", PARTS)
def test_the_envelope_is_the_ac_siblings_and_declared_borrowed(ref):
    c, ac = _contract(ref), _contract(PARTS[ref]["ac"])
    w, h = PARTS[ref]["size"]
    assert (c["size"]["w"], c["size"]["h"]) == (w, h) == (ac["size"]["w"], ac["size"]["h"])
    assert c["size-confidence"]["w"] == "borrowed" and c["size-confidence"]["h"] == "borrowed"
    text = _words(c["provenance"]["size"])
    assert PARTS[ref]["ac"] in text, "the borrowed size names the part it came from"
    assert "BORROWED" in text.upper()


@pytest.mark.parametrize("ref", PARTS)
def test_every_figure_is_estimated_and_no_photograph_is_claimed(ref):
    p = _contract(ref)["provenance"]
    face = _words(p["the-face"])
    for word in ("illustration", "estimated", "quick start"):
        assert word in face.lower(), word
    assert "no photograph" in face.lower()
    assert "no 3d model" in face.lower() or "3d-models" in face.lower()


@pytest.mark.parametrize("ref", PARTS)
def test_the_connector_direction_and_pole_order_are_stated_or_not_stated(ref):
    d = _words(_contract(ref)["provenance"]["connector-direction"])
    assert "not stated" in d
    assert "out of the face" in d
    assert re.search(r"DC return", d)
    assert re.search(r"left", d) and re.search(r"right", d)


@pytest.mark.parametrize("ref", PARTS)
def test_what_is_not_stated_is_not_in_the_contract(ref):
    c = _contract(ref)
    # no wire, lug or mating plug is drawn and no wire direction is claimed as a fact
    svg = _skin(ref).lower()
    for word in ("wire", "lug", "plug"):
        assert f'id="{word}' not in svg
    assert not any("wire" in k or "lug" in k for k in c["elements"])
    assert not any("wire" in k for k in c["attrs"])


@pytest.mark.parametrize("ref", PARTS)
def test_no_vendor_logo_or_wordmark_is_drawn(ref):
    svg = _skin(ref).lower()
    assert "edgecore" not in svg and "accton" not in svg
    assert "<image" not in svg


def test_the_cor550_reserves_the_logo_zone_where_the_figure_prints_a_mark_and_draws_none():
    ref = "edgecore/cor550-psu-dc@1"
    c = _contract(ref)
    assert c["elements"]["logo-zone"]["class"] == "label"
    assert re.search(r'<rect id="logo-zone"[^>]*fill="none"', _skin(ref))
    assert "diamond" in _words(c["provenance"]["logo-zone"])
    assert "polygon" not in _skin(ref).lower()


@pytest.mark.parametrize("ref", ["edgecore/fsj033-610g@1", "edgecore/csr440-psu-dc@1"])
def test_the_other_two_figures_print_no_mark_so_no_zone_is_reserved(ref):
    assert "logo-zone" not in _contract(ref)["elements"]
    assert "none reserved" in _words(_contract(ref)["provenance"]["logo-zone"])


@pytest.mark.parametrize("ref", PARTS)
def test_the_face_has_its_poles_its_handle_and_its_latch_counted(ref):
    svg = _skin(ref)
    want = PARTS[ref]
    assert len(re.findall(r'id="pole-\d"', svg)) == want["poles"]
    assert len(re.findall(r'id="ground-stud"', svg)) + len(
        [p for p in _contract(ref).get("parts", []) if p["id"] == "ground-stud"]) == want["ground"]
    assert len(re.findall(r'id="handle"', svg)) == 1
    assert len(re.findall(r'id="latch"', svg)) == 1
    studs = [p for p in _contract(ref).get("parts", []) if p["id"].startswith("hex-stud")]
    assert len(studs) == want["studs"]
    assert all(p["ref"] == "common/screw-head@1" for p in studs)


@pytest.mark.parametrize("ref", PARTS)
def test_the_named_elements_and_parts_lie_inside_the_envelope(ref):
    c = _contract(ref)
    w, h = PARTS[ref]["size"]
    env = (0, 0, w, h)
    for k, e in c["elements"].items():
        assert _inside((*e["at"], *e["size"]), env), k
    for p in c.get("parts", []):
        assert _inside((*p["at"], 3.6, 3.6), env), p["id"]


@pytest.mark.parametrize("ref", PARTS)
def test_the_skin_is_the_envelope_and_names_what_the_contract_names(ref):
    w, h = PARTS[ref]["size"]
    svg = _skin(ref)
    assert f'viewBox="0 0 {w:g} {h:g}"' in svg
    for k in _contract(ref)["elements"]:
        assert f'id="{k}"' in svg, k


@pytest.mark.parametrize("ref", PARTS)
def test_colours_are_sampled_and_filed_estimated_with_their_source(ref):
    colour = _words(_contract(ref)["provenance"]["colour"])
    for word in ("estimated", "illustration", "pixels"):
        assert word in colour, word
    assert "#" in colour


@pytest.mark.parametrize("ref", PARTS)
def test_the_body_is_the_ac_siblings_and_declared_borrowed(ref):
    c, ac = _contract(ref), _contract(PARTS[ref]["ac"])
    if "body" in ac:
        assert c["body"]["color"] == ac["body"]["color"]
        assert c["body"]["depth"] == ac["body"]["depth"]
    assert "body" in c["provenance"] and "borrowed" in _words(c["provenance"]["body"]).lower()


def test_cor550_supply_conflict_between_its_two_documents_is_declared():
    p = _words(_contract("edgecore/cor550-psu-dc@1")["provenance"]["input"])
    for word in ("-48 - -60 VDC", "40 A max", "40 to 72 VDC", "data sheet", "quick start", "conflict"):
        assert word in p, word
    assert "#10 AWG" in p


def test_cor580_system_range_conflict_is_declared_and_the_fru_is_named():
    p = _contract("edgecore/fsj033-610g@1")["provenance"]
    text = _words(p["input"])
    for word in ("-40 V - -75 V", "-36 to-72 VDC", "conflict", "EC-DS-0222-R04"):
        assert word in text, word
    assert "FSJ033-610G" in _words(p["model"]) and "FSH082-610G" in _words(p["model"])


def test_csr440_legend_and_callouts_are_read_and_the_note_is_declared():
    d = _words(_contract("edgecore/csr440-psu-dc@1")["provenance"]["connector-direction"])
    for word in ("RTN - 48V", "upside down", "-48V", "RTN", "callout"):
        assert word in d, word


def test_no_other_component_carries_these_part_numbers_or_models():
    found = {}
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        c = _load(p)
        a = c.get("attrs") or {}
        for key in ("model", "part"):
            if a.get(key) in ("FSJ033-610G", "F0OEC9524003Z", "AS7535-28XB DC PSU"):
                found.setdefault(a[key], []).append(f"{p.parent.parent.parent.name}/{p.parent.parent.name}")
    assert found == {"FSJ033-610G": ["edgecore/fsj033-610g"],
                     "F0OEC9524003Z": ["edgecore/fsj033-610g"],
                     "AS7535-28XB DC PSU": ["edgecore/csr440-psu-dc"]}


# ---- the two AC parts that are patched ---------------------------------------

def test_the_cor550_ac_part_is_patched_and_no_longer_says_no_dc_face_is_drawn():
    c = _contract("edgecore/cor550-psu-ac@1")
    assert c["version"] == "1.0.1"
    assert c["attrs"]["input"] == "ac"
    assert "the-dc-build-is-not-drawn" not in c["provenance"]
    text = _words(c["provenance"]["the-dc-build-is-a-separate-part"])
    assert "edgecore/cor550-psu-dc@1" in text
    assert "no `cor550-psu-dc` is written" not in text
    assert "There is therefore no DC face to model" not in text


def test_the_csr440_ac_part_states_ac_and_keeps_its_sentence_in_the_note():
    c = _contract("edgecore/csr440-psu-ac@1")
    assert c["version"] == "1.1.2"
    assert c["attrs"]["input"] == "ac"
    assert c["attrs"]["input-note"] == "100V-240V, 6.0-2.4 A per PS"
    text = _words(c["provenance"]["the-dc-variant"])
    assert "NOT DRAWN AND NOT MODELLED" not in text
    assert "csr440-psu-dc" in text


# ---- the three devices --------------------------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_supply_bays_accept_the_ac_part_and_the_dc_part_and_nothing_else(name):
    d = DEVICES[name]
    for i in d["bays"]:
        assert _bays(name)[i]["accepts"] == [d["ac"], d["dc"]], i
        assert _bays(name)[i]["default"] == d["ac"], i


@pytest.mark.parametrize("name", DEVICES)
def test_the_dc_configuration_seats_the_dc_part_in_every_supply_bay_through_bays(name):
    d = DEVICES[name]
    cfg = _device(name)["configurations"][d["dc_cfg"]]
    assert {i: cfg["bays"][i] for i in d["bays"]} == {i: d["dc"] for i in d["bays"]}
    assert "component-attrs" not in cfg
    assert _layout(name)["configurations"][d["dc_cfg"]].get("component-attrs") is None


@pytest.mark.parametrize("name", DEVICES)
def test_the_ac_configuration_still_seats_the_ac_part(name):
    d = DEVICES[name]
    assert _fitted(name, d["ac_cfg"]) == {i: d["ac"] for i in d["bays"]}
    assert _device(name)["configurations"][d["ac_cfg"]].get("default") is True


@pytest.mark.parametrize("name", DEVICES)
def test_every_fitted_supply_of_every_configuration_states_a_token_and_the_two_builds_read_ac_and_dc(name):
    d = DEVICES[name]
    for cfg in _device(name)["configurations"]:
        for bay, ref in _fitted(name, cfg).items():
            assert _contract(ref)["attrs"]["input"] in TOKENS, (cfg, bay, ref)
    read = {cfg: {_contract(r)["attrs"]["input"] for r in _fitted(name, cfg).values()}
            for cfg in (d["ac_cfg"], d["dc_cfg"])}
    assert read == {d["ac_cfg"]: {"ac"}, d["dc_cfg"]: {"dc"}}


@pytest.mark.parametrize("name", DEVICES)
def test_the_dc_description_no_longer_says_it_is_drawn_with_the_ac_face(name):
    d = DEVICES[name]
    text = _words(_layout(name)["configurations"][d["dc_cfg"]]["description"])
    for stale in ("DRAWN WITH THE AC", "drawn as the AC part", "wrong at the connector", "seats the AC part"):
        assert stale not in text, stale
    assert d["dc"].split("@")[0].split("/")[1] in text or "own supply" in text


@pytest.mark.parametrize("name", DEVICES)
def test_the_dc_gap_says_what_remains_and_not_that_the_face_is_missing(name):
    d = DEVICES[name]
    gaps = {g["what"]: g for g in _layout(name)["gaps"]}
    text = _words(gaps[d["gap"]]["wanted"])
    for word in ("borrowed", "illustration", "not stated"):
        assert word in text, word
    for stale in ("lint L120", "keep in view", "so no cor550-psu-dc part was written",
                  "draws the AC part", "The bay therefore accepts"):
        assert stale not in text, stale
    assert gaps[d["gap"]]["reason"] != "needs-drawing" or name == "cor550"


@pytest.mark.parametrize("name", DEVICES)
def test_the_device_takes_one_minor_and_its_quick_start_stays_a_reference(name):
    doc = _layout(name)
    assert doc["version"] == DEVICES[name]["version"]
    assert any("Quick Start Guide" in r["title"] for r in doc["references"])
    assert _device(name)["version"] == DEVICES[name]["version"]


def test_the_cor550_dc_gap_records_the_two_input_ranges_and_the_rest_that_stays():
    gaps = {g["what"]: g for g in _layout("cor550")["gaps"]}
    text = _words(gaps["dc-supply-face"]["wanted"])
    for word in ("-48 - -60 VDC", "40 to 72 VDC", "ordering code"):
        assert word in text, word


def test_the_cor580_system_attribute_still_states_the_data_sheet_range():
    assert "-36 to -72 VDC" in _device("cor580")["attrs"]["power"]["input-dc"]


# ---- the supplies' places in the bays -----------------------------------------

@pytest.mark.parametrize("name", DEVICES)
def test_the_dc_part_fits_each_bay_it_is_seated_in(name):
    d = DEVICES[name]
    c = _contract(d["dc"])
    for i in d["bays"]:
        b = _bays(name)[i]
        assert b["size"]["w"] == pytest.approx(c["size"]["w"], abs=TOL), i
        assert b["size"]["h"] == pytest.approx(c["size"]["h"], abs=TOL), i


# ---- exports and the lock -----------------------------------------------------

EXPORT_NAMES = {"edgecore/cor550-psu-dc@1": "cor550-psu-dc",
                "edgecore/fsj033-610g@1": "FSJ033-610G",
                "edgecore/csr440-psu-dc@1": "AS7535-28XB DC PSU"}


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
@pytest.mark.parametrize("ref", EXPORT_NAMES)
def test_one_module_type_per_new_component_is_exported(flavour, ref):
    d = LIB / "exports" / flavour / "module-types" / "Edgecore"
    assert (d / f"{EXPORT_NAMES[ref]}.yaml").exists()
    assert len(list(d.glob(f"{EXPORT_NAMES[ref]}*.yaml"))) == 1


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_dc_device_types_are_exported(flavour):
    for model in ("7926-40XKFB-O-48V-F", "AS9926-24D-O-48V-F", "AS7535-28XB-O-48V-F V2"):
        found = list((LIB / "exports" / flavour / "device-types").glob(f"*/{model}.yaml"))
        assert found, model


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_committed_module_exports_equal_the_exporters_own_output(flavour, tmp_path):
    dist = LIB / "dist"
    assert (dist / "components.json").exists(), "this test reads a build: run ./build.sh first"
    r = subprocess.run([sys.executable, str(EXPORT), "--dist", str(dist), "--out", str(tmp_path),
                        "--modules"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for name in EXPORT_NAMES.values():
        made = list((tmp_path / flavour / "module-types").glob(f"*/{name}.yaml"))
        assert len(made) == 1, name
        committed = LIB / "exports" / flavour / "module-types" / "Edgecore" / f"{name}.yaml"
        assert made[0].read_text() == committed.read_text(), name


def test_the_lock_agrees_with_the_three_devices_and_the_five_parts():
    from portrayal import devicelock

    mine = {"cor550", "cor580", "csr440", "cor550-psu-ac", "cor550-psu-dc", "fsj033-610g",
            "csr440-psu-ac", "csr440-psu-dc"}
    found = [f for f in devicelock.check(LIB) if f[0] in mine]
    assert found == []
