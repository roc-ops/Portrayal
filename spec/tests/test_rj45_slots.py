"""RJ45 jacks accept the RJ45 plug (#610).

generic/rj45-plug@1 `mates: rj45` and std/rj45@2 presents `interface: rj45`, so
the two always matched on paper. What was missing was the registry entry that
makes a presented interface a SLOT (spec/schemas/connectors.yaml): without
`rj45` there, no jack in the library published a slot, the kit had nowhere to
swap a plug in, and a copper cable could only leave from the jack's bare point.

The second half is the wrapper census. The slot code looks through ONE wrapper
to the aperture inside it, and dell/rj45-port-14g@1 wraps a wrapper, so its four
NDC ports stayed shut after the registry line alone. Every port component that
composes an RJ45 jack at any depth must present `rj45` itself.

These run against the real library and a components.json built here by the
indexer, never a fixture and never a possibly stale dist.
"""
import functools
import json
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import render as render_mod
from portrayal.manifest import presented_interface

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INDEXER = ROOT / "spec/tools/portrayal/components_index.py"
PLUG = "generic/rj45-plug@1"
JACKS = ("std/rj45", "std/rj45-ganged")


@pytest.fixture(scope="module")
def lib():
    return render_mod.Library([str(LIB)])


@pytest.fixture(scope="module")
def comps(tmp_path_factory):
    out = tmp_path_factory.mktemp("components")
    r = warmrender.run([sys.executable, str(INDEXER), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((out / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def test_rj45_is_a_connector_and_its_standard_exists():
    reg = render_mod._connector_registry()
    assert "rj45" in reg
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    assert reg["rj45"]["standard"] in std["standards"], reg["rj45"]


def _card_slot(comps, ref, cage):
    return next((c for c in comps[ref].get("cages") or [] if c["id"] == cage), None)


# The card ports #610 names: the Dell NDC's four and the RSP880's two management
# jacks. Both cards reach their jacks through wrappers, which is the case that
# needed more than the registry line.
@pytest.mark.parametrize("ref,cage", [
    ("dell/ndc-4x-rj45-14g@1", "port-1"),
    ("dell/ndc-4x-rj45-14g@1", "port-4"),
    ("cisco/a9k-rsp880-se@2", "mgt-lan-0"),
    ("cisco/a9k-rsp880-se@2", "mgt-lan-1"),
])
def test_a_named_card_port_accepts_the_plug(comps, ref, cage):
    slot = _card_slot(comps, ref, cage)
    assert slot is not None, f"{ref} publishes no slot {cage}"
    assert (slot["kind"], slot["interface"]) == ("connector", "rj45"), slot
    assert PLUG in slot["accepts"], slot["accepts"]
    assert not any("boot" in r for r in slot["accepts"]), "a boot mates the plug, not the jack"


def test_the_dell_jack_is_one_opening_not_two(comps):
    """dell/rj45-port-14g@1 now presents `rj45` itself, so - like a duplex LC
    adapter over its bores - its composed common/rj45-eth@1 is ALSO published,
    as the part's own `port`. What keeps that from being a second place to seat
    a plug is the host's `bores`: the kit drops a nested slot its host does not
    list there (swap.js nestedSlots), so an NDC port offering none is one level."""
    inner = _card_slot(comps, "dell/rj45-port-14g@1", "port")
    assert inner is not None and inner["interface"] == "rj45"
    for n in range(1, 5):
        assert _card_slot(comps, "dell/ndc-4x-rj45-14g@1", f"port-{n}")["bores"] == []


def _placement(dev, pid):
    d = yaml.safe_load((LIB / "devices" / dev / "device.yaml").read_text())
    for v in (d.get("views") or {}).values():
        for p in ((v or {}).get("components") or {}).get("placements") or []:
            if p.get("id") == pid:
                return p, (d.get("groups") or {}).get(p.get("group"))
    raise AssertionError(f"{dev} has no placement {pid}")


# The device ports #610 names, for the portrayal-site patching stage.
@pytest.mark.parametrize("dev,pid", [
    ("edgecore/eps201", "port-1"),
    ("edgecore/eps201", "port-48"),
    ("edgecore/eps201", "mgmt"),
    ("edgecore/as7726-32x", "mgmt-eth"),
    ("dell/r740xd", "idrac9"),
])
def test_a_named_device_port_accepts_the_plug(lib, dev, pid):
    p, group = _placement(dev, pid)
    slot = render_mod.slot_entry(p, lib, render_mod._pluggable_families(),
                                 render_mod._connector_registry(),
                                 render_mod._pluggable_candidates([str(LIB)]),
                                 group=group)
    assert slot is not None, f"{dev}:{pid} is not a slot"
    assert (slot["kind"], slot["interface"]) == ("connector", "rj45"), slot
    assert PLUG in slot["accepts"], slot["accepts"]


def test_every_port_that_composes_an_rj45_jack_presents_rj45(lib):
    """THE CENSUS THAT WOULD HAVE CAUGHT THE DELL PART. A port component that
    reaches std/rj45 or std/rj45-ganged at any depth is a jack, and a jack a
    plug cannot find is a jack nobody can cable. presented_interface looks
    through one wrapper, so a wrapper of a wrapper has to say `rj45` itself."""
    def resolve(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None

    @functools.lru_cache(None)
    def reaches(ref, depth=0):
        if ref.split("@")[0] in JACKS:
            return True
        c = resolve(ref)
        return depth < 6 and c is not None and any(
            reaches(p["ref"], depth + 1) for p in c.get("parts") or [] if p.get("ref"))

    jacks, shut = [], []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        if c.get("kind") != "component" or c.get("class") != "port" or c.get("mates"):
            continue
        ns, name, v = f.parent.relative_to(LIB / "components").parts
        ref = f"{ns}/{name}@{v[1:]}"
        if not reaches(ref):
            continue
        jacks.append(ref)
        if presented_interface(c, resolve)[0] != "rj45":
            shut.append(ref)
    # the two std apertures and at least the three wrappers #610 was measured on
    assert len(jacks) >= 5, jacks
    assert shut == [], f"these compose an RJ45 jack a plug cannot reach: {shut}"
