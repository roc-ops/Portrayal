"""A slot seats cards by form: `interface:` on the bay, `mates:` on the card.

The mechanism of docs/cards-by-interface-design.md ("How a card seats" and
"With `slot-width` and `span`"). A component bay may state an `interface`; a
part is TAKEN by a bay when the bay's `accepts` names it, or the bay's
`interface` is in the part's `mates` and the part is wide enough
(manifest.takes). Every reader of a bay asks that one question.

One library card states one of them so far (see test_n3100_by_interface.py), so
the cases are built on a small library in tmp_path: a riser shaped like the R740xd's riser 1A (slot 1 spans slot 2,
slot 3 spans nothing), cards that mate `pcie-fh`, a low-profile card, a
two-slot card and a vendor filler. The last section holds the real library to
the one thing this slice promises: no bay's published list moves.
"""
import json
import pathlib

import jsonschema
import pytest
import yaml

from portrayal import dcim_export as dcim
from portrayal import devicelock as dl
from portrayal import libwalk
from portrayal import lint
from portrayal import manifest
from portrayal import render
from portrayal.manifest import load_yaml, mates_of, offers, takes

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"
LIB = ROOT / "library"
DEVICE_VALIDATOR = jsonschema.Draft202012Validator(
    json.loads((SCHEMAS / "device.schema.json").read_text()))
COMPONENT_VALIDATOR = jsonschema.Draft202012Validator(
    json.loads((SCHEMAS / "component.schema.json").read_text()))

FILLER = "acme/filler@1"
NIC_A, NIC_B = "acme/nic-a@1", "acme/nic-b@1"
LP_NIC = "acme/lp-nic@1"
GPU2 = "acme/gpu2@1"
RISER = "acme/riser@1"


def _card(name, mates=None, **extra):
    doc = {"format": 1, "kind": "component", "name": name, "version": "1.0.0",
           "class": "card", "behaviour": "fills", "size": {"w": 120.02, "h": 21.59},
           "description": "A test card.", **extra}
    if mates:
        doc["mates"] = mates
    return doc


CARDS = {
    FILLER: _card("filler"),                                   # a blank: mates nothing
    NIC_A: _card("nic-a", "pcie-fh"),
    NIC_B: _card("nic-b", ["pcie-fh"]),                        # the list spelling
    LP_NIC: _card("lp-nic", "pcie-lp"),
    GPU2: _card("gpu2", "pcie-fh", **{"slot-width": 2}),
}


def _slot(i, **extra):
    return {"at": [0, round(20.32 * (i - 1), 2)], "size": [120.02, 21.59], **extra}


def riser():
    """Riser 1A's shape. slot-1 takes by interface and spans slot-2; slot-2 has
    no connector behind it and is a closed list; slot-3 takes by interface and
    spans nothing; slot-4 is a low-profile slot; slot-5 is a bay that states
    only a list."""
    return {
        "format": 1, "kind": "component", "name": "riser", "version": "1.0.0",
        "class": "riser", "size": {"w": 130, "h": 70}, "description": "A test riser.",
        "bays": {
            "slot-1": _slot(1, interface="pcie-fh", accepts=[FILLER], default=FILLER,
                            span=["slot-2"]),
            "slot-2": _slot(2, accepts=[FILLER], default=FILLER),
            "slot-3": _slot(3, interface="pcie-fh", accepts=[FILLER], default=FILLER),
            "slot-4": _slot(4, interface="pcie-lp", accepts=[FILLER], default=FILLER),
            "slot-5": _slot(5, accepts=[NIC_B, NIC_A, FILLER]),
        }}


def _write(lib, ref, doc):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "library"
    for ref, doc in CARDS.items():
        _write(root, ref, doc)
    _write(root, RISER, riser())
    (root / "devices").mkdir(parents=True)
    return root


def _contract(ref):
    return CARDS.get(ref)


def _bays():
    return riser()["bays"]


def _library_offers(lib, bay):
    return render.Library([str(lib)]).offers(bay)


# --- the schema ---------------------------------------------------------------

def _component_errors(doc):
    return [e.message for e in COMPONENT_VALIDATOR.iter_errors(doc)]


@pytest.mark.parametrize("bay", [
    {"interface": "pcie-fh"},
    {"accepts": [FILLER]},
    {"interface": "pcie-fh", "accepts": [FILLER]},
])
def test_a_component_bay_states_an_interface_or_a_list_or_both(bay):
    doc = riser()
    doc["bays"] = {"slot-1": {"at": [0, 0], "size": [120.02, 21.59], **bay}}
    assert _component_errors(doc) == []


def test_a_component_bay_with_neither_is_still_a_hole_that_promises_nothing():
    doc = riser()
    doc["bays"] = {"slot-1": {"at": [0, 0], "size": [120.02, 21.59]}}
    assert _component_errors(doc), "a bay that names nothing offers nothing"


def test_an_interface_may_not_contain_a_dot():
    doc = riser()
    doc["bays"]["slot-1"]["interface"] = "pcie.fh"
    assert _component_errors(doc)


def test_nothing_else_in_a_component_bay_changed():
    doc = riser()
    doc["bays"]["slot-1"]["group"] = "rear"
    assert _component_errors(doc), "`group` is still a device bay's key only"


# --- the two keys -------------------------------------------------------------

def test_the_two_keys_are_registered_and_point_at_their_standards():
    reg = load_yaml(SCHEMAS / "connectors.yaml")["interfaces"]
    stds = load_yaml(SCHEMAS / "standards.yaml")
    stds = stds.get("standards", stds)
    assert reg["pcie-fh"]["standard"] == "pcie-bracket-fh"
    assert reg["pcie-lp"]["standard"] == "pcie-bracket-lp"
    assert reg["pcie-fh"]["note"] and reg["pcie-lp"]["note"]
    assert "pcie-bracket-fh" in stds and "pcie-bracket-lp" in stds


def test_no_other_pcie_form_is_a_key_yet():
    reg = load_yaml(SCHEMAS / "connectors.yaml")["interfaces"]
    for key in reg:
        assert not key.startswith(("e3", "edsff")), key
        if key.startswith("ocp"):
            assert key in {"ocp3-sff", "ocp3-tsff", "ocp3-dsff", "ocp3-tdsff"}, key
    assert "pcie-fh-2slot" not in reg, "the two-slot bracket mates pcie-fh"
    assert not [k for k in reg if "." in k]


# --- the predicate ------------------------------------------------------------

def test_a_card_named_in_no_list_is_taken_by_its_mates():
    bay = _bays()["slot-3"]
    assert NIC_A not in bay["accepts"] and NIC_B not in bay["accepts"]
    assert takes(bay, NIC_A, _contract(NIC_A))
    assert takes(bay, NIC_B, _contract(NIC_B)), "`mates` as a list reads the same"


def test_a_card_of_the_other_height_is_refused():
    assert not takes(_bays()["slot-3"], LP_NIC, _contract(LP_NIC))
    assert not takes(_bays()["slot-4"], NIC_A, _contract(NIC_A))
    assert takes(_bays()["slot-4"], LP_NIC, _contract(LP_NIC))


def test_a_bay_with_both_takes_the_union():
    bay = _bays()["slot-3"]
    assert takes(bay, FILLER, _contract(FILLER)), "the list is a positive claim"
    assert takes(bay, NIC_A, _contract(NIC_A)), "and the interface takes the rest"
    assert not takes(bay, "acme/unknown@1", None)


def test_a_bay_with_no_interface_stays_a_closed_list():
    bay = _bays()["slot-2"]
    assert takes(bay, FILLER, _contract(FILLER))
    assert not takes(bay, NIC_A, _contract(NIC_A)), "mating pcie-fh opens no closed bay"
    assert not takes(_bays()["slot-5"], LP_NIC, _contract(LP_NIC))


def test_a_part_that_does_not_resolve_is_taken_only_by_name():
    bay = _bays()["slot-3"]
    assert takes(bay, FILLER, None)
    assert not takes(bay, NIC_A, None)


def test_a_retired_part_is_not_offered_by_its_mates():
    old = {**_contract(NIC_A), "superseded-by": NIC_B}
    assert not takes(_bays()["slot-3"], NIC_A, old)


def test_a_two_slot_card_is_taken_where_the_span_is_long_enough_and_not_elsewhere():
    bays = _bays()
    assert takes(bays["slot-1"], GPU2, _contract(GPU2)), "slot-1 spans slot-2"
    assert not takes(bays["slot-3"], GPU2, _contract(GPU2)), "slot-3 spans nothing"
    assert takes(bays["slot-3"], NIC_A, _contract(NIC_A)), "a one-slot card needs no span"


def test_the_covered_bay_is_not_consulted():
    bays = _bays()
    bays["slot-2"]["accepts"] = [FILLER, "acme/other@1"]
    assert takes(bays["slot-1"], GPU2, _contract(GPU2))
    bays["slot-2"].pop("accepts")
    bays["slot-2"]["interface"] = "pcie-lp"
    assert takes(bays["slot-1"], GPU2, _contract(GPU2))


def test_a_card_three_slots_wide_needs_two_bays_in_the_span():
    wide = {**_contract(GPU2), "slot-width": 3}
    assert not takes(_bays()["slot-1"], "acme/triple@1", wide)
    bay = {**_bays()["slot-1"], "span": ["slot-2", "slot-3"]}
    assert takes(bay, "acme/triple@1", wide)


# --- offers: the list the build publishes ---------------------------------------

CANDIDATES = {"pcie-fh": [(r, c) for r, c in CARDS.items() if "pcie-fh" in mates_of(c)],
              "pcie-lp": [(LP_NIC, CARDS[LP_NIC])]}


def test_offers_is_the_authored_list_then_every_part_that_mates_and_fits():
    bays = _bays()
    assert offers(bays["slot-1"], CANDIDATES) == [FILLER, GPU2, NIC_A, NIC_B]
    assert offers(bays["slot-3"], CANDIDATES) == [FILLER, NIC_A, NIC_B], "no two-slot card here"
    assert offers(bays["slot-4"], CANDIDATES) == [FILLER, LP_NIC]


def test_a_bay_with_no_interface_publishes_the_list_it_states_in_the_order_it_states_it():
    bays = _bays()
    assert offers(bays["slot-5"], CANDIDATES) == [NIC_B, NIC_A, FILLER]
    assert offers(bays["slot-5"], None) == [NIC_B, NIC_A, FILLER]
    assert offers(bays["slot-2"], CANDIDATES) == [FILLER]
    assert offers({"interface": "pcie-fh"}, None) == []


def test_offers_names_a_listed_part_once():
    bay = {**_bays()["slot-3"], "accepts": [FILLER, NIC_A]}
    assert offers(bay, CANDIDATES) == [FILLER, NIC_A, NIC_B]


def test_the_build_library_publishes_what_the_predicate_takes(lib):
    bays = riser()["bays"]
    assert _library_offers(lib, bays["slot-1"]) == [FILLER, GPU2, NIC_A, NIC_B]
    assert _library_offers(lib, bays["slot-3"]) == [FILLER, NIC_A, NIC_B]
    assert _library_offers(lib, bays["slot-5"]) == [NIC_B, NIC_A, FILLER]


def test_every_ref_a_bay_offers_is_taken_by_it(lib):
    for bid, bay in riser()["bays"].items():
        for ref in _library_offers(lib, bay):
            assert takes(bay, ref, _contract(ref)), (bid, ref)


# --- lint: L6, L8 ---------------------------------------------------------------

def _device(bays=(), configurations=None):
    doc = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "manufacturer": "M", "model": "M", "maturity": "modelled",
           "profile": "networking",
           "chassis": {"width": 440.0, "height": 44.45, "depth": 500.0, "ru": 1},
           "views": {"front": {"size": {"w": 440.0, "h": 44.45},
                              "components": {"bays": list(bays)}}}}
    if configurations:
        doc["configurations"] = configurations
    return doc


def _device_findings(lib, doc):
    path = lib / "devices" / "acme" / "d" / "device.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with lint.collecting() as found:
        lint.lint_device(path, DEVICE_VALIDATOR, [str(lib)])
    assert not [e for e in found.errors if "[L1]" in e], found.errors
    return found.errors + found.warnings


def _device_bay(**extra):
    return {"id": "slot", "at": [10, 2], "size": {"w": 20, "h": 40}, **extra}


def test_l6_a_default_that_mates_the_bays_interface_is_taken(lib):
    doc = _device([_device_bay(interface="pcie-fh", default=NIC_A)])
    assert [f for f in _device_findings(lib, doc) if "[L6]" in f] == []


def test_l6_a_default_of_the_other_height_is_refused(lib):
    doc = _device([_device_bay(interface="pcie-fh", default=LP_NIC)])
    got = [f for f in _device_findings(lib, doc) if "[L6]" in f]
    assert len(got) == 1 and "default acme/lp-nic@1 not in accepts" in got[0]
    assert "pcie-fh" in got[0]


def test_l6_a_bay_with_no_interface_reads_as_it_always_did(lib):
    doc = _device([_device_bay(accepts=[FILLER], default=NIC_A)])
    got = [f for f in _device_findings(lib, doc) if "[L6]" in f]
    assert len(got) == 1 and got[0].endswith("bay slot default acme/nic-a@1 not in accepts")


def _config_findings(lib, cfg_bays):
    doc = _device(
        [{"id": "riser-1", "at": [10, 2], "size": {"w": 130, "h": 70},
          "accepts": [RISER], "default": RISER}],
        {"c": {"bays": cfg_bays}})
    with lint.collecting() as found:
        lint.lint_device_configuration_bays(lib / "devices" / "d.yaml", doc, [str(lib)])
    return [f for f in found.errors if "[L8]" in f]


def test_l8_a_configuration_seats_a_card_named_in_no_list_by_its_mates(lib):
    assert _config_findings(lib, {"riser-1/slot-1": NIC_A, "riser-1/slot-3": NIC_B}) == []


def test_l8_a_card_of_the_other_height_or_in_a_closed_bay_is_refused(lib):
    got = _config_findings(lib, {"riser-1/slot-1": LP_NIC, "riser-1/slot-2": NIC_A,
                                 "riser-1/slot-4": NIC_A})
    assert len(got) == 3, got
    assert all("does not accept" in f for f in got)


def test_l8_the_union_keeps_the_filler_and_the_empty_string(lib):
    assert _config_findings(lib, {"riser-1/slot-1": FILLER, "riser-1/slot-3": FILLER,
                                  "riser-1/slot-2": ""}) == []


def test_l8_a_two_slot_card_is_seated_over_a_span_and_refused_without_one(lib):
    assert _config_findings(lib, {"riser-1/slot-1": GPU2}) == []
    got = _config_findings(lib, {"riser-1/slot-3": GPU2})
    assert len(got) == 1 and "riser-1/slot-3 does not accept acme/gpu2@1" in got[0]


# --- lint: L185 stays a rule about explicit lists --------------------------------

def _component_findings(fn, doc, lib):
    with lint.collecting() as found:
        fn(lib / "components" / "x" / "contract.yaml", doc, [str(lib)])
    return found.errors + found.warnings


def test_l185_a_two_slot_card_in_no_list_is_not_an_error_on_a_riser_it_cannot_reach(lib):
    """The point of the width rule: adding GPU2 to the library does not break the
    riser file whose slot 3 can never span."""
    assert [f for f in _component_findings(lint.lint_component_span, riser(), lib)
            if "L185" in f] == []


def test_l185_a_list_that_names_a_two_slot_card_still_needs_the_span(lib):
    doc = riser()
    doc["bays"]["slot-3"]["accepts"].append(GPU2)
    got = _component_findings(lint.lint_component_span, doc, lib)
    assert len(got) == 1 and "bays/slot-3: accepts acme/gpu2@1, which is 2 slots wide" in got[0]


# --- lint: L11 ------------------------------------------------------------------

def _mating(doc, lib):
    return [f for f in _component_findings(lint.lint_component_mating, doc, lib)
            if "[L11]" in f]


def test_l11_does_not_ask_a_mate_point_of_a_part_that_fills_a_bay(lib):
    assert _mating(CARDS[NIC_A], lib) == []
    assert _mating(CARDS[GPU2], lib) == []


def test_l11_still_asks_one_of_a_part_that_occupies(lib):
    cage_part = {**CARDS[NIC_A], "behaviour": "occupies"}
    got = _mating(cage_part, lib)
    assert len(got) == 2 and any("mates: 'pcie-fh' declared but no 'mate'" in f for f in got), got
    assert _mating({**cage_part, "connection-points": {"mate": {"at": [0, 0]}}}, lib) == []


def test_l11_a_part_that_states_no_behaviour_is_still_asked(lib):
    plug = {k: v for k, v in CARDS[NIC_A].items() if k != "behaviour"}
    assert len(_mating(plug, lib)) == 1


def test_l11_a_part_that_fills_and_presents_an_interface_is_still_asked_for_its_point(lib):
    jack = {**CARDS[NIC_A], "interface": "rj45"}
    assert len(_mating(jack, lib)) == 1, "only `mates` is waived for a part that fills"


def test_the_schema_description_of_mates_says_so():
    schema = json.loads((SCHEMAS / "component.schema.json").read_text())
    text = schema["properties"]["mates"]["description"]
    assert "`behaviour: fills`" in text and "FILLS a bay" in text


# --- lint: the redundant-list warning ---------------------------------------------

def _redundant(doc, lib):
    return [f for f in _component_findings(lint.lint_component_bay_interface, doc, lib)
            if "[L194]" in f]


def test_l194_warns_for_an_accepts_entry_the_interface_already_takes(lib):
    doc = riser()
    doc["bays"]["slot-3"]["accepts"] = [FILLER, NIC_A]
    got = _redundant(doc, lib)
    assert len(got) == 1 and "bays/slot-3: accepts acme/nic-a@1" in got[0]


def test_l194_is_quiet_for_a_filler_a_card_of_the_other_height_and_a_closed_bay(lib):
    doc = riser()
    doc["bays"]["slot-3"]["accepts"] = [FILLER, LP_NIC]
    assert _redundant(doc, lib) == []
    assert _redundant(riser(), lib) == []


def test_l194_is_quiet_for_a_wide_card_the_bay_cannot_reach_and_loud_where_it_can(lib):
    doc = riser()
    doc["bays"]["slot-3"]["accepts"] = [FILLER, GPU2]
    assert _redundant(doc, lib) == [], "slot-3 spans nothing: the list is not redundant"
    doc["bays"]["slot-1"]["accepts"] = [FILLER, GPU2]
    assert len(_redundant(doc, lib)) == 1


def test_l194_is_a_warning_in_the_catalogue():
    assert lint.RULES["L194"][4] == lint.WARNING and lint.RULES["L194"][0] == "component"


# --- the readers of a bay ---------------------------------------------------------

def test_the_lock_follows_a_card_a_riser_takes_by_its_mates(lib):
    versions = dl.component_versions(lib)
    assert {FILLER, NIC_A, NIC_B, GPU2, LP_NIC} <= set(versions["acme/riser"]["v1"]), (
        "an edit to a card the riser takes by `mates` must reach the lock of a device that draws it")


def test_the_lock_follows_a_device_bay_that_states_an_interface(lib):
    versions = dl.component_versions(lib)
    doc = _device([_device_bay(interface="pcie-fh", accepts=[FILLER])])
    assert set(dl.entry(doc, versions)["composed-refs"]) == {FILLER, NIC_A, NIC_B}, (
        "the two-slot card is not taken by a bay that spans nothing")


def test_a_bay_that_states_no_interface_composes_what_it_always_did(lib):
    versions = dl.component_versions(lib)
    doc = _device([_device_bay(accepts=[FILLER])])
    assert set(dl.entry(doc, versions)["composed-refs"]) == {FILLER}


def test_the_catalogue_counts_a_bay_taken_part_as_seated(lib):
    from portrayal import components_index
    doc = _device([_device_bay(interface="pcie-fh", accepts=[FILLER])])
    _write(lib, "acme/dummy@1", _card("dummy"))
    (lib / "devices" / "acme" / "d").mkdir(parents=True)
    (lib / "devices" / "acme" / "d" / "device.yaml").write_text(yaml.safe_dump(doc))
    from portrayal import components_catalogue as cat
    seated = cat.seated_by(lib)
    assert set(seated) >= {FILLER, NIC_A, NIC_B} and "acme/dummy@1" not in seated
    assert {NIC_A, FILLER} <= components_index.seated_in_bays([str(lib)])


def test_a_dcim_bay_row_says_the_interface_and_a_row_without_one_is_unchanged():
    row = dcim.bay_row("slot-1", None, ["slot-2"], "pcie-fh")
    assert row["description"].startswith(
        "Spans slot-2 for a card 2 slots wide. Takes a PCIe slot whose opening takes a "
        "full-height add-in card bracket")
    assert len(row["description"]) <= dcim.LIMIT
    both = dcim.bay_row("slot-3", [FILLER], None, "pcie-lp")
    assert both["description"].endswith("Also accepts: filler")
    assert dcim.bay_row("slot-3", [FILLER])["description"] == "Accepts: filler"
    assert "description" not in dcim.bay_row("slot-3")


# --- the real library: nothing moved -----------------------------------------------

def _authored_bays(contract):
    return {bid: b for bid, b in (contract.get("bays") or {}).items() if isinstance(b, dict)}


@pytest.mark.heavy
def test_a_bay_that_states_an_interface_takes_no_part_beyond_its_list():
    """THIS TEST HOLDS A FACT THE READERS RELY ON. Some readers of a bay's `accepts` still read the
    authored list alone: in dcim_export.py `_chassis_seated`, `_chassis_seats`,
    `pass_through_bays`, `anchored_bays`, `seating_depths` and the device-bay
    rows, and `manifest.component_refs` (the incremental build's dependency
    graph). A bay may state the class of module it takes as its `interface`
    while no part mates that interface, and those readers lose nothing. The
    change that first lets a part mate such an interface routes them through
    `manifest.offers` first, and only then does this test move."""
    lib = render.Library([str(LIB)])
    found = []
    for cf in libwalk.iter_components([LIB]):
        for bid, b in _authored_bays(load_yaml(cf) or {}).items():
            if b.get("interface") and lib.offers(b) != list(b.get("accepts") or []):
                found.append(f"{cf.parent.parent.name}/{cf.parent.name}:{bid}")
    for df in libwalk.iter_devices([LIB]):
        for view in ((load_yaml(df) or {}).get("views") or {}).values():
            for b in manifest.view_parts(view or {})["bays"]:
                if b.get("interface") and lib.offers(b) != list(b.get("accepts") or []):
                    found.append(f"{df.parent.name}:{b['id']}")
    assert found == [], found


def test_a_published_component_bay_list_is_the_list_the_contract_states():
    f = LIB / "dist" / "components.json"
    if not f.exists():
        pytest.skip("components.json not built")
    checked = 0
    for c in json.loads(f.read_text())["components"]:
        cf = LIB / "components" / c["ns"] / c["name"] / c["major"] / "contract.yaml"
        if not cf.exists():
            continue
        for bid, b in _authored_bays(load_yaml(cf) or {}).items():
            published = c["bays"][bid]
            assert published["accepts"] == (b.get("accepts") or []), (cf, bid)
            assert published.get("interface") == b.get("interface"), (cf, bid)
            checked += 1
    assert checked > 50, f"read {checked} bays"


@pytest.mark.heavy
def test_a_published_device_bay_list_is_the_list_the_manifest_states():
    if not (LIB / "dist" / "components.json").exists():
        pytest.skip("components.json not built")
    files = sorted((LIB / "dist").glob("**/*.configs.json"))
    assert files, "components.json is built and no configs.json is"
    checked = 0
    manifests = {m.parent.name: m for m in libwalk.iter_devices([LIB])}
    for f in files:
        data = json.loads(f.read_text())
        man = manifests.get(data.get("device") or data.get("name"))
        if man is None:
            continue
        for view, bays in (data.get("bays") or {}).items():
            authored = {b["id"]: b for b in manifest.view_parts(
                (load_yaml(man).get("views") or {}).get(view) or {})["bays"]}
            for b in bays:
                assert b["accepts"] == (authored[b["id"]].get("accepts") or []), (f, b["id"])
                assert b.get("interface") == authored[b["id"]].get("interface")
                checked += 1
    assert checked, "no bay was compared; the layout of configs.json moved"
