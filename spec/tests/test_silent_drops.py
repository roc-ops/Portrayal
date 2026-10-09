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

from portrayal import dcim_export as dx
from portrayal import lint
from portrayal.manifest import load_yaml, view_parts   # noqa: E402
from portrayal import libwalk
from portrayal import optical_ports

# `port` is a connector on a faceplate; `inlet` is power entry. Both are things a
# DCIM has somewhere to put, which is what makes their silence worth auditing.
# Every other class - led, mechanical, riser, filter, bezel, button - is
# furniture no schema has a field for, and dropping it is not a defect.
PORT_CLASSES = {"port", "inlet"}


@functools.lru_cache(maxsize=1)
def _contracts():
    """Every component contract, parsed once: ref -> the whole document."""
    out = {}
    for cf in libwalk.iter_components([LIB]):
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
    chain below. Gated exactly as build_module gates it -
    `optical_ports.projects`, a rear face or a stated `optical.trunk` - so the
    PPMs, which state a trunk since #246, are heard here because they export
    there.
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
    if ref in dx.USB_CONSOLE_REFS:                  # a USB console, as on a device
        return bool(dx.device_console_row(part, part.get("attrs") or {}))
    if ref in dx.PART_IFACE:
        return dx.cage_type(ref, attrs) is not None
    return bool(fibre)


def _device_exports(pl, ref, attrs, group_role):
    """EVERY ONE OF build's EXITS, and the list is the point.

    A mirror that knows about only some of a tool's exits is the mistake this
    whole file is about, and it has now been made twice on this function - both
    times caught here, on the commit that added the exit. #286's power path left
    `common/dc-barrel` reading as silent the moment it started exporting;
    #285's RF path did the same to the three timing jacks. Anything added to
    `build` belongs in this list on the same commit.
    """
    if ref in dx.PART_POWER:                        # power-ports
        return True
    if ref in dx.PART_OUTLET:                       # power-outlets (#806)
        return True
    if ref in dx.PART_RF:                          # RF and timing, as `other`
        return True
    if pl["ref"] in dx.FAMILY_PART and dx.rj45_timing_label({**pl, "attrs": attrs}):
        return True                                 # a bare RJ45 naming a timing job
    if dx.device_console_row(pl, attrs):            # console-ports, micro-USB too (#384)
        return True
    if attrs.get("role") == "console" or group_role in dx.PORT_ROLES:
        return dx.iface_type(pl, attrs, group_role) is not None   # interfaces
    return False


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
        fibre = optical_ports.projects(doc)
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
                    g = groups.get(pl.get("group")) or {}
                    a = {**(g.get("attrs") or {}), **(pl.get("attrs") or {})}
                    if _device_exports(pl, r, a, g.get("role")):
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


def test_an_outlet_part_is_not_also_registered_silent():
    """PART_OUTLET and the register share no ref (#806): a part that exports an
    outlet has something to say, and a reason for saying nothing would be
    false the day it was written."""
    both = sorted(set(dx.PART_OUTLET) & set(dx.NOT_A_DCIM_PORT))
    assert not both, f"in PART_OUTLET and NOT_A_DCIM_PORT: {both}"
    assert dx.PART_OUTLET, "no outlet part - the check measured nothing"


def test_every_register_entry_gives_a_reason():
    """A reason, not a shrug. Long enough to say WHY rather than to restate the
    part's name, which is what a one-word entry always turns out to be."""
    thin = {r: why for r, why in dx.NOT_A_DCIM_PORT.items() if len(why) < 40}
    assert not thin, f"register entries with no real reason: {thin}"


OPTICAL_NOTE = "Optical ports not exported: "


def _named_in(comments):
    """The ids `dcim_export.unexported_optical` wrote into a type's comments."""
    line = next((ln for ln in str(comments or "").split("\n")
                 if ln.startswith(OPTICAL_NOTE)), None)
    if line is None:
        return set()
    return set(line[len(OPTICAL_NOTE):].split(". ", 1)[0].split(", "))


def test_a_fibre_adapter_that_exports_nothing_is_named_in_its_types_comments():
    """#204, held as the register above holds a part: by NAME, per placement.

    Once the PPMs state a trunk, `common/lc-duplex-adapter` exports somewhere
    and leaves NOT_A_DCIM_PORT - and the census, which asks whether ANY
    placement of a part is heard, stops seeing the 117 on DCP chassis that
    still export nothing. So every fibre adapter on a device that is not an
    interface must be named in that device type's comments, and every one on a
    module whose glass does not project must be named in the module type's.
    """
    devices = modules = 0
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        cfgs = dev.get("configurations") or {"default": {}}
        for cfg_name, cfg in cfgs.items():
            fibre = {pl["id"] for view in dx.views_for(dev, cfg_name)
                     for pl in dx.scoped(view_parts(view)["placements"], cfg_name)
                     if optical_ports.family_of(pl["ref"])}
            if not fibre:
                continue
            doc = dx.build(dev, cfg_name, cfg, None)
            exported = {i["name"] for i in doc.get("interfaces") or []}
            missing = sorted(fibre - exported - _named_in(doc.get("comments")))
            assert not missing, f"{p.parent.name} ({cfg_name}): fibre adapters silent: {missing}"
            devices += 1
    for doc in _contracts().values():
        if doc.get("kind") != "module":
            continue
        fibre = {str(pt["id"]) for pt in doc.get("parts") or []
                 if isinstance(pt, dict) and optical_ports.family_of(pt.get("ref") or "")}
        if not fibre or optical_ports.projects(doc):
            continue
        built = dx.build_module(doc, "Vendor")
        typed = {i["name"] for i in built.get("interfaces") or []}
        missing = sorted(fibre - typed - _named_in(built.get("comments")))
        assert not missing, f"{doc.get('name')}: fibre adapters silent: {missing}"
        modules += 1
    # the three DCP chassis, and the A22 among the modules
    assert devices >= 3 and modules >= 1, (devices, modules)


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
    ("std/cfp4", "100gbase-x-cfp4"),
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
        "coax-bnc",     # a coax jack a cable plug seats in, not a module cage (the GL-12xB sync jacks)
        "usb-c",        # power in, on the GL-8xEP
        "db9",          # a D-sub alarm or serial connector (the 7750 SR-1 alarm port) takes no module
        "usb-a",        # a USB Type-A receptacle takes a USB device, not a transceiver (the DL160 Gen10's front and rear USB group)
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


def test_a_db9_that_is_a_console_exports_as_one():
    """common/db9-receptacle is in the register because it is mostly an alarm
    relay, and that silence swallowed the 7750 SF/CPM4's RS-232 Console, leaving
    its reserved AUX jack as the card's only console port. A placement that says
    `console` exports as `de-9`; aux, alarm, craft and monitoring D-subs do not."""
    load = lambda n: yaml.safe_load(
        (LIB / "components" / "nokia" / n / "v1" / "contract.yaml").read_text())
    for card in ("sfm4-12", "sfm4-7"):
        out = dx.build_module(load(card), "Nokia")
        assert {"name": "console", "type": "de-9"} in out["console-ports"], card
    cpm5 = dx.build_module(load("cpm5"), "Nokia")
    assert not any(c["type"] == "de-9" for c in cpm5.get("console-ports") or [])
    assert not dx.DB9_CONSOLE.search("aux mgmt"), "an AUX D-sub is not claimed"
    assert not dx.DB9_CONSOLE.search("craft remote craft port")


def test_a_dc_pem_exports_its_inlet():
    """The 7750 SR-7 and SR-12 DC PEM-3 are where the -48 V feed lands. Without
    `inlet:` they exported no power port, so a chassis assembled in a DCIM had no
    power input. nokia/sr-e-psu-dc is the precedent."""
    for pem in ("sr-12-pem-3", "sr-7-pem-3"):
        d = yaml.safe_load((LIB / "components" / "nokia" / pem / "v1"
                            / "contract.yaml").read_text())
        out = dx.build_module(d, "Nokia")
        assert out.get("power-ports") == [{"name": "Inlet", "type": "dc-terminal"}], pem


def test_the_m48_exports_every_port_behind_its_mrj21s():
    """An MRJ21 carries six 10/100/1000 ports. Registered as silent, it exported the
    Nokia 7750 M48-1GB-XP-TX - a 48-port card - with no interfaces at all. Each
    connector now lists its six in `interfaces:` (MDA-XP guide p44 key 4: connector 1
    = ports 1-6 ... connector 8 = ports 43-48), typed by the signal, 1000base-t."""
    assert "std/mrj21" not in dx.NOT_A_DCIM_PORT
    d = yaml.safe_load((LIB / "components" / "nokia" / "m48-1gb-xp-tx" / "v1"
                        / "contract.yaml").read_text())
    ifaces = dx.build_module(d, "Nokia")["interfaces"]
    assert [i["name"] for i in ifaces] == [f"port-{n}" for n in range(1, 49)]
    assert {i["type"] for i in ifaces} == {"1000base-t"}
    for target in ("netbox", "nautobot"):
        f = LIB / "exports" / target / "module-types" / "Nokia" / "M48-1GB-XP-TX.yaml"
        assert f.read_text().count("type: 1000base-t") == 48, target
