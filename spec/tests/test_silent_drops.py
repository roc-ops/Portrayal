"""Failure by omission: a part that exports nothing, and nothing says a word.

#251 found two defects of one shape on one day, and only because somebody read
an output and asked whether the number was right. An id-prefix test dropped 271
ports across 13 devices; a type table with no 800G row dropped 773 more. Neither
raised anything. A 76-port router exporting an empty interface list and a device
with no ports produce the SAME DOCUMENT, and every gate passed on both for as
long as the exporter had existed.

That is the asymmetry this file exists to close. The library's other guards all
protect against saying something FALSE - lint, the lock, the provenance
vocabulary. None of them protects against saying NOTHING, because nothing is not
a claim and there is no rule to break.

So the test is a census with a register beside it. Every part the library calls
`class: port` or `class: inlet` is asked whether ANY of its placements, anywhere,
reaches either export. Those that never do must be named in
`dcim_export.NOT_A_DCIM_PORT` with a reason. A new form factor that types
nowhere then fails here, on the day it lands, instead of being discovered by
somebody counting ports in a datasheet two releases later.

The register is held tight from both ends: an unnamed silent part fails, and so
does a register entry for a part that has since started exporting. Ten of the
reasons say "upstream has no type for this", which is a perfectly good reason -
and a completely different one from "nobody noticed".
"""
import collections
import functools
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import dcim_export as dx        # noqa: E402
import lint                     # noqa: E402
from faces import face_ref                  # noqa: E402
from manifest import load_yaml, view_parts   # noqa: E402

# `port` is a connector on a faceplate; `inlet` is power entry. Both are things a
# DCIM has somewhere to put, which is what makes their silence worth auditing.
# Every other class - led, mechanical, riser, filter, bezel, button - is
# furniture no schema has a field for, and dropping it is not a defect.
PORT_CLASSES = {"port", "inlet"}


@functools.lru_cache(maxsize=1)
def _contracts():
    """Every component contract, parsed once: ref -> the whole document."""
    out = {}
    for cf in sorted(LIB.glob("components/*/*/*/contract.yaml")):
        d = yaml.safe_load(cf.read_text()) or {}
        ref = f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"
        # Several majors of one part share a ref here on purpose: the question
        # is whether the exporter has anything to say about the PART, and it
        # keys all but FAMILY_PART without the version.
        cur = out.get(ref)
        if cur is None or str(d.get("version") or "") > str(cur.get("version") or ""):
            out[ref] = d
    return out


def _module_exports(part, attrs, fibre):
    """Does build_module emit anything for this part? Mirrors its branch chain.

    `fibre` is build_module's OTHER exit, and leaving it out of the mirror is
    how the first draft of this file accused four MPO adapters that export
    perfectly well: a module with a declared rear face and optical paths emits
    its whole fibre list through `optical_ports`, never touching the branch
    chain below. Gated exactly as build_module gates it, so a single-faced
    module - a PPM coupler, whose paths run front-to-front - stays silent here
    because it is silent there, which is the decision optical-paths-design.md
    C3 records rather than an oversight.
    """
    full_ref = part["ref"]
    ref = full_ref.split("@")[0]
    if ref in dx.PART_SKIP:
        return False
    if dx.placed_type(part):
        return True
    if full_ref in dx.FAMILY_PART:
        return True
    if ref in dx.PART_POWER or ref in dx.PART_CONSOLE or ref in dx.PART_RF:
        return True
    if ref in dx.PART_IFACE:
        return dx.cage_type(ref, attrs) is not None
    return bool(fibre)


@functools.lru_cache(maxsize=1)
def _census():
    """ref -> (placements seen, placements that reach an export).

    Walks the library rather than a build, so the suite does not need one. Both
    passes are counted: a part can be silent on a card and heard on a chassis,
    and only a part silent on BOTH is a silence worth a register entry.
    """
    seen, heard = collections.Counter(), collections.Counter()

    for doc in _contracts().values():
        # MODULES ONLY, because build_module walks module contracts and nothing
        # else. A port-class part placed inside ANOTHER component is a composed
        # shell, not a port on a faceplate - `common/db9-receptacle` composes
        # `std/db9` for its shell and `common/mpo-adapter` composes `std/mpo`
        # for its bore. Counting those accused three parts that are never
        # placed on a card at all.
        if doc.get("kind") != "module":
            continue
        attrs = doc.get("attrs") or {}
        fibre = bool(face_ref(doc, "rear") and (doc.get("optical") or {}).get("paths"))
        for part in (doc.get("parts") or []):
            if not isinstance(part, dict) or "ref" not in part:
                continue
            r = part["ref"].split("@")[0]
            seen[r] += 1
            if _module_exports(part, attrs, fibre):
                heard[r] += 1

    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        groups = dev.get("groups") or {}
        for cfg in (dev.get("configurations") or {"default": {}}):
            for view in dx.views_for(dev, cfg):
                for pl in dx.scoped(view_parts(view)["placements"], cfg):
                    r = pl["ref"].split("@")[0]
                    seen[r] += 1
                    # BOTH OF build's EXITS. It grew a power path in #286, and
                    # a mirror that knows about only one of a tool's exits is
                    # the mistake this whole file is about: with `iface_type`
                    # alone, `common/dc-barrel` read as silent on the very
                    # commit that made it export.
                    if r in dx.PART_POWER:
                        heard[r] += 1
                        continue
                    g = groups.get(pl.get("group")) or {}
                    a = {**(g.get("attrs") or {}), **(pl.get("attrs") or {})}
                    role = g.get("role")
                    if a.get("role") == "console" or role in dx.PORT_ROLES:
                        if dx.iface_type(pl, a, role) is not None:
                            heard[r] += 1
    return seen, heard


def _silent():
    """Port-class refs not one of whose placements reaches either export."""
    seen, heard = _census()
    cls = {r: d.get("class") for r, d in _contracts().items()}
    return {r: seen[r] for r in seen
            if cls.get(r) in PORT_CLASSES and not heard[r]}


# --- the register, held tight from both ends ---------------------------------

def test_every_silent_port_is_named():
    """THE GUARD. A port-class part that exports nothing, anywhere, must say why.

    This is the test the S9710-76D needed and did not have. Run against the
    exporter as it stood before this file, it names `std/cfp`, `std/cfp2` and
    `std/cxp` - twenty-four 100GbE ports on fourteen Juniper cards, absent for
    the same reason XFP was: a form factor whose name is nobody's substring.
    """
    silent = _silent()
    unnamed = {r: n for r, n in silent.items() if r not in dx.NOT_A_DCIM_PORT}
    assert not unnamed, (
        "port-class parts that export nothing and are not in NOT_A_DCIM_PORT:\n"
        + "\n".join(f"  {n:5d} placement(s)  {r}" for r, n in
                    sorted(unnamed.items(), key=lambda kv: -kv[1]))
        + "\n\nEither give it a row in one of the type tables, or add it to "
          "NOT_A_DCIM_PORT with the reason it has none.")


def test_the_register_carries_no_stale_entries():
    """A part that has started exporting must come OFF the register.

    Otherwise the register decays into a list of things that were once true,
    which is the failure mode of every hand-maintained exception list. #285 will
    take the three timing jacks off it; this is what makes that a test failure
    rather than something to remember.
    """
    silent = _silent()
    stale = sorted(r for r in dx.NOT_A_DCIM_PORT if r not in silent)
    assert not stale, (
        "these are in NOT_A_DCIM_PORT but now export something (or are no "
        f"longer placed): {stale}")


def test_every_register_entry_names_a_real_component():
    """A renamed part leaves a register entry pointing at nothing, and a register
    entry pointing at nothing silently stops covering the part it was written
    for - which is this file's own failure mode arriving one level up."""
    missing = sorted(r for r in dx.NOT_A_DCIM_PORT if r not in _contracts())
    assert not missing, f"NOT_A_DCIM_PORT names parts that do not exist: {missing}"


def test_every_register_entry_gives_a_reason():
    """A reason, not a shrug. Long enough to say WHY rather than to restate the
    part's name, which is what a one-word entry always turns out to be."""
    thin = {r: why for r, why in dx.NOT_A_DCIM_PORT.items() if len(why) < 40}
    assert not thin, f"register entries with no real reason: {thin}"


def test_the_census_is_not_vacuous():
    """A sweep over an empty collection passes exactly as quietly as the bug it
    exists to find - the lesson test_dcim_interfaces records at the end of its
    own sweep, and the reason that one counts its devices."""
    seen, heard = _census()
    cls = {r: d.get("class") for r, d in _contracts().items()}
    ports = [r for r in seen if cls.get(r) in PORT_CLASSES]
    assert len(ports) >= 30, f"only {len(ports)} port-class part(s) reached the census"
    assert sum(heard[r] for r in ports) >= 5000, "the heard side collapsed"


# --- the three families this sweep found -------------------------------------

@pytest.mark.parametrize("ref,expected", [
    ("std/cfp", "100gbase-x-cfp"),
    ("std/cfp2", "100gbase-x-cfp2"),
    ("std/cxp", "100gbase-x-cxp"),
])
def test_the_100g_form_factors_that_are_nobodys_substring(ref, expected):
    """CFP, CFP2 and CXP do not contain "sfp", so `iface_type`'s family test
    cannot see them and `PART_IFACE` has to name them. Every card carrying one
    says 100GbE in its own description; all three slugs ship in netbox and
    nautobot alike."""
    assert dx.PART_IFACE[ref] == expected
    assert dx.cage_type(ref, {}) == expected


def test_a_dc_supply_exports_its_inlet():
    """dell/psu-1100w-dc-14g exported no power port while its two AC siblings in
    the same family each exported theirs - and a supply with no power port reads
    as a supply drawn without an inlet."""
    assert dx.PART_POWER["dell/dc-terminal-6ryj9"] == "dc-terminal"


# --- the same shape, one table over ------------------------------------------

def test_every_pluggable_media_the_library_uses_is_a_pluggable_cage():
    """L40 asks a port group which optics run in it, and skips any group whose
    media is not in PLUGGABLE_CAGES. A pluggable cage missing from that set is
    therefore never asked, in silence - the identical shape one tool over.

    `sfp56` was missing: two groups on two devices escaped L40 entirely while
    `sfp`, `sfp-plus`, `sfp28` and `qsfp56` were all listed. The non-cages are
    named here rather than inferred, because "is this a pluggable cage?" is a
    fact about the hardware and not something a substring can answer.
    """
    not_a_cage = {
        None,           # a group that states no media
        "rj45",         # a fixed copper jack takes no module
        "fiber",        # bare glass in an adapter, not a cage
        "coax-smb",     # a timing connector
        "usb-c",        # power in, on the GL-8xEP
    }
    used = set()
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        for g in (dev.get("groups") or {}).values():
            g = g or {}
            if g.get("term") == "Port":
                used.add((g.get("attrs") or {}).get("media"))
    unasked = sorted(m for m in used - not_a_cage
                     if m not in lint.PLUGGABLE_CAGES) 
    assert not unasked, (
        f"port-group media L40 never asks about: {unasked}. Either add them to "
        "PLUGGABLE_CAGES or say here why they are not cages.")
