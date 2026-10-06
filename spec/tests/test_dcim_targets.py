"""Where the NetBox and Nautobot documents part.

Both trees were one document until every export was imported into a running
NetBox 4.7 and Nautobot 3.2. NetBox took all 1237; Nautobot refused 37: two
device types with a half-U height, which it stores as a whole number, and the
35 cassettes and panels with front ports, which it still binds to a rear port
inside the type. `dcim_export.for_target` writes what each can import.

The unit tests need no build. The sweeps read `library/exports`, which is
committed.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "library" / "exports"

from portrayal import dcim_export as dx   # noqa: E402


def breakout():
    """One MPO-4 trunk to four LC fibres, as `build_module` and `fibre_map` leave them."""
    doc = {"manufacturer": "Acme", "model": "B4", "comments": "A breakout.",
           "rear-ports": [{"name": "{module}/MTP-1", "type": "mpo", "positions": 4}],
           "front-ports": [{"name": f"{{module}}/{n}", "type": "lc-upc", "positions": 1}
                           for n in (1, 2, 3, 4)]}
    rows = [{"front": f"{{module}}/{n}", "front_position": 1,
             "rear": "{module}/MTP-1", "rear_position": p}
            for n, p in ((1, 4), (2, 3), (3, 2), (4, 1))]
    return doc, {"model": "B4", "rows": rows}


def panel():
    """One MPO-12 adapter: a twelve-fibre front connector on a twelve-fibre rear."""
    doc = {"manufacturer": "Acme", "model": "P1", "comments": "A panel.",
           "rear-ports": [{"name": "{module}/B01-1", "type": "mpo", "positions": 12}],
           "front-ports": [{"name": "{module}/1", "type": "mpo", "positions": 12}]}
    rows = [{"front": "{module}/1", "front_position": p,
             "rear": "{module}/B01-1", "rear_position": p} for p in range(1, 13)]
    return doc, {"model": "P1", "rows": rows}


def test_netbox_takes_the_document_as_written():
    doc, fmap = breakout()
    doc["u_height"] = 3.5
    assert dx.for_target(doc, "netbox", fmap) is doc


def test_a_whole_height_with_no_front_ports_is_the_same_document_in_both():
    doc = {"manufacturer": "Acme", "model": "S1", "u_height": 2.0, "comments": "x"}
    assert dx.for_target(doc, "nautobot") is doc


def test_a_half_u_box_rounds_up_for_nautobot_and_keeps_its_height_in_words():
    doc = {"manufacturer": "Acme", "model": "S2", "u_height": 3.5, "comments": "A box."}
    out = dx.for_target(doc, "nautobot")
    assert out["u_height"] == 4.0
    assert "3.5U" in out["comments"] and out["comments"].startswith("A box.")
    assert doc["u_height"] == 3.5, "the NetBox document is written from the same dict"


def test_a_breakout_front_port_names_its_rear_port_and_position():
    doc, fmap = breakout()
    out = dx.for_target(doc, "nautobot", fmap)
    assert [(p["name"], p["rear_port"], p["rear_port_position"]) for p in out["front-ports"]] == [
        ("{module}/1", "{module}/MTP-1", 4), ("{module}/2", "{module}/MTP-1", 3),
        ("{module}/3", "{module}/MTP-1", 2), ("{module}/4", "{module}/MTP-1", 1)]
    assert all("positions" not in p for p in out["front-ports"])
    assert out["rear-ports"][0]["positions"] == 4
    assert "positions" in doc["front-ports"][0], "the NetBox document is written from the same dict"


def test_an_mpo_pass_through_is_one_position_and_says_where_the_fibres_are():
    doc, fmap = panel()
    out = dx.for_target(doc, "nautobot", fmap)
    assert out["front-ports"] == [{"name": "{module}/1", "type": "mpo",
                                   "rear_port": "{module}/B01-1", "rear_port_position": 1}]
    assert out["rear-ports"][0]["positions"] == 1
    assert "fibre map" in out["comments"]
    assert doc["rear-ports"][0]["positions"] == 12


def test_a_reversing_adapter_is_not_called_straight_through():
    """A Type B adapter turns the fibres over (front 12 on rear 1). The binding
    is the same one position; the note must not say the opposite of the map."""
    doc, fmap = panel()
    assert "straight through" in dx.for_target(doc, "nautobot", fmap)["comments"]
    for row in fmap["rows"]:
        row["front_position"] = 13 - row["rear_position"]
    out = dx.for_target(doc, "nautobot", fmap)
    assert out["front-ports"][0]["rear_port_position"] == 1
    assert "straight through" not in out["comments"]
    assert "different order" in out["comments"] and "fibre map" in out["comments"]


def test_a_wide_front_port_with_one_stated_path_stops_the_export():
    """Twelve fibres wide with one row stated: the map says one fibre passes,
    and one position for the whole connector would say all twelve do (#771)."""
    doc, fmap = panel()
    fmap["rows"] = fmap["rows"][:1]
    with pytest.raises(dx.NotExpressible, match="P1.*module./1.*not the whole of"):
        dx.for_target(doc, "nautobot", fmap)


@pytest.mark.parametrize("stated,whole", [(2.5, 3.0), (0.5, 1.0)])
def test_any_half_u_rounds_up_not_to_even(stated, whole):
    """3.5 and 1.5 round up under round() too; 2.5 and 0.5 do not."""
    doc = {"manufacturer": "Acme", "model": "S3", "u_height": stated, "comments": "x"}
    assert dx.for_target(doc, "nautobot")["u_height"] == whole


# --- a front port that is not what its rows say (#771) ------------------------

def test_a_one_fibre_front_port_with_no_rear_position_stops_the_export():
    doc, fmap = breakout()
    del fmap["rows"][2]["rear_position"]
    with pytest.raises(dx.NotExpressible, match="B4.*module./3.*None.*1..4"):
        dx.for_target(doc, "nautobot", fmap)


@pytest.mark.parametrize("bad", [0, 5, 9])
def test_a_one_fibre_front_port_past_its_rear_port_stops_the_export(bad):
    doc, fmap = breakout()
    fmap["rows"][0]["rear_position"] = bad
    with pytest.raises(dx.NotExpressible, match=f"module./1.*position {bad}.*1..4"):
        dx.for_target(doc, "nautobot", fmap)


def test_a_one_position_front_port_on_two_rear_positions_stops_the_export():
    """Two rows from one `positions: 1` front port into a 2-position rear: the
    collapse would have rewritten the rear to one position without a word."""
    doc = {"manufacturer": "Acme", "model": "T2", "comments": "x",
           "rear-ports": [{"name": "{module}/R", "type": "lc-upc", "positions": 2}],
           "front-ports": [{"name": "{module}/F", "type": "lc-upc", "positions": 1}]}
    rows = [{"front": "{module}/F", "front_position": 1, "rear": "{module}/R", "rear_position": p}
            for p in (1, 2)]
    with pytest.raises(dx.NotExpressible, match="T2.*module./F.*not the whole of"):
        dx.for_target(doc, "nautobot", {"model": "T2", "rows": rows})


def test_a_wide_front_port_on_part_of_its_rear_port_stops_the_export():
    """A 2-wide front port on positions 5-6 of a twelve-position rear: one
    position would claim the other ten fibres pass through it too."""
    doc = {"manufacturer": "Acme", "model": "W2", "comments": "x",
           "rear-ports": [{"name": "{module}/R", "type": "mpo", "positions": 12}],
           "front-ports": [{"name": "{module}/F", "type": "lc-upc", "positions": 2}]}
    rows = [{"front": "{module}/F", "front_position": f, "rear": "{module}/R", "rear_position": r}
            for f, r in ((1, 5), (2, 6))]
    with pytest.raises(dx.NotExpressible, match="W2.*module./F.*not the whole of"):
        dx.for_target(doc, "nautobot", {"model": "W2", "rows": rows})
    assert doc["rear-ports"][0]["positions"] == 12


def test_a_front_port_with_no_row_stops_the_export():
    doc, fmap = breakout()
    fmap["rows"] = fmap["rows"][:-1]
    with pytest.raises(dx.NotExpressible, match="B4.*module./4"):
        dx.for_target(doc, "nautobot", fmap)


def test_front_ports_with_no_fibre_map_stop_the_export():
    doc, _ = breakout()
    with pytest.raises(dx.NotExpressible):
        dx.for_target(doc, "nautobot")


def test_two_front_ports_on_one_rear_position_stop_the_export():
    """A tap: NetBox's many-to-many holds it, Nautobot's unique pair does not."""
    doc, fmap = breakout()
    fmap["rows"][1]["rear_position"] = fmap["rows"][0]["rear_position"]
    with pytest.raises(dx.NotExpressible, match="one front port per rear position"):
        dx.for_target(doc, "nautobot", fmap)


def _docs(tree):
    return [(f, yaml.safe_load(f.read_text()))
            for f in sorted((EXPORTS / tree).glob("*-types/*/*.yaml"))]


def test_every_nautobot_height_is_a_whole_number():
    heights = [(f, d["u_height"]) for f, d in _docs("nautobot") if "u_height" in d]
    assert len(heights) > 400
    assert not [str(f.relative_to(EXPORTS)) for f, h in heights if not float(h).is_integer()]


def test_every_nautobot_front_port_is_bound_to_a_rear_position_of_its_own_type():
    seen, wrong = 0, []
    for f, d in _docs("nautobot"):
        rears = {r["name"]: r["positions"] for r in d.get("rear-ports") or []}
        pairs = set()
        for p in d.get("front-ports") or []:
            seen += 1
            pair = (p.get("rear_port"), p.get("rear_port_position"))
            if ("positions" in p or pair[0] not in rears or pair in pairs
                    or not 1 <= (pair[1] or 0) <= rears[pair[0]]):
                wrong.append(f"{f.relative_to(EXPORTS)}: {p['name']}")
            pairs.add(pair)
    assert seen > 600, "the cassettes are what this reads; none found is not a pass"
    assert not wrong, wrong


def test_the_netbox_front_ports_carry_no_binding():
    """netbox#20564 took it out of the type; the fibre map carries it."""
    fronts = [p for _f, d in _docs("netbox") for p in d.get("front-ports") or []]
    assert len(fronts) > 600
    assert all(set(p) == {"name", "type", "positions"} for p in fronts)


@pytest.mark.parametrize("vendor,model,stated,whole", [
    ("Juniper", "MX104", 3.5, 4.0),
    ("BATM/Telco Systems", "TM-7124S", 1.5, 2.0),
])
def test_the_half_u_boxes_differ_between_the_trees_only_in_height(vendor, model, stated, whole):
    where = dx.manufacturer_dir(vendor)
    nb = yaml.safe_load((EXPORTS / "netbox/device-types" / where / f"{model}.yaml").read_text())
    nt = yaml.safe_load((EXPORTS / "nautobot/device-types" / where / f"{model}.yaml").read_text())
    assert nb["manufacturer"] == nt["manufacturer"] == vendor
    assert (nb["u_height"], nt["u_height"]) == (stated, whole)
    assert f"{stated:g}U" in nt["comments"]
    assert {k for k in nb if nb[k] != nt.get(k)} == {"u_height", "comments"}


def test_the_trees_differ_nowhere_else():
    """Everything `for_target` and `nested_bays_for` do not rewrite is still one
    document in both: the files that differ are the ones with front ports or a
    part-unit height, and the module types that carry bays of their own, which
    only NetBox is given."""
    differ, rewritten = set(), set()
    for f, d in _docs("netbox"):
        rel = str(f.relative_to(EXPORTS / "netbox"))
        if d != yaml.safe_load((EXPORTS / "nautobot" / rel).read_text()):
            differ.add(rel)
        nested = rel.startswith("module-types/") and d.get("module-bays")
        if d.get("front-ports") or nested or not float(d.get("u_height") or 0).is_integer():
            rewritten.add(rel)
    assert len(rewritten) > 30
    assert differ == rewritten, sorted(differ ^ rewritten)


# --- a manufacturer whose name holds a slash ---------------------------------

def test_a_slash_in_a_manufacturer_is_not_a_directory():
    """`BATM/Telco Systems` is one manufacturer. Joined into a path as written
    it opened a `BATM` directory with `Telco Systems` inside it, one level
    below where every reader of the tree looks. The document keeps the name;
    the directory does not keep the slash."""
    assert dx.manufacturer_dir("BATM/Telco Systems") == "BATM-Telco Systems"
    assert dx.manufacturer_dir("Juniper") == "Juniper"
    assert "/" not in dx.manufacturer_dir("a/b/c")


def test_every_export_sits_one_directory_below_its_tree_under_its_manufacturer():
    """The files, not the function: each device type and module type is at
    `<tree>/<kind>/<manufacturer directory>/<file>`, and the directory is its
    own manufacturer's. A slashed name is among them, or this measured nothing
    about the case it is here for."""
    seen, slashed = 0, set()
    for tree in ("netbox", "nautobot"):
        for kind in ("device-types", "module-types"):
            top = EXPORTS / tree / kind
            for f in sorted(top.rglob("*.yaml")):
                doc = yaml.safe_load(f.read_text())
                rel = f.relative_to(top)
                assert len(rel.parts) == 2, f"{f}: not one directory below {kind}"
                assert rel.parts[0] == dx.manufacturer_dir(doc["manufacturer"]), f
                seen += 1
                if "/" in doc["manufacturer"]:
                    slashed.add(doc["manufacturer"])
    assert seen > 1000, "measured almost no exports - run ./publish.sh --no-images"
    assert slashed, "no manufacturer with a slash was read"

