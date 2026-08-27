"""The vendor registry: who made this, who owns it now, who wrote the software."""
import os
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

REG = yaml.safe_load((ROOT / "spec" / "schemas" / "vendors.yaml").read_text())
VENDORS = REG["vendors"]
NAMESPACES = REG["namespaces"]


def test_every_library_namespace_is_declared():
    """A namespace with no entry breaks resolution silently, which is how the
    gap arrived: a vendor is added during intake and the lineage is known to
    whoever staged it that week and never written down."""
    dirs = set()
    for base in ("components", "devices"):
        d = ROOT / "library" / base
        dirs |= {c.name for c in d.iterdir() if c.is_dir()}
    missing = sorted(dirs - set(VENDORS) - set(NAMESPACES))
    assert not missing, f"no registry entry for {missing}"


def test_lineage_points_at_real_vendors():
    for slug, v in VENDORS.items():
        for key in ("successor", "parent"):
            if v.get(key):
                assert v[key] in VENDORS, f"{slug}.{key} -> {v[key]} is not a vendor"
        for brand in (v.get("brands") or []):
            assert brand in VENDORS, f"{slug}.brands -> {brand} is not a vendor"


def test_every_vendor_says_where_it_came_from():
    """A corporate lineage claim is a fact about the world and it decays, so the
    next reader needs to know whether it came from a live device or a memory."""
    for slug, v in VENDORS.items():
        assert str(v.get("source") or "").strip(), f"{slug} states no source"


def test_every_vendor_declares_a_role():
    """`role` is what lets a NOS vendor be named by an overlay without being
    confused for the company that made the metal."""
    for slug, v in VENDORS.items():
        assert v.get("role") in ("hardware", "software", "both"), \
            f"{slug} has role {v.get('role')!r}"


def test_lineage_does_not_loop():
    for slug in VENDORS:
        seen, cur = {slug}, VENDORS[slug].get("successor")
        while cur:
            assert cur not in seen, f"successor loop through {slug}"
            seen.add(cur)
            cur = (VENDORS.get(cur) or {}).get("successor")


def test_a_software_vendor_is_not_a_successor_of_a_hardware_one():
    """Disaggregation is not lineage. The company that wrote the NOS did not
    buy the company that made the metal, and modelling it as `successor` would
    make a search for the hardware vendor return a software house."""
    for slug, v in VENDORS.items():
        succ = VENDORS.get(v.get("successor") or "")
        if succ:
            assert not (v.get("role") == "hardware" and succ.get("role") == "software"), \
                f"{slug} claims a software vendor as its successor"


def test_reserved_namespaces_are_not_vendors():
    for ns in NAMESPACES:
        assert ns not in VENDORS, f"{ns} is both a namespace and a vendor"


def test_the_arcos_claim_is_backed_by_the_dump_it_cites():
    """The registry says the running device names both companies. Check it does."""
    dump = ROOT / "library/devices/edgecore/as7726-32x/dumps/arcos-show-version.txt"
    text = dump.read_text()
    assert "Arrcus ArcOS" in text
    assert "EdgeCore" in text
    assert VENDORS["arrcus"]["role"] == "software"
    assert "arcos" in VENDORS["arrcus"]["products"]


def test_the_accton_claim_is_backed_by_the_dump_it_cites():
    dump = ROOT / "library/devices/edgecore/as7726-32x/dumps/arcos-openconfig-components.json"
    text = dump.read_text()
    assert "Accton" in text and "accton_as7726_32x" in text
    assert VENDORS["edgecore"]["parent"] == "accton"
