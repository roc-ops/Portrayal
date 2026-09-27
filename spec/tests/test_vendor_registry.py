"""The vendor registry: who made this, who owns it now, who wrote the software."""
import os
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

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


# ---- listings: the disaggregation case --------------------------------------

LISTINGS = sorted((ROOT / "library" / "devices").glob("*/*/listing.yaml"))


def test_every_listing_lives_under_a_software_vendor():
    """Filing a disaggregated box under a hardware brand is the thing a listing
    exists to avoid, so the namespace it lives in has to write software."""
    assert LISTINGS, "no listing in the library; this test proved nothing"
    for f in LISTINGS:
        ns = f.parent.parent.name
        v = VENDORS.get(ns)
        assert v, f"{ns}/{f.parent.name}: {ns} is not in the registry"
        assert v["role"] in ("software", "both"), f"{ns} has role {v['role']}"
        doc = yaml.safe_load(f.read_text()) or {}
        assert str(doc.get("source") or "").strip(), f"{ns}/{f.parent.name} states no source"


def test_a_listing_is_not_a_device():
    """A NOS vendor's namespace holds listings. A device.yaml there would be a
    second copy of the metal - the thing listings exist to avoid."""
    for slug, v in VENDORS.items():
        if v.get("role") != "software":
            continue
        d = ROOT / "library" / "devices" / slug
        if d.is_dir():
            assert not list(d.glob("*/device.yaml")), f"{slug} holds a device"


def test_the_four_nos_vendors_are_registered():
    """The whitebox NOSes the HCL work covers (#674, #515)."""
    for slug, product in (("arrcus", "arcos"), ("ipinfusion", "ocnos"),
                          ("drivenets", "dnos"), ("sonic", "sonic")):
        assert VENDORS[slug]["role"] in ("software", "both"), slug
        assert product in VENDORS[slug]["products"], slug
