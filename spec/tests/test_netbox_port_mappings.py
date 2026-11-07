"""A NetBox module type states its front-to-rear binding as `port-mappings`.

NetBox 4.6 and later store the binding in the type (PortTemplateMapping), as
`{front_port, front_port_position, rear_port, rear_port_position}`. The fibre map
beside the types is the full record and keeps its `ratio` and `band`; the
mappings are the same rows under the type's own keys. Nautobot binds inside the
front port and is not given them.

The unit tests need no build. The sweeps read `library/exports`, which is
committed.
"""
import copy
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "library" / "exports"

from portrayal import dcim_export as dx   # noqa: E402

KEYS = {"front_port", "front_port_position", "rear_port", "rear_port_position"}


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


def coupler():
    """Two front ports on one rear position, a declared 50/50 split."""
    doc = {"manufacturer": "Acme", "model": "C1", "comments": "A coupler.",
           "rear-ports": [{"name": "{module}/COMMON-1", "type": "lc-upc", "positions": 2}],
           "front-ports": [{"name": f"{{module}}/{n}", "type": "lc-upc", "positions": 1}
                           for n in (3, 4)]}
    rows = [{"front": f"{{module}}/{n}", "front_position": 1,
             "rear": "{module}/COMMON-1", "rear_position": 1, "ratio": 50}
            for n in (3, 4)]
    return doc, {"model": "C1", "rows": rows}


def test_a_netbox_type_carries_one_mapping_per_fibre_map_row():
    doc, fmap = breakout()
    out = dx.for_target(doc, "netbox", fmap)
    assert out["port-mappings"] == [
        {"front_port": r["front"], "front_port_position": r["front_position"],
         "rear_port": r["rear"], "rear_port_position": r["rear_position"]}
        for r in fmap["rows"]]


def test_a_mapping_leaves_the_ports_and_the_rest_of_the_type_as_they_were():
    doc, fmap = breakout()
    before = copy.deepcopy(doc)
    out = dx.for_target(doc, "netbox", fmap)
    assert doc == before
    assert {k: v for k, v in out.items() if k != "port-mappings"} == before


def test_the_mappings_follow_the_front_ports_in_the_document():
    doc, fmap = breakout()
    keys = list(dx.for_target(doc, "netbox", fmap))
    assert keys.index("port-mappings") == keys.index("front-ports") + 1


def test_a_split_leaves_its_ratio_in_the_fibre_map_only():
    doc, fmap = coupler()
    out = dx.for_target(doc, "netbox", fmap)
    assert len(out["port-mappings"]) == 2
    assert all(set(m) == KEYS for m in out["port-mappings"])
    assert {m["rear_port_position"] for m in out["port-mappings"]} == {1}


def test_a_type_with_no_fibre_map_is_the_document_as_written():
    doc = {"manufacturer": "Acme", "model": "S1", "u_height": 2.0, "comments": "x"}
    assert dx.for_target(doc, "netbox") is doc


def test_nautobot_is_not_given_mappings():
    doc, fmap = breakout()
    assert "port-mappings" not in dx.for_target(doc, "nautobot", fmap)


def test_a_row_naming_a_port_the_type_lacks_stops_the_export():
    doc, fmap = breakout()
    fmap["rows"][0]["rear"] = "{module}/MTP-9"
    with pytest.raises(dx.NotExpressible):
        dx.for_target(doc, "netbox", fmap)


def test_a_row_past_the_end_of_its_port_stops_the_export():
    doc, fmap = breakout()
    fmap["rows"][0]["rear_position"] = 5
    with pytest.raises(dx.NotExpressible):
        dx.for_target(doc, "netbox", fmap)


# --- the committed exports ---------------------------------------------------

def _pairs():
    """(netbox type, fibre map) for every module type that has a fibre map."""
    out = []
    for fm in sorted((EXPORTS / "fibre-maps").glob("*/*.yaml")):
        nb = EXPORTS / "netbox" / "module-types" / fm.parent.name / fm.name
        out.append((nb, fm))
    return out


def test_every_netbox_type_with_a_fibre_map_carries_its_rows_as_mappings():
    seen, wrong = 0, []
    for nb, fm in _pairs():
        doc = yaml.safe_load(nb.read_text())
        rows = yaml.safe_load(fm.read_text())["rows"]
        want = [{"front_port": r["front"], "front_port_position": r["front_position"],
                 "rear_port": r["rear"], "rear_port_position": r["rear_position"]}
                for r in rows]
        seen += 1
        if doc.get("port-mappings") != want:
            wrong.append(str(nb.relative_to(EXPORTS)))
    assert seen > 50, "the fibre maps are what this reads; none found is not a pass"
    assert not wrong, wrong


def test_every_mapping_names_a_port_of_its_own_type_at_a_position_it_has():
    seen, wrong = 0, []
    for f in sorted((EXPORTS / "netbox" / "module-types").glob("*/*.yaml")):
        doc = yaml.safe_load(f.read_text())
        fronts = {p["name"]: p["positions"] for p in doc.get("front-ports") or []}
        rears = {p["name"]: p["positions"] for p in doc.get("rear-ports") or []}
        for m in doc.get("port-mappings") or []:
            seen += 1
            if (set(m) != KEYS or m["front_port"] not in fronts or m["rear_port"] not in rears
                    or not 1 <= m["front_port_position"] <= min(fronts[m["front_port"]], 1024)
                    or not 1 <= m["rear_port_position"] <= min(rears[m["rear_port"]], 1024)):
                wrong.append(f"{f.relative_to(EXPORTS)}: {m}")
    assert seen > 500, "no mappings read - run ./publish.sh --no-images"
    assert not wrong, wrong[:5]


def test_no_mapping_carries_a_ratio_or_a_band():
    docs = [yaml.safe_load(f.read_text())
            for f in sorted((EXPORTS / "netbox" / "module-types").glob("*/*.yaml"))]
    mapped = [m for d in docs for m in d.get("port-mappings") or []]
    assert mapped, "no mappings read - run ./publish.sh --no-images"
    assert not [m for m in mapped if {"ratio", "band"} & set(m)]


def test_no_nautobot_type_carries_mappings():
    docs = [yaml.safe_load(f.read_text())
            for f in sorted((EXPORTS / "nautobot" / "module-types").glob("*/*.yaml"))]
    assert len(docs) > 100
    assert not [d["model"] for d in docs if "port-mappings" in d]


def test_every_netbox_type_with_front_ports_carries_mappings():
    """A module type with front ports and no mappings would be a cassette whose
    binding is stated nowhere in its NetBox type."""
    bare = []
    for f in sorted((EXPORTS / "netbox" / "module-types").glob("*/*.yaml")):
        doc = yaml.safe_load(f.read_text())
        if doc.get("front-ports") and not doc.get("port-mappings"):
            bare.append(str(f.relative_to(EXPORTS)))
    assert not bare, bare
