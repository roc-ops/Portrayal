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


# ---- overlay identity: the disaggregation case -------------------------------

import importlib  # noqa: E402
dx = importlib.import_module("dcim_export")

OVERLAYS = sorted((ROOT / "library" / "devices").glob("*/*/overlays/*.yaml"))


def test_every_overlay_identity_names_a_software_vendor():
    """Filing a disaggregated SKU under a hardware brand is the thing the field
    exists to avoid, so the vendor it names has to write software."""
    for f in OVERLAYS:
        ident = (yaml.safe_load(f.read_text()) or {}).get("identity")
        if not ident:
            continue
        v = VENDORS.get(ident["vendor"])
        assert v, f"{f.name}: identity.vendor {ident['vendor']} is not in the registry"
        assert v["role"] in ("software", "both"), \
            f"{f.name}: identity.vendor {ident['vendor']} has role {v['role']}"
        assert str(ident.get("source") or "").strip(), f"{f.name}: identity states no source"


def test_the_model_placeholder_expands_to_the_hardware_sku():
    doc = {"manufacturer": "Edgecore", "model": "7726-32X-O-AC-F", "part_number": "X"}
    out = dx.apply_identity(dict(doc),
                            {"vendor": "arrcus", "model": "ArcOS on {model}", "source": "s"},
                            VENDORS)
    assert out["manufacturer"] == "Arrcus"
    assert out["model"] == "ArcOS on 7726-32X-O-AC-F"
    assert out["slug"] == "arrcus-arcos-on-7726-32x-o-ac-f"


def test_four_hardware_skus_do_not_collapse_onto_one_name():
    """One device can be four orderable things. A NOS identity naming none of
    them would write four documents to one filename and keep the last."""
    names = set()
    for sku in ("7726-32X-O-AC-F", "7726-32X-O-AC-B", "7726-32X-O-48V-F", "7726-32X-O-48V-B"):
        out = dx.apply_identity({"manufacturer": "Edgecore", "model": sku},
                                {"vendor": "arrcus", "model": "ArcOS on {model}", "source": "s"},
                                VENDORS)
        names.add(out["slug"])
    assert len(names) == 4


def test_a_model_without_the_placeholder_still_does_not_collide():
    """The fallback appends the hardware model rather than losing a document."""
    a = dx.apply_identity({"manufacturer": "E", "model": "SKU-A"},
                          {"vendor": "arrcus", "model": "ArcOS", "source": "s"}, VENDORS)
    b = dx.apply_identity({"manufacturer": "E", "model": "SKU-B"},
                          {"vendor": "arrcus", "model": "ArcOS", "source": "s"}, VENDORS)
    assert a["slug"] != b["slug"]


def test_the_hardware_part_number_is_not_attributed_to_the_software_vendor():
    out = dx.apply_identity({"manufacturer": "Edgecore", "model": "M", "part_number": "7726-X"},
                            {"vendor": "arrcus", "model": "ArcOS on {model}", "source": "s"},
                            VENDORS)
    assert "part_number" not in out


def test_no_identity_leaves_the_document_alone():
    doc = {"manufacturer": "Edgecore", "model": "M", "slug": "edgecore-m", "part_number": "P"}
    assert dx.apply_identity(dict(doc), None, VENDORS) == doc
