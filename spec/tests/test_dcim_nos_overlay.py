"""The exporter names interfaces from the overlay, and only from the overlay.

`nos_name()` hardcoded arcos as swp{n}/ma1 and sonic as Ethernet{(n-1)*4} in
Python, while the ArcOS overlay already stated the rule as data - with breakout
modes the Python never read. Nothing joined the two, so a renamed interface in
the overlay left the exporter emitting the old name, and `--nos sonic` wrote
144 device types for a NOS nothing in the library describes (#63, #56).

Now the overlay's `interfaces:` rules are the only source of a NOS name. A
device with no overlay for a NOS exports no document for it; a `--nos` that no
overlay anywhere declares is refused; and a NOS-neutral document names its
ports by the id on the faceplate, which is a fact about the metal.
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

pytestmark = pytest.mark.skipif(not (DIST / "overlays.json").exists(),
                                reason="library/dist not built")


# ---- the rules, expanded ----------------------------------------------------

ARCOS = {"interfaces": [
    {"physical": "port-{n}", "name": "swp{n}", "range": "1-32",
     "breakout": {"modes": ["4x25g", "4x10g"], "child-name": "swp{n}s{i}"}},
    {"physical": "mgmt-eth", "name": "ma1"},
]}


def test_a_ranged_rule_expands_over_its_range():
    names = dx.overlay_names(ARCOS)
    assert names["port-1"][0] == "swp1"
    assert names["port-32"][0] == "swp32"
    assert "port-33" not in names
    assert names["mgmt-eth"][0] == "ma1"


def test_the_name_pattern_may_do_arithmetic_over_n():
    """The schema's own example: SONiC counts lanes, `Ethernet{(n-1)*4}`."""
    names = dx.overlay_names({"interfaces": [
        {"physical": "port-{n}", "name": "Ethernet{(n-1)*4}", "range": "1-3"}]})
    assert [names[f"port-{n}"][0] for n in (1, 2, 3)] == ["Ethernet0", "Ethernet4", "Ethernet8"]


def test_a_name_pattern_is_arithmetic_and_nothing_else():
    with pytest.raises(SystemExit):
        dx.overlay_names({"interfaces": [
            {"physical": "port-{n}", "name": "{__import__('os').getcwd()}", "range": "1-1"}]})


def test_a_ranged_physical_needs_a_range():
    with pytest.raises(SystemExit):
        dx.overlay_names({"interfaces": [{"physical": "port-{n}", "name": "swp{n}"}]})


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


def test_the_arcos_export_says_what_the_overlay_says(tmp_path):
    r = run(tmp_path, "--device", "as7726-32x", "--nos", "arcos")
    assert r.returncode == 0, r.stderr[-800:]
    ov = json.loads((DIST / "overlays.json").read_text())["overlays"]["edgecore/as7726-32x"]["arcos"]
    want = dx.overlay_names(ov)
    arcos = [d for n, d in docs(tmp_path).items() if n.startswith("Arrcus/")]
    assert arcos, "no ArcOS document filed under Arrcus"
    for doc in arcos:
        names = [i["name"] for i in doc["interfaces"]]
        assert set(names) <= {v[0] for v in want.values()}, set(names) - {v[0] for v in want.values()}
        assert "ma1" in names, "the overlay names mgmt-eth ma1 and the export does not"
        assert [n for n in names if n.startswith("swp")] == [f"swp{i}" for i in range(1, 33)]
        ma1 = next(i for i in doc["interfaces"] if i["name"] == "ma1")
        assert ma1.get("mgmt_only") is True
        swp7 = next(i for i in doc["interfaces"] if i["name"] == "swp7")
        assert "4x25g" in swp7.get("description", ""), swp7


def test_a_neutral_document_names_ports_by_the_faceplate(tmp_path):
    """No NOS, no invented name: the id on the metal is the fact we have."""
    r = run(tmp_path, "--device", "as7726-32x", "--nos", "arcos")
    assert r.returncode == 0, r.stderr[-800:]
    neutral = [d for n, d in docs(tmp_path).items() if n.startswith("Edgecore/")]
    assert neutral, "the hardware vanished from under its own manufacturer"
    for doc in neutral:
        names = [i["name"] for i in doc["interfaces"]]
        assert [n for n in names if n.startswith("port-")] == [f"port-{i}" for i in range(1, 33)]
        assert not any(n.startswith("swp") or n.startswith("Ethernet") for n in names), names


def test_a_nos_no_overlay_declares_is_refused(tmp_path):
    r = run(tmp_path, "--device", "as7726-32x", "--nos", "sonic")
    assert r.returncode != 0
    assert "sonic" in (r.stderr + r.stdout)
    assert "overlay" in (r.stderr + r.stdout)
    assert not list(tmp_path.rglob("*.yaml")), "it refused and wrote anyway"


def test_a_device_without_the_overlay_gets_no_document_for_that_nos(tmp_path):
    """UfiSpace runs no ArcOS in this library. Asking for arcos across the
    build must not invent one for it - only the neutral type is written."""
    r = run(tmp_path, "--device", "s9510-28dc", "--nos", "arcos")
    assert r.returncode == 0, r.stderr[-800:]
    made = list(docs(tmp_path))
    assert made
    assert not any("arcos" in n.lower() for n in made), made
