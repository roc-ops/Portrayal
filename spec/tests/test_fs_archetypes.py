"""The FS archetypes - one real part per shape the catalogue contains.

Every figure here is either measured off FS's own dimensioned drawing (the
enclosure) or off a face-on render validated by panel_measure (the cassettes),
except the splice cassette, which no image in the corpus shows at all. Where a
number is estimated the contract says so; these tests check the claims, not the
prose.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def device(rel):
    p = LIB / "devices" / rel / "device.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def contract(rel):
    p = LIB / "components" / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_enclosure_carries_its_dimensioned_figures():
    """Read off page 7 of FS's own datasheet: front and top views, dimensioned.

    448.0 body in a 482.6 rack, 44.0 high, 432.8 deep. This is the only part in
    this plan whose size needs no estimating at all.

    A DEVICE DECLARES `chassis`, not `size` - `size` is a per-view key. See
    library/devices/smartoptics/dcp-2/device.yaml for the shape.
    """
    d = device("fs/fhd-1ufce")
    assert d is not None, "fs/fhd-1ufce not built"
    assert d["manufacturer"] == "FS.com"
    ch = d["chassis"]
    assert (ch["width"], ch["height"], ch["depth"]) == (448.0, 44.0, 432.8)
    assert ch["ru"] == 1


def test_the_enclosure_holds_four_modules():
    """Four slots at the 108.97 module width need 435.88, inside the 448.0 body."""
    d = device("fs/fhd-1ufce")
    bays = d["views"]["front"]["components"]["bays"]
    assert len(bays) == 4, f"expected 4 cassette slots, found {len(bays)}"
    assert 4 * 108.97 <= 448.0


def test_the_enclosure_accepts_every_fs_cassette_in_the_library():
    """THIS IS WHAT KEEPS THE `accepts` LIST HONEST.

    Four later tasks each add a cassette, and an `accepts` list written once is
    an omission that passes quietly - the enclosure would ship accepting one of
    the five modules that seat in it. Every FHD cassette seats in every FHD
    enclosure; that is what the format is for, so the assertion is total rather
    than a list someone maintains by hand.
    """
    d = device("fs/fhd-1ufce")
    accepted = set()
    for bay in d["views"]["front"]["components"]["bays"]:
        accepted |= set(bay.get("accepts") or [])
    modelled = set()
    for c in (LIB / "components" / "fs").glob("*/v*/contract.yaml"):
        doc = yaml.safe_load(c.read_text()) or {}
        if doc.get("kind") != "module":
            continue                       # a rear face is not a seatable part
        modelled.add(f"fs/{doc['name']}@{c.parent.name[1:]}")
    missing = sorted(modelled - accepted)
    assert not missing, f"cassettes the enclosure does not accept: {missing}"


SPLICE = "fs/fhd-splice-12-lc/v1"


def test_the_splice_cassette_states_that_nothing_measured_it():
    """Eleven splice cassettes in the catalogue and not one photograph.

    The whole contract is derived from family constants. If a later intake
    fetches imagery and someone measures it, this assertion is what tells them
    the prose needs rewriting too.
    """
    c = contract(SPLICE)
    assert c is not None, "fs/fhd-splice-12-lc@1 not built"
    conf = set(c["size-confidence"].values())
    assert conf <= {"estimated", "borrowed"}, \
        f"claims a measurement the corpus cannot support: {c['size-confidence']}"
    note = (c.get("provenance") or {}).get("size", "")
    assert "no image" in note.lower() or "not photographed" in note.lower(), \
        "provenance must say plainly that no imagery of this part exists"


def test_the_splice_cassettes_polish_is_sourced_not_assumed():
    """Unlike SKU 57016, this row names it: 'Fiber Splice Cassette, LC UPC'."""
    c = contract(SPLICE)
    assert c["optical"]["polish"] == "upc"
    note = (c.get("provenance") or {}).get("optical", "")
    assert "382907" in note, "cite the catalogue row that names the polish"


def test_the_splice_cassette_has_a_splice_rear():
    c = contract(SPLICE)
    assert c["optical"]["rear-kind"] == "splice"
    assert (c.get("faces") or {}).get("rear"), "a rear-kind needs a rear face (L87)"
    assert len(c["optical"]["paths"]) == 12


TWO_MTP = "fs/fhd-2mtp12-lc-os2-a/v1"


def test_two_rear_connectors_export_as_two_distinct_ports():
    """The first module with more than one rear port.

    `rear_port_names` numbers within a part id, so two parts sharing an id would
    collapse to one name and the fibre map would bind 24 fibres to 12 positions.
    Distinct ids are what prevent that, and this is what checks it.
    """
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-2mtp12-lc-os2-a@1"]
    got = P.ports(D.contract_view(e), idx.get)
    names = [p["name"] for p in got["rear"]]
    assert len(names) == 2, got["rear"]
    assert len(set(names)) == 2, f"two rear ports share one name: {names}"
    assert sum(p["positions"] for p in got["rear"]) == 24
    assert len(got["front"]) == 24


def test_every_one_of_the_24_fibres_is_bound():
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-2mtp12-lc-os2-a@1"]
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-2X12MTPLCOS2A")
    assert len(m["rows"]) == 24
    assert len({(r["rear"], r["rear_position"]) for r in m["rows"]}) == 24, \
        "two fibres land on one rear position"


SC = "fs/fhd-1mtp12-sc-os2-a/v1"


def test_the_sc_cassette_is_the_first_user_of_the_sc_adapter():
    """`common/sc-duplex-adapter@1` was measured and then composed by nothing.

    Its 13.0 pitch floor has never been checked against a real layout, because
    L81 reads `conforms` off a composed part and nothing composed it.
    """
    c = contract(SC)
    assert c is not None, "fs/fhd-1mtp12-sc-os2-a@1 not built"
    refs = [p["ref"] for p in c["parts"]]
    assert refs.count("common/sc-duplex-adapter@1") == 6, refs


def test_the_sc_adapters_are_the_first_real_check_of_the_registry_floor():
    """L81 checks a UNIFORM composed pitch against the registry floor - this
    one is not uniform, and that is the finding, not a bug in this test.

    The six centres are 57058.main.jpg's own render, the same image
    common/sc-duplex-adapter@1's pitch floor (13.0, `pitch-kind: floor`) was
    set from. Reproducing them here for the first real cassette shows the
    floor is the MEAN of five noisy gaps (12.71-13.22), not their minimum:
    the narrowest gap sits 0.29 under it. Because the gaps are not all equal,
    L81's own uniform-pitch check (`if len(set(gaps)) != 1: continue`) never
    fires - so lint stays clean - but the raw number is still worth pinning
    here rather than only in prose. See the contract's `provenance.pitch-note`
    and task-5-report.md for why the placement is not widened to hide it.
    """
    import lint as L
    L.STANDARDS.update(
        L.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])
    assert L.STANDARDS["sc-duplex-adapter"]["pitch"] == 13.0
    c = contract(SC)
    xs = sorted(float(p["at"][0]) for p in c["parts"]
                if p["ref"] == "common/sc-duplex-adapter@1")
    gaps = [round(xs[i] - xs[i - 1], 2) for i in range(1, len(xs))]
    assert len(set(gaps)) > 1, \
        f"expected the render's own measurement noise, got a uniform {gaps}"
    assert min(gaps) == 12.71, gaps
    assert min(gaps) < 13.0, (
        "the registry floor is a rounded MEAN of these same five gaps, not "
        f"their minimum - {min(gaps)} is honestly narrower than it, and "
        "task-5-report.md records that as a finding about the standard")


def test_the_sc_front_ports_type_as_sc():
    c = contract(SC)
    assert c["optical"]["polish"] in ("upc", "apc")


MTP24 = "fs/fhd-1mtp24-lc-os2-a/v1"


def test_the_library_has_an_mpo_wider_than_twelve():
    """`common/mpo-adapter@1` is 12 positions and the catalogue needs 8, 12, 16
    and 24 across 48 modules. This is the first part that needs another."""
    a = contract("common/mpo24-adapter/v1")
    assert a is not None, "common/mpo24-adapter@1 not built"
    assert a["optical"]["positions"] == 24
    twelve = contract("common/mpo-adapter/v1")
    assert twelve["optical"]["positions"] == 12, "the 12 must stay a 12"


def test_the_mtp24_cassette_carries_24_fibres_on_one_rear_port():
    """One rear connector, 24 positions - the count is on the port, not the
    number of ports. This is C1's asymmetry at a width nothing has exercised."""
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-1mtp24-lc-os2-a@1"]
    got = P.ports(D.contract_view(e), idx.get)
    assert len(got["rear"]) == 1, got["rear"]
    assert got["rear"][0]["positions"] == 24
    assert got["rear"][0]["type"] == "mpo"
    assert len(got["front"]) == 24


def test_the_front_numbering_covers_all_24_without_a_gap():
    """The front-label derivation walks adapters by `at.x`. Twelve adapters do
    not fit one row on a 108.97 face, so if the real arrangement is two rows the
    x-order alone may not reproduce the vendor's numbering - which is exactly the
    soft spot plan 5's self-review named. This is where it gets tested."""
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-1mtp24-lc-os2-a@1"]
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-1X24MTPLCOS2A")
    assert sorted(int(r["front"]) for r in m["rows"]) == list(range(1, 25))
