"""The exporter files a listed box under its NOS vendor, named by the listing.

`nos_name()` hardcoded arcos as swp{n}/ma1 and sonic as Ethernet{(n-1)*4} in
Python, while the ArcOS data already stated the rule - with breakout modes the
Python never read. Nothing joined the two, so a renamed interface left the
exporter emitting the old name, and `--nos sonic` wrote 144 device types for a
NOS nothing in the library describes (#63, #56).

Then an overlay under the hardware had to opt in with `identity:` to be filed
under the software vendor. Now the NOS vendor LISTS the box (#674): a listing
under `devices/arrcus/` points at the hardware and is the only source of a NOS
name, a model under Arrcus, and an Arrcus part number. A box nobody lists
exports only its own type, which names its ports by the faceplate.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml


from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library/dist"
TOOL = ROOT / "spec/tools/portrayal/dcim_export.py"

pytestmark = pytest.mark.skipif(not (DIST / "listings.json").exists(),
                                reason="library/dist not built")


# ---- the rules, expanded ----------------------------------------------------

ARCOS = {"interfaces": [
    {"physical": "port-{n}", "name": "swp{n}", "range": "1-32",
     "breakout": {"modes": ["4x25g", "4x10g"], "child-name": "swp{n}s{i}"}},
    {"physical": "mgmt-eth", "name": "ma1"},
]}


def test_a_ranged_rule_expands_over_its_range():
    names = dx.listing_names(ARCOS)
    assert names["port-1"][0] == "swp1"
    assert names["port-32"][0] == "swp32"
    assert "port-33" not in names
    assert names["mgmt-eth"][0] == "ma1"


def test_the_name_pattern_may_do_arithmetic_over_n():
    """The schema's own example: SONiC counts lanes, `Ethernet{(n-1)*4}`."""
    names = dx.listing_names({"interfaces": [
        {"physical": "port-{n}", "name": "Ethernet{(n-1)*4}", "range": "1-3"}]})
    assert [names[f"port-{n}"][0] for n in (1, 2, 3)] == ["Ethernet0", "Ethernet4", "Ethernet8"]


def test_a_name_pattern_is_arithmetic_and_nothing_else():
    with pytest.raises(SystemExit):
        dx.listing_names({"interfaces": [
            {"physical": "port-{n}", "name": "{__import__('os').getcwd()}", "range": "1-1"}]})


def test_a_ranged_physical_needs_a_range():
    with pytest.raises(SystemExit):
        dx.listing_names({"interfaces": [{"physical": "port-{n}", "name": "swp{n}"}]})


def test_breakout_reaches_the_interface_as_a_description():
    """A device type lists the physical ports; the 128 children a breakout
    would make are a property of how a DEVICE is configured, so they go in the
    description rather than as 96 interfaces the metal has not got."""
    d = dx.breakout_note(ARCOS["interfaces"][0]["breakout"], 7)
    assert "4x25g" in d and "4x10g" in d
    assert "swp7s{i}" in d, d


def test_nos_name_is_gone():
    assert not hasattr(dx, "nos_name"), "the hardcoded convention is back"


# ---- the export, run --------------------------------------------------------

def run(tmp, *args):
    return subprocess.run([sys.executable, str(TOOL), "--dist", str(DIST),
                           "--out", str(tmp), "--no-raster", *args],
                          capture_output=True, text=True)


def docs(tmp):
    return {p.relative_to(tmp / "netbox" / "device-types").as_posix(): yaml.safe_load(p.read_text())
            for p in (tmp / "netbox" / "device-types").rglob("*.yaml")}


def test_the_arcos_export_says_what_the_listing_says(tmp_path):
    r = run(tmp_path, "--device", "as7726-32x")
    assert r.returncode == 0, r.stderr[-800:]
    ls = json.loads((DIST / "listings.json").read_text())["listings"]["arrcus/as7726-32x"]
    want = dx.listing_names(ls)
    arcos = [d for n, d in docs(tmp_path).items() if n.startswith("Arrcus/")]
    assert arcos, "no ArcOS document filed under Arrcus"
    for doc in arcos:
        names = [i["name"] for i in doc["interfaces"]]
        assert set(names) <= {v[0] for v in want.values()}, set(names) - {v[0] for v in want.values()}
        assert "ma1" in names, "the listing names mgmt-eth ma1 and the export does not"
        assert [n for n in names if n.startswith("swp")] == [f"swp{i}" for i in range(1, 33)]
        ma1 = next(i for i in doc["interfaces"] if i["name"] == "ma1")
        assert ma1.get("mgmt_only") is True
        swp7 = next(i for i in doc["interfaces"] if i["name"] == "swp7")
        assert "4x25g" in swp7.get("description", ""), swp7


def test_a_listed_type_is_the_hardware_type_under_another_manufacturer(tmp_path):
    """ONE TYPE PER MANUFACTURER THAT SELLS IT, which is how NetBox and Nautobot
    file a disaggregated box. The same SKUs, the same part numbers - the metal
    is the same metal - under Arrcus, with the hardware named in the comments."""
    r = run(tmp_path, "--device", "as7726-32x")
    assert r.returncode == 0, r.stderr[-800:]
    made = docs(tmp_path)
    hw = {n.split("/", 1)[1]: d for n, d in made.items() if n.startswith("Edgecore/")}
    ar = {n.split("/", 1)[1]: d for n, d in made.items() if n.startswith("Arrcus/")}
    assert len(hw) == 4 and set(ar) == set(hw), (sorted(hw), sorted(ar))
    for name, doc in ar.items():
        assert doc["model"] == hw[name]["model"]
        assert doc.get("part_number") == hw[name].get("part_number")
        assert doc["slug"].startswith("arrcus-")
        assert doc["u_height"] == hw[name]["u_height"]
        assert "Arrcus lists Edgecore" in doc["comments"], doc["comments"][:200]


def test_a_listing_can_rename_and_renumber_a_configuration():
    """What DriveNets does: its own name for the metal, its own SKU for a build."""
    base = {"manufacturer": "UfiSpace", "model": "S9700-53DX-AC", "slug": "x",
            "part_number": "S9700-53DX-AC", "comments": "hw"}
    ls = {"ns": "drivenets", "manufacturer": "DriveNets", "nos": "dnos", "model": "NCP-40C",
          "configurations": {"ac": {"part-numbers": {"NCP-40C-AC": {"part": "DN-123"}}},
                             "dc": {"model": "NCP-40C DC"}}}
    ac = dx.apply_listing(dict(base), ls, "ac")
    assert (ac["manufacturer"], ac["model"], ac["part_number"]) == ("DriveNets", "NCP-40C-AC", "DN-123")
    assert ac["slug"] == "drivenets-ncp-40c-ac"
    assert "DriveNets also calls it: NCP-40C" in ac["comments"]
    dc = dx.apply_listing(dict(base), ls, "dc")
    assert dc["model"] == "NCP-40C DC" and dc["part_number"] == "S9700-53DX-AC"
    same = dx.apply_listing(dict(base), ls, "other")
    assert same["model"] == "S9700-53DX-AC", "no override keeps the hardware's SKU"


def test_two_types_written_to_one_file_stop_the_run(tmp_path):
    """Two listings that export one model would keep the second silently."""
    dx.WRITTEN.clear()
    doc = {"manufacturer": "DriveNets", "model": "NCP-40C"}
    dx.write(dict(doc), tmp_path, "netbox", "drivenets/s9700-53dx:ac")
    dx.write(dict(doc), tmp_path, "netbox", "drivenets/s9700-53dx:ac")   # same owner: fine
    with pytest.raises(SystemExit):
        dx.write(dict(doc), tmp_path, "netbox", "drivenets/cor550:ac")
    dx.WRITTEN.clear()


def test_a_neutral_document_names_ports_by_the_faceplate(tmp_path):
    """No NOS, no invented name: the id on the metal is the fact we have."""
    r = run(tmp_path, "--device", "as7726-32x")
    assert r.returncode == 0, r.stderr[-800:]
    neutral = [d for n, d in docs(tmp_path).items() if n.startswith("Edgecore/")]
    assert neutral, "the hardware vanished from under its own manufacturer"
    for doc in neutral:
        names = [i["name"] for i in doc["interfaces"]]
        assert [n for n in names if n.startswith("port-")] == [f"port-{i}" for i in range(1, 33)]
        assert not any(n.startswith("swp") or n.startswith("Ethernet") for n in names), names


def test_nos_is_no_longer_a_flag(tmp_path):
    """A listing exports because it exists; there is nothing to ask for."""
    r = run(tmp_path, "--device", "as7726-32x", "--nos", "arcos")
    assert r.returncode != 0 and "--nos" in r.stderr


def test_a_device_nobody_lists_gets_only_its_own_document(tmp_path):
    """No NOS vendor lists the S9501-18SMT in this library. Its export must be
    UfiSpace's alone - no NOS document invented for it."""
    listed = {v["hardware"] for v in json.loads((DIST / "listings.json").read_text())["listings"].values()}
    assert "ufispace/s9501-18smt" not in listed, "pick a device nobody lists"
    r = run(tmp_path, "--device", "s9501-18smt")
    assert r.returncode == 0, r.stderr[-800:]
    made = list(docs(tmp_path))
    assert made
    assert all(n.startswith("UfiSpace/") for n in made), made


def test_a_listing_with_no_port_names_exports_the_faceplate_ids(tmp_path):
    """Arrcus lists the S9510-28DC, and no document we hold says whether ArcOS
    numbers its ports from swp0 or swp1 - the listing records that as a gap.
    Its type is filed under Arrcus with the metal's own ids, not a guess."""
    r = run(tmp_path, "--device", "s9510-28dc")
    assert r.returncode == 0, r.stderr[-800:]
    made = docs(tmp_path)
    ar = {n.split("/", 1)[1]: d for n, d in made.items() if n.startswith("Arrcus/")}
    hw = {n.split("/", 1)[1]: d for n, d in made.items() if n.startswith("UfiSpace/")}
    assert ar and set(ar) == set(hw), (sorted(ar), sorted(hw))
    for name, doc in ar.items():
        assert [i["name"] for i in doc["interfaces"]] == [i["name"] for i in hw[name]["interfaces"]]
        assert not any(i["name"].startswith("swp") for i in doc["interfaces"])
