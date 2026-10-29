"""The ASR 9906 and ASR 9910 seat the version 3 power modules.

PWR-6KW-AC-V3 and PWR-4.4KW-DC-V3 are new components, and both chassis carry the
module bays they sit in. Everything here pins a number or a sentence the change
writes, so that a later edit has to say it is moving one.

The shapes this pins:

- a module is drawn once, in the 9910's horizontal attitude, and the 9906's
  vertical column turns it (`rotate: 270`, so M0 is at the bottom);
- each shelf has an AC bay set (three) and a DC bay set (four) on one footprint;
  they are `only-in` different configurations, so they never coexist, and
  nothing enforces that the two types are not mixed;
- the shelf cutouts are the measured extent of the module stack.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

AC = "cisco/pwr-6kw-ac-v3@1"
DC = "cisco/pwr-4p4kw-dc-v3@1"
AC_W, AC_H = 139.0, 40.1
DC_W, DC_H = 104.7, 40.6
TOL = 0.06


def _device(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def _contract(ref):
    name, major = ref.split("@")
    return yaml.safe_load((LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def _skin(ref):
    name, major = ref.split("@")
    return (LIB / "components" / name / f"v{major}" / "skins" / "default.svg").read_text()


def _bays(doc):
    return {b["id"]: b for b in doc["views"]["front"]["components"]["bays"]}


def _power_bays(doc, kind):
    marker = "-pm-" if kind == "ac" else "-dcpm-"
    return {i: b for i, b in _bays(doc).items() if marker in i}


def _all_devices():
    for p in (LIB / "devices").glob("*/*/device.yaml"):
        yield p, yaml.safe_load(p.read_text())


# --- the two parts -------------------------------------------------------------

def test_the_ac_module_carries_the_figures_the_guide_prints():
    c = _contract(AC)
    assert c["version"] == "1.0.0"
    a = c["attrs"]
    assert a["model"] == "PWR-6KW-AC-V3"
    assert a["power-output-w"] == 6000
    assert a["input"] == "ac"
    assert a["generation"] == "3"
    assert a["fans"] == "2"
    assert c["size"] == {"w": AC_W, "h": AC_H}
    assert "d" not in c["size"] and "body" not in c


def test_the_dc_module_carries_the_figures_the_guide_prints():
    c = _contract(DC)
    assert c["version"] == "1.0.0"
    a = c["attrs"]
    assert a["model"] == "PWR-4.4KW-DC-V3"
    assert a["power-output-w"] == 4400
    assert a["input"] == "dc"
    assert a["generation"] == "3"
    assert a["fans"] == "2"
    assert c["size"] == {"w": DC_W, "h": DC_H}
    assert "d" not in c["size"] and "body" not in c


@pytest.mark.parametrize("ref,lamps", [(AC, 3), (DC, 3)])
def test_a_module_face_has_two_fan_wheels_a_handle_and_three_lamps(ref, lamps):
    c = _contract(ref)
    leds = [k for k, v in c["elements"].items() if v.get("class") == "led"]
    assert sorted(leds) == ["fault", "input", "output"]
    svg = _skin(ref)
    assert len(re.findall(r'id="fan-[12]"', svg)) == 2
    assert 'id="handle"' in svg
    for k in leds:
        assert f'id="{k}"' in svg
    assert 'id="logo-zone"' not in svg and "cisco" not in svg.lower()


@pytest.mark.parametrize("ref", [AC, DC])
def test_the_size_provenance_says_drawing_and_names_its_anchor(ref):
    p = _contract(ref)["provenance"]
    assert p["size"].lstrip().startswith("drawing")
    for word in ("ASR-9906 Front", "ASR-9910 Rear", "19.0 in"):
        assert word in p["size"], word
    assert "Figure 44" in p["size"] or "Figure 45" in p["size"]
    for key in ("power", "lamps", "colour", "body"):
        assert key in p, key


def test_the_input_ratings_are_filed_with_their_conflicts_declared():
    ac = _contract(AC)["provenance"]["power"]
    dc = _contract(DC)["provenance"]["power"]
    for word in ("6510 VA", "15 A maximum at 200 VAC", "two single-phase"):
        assert word in ac, word
    for word in ("4730 W", "49 A maximum at -48 VDC", "-40.5 to -72 VDC", "-40 to -72 VDC", "39 A"):
        assert word in dc, word


def test_no_other_component_carries_either_model():
    models = {}
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        m = (yaml.safe_load(p.read_text()).get("attrs") or {}).get("model")
        if m in ("PWR-6KW-AC-V3", "PWR-4.4KW-DC-V3"):
            models.setdefault(m, []).append(p.parent.parent.name)
    assert models == {"PWR-6KW-AC-V3": ["pwr-6kw-ac-v3"], "PWR-4.4KW-DC-V3": ["pwr-4p4kw-dc-v3"]}


# --- which bays take them ------------------------------------------------------

def test_the_ac_module_is_accepted_in_the_ac_positions_of_the_two_chassis_and_nowhere_else():
    seen = {}
    for p, doc in _all_devices():
        for view, v in doc.get("views", {}).items():
            for b in (v.get("components") or {}).get("bays", []) or []:
                for ref in (AC, DC):
                    if ref in (b.get("accepts") or []):
                        seen.setdefault(ref, {}).setdefault(doc["name"], []).append(b["id"])
    assert seen[AC] == {"asr-9906": ["ps0-pm-0", "ps0-pm-1", "ps0-pm-2"],
                        "asr-9910": ["ps0-pm-0", "ps0-pm-1", "ps0-pm-2", "ps1-pm-0", "ps1-pm-1", "ps1-pm-2"]}
    assert seen[DC] == {"asr-9906": [f"ps0-dcpm-{i}" for i in range(4)],
                        "asr-9910": [f"ps{s}-dcpm-{i}" for s in (0, 1) for i in range(4)]}


@pytest.mark.parametrize("name", ["asr-9906", "asr-9910"])
def test_each_bay_takes_exactly_its_own_module(name):
    doc = _device(name)
    for i, b in _power_bays(doc, "ac").items():
        assert b["accepts"] == [AC], i
        assert b["default"] == AC and b["group"] == "power-modules"
        assert b["only-in"] == ["base", "ac"], i
    for i, b in _power_bays(doc, "dc").items():
        assert b["accepts"] == [DC], i
        assert b["default"] == DC and b["group"] == "power-modules"
        assert b["only-in"] == ["dc"], i


def test_the_per_tray_counts_are_the_guides():
    for name, trays in (("asr-9906", 1), ("asr-9910", 2)):
        doc = _device(name)
        assert len(_power_bays(doc, "ac")) == 3 * trays
        assert len(_power_bays(doc, "dc")) == 4 * trays
        cfg = doc["configurations"]
        assert len([k for k, v in cfg["ac"]["bays"].items() if v == AC]) == 3 * trays
        assert len([k for k, v in cfg["dc"]["bays"].items() if v == DC]) == 4 * trays
        assert set(cfg["ac"]["bays"]) == set(_power_bays(doc, "ac"))
        assert set(cfg["dc"]["bays"]) == set(_power_bays(doc, "dc"))


@pytest.mark.parametrize("name", ["asr-9906", "asr-9910"])
def test_the_base_stays_the_default_and_seats_the_ac_modules(name):
    cfg = _device(name)["configurations"]
    assert cfg["base"].get("default") is True
    assert not cfg["ac"].get("default") and not cfg["dc"].get("default")
    for k, v in cfg["base"]["bays"].items():
        if "-pm-" in k:
            assert v == AC
    assert sum(1 for k in cfg["base"]["bays"] if "-pm-" in k) == len(_power_bays(_device(name), "ac"))
    assert not any("-dcpm-" in k for k in cfg["base"]["bays"])
    for c in ("ac", "dc"):
        assert "part-numbers" not in cfg[c], c
        assert cfg[c]["kind"] == "example"


# --- geometry ------------------------------------------------------------------

def _inside(inner, outer):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return ix >= ox - TOL and iy >= oy - TOL and ix + iw <= ox + ow + TOL and iy + ih <= oy + oh + TOL


def _box(b):
    return (b["at"][0], b["at"][1], b["size"]["w"], b["size"]["h"])


def test_9906_bays_turn_the_horizontal_module_and_fit_the_shelf():
    doc = _device("asr-9906")
    shelf = {c["id"]: c for c in doc["views"]["front"]["panel"]["cutouts"]}["power-shelf"]
    assert shelf["at"] == [16.0, 35.9] and shelf["size"] == [46.0, 418.8]
    outer = (*shelf["at"], *shelf["size"])
    for kind, mod_w, mod_h in (("ac", AC_W, AC_H), ("dc", DC_W, DC_H)):
        bays = _power_bays(doc, kind)
        ordered = [bays[k] for k in sorted(bays, key=lambda k: int(k.rsplit("-", 1)[1]))]
        for b in ordered:
            assert b["rotate"] == 270
            # the bay is the landed footprint: the module's height across, its width down
            assert b["size"] == {"w": pytest.approx(mod_h), "h": pytest.approx(mod_w)}
            assert _inside(_box(b), outer), b["id"]
        ys = [b["at"][1] for b in ordered]
        assert ys == sorted(ys, reverse=True), "M0 is at the bottom, the last module at the top"
        for lower, upper in zip(ordered, ordered[1:]):
            assert upper["at"][1] + upper["size"]["h"] == pytest.approx(lower["at"][1], abs=TOL)


def test_9906_shelf_clears_the_cage_the_intake_and_the_esd_jack():
    doc = _device("asr-9906")
    front = doc["views"]["front"]
    shelf = {c["id"]: c for c in front["panel"]["cutouts"]}["power-shelf"]
    sx, sy = shelf["at"]
    sw, sh = shelf["size"]
    assert sx == 16.0 and sw == 46.0
    for b in _bays(doc).values():
        if "-pm-" in b["id"] or "-dcpm-" in b["id"]:
            continue
        bx, by = b["at"]
        assert sx + sw <= bx + 1e-6, b["id"]
    for d in front["panel"]["decor"]:
        dx, dy = d["at"]
        assert sy + sh <= dy or sx + sw <= dx, d
    esd = {c["id"]: c for c in front["panel"]["cutouts"]}["esd"]
    assert esd["at"][0] > sx + sw
    jack = [p for p in front["components"]["placements"] if p["id"] == "esd-jack"][0]
    assert jack["at"][0] > sx + sw


def test_9910_shelves_are_the_module_stack_and_the_bays_fit_them():
    doc = _device("asr-9910")
    cut = {c["id"]: c for c in doc["views"]["front"]["panel"]["cutouts"]}
    assert cut["shelf-0"]["at"] == [15.9, 821.24] and cut["shelf-0"]["size"] == [418.8, 46.0]
    assert cut["shelf-1"]["at"] == [15.9, 873.0] and cut["shelf-1"]["size"] == [418.8, 46.0]
    for s in (0, 1):
        c = cut[f"shelf-{s}"]
        outer = (*c["at"], *c["size"])
        assert outer[0] + outer[2] <= 447.0
        for kind, mod_w, mod_h in (("ac", AC_W, AC_H), ("dc", DC_W, DC_H)):
            bays = {i: b for i, b in _power_bays(doc, kind).items() if i.startswith(f"ps{s}-")}
            assert len(bays) == (3 if kind == "ac" else 4)
            ordered = [bays[k] for k in sorted(bays, key=lambda k: int(k.rsplit("-", 1)[1]))]
            for b in ordered:
                assert "rotate" not in b
                assert b["size"] == {"w": pytest.approx(mod_w), "h": pytest.approx(mod_h)}
                assert _inside(_box(b), outer), b["id"]
            xs = [b["at"][0] for b in ordered]
            assert xs == sorted(xs), "M0 is leftmost"
            for left, right in zip(ordered, ordered[1:]):
                assert left["at"][0] + left["size"]["w"] == pytest.approx(right["at"][0], abs=TOL)


def test_the_shelves_do_not_reach_the_air_intake_or_the_cards():
    doc = _device("asr-9910")
    grille = [d for d in doc["views"]["front"]["panel"]["decor"] if d.get("pattern") == "grille"][0]
    shelf0 = {c["id"]: c for c in doc["views"]["front"]["panel"]["cutouts"]}["shelf-0"]
    assert grille["at"][1] + grille["size"][1] <= shelf0["at"][1]
    for b in _bays(doc).values():
        if b["id"].startswith("slot-"):
            assert b["at"][1] + b["size"]["h"] <= shelf0["at"][1]


# --- nothing that was there is gone --------------------------------------------

def test_the_existing_bays_are_unchanged():
    d6, d10 = _device("asr-9906"), _device("asr-9910")
    b6, b10 = _bays(d6), _bays(d10)
    assert [b6[f"slot-{i}"]["at"] for i in range(6)] == [
        [72.605, 78.4], [116.025, 78.4], [159.445, 78.4], [202.885, 78.4], [246.285, 78.4], [289.705, 78.4]]
    assert all(b6[f"slot-{i}"]["size"] == {"w": 41.4, "h": 395.7} for i in range(6))
    assert [b10[f"slot-{i}"]["at"][0] for i in range(10)][:3] == [9.295, 53.085, 96.855]
    assert all(b10[f"slot-{i}"]["size"] == {"w": 41.4, "h": 395.7} for i in range(10))
    rear = {b["id"] for b in d10["views"]["rear"]["components"]["bays"]}
    assert rear == {"fc-0", "fc-1", "fc-2", "fc-3", "fc-4", "ft-0", "ft-1"}
    esd = {c["id"] for c in d6["views"]["front"]["panel"]["cutouts"]}
    assert esd == {"power-shelf", "esd"}
    assert d6["views"]["rear"].get("components") == {"placements": [
        {"ref": "cisco/a9k-ground-pad@1", "id": "ground-pad-rear", "at": [375.0, 566.01], "group": "grounding", "rel-pos": 1}]}
    for doc in (d6, d10):
        slots = [k for k in doc["configurations"]["base"]["bays"] if k.startswith("slot-")]
        assert all(doc["configurations"]["base"]["bays"][k] == "cisco/a9k-slot-cover@1" for k in slots)


@pytest.mark.parametrize("name", ["asr-9906", "asr-9910"])
def test_the_power_group_is_declared_and_the_rear_is_still_undrawn_for_power(name):
    doc = _device(name)
    g = doc["groups"]["power-modules"]
    assert g["term"] == "PM" and g["role"] == "service"
    assert g["physical-context"] == "Power Module"
    # devicelock: "This change needs at least a major bump" - the shelf cutouts moved and grew
    assert doc["version"] == "2.0.0"
    rear_ids = {b["id"] for b in doc["views"]["rear"]["components"].get("bays", [])}
    assert not any("pm" in i for i in rear_ids)


# --- what the prose says, pinned -----------------------------------------------

def _gaps(doc):
    return {g["what"]: g for g in doc["gaps"]}


@pytest.mark.parametrize("name", ["asr-9906", "asr-9910"])
def test_the_openings_gap_is_restated_and_the_old_sentence_is_gone(name):
    doc = _device(name)
    g = _gaps(doc)["power-module-openings"]
    text = " ".join(g["note"].split())
    assert "single opening" not in text and "single openings" not in text
    assert "rather than three module openings" not in text
    for word in ("not enforced", "share one footprint", "mixing"):
        assert word in text.lower(), word
    assert re.search(r"Tables? 15", text)
    assert ("Figure 42" if name == "asr-9906" else "Figure 44") in text
    assert "v3-dc-power-bays" not in _gaps(doc), "the preferred layout holds, so no fallback gap"


def test_the_9906_shelf_provenance_names_the_figure_the_stencil_and_the_scale_check():
    p = _device("asr-9906")["provenance"]["power-shelf"]
    assert p["confidence"] == "drawing"
    note = " ".join(p["note"].split())
    for word in ("Figure 42", "Figure 43", "ASR-9906 Front", "19.0 in", "139.0", "418.8", "35.9"):
        assert word in note, word


def test_the_9910_shelf_provenance_names_the_stencil_and_the_swap():
    p = _device("asr-9910")["provenance"]["power-shelves"]
    assert p["confidence"] == "drawing"
    note = " ".join(p["note"].split())
    for word in ("Figure 44", "Figure 45", "ASR-9910 Rear", "418.8", "swapped"):
        assert word in note, word


def test_the_9906_rear_master_sentence_is_corrected_and_the_rest_of_the_rear_gap_stays():
    text = " ".join(_gaps(_device("asr-9906"))["rear-face"]["note"].split())
    assert "There is no ASR-9906 Rear master" not in text
    assert "ASR-9906 Rear" in text
    assert "five fabric cards" in text


@pytest.mark.parametrize("name", ["asr-9906", "asr-9910"])
def test_the_power_block_carries_the_dc_rows_and_the_module_counts(name):
    power = _device(name)["attrs"]["power"]
    assert power["power-ac-input-per-module-v3"] == "6510 VA (6000 W output module)"
    assert power["power-dc-input-per-module-v3"] == "4730 W (4400 W output module)"
    assert "-40.5 to -72 VDC" in power["power-dc-input-voltage"]
    assert "49 A maximum at -48 VDC" in power["power-dc-input-current"]
    assert "-54.0 VDC nominal" in power["power-output-bus-voltage"]
    if name == "asr-9906":
        assert "18,000 W" in power["power-output-maximum"] and "17,600 W" in power["power-output-maximum"]
        assert power["power-modules-per-tray-v3"] == "three AC or four DC, one tray"
    else:
        assert "not stated" in power["power-output-maximum"]
        assert power["power-modules-per-tray-v3"] == "three AC or four DC per tray, two trays"
        assert "4+2" in power["power-redundancy-text"] and "N+N" in power["power-redundancy-text"]


# --- exports and the lock ------------------------------------------------------

@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
@pytest.mark.parametrize("model", ["PWR-6KW-AC-V3", "PWR-4.4KW-DC-V3"])
def test_one_module_type_per_component_is_exported(flavour, model):
    d = LIB / "exports" / flavour / "module-types" / "Cisco"
    assert (d / f"{model}.yaml").exists()
    assert len(list(d.glob(f"{model}*.yaml"))) == 1


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", ["ASR 9906", "ASR 9910"])
def test_the_chassis_device_types_are_exported(flavour, name):
    assert (LIB / "exports" / flavour / "device-types" / "Cisco" / f"{name}.yaml").exists()


def test_the_lock_agrees_with_the_chassis_and_the_new_parts():
    from portrayal import devicelock

    found = [f for f in devicelock.check(LIB) if f[0] in ("asr-9906", "asr-9910", "pwr-6kw-ac-v3", "pwr-4p4kw-dc-v3")]
    assert found == []
