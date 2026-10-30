"""The DCS500 (AS7816-64X) has a 48 V DC supply and two DC builds.

The DC supply is sold only in the O series, and this device is drawn on the OZ
silkscreen, so the two DC configurations are declared stand-ins on that
silkscreen rather than a second device. Everything here pins a number or a
sentence the change writes.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

AC = "edgecore/dcs500-psu-ac@1"
DC = "edgecore/dcs500-psu-dc@1"
DEVICE = LIB / "devices/edgecore/dcs500"
TOL = 0.06
FRUS = ("YM-2851J ER", "YM-2851J FR", "F0TAT7664000A", "F0TAT7664002A")
SKUS = {
    "dc-f2b": ("7816-64X-O-48V-F-R", "FP3ZZ7664024A"),
    "dc-b2f": ("7816-64X-O-48V-B-R", "FP3ZZ7664026A"),
}


def _device():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def _layout():
    return yaml.safe_load((DEVICE / "layout.yaml").read_text())


def _contract(ref):
    name, major = ref.split("@")
    return yaml.safe_load((LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def _skin(ref):
    name, major = ref.split("@")
    return (LIB / "components" / name / f"v{major}" / "skins" / "default.svg").read_text()


def _bays():
    return {b["id"]: b for b in _device()["views"]["rear"]["components"]["bays"]}


def _flat(text):
    return " ".join(text.split())


def _gap(name):
    return {g["what"]: g for g in _device()["gaps"]}[name]


# --- the part ------------------------------------------------------------------

def test_the_part_states_a_dc_terminal_input_as_printed():
    c = _contract(DC)
    assert c["version"] == "1.0.0"
    a = c["attrs"]
    assert a["input"] == "dc"
    assert a["inlet"] == "dc-terminal"
    assert a["input-note"] == "-36 - -72 VDC, 28-14 A"
    assert a["power-output-w"] == 850


def test_the_part_carries_no_single_model_number_and_records_both_frus():
    c = _contract(DC)
    assert "model" not in c["attrs"]
    text = _flat(" ".join(str(v) for v in c["provenance"].values()))
    for code in FRUS:
        assert code in text, code


def test_no_other_component_carries_either_fru_as_its_model():
    for p in (LIB / "components").glob("*/*/v*/contract.yaml"):
        model = (yaml.safe_load(p.read_text()).get("attrs") or {}).get("model")
        assert model not in ("YM-2851J ER", "YM-2851J FR"), p


def test_the_envelope_is_the_ac_parts_and_declared_borrowed():
    ac, dc = _contract(AC), _contract(DC)
    assert dc["size"] == ac["size"] == {"w": 50.9, "h": 39.4}
    assert dc["size-confidence"] == {"w": "borrowed", "h": "borrowed"}
    assert "edgecore/dcs500-psu-ac@1" in _flat(dc["provenance"]["size"])


def test_the_envelope_fits_the_bay():
    for b in _bays().values():
        if DC in b["accepts"]:
            assert b["size"] == {"w": 50.9, "h": 39.4}


def test_the_named_elements_lie_inside_the_envelope():
    c = _contract(DC)
    w, h = c["size"]["w"], c["size"]["h"]
    for name, e in c["elements"].items():
        x, y = e["at"]
        ew, eh = e["size"]
        assert x >= -TOL and y >= -TOL and x + ew <= w + TOL and y + eh <= h + TOL, name


def test_the_skin_draws_three_poles_one_handle_one_latch_and_no_logo():
    svg = _skin(DC)
    assert len(re.findall(r'id="pole-\d"', svg)) == 3
    assert len(re.findall(r'id="handle"', svg)) == 1
    assert len(re.findall(r'id="latch"', svg)) == 1
    for word in ("edgecore", "<text"):
        assert word not in svg.lower()


def test_the_connector_direction_and_pole_order_are_written_and_not_stated_is_said():
    p = _contract(DC)["provenance"]
    text = _flat(p["connector-direction"])
    for word in ("screws face", "wires leave", "RTN", "chassis ground", "not stated", "half turn"):
        assert word in text, word


def test_the_back_to_front_latch_colour_is_said_to_be_not_shown():
    assert "not shown" in _flat(_contract(DC)["provenance"]["latch-colour"])


def test_the_colours_are_filed_as_estimated_with_their_regions():
    text = _flat(_contract(DC)["provenance"]["colour"])
    assert "estimated" in text and "terminal end" in text and "pixels" in text


def test_the_ac_part_is_patched_and_its_stale_sentence_is_gone():
    c = _contract(AC)
    assert c["version"] == "1.0.1"
    text = _flat(c["provenance"]["dc-build"])
    assert "is not modelled" not in text
    assert "edgecore/dcs500-psu-dc@1" in text


# --- the seats -----------------------------------------------------------------

def test_the_supply_bays_accept_the_ac_part_and_the_dc_part_and_nothing_else():
    bays = _bays()
    for i in ("psu-0", "psu-1"):
        assert bays[i]["accepts"] == [AC, DC], i
        assert bays[i]["default"] == AC, i


def test_the_dc_part_is_accepted_in_no_other_device():
    for p in (LIB / "devices").glob("*/*/layout.yaml"):
        if p.parent.name == "dcs500":
            continue
        assert "dcs500-psu-dc" not in p.read_text(), p


def test_the_two_dc_configurations_are_orderable_with_the_ordering_tables_numbers():
    cfg = _device()["configurations"]
    for name, (model, part) in SKUS.items():
        c = cfg[name]
        assert c["kind"] == "orderable"
        assert c["power"] == "dc"
        assert c["part-numbers"] == {model: {"part": part}}


def test_the_dc_configurations_seat_the_dc_part_through_bays_only():
    cfg = _device()["configurations"]
    for name in SKUS:
        c = cfg[name]
        assert c["bays"]["psu-0"] == DC and c["bays"]["psu-1"] == DC
        assert "component-attrs" not in c


def test_dc_b2f_swaps_the_airflow_regions_as_ac_b2f_does():
    cfg = _device()["configurations"]
    assert cfg["dc-b2f"]["airflow"] == cfg["ac-b2f"]["airflow"] == "back-to-front"
    assert cfg["dc-b2f"]["region-context"] == cfg["ac-b2f"]["region-context"] == {
        "intake": "Exhaust", "exhaust": "Intake"}
    assert "airflow" not in cfg["dc-f2b"] or cfg["dc-f2b"]["airflow"] == "front-to-back"
    assert "region-context" not in cfg["dc-f2b"]


def test_the_existing_three_configurations_are_unchanged():
    cfg = _device()["configurations"]
    assert list(cfg)[:3] == ["base", "ac-f2b", "ac-b2f"]
    assert cfg["base"]["default"] is True
    assert "power" not in cfg["base"] and "power" not in cfg["ac-f2b"] and "power" not in cfg["ac-b2f"]
    assert sorted(cfg["ac-f2b"]["part-numbers"].values(), key=lambda v: v["part"])[0]["part"] == "FP3AT7664004A"
    assert len(cfg["ac-f2b"]["part-numbers"]) == len(cfg["ac-b2f"]["part-numbers"]) == 5
    assert set(cfg) == {"base", "ac-f2b", "ac-b2f", "dc-f2b", "dc-b2f"}


def test_every_fitted_supply_states_an_input_a_consumer_can_read_and_the_builds_tell_apart():
    dev = _device()
    bays = _bays()
    seen = {}
    for name, c in dev["configurations"].items():
        fitted = {}
        for i in ("psu-0", "psu-1"):
            ref = (c.get("bays") or {}).get(i, bays[i]["default"])
            fitted[i] = _contract(ref)["attrs"]["input"]
        assert set(fitted.values()) <= {"ac", "dc", "hvdc"}, name
        assert len(set(fitted.values())) == 1, name
        seen[name] = set(fitted.values()).pop()
    assert seen == {"base": "ac", "ac-f2b": "ac", "ac-b2f": "ac", "dc-f2b": "dc", "dc-b2f": "dc"}


# --- what the prose says, pinned -----------------------------------------------

def test_the_numbering_gap_says_the_dc_builds_wear_the_oz_labels_and_what_the_o_series_prints():
    g = _gap("o-series-numbering")
    text = _flat(g["wanted"])
    assert "the DC builds wear the OZ labels" in text
    for word in ("PSU 2", "PSU 1", "fans 4", "O series", "data sheet", "dc-f2b", "dc-b2f"):
        assert word in text, word
    assert "front-o" not in " ".join(_device()["views"]) and "rear-o" not in " ".join(_device()["views"])
    assert "only in the O series" in text


def test_the_dc_configuration_descriptions_say_the_oz_silkscreen_stand_in():
    cfg = _device()["configurations"]
    for name in SKUS:
        text = _flat(cfg[name]["description"])
        assert "O-series" in text and "OZ" in text, name


def test_the_layout_is_the_source_of_the_expanded_device():
    assert _layout()["version"] == _device()["version"]
    assert _device()["version"] == "4.1.0"


# --- exports and the lock ------------------------------------------------------

@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_one_module_type_is_exported_for_the_part(flavour):
    d = LIB / "exports" / flavour / "module-types" / "Edgecore"
    assert len(list(d.glob("dcs500-psu-dc*.yaml"))) == 1


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
@pytest.mark.parametrize("model", [m for m, _ in SKUS.values()])
def test_a_device_type_is_exported_for_each_dc_sku(flavour, model):
    assert (LIB / "exports" / flavour / "device-types" / "Edgecore" / f"{model}.yaml").exists()


def test_the_lock_agrees_with_the_device_and_the_two_supply_parts():
    from portrayal import devicelock

    found = [f for f in devicelock.check(LIB) if f[0] in ("dcs500", "dcs500-psu-ac", "dcs500-psu-dc")]
    assert found == []
