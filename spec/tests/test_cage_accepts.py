"""`cages[]` in `<device>.configs.json`: what the library could seat, derived.

A device's compiled index gains one entry per placement that presents a
pluggable interface, each carrying an `accepts` list computed from THREE
inputs that have each been wrong in this project before: a part's `mates`, a
wrapper's presented interface (`manifest.presented_interface`), and a port
group's declared `media`. Nothing consumes this list until spec C2 - the same
shape spec B1 shipped a kit accessor in, tested only against hand-built
fakes, where a latent defect survived until B2 became its first real
consumer (docs/... the C1 plan says so directly). These tests are what stands
in for that consumer here, so they run against the REAL library and REAL
built `configs.json`, never a fixture.

THE THREE DEVICES ARE PICKED BY CHECKING THEIR DECLARED MEDIA, not by
trusting a name - that assumption has been wrong repeatedly on this project
(docs/visio-stencils-are-simplifications.md is the same lesson one level
down, about a datasheet instead of a device name):

  - edgecore/csr310, placement `m1-0`: `groups.sfp28.attrs.media == sfp28`,
    ref `std/sfp-ganged@1`, which presents interface `sfp` - the `sfp` family
    on the ladder, ceiling `sfp28`.
  - edgecore/dcs510, placement `port-1`: `groups.qsfpdd-400g.attrs.media ==
    qsfp-dd`, ref `std/qsfp-dd@1`, interface `qsfp-dd` - the ONLY case in this
    library that exercises `also-accepts` (`qsfp-dd` also-accepts `qsfp`).
  - edgecore/ais800-32o, placement `port-1`: `groups.osfp800.attrs.media ==
    osfp`, ref `std/osfp@1`, interface `osfp` - one of four families (osfp,
    xfp, cfp, cfp2) with a cage in the library and no component that mates
    it, so its accept list is legitimately `[]`.

Checked directly, once, in `spec/tools/portrayal/render.py`:

    grep -n "ref: std/sfp-ganged@1" library/devices/edgecore/csr310/device.yaml
    grep -n "ref: std/qsfp-dd@1" library/devices/edgecore/dcs510/device.yaml
    grep -n "ref: std/osfp@1" library/devices/edgecore/ais800-32o/device.yaml

all resolve to placements inside a `groups:` entry carrying the media named
above.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"

from portrayal import render as render_mod

CSR310 = LIB / "devices/edgecore/csr310/device.yaml"
DCS510 = LIB / "devices/edgecore/dcs510/device.yaml"
AIS800_32O = LIB / "devices/edgecore/ais800-32o/device.yaml"


def _build(device_yaml, tmp_path):
    r = subprocess.run([sys.executable, str(RENDER), str(device_yaml),
                        "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    name = yaml.safe_load(device_yaml.read_text())["name"]
    return json.loads((tmp_path / f"{name}.configs.json").read_text())


def _cage(idx, view, cage_id):
    return next(c for c in idx["cages"][view] if c["id"] == cage_id)


# --- the three real cages ------------------------------------------------

def test_an_sfp28_cage_accepts_exactly_the_two_sfp_generics(tmp_path):
    idx = _build(CSR310, tmp_path)
    cage = _cage(idx, "front", "m1-0")
    assert cage["interface"] == "sfp"
    assert cage["media"] == "sfp28"
    assert cage["group"] == "sfp28"
    # ORDER IS PART OF THE CONTRACT - generics first, alphabetical - so a
    # wrong-but-nonempty list (the failure mode an unordered `set()` compare
    # would hide) fails loudly here.
    assert cage["accepts"] == ["generic/sfp-lc-simplex@1", "generic/sfp-lc@1"]


def test_a_qsfp_dd_cage_accepts_its_own_generic_and_the_also_accepted_qsfp_one(tmp_path):
    """The ONLY case in this library exercising `also-accepts`:
    `generic/qsfp-lc@1` (`mates: qsfp`) reaches this cage through
    `qsfp-dd`'s `also-accepts: [qsfp]`, not through its own family. If
    `also-accepts` were silently dropped, this list would still be
    non-empty (`generic/qsfp-dd-lc@1` alone) - an easy defect to miss without
    an exact-list assertion, which is why this checks both members and the
    order together rather than membership alone."""
    idx = _build(DCS510, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "qsfp-dd"
    assert cage["media"] == "qsfp-dd"
    assert cage["group"] == "qsfpdd-400g"
    assert cage["accepts"] == ["generic/qsfp-dd-lc@1", "generic/qsfp-lc@1"]


def test_an_osfp_cage_accepts_nothing_but_says_so_explicitly(tmp_path):
    """Four families - osfp, xfp, cfp, cfp2 - have a cage in the library and
    no component that mates one. `[]`, EMPTY, NOT ABSENT: a consumer has to
    be able to tell "the library offers nothing here" from "this placement
    is not a cage at all", and those are different facts only if the key is
    always present."""
    idx = _build(AIS800_32O, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "osfp"
    assert "accepts" in cage
    assert cage["accepts"] == []


def test_a_cage_entry_carries_the_documented_shape(tmp_path):
    idx = _build(CSR310, tmp_path)
    cage = _cage(idx, "front", "m1-0")
    assert set(cage) == {"id", "at", "interface", "media", "group", "rel-pos",
                          "rotate", "accepts", "occupant"}
    assert cage["rel-pos"] == 0
    assert cage["rotate"] is None
    # AFTER SPEC A NO SHIPPED DEVICE SEATS ONE - this is the honest value for
    # every real device today, and is checked as a fact about the corpus
    # below rather than assumed here.
    assert cage["occupant"] is None


def test_a_group_with_no_media_has_no_ceiling(tmp_path):
    """`media` is the port GROUP's declared media - the cage's ceiling on its
    family's ladder. A group with no `media` declares none, so the cage
    accepts every rate of its family rather than nothing: checked on a copy
    of csr310 with `groups.sfp28.attrs.media` removed. The accept list is
    unchanged from the media-bearing case (nothing in the library declares a
    rate yet, so no ceiling has anything to exclude either way) - what this
    proves is that a missing `media` reads as `None` and does not make the
    derivation empty or raise, which a `.get("media")` typo could do
    silently."""
    dev = tmp_path / "src" / "csr310" / "device.yaml"
    shutil.copytree(CSR310.parent, dev.parent)
    d = yaml.safe_load(dev.read_text())
    del d["groups"]["sfp28"]["attrs"]["media"]
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))

    idx = _build(dev, tmp_path / "out")
    cage = _cage(idx, "front", "m1-0")
    assert cage["group"] == "sfp28"
    assert cage["media"] is None
    assert cage["accepts"] == ["generic/sfp-lc-simplex@1", "generic/sfp-lc@1"]


# --- the configured occupant, read from the manifest, not hardcoded ------

SFP_SRC = LIB / "devices/ufispace/s9510-28dc"


def test_the_configured_occupant_is_read_from_the_default_configuration(tmp_path):
    """No shipped device seats one (spec A), so this is the one place the
    field is proven live rather than merely absent everywhere: a real device,
    copied to a scratch path and given a real `occupants:` entry in its
    DEFAULT configuration (`dc`, `default: true`) - the same idiom
    test_occupants.py uses, because the library ships no fitted device by
    policy (docs/pluggables-design.md decision 2) and a corpus other tests
    read is not a scratch pad."""
    dev = tmp_path / "src" / "s9510-28dc" / "device.yaml"
    shutil.copytree(SFP_SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    assert d["configurations"]["dc"].get("default") is True
    d["configurations"]["dc"]["occupants"] = {"port-4": "generic/sfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))

    idx = _build(dev, tmp_path / "out")
    seated = _cage(idx, "front", "port-4")
    empty = _cage(idx, "front", "port-5")
    assert seated["occupant"] == "generic/sfp-lc@1"
    assert empty["occupant"] is None


def test_no_shipped_device_seats_an_occupant():
    """The corpus-wide fact `test_a_cage_entry_carries_the_documented_shape`
    pins one example of: after spec A, `occupants:` is empty on every
    configuration this library ships (docs/pluggables-design.md decision 2)."""
    seated = []
    for man in LIB.glob("devices/*/*/device.yaml"):
        d = yaml.safe_load(man.read_text())
        for name, cfg in (d.get("configurations") or {}).items():
            if (cfg or {}).get("occupants"):
                seated.append(f"{man.parent.name}:{name}")
    assert not seated, seated


# --- what never reaches an accept list, checked directly against the whole
# library rather than one device at a time - the corpus B1's kit accessor
# did not have, and the reason its defect survived to B2. ----------------

def test_superseded_parts_are_real_but_excluded_from_every_candidate_pool():
    """`common/sfp-lc-duplex@1` and `common/qsfp-transceiver@1` are not
    hypothetical - they are real, live contracts in this library, checked
    here so the exclusion below is not vacuous (the exact failure mode a
    silently-empty `iter_components` walk would produce)."""
    dup = yaml.safe_load((LIB / "components/common/sfp-lc-duplex/v1/contract.yaml").read_text())
    assert dup["mates"] == "sfp" and dup.get("superseded-by") == "generic/sfp-lc@1"
    qxc = yaml.safe_load((LIB / "components/common/qsfp-transceiver/v1/contract.yaml").read_text())
    assert qxc["mates"] == "qsfp" and qxc.get("superseded-by") == "generic/qsfp-lc@1"

    candidates = render_mod._pluggable_candidates([LIB])
    all_refs = {ref for entries in candidates.values() for ref, _c in entries}
    assert "common/sfp-lc-duplex@1" not in all_refs
    assert "common/qsfp-transceiver@1" not in all_refs
    # NOT VACUOUS the other way either: real, live candidates for the same two
    # interfaces ARE in the pool, so the exclusion is `superseded-by` at work
    # and not an empty table passing every check by having nothing to check.
    assert any(ref == "generic/sfp-lc@1" for ref, _c in candidates.get("sfp", []))
    assert any(ref == "generic/qsfp-lc@1" for ref, _c in candidates.get("qsfp", []))


def test_a_boot_never_reaches_an_accept_list():
    """`common/lc-boot@1` (`mates: lc-plug`) and `common/rj45-boot@1`
    (`mates: rj45-plug`) pass `behaviour: occupies` and carry no
    `superseded-by` - they are real candidates in the pool, exactly like a
    transceiver. The ONLY reason neither ever seats in a cage is that
    `lc-plug`/`rj45-plug` name no family's `interface` in
    spec/schemas/pluggables.yaml, so no cage's derivation can ever draw from
    either bucket - checked directly against the registry rather than by
    grepping every device's rendered `accepts` list for the two refs."""
    candidates = render_mod._pluggable_candidates([LIB])
    assert any(ref == "common/lc-boot@1" for ref, _c in candidates.get("lc-plug", []))
    assert any(ref == "common/rj45-boot@1" for ref, _c in candidates.get("rj45-plug", []))

    families = render_mod._pluggable_families()
    family_interfaces = {fam["interface"] for fam in families.values()}
    assert "lc-plug" not in family_interfaces
    assert "rj45-plug" not in family_interfaces


def test_the_registry_load_is_not_vacuous():
    """A registry that failed to parse would pass every check above by
    having nothing to check - test_pluggable_ladder.py's own vacuity test,
    one file over, for the same reason."""
    families = render_mod._pluggable_families()
    assert len(families) >= 8
    assert render_mod._family_by_interface(families, "sfp")[0] == "sfp"
    assert render_mod._family_by_interface(families, "not-a-real-interface") is None


# --- fix round 1: the group's media governs when it disagrees with the -----
# cage's presented interface ---------------------------------------------
#
# The accept list derivation surfaced a real corpus fact: 78 ports across six
# devices (edgecore/as7946-30xb, as7946-74xksb, csr440, dcs240, dcs511,
# ufispace/s9510-28dc) declare `media: qsfp-dd` on their port group while
# being modelled with `std/qsfp-ganged@1`, a QSFP aperture, not a QSFP-DD
# one. QSFP-DD and QSFP share a face opening and differ mainly in depth, so
# the DRAWING may be correct - which family should govern the accept list is
# Jason's ruling, not something this code derives: the group's media, because
# the group says what the port IS and the aperture only says what it looks
# like. `spec/tools/portrayal/lint.py`'s L104
# (`lint_device_cage_media_disagreement`) flags every one of the 78 so the
# modelling question - aperture wrong, or group media wrong - stays visible;
# `spec/tests/test_ladder_lint.py` pins that count and the exact six devices.
# This is the other half: that render.py's derivation actually serves the
# RIGHT optic once the two disagree, checked against a real device rather
# than the six being taken on faith.
#
# edgecore/csr440, placement `port-2`: `groups.qsfp-dd.attrs.media ==
# qsfp-dd`, ref `std/qsfp-ganged@1`, which presents interface `qsfp` - one of
# the 78, checked directly:
#
#     grep -n "ref: std/qsfp-ganged@1" library/devices/edgecore/csr440/device.yaml
#
# resolves to `port-2`, inside the `qsfp-dd` group.

CSR440 = LIB / "devices/edgecore/csr440/device.yaml"


def test_a_qsfp_shaped_cage_with_qsfp_dd_media_offers_the_qsfp_dd_optic(tmp_path):
    idx = _build(CSR440, tmp_path)
    cage = _cage(idx, "front", "port-2")
    # THE DRAWING FACT IS UNCHANGED - this really is a QSFP-shaped aperture,
    # and the entry says so honestly.
    assert cage["interface"] == "qsfp"
    assert cage["media"] == "qsfp-dd"
    assert cage["group"] == "qsfp-dd"
    # THE ACCEPT LIST FOLLOWS THE MEDIA, NOT THE APERTURE: the qsfp-dd
    # family's own generic, plus generic/qsfp-lc@1 through qsfp-dd's
    # `also-accepts: [qsfp]` - exactly what a genuine std/qsfp-dd@1 cage with
    # this same media would offer (test_a_qsfp_dd_cage_accepts_its_own_generic_
    # and_the_also_accepted_qsfp_one, above, on edgecore/dcs510).
    assert cage["accepts"] == ["generic/qsfp-dd-lc@1", "generic/qsfp-lc@1"]


def test_a_qsfp_shaped_cage_with_agreeing_media_is_unaffected(tmp_path):
    """The precedence rule only fires on a disagreement. `port-1` on the same
    device is in the plain `qsfp28` group - QSFP media on a QSFP aperture,
    the ordinary case everywhere else in this suite - and must not be
    touched by the code path the 78 disagreeing ports exercise."""
    idx = _build(CSR440, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "qsfp"
    assert cage["media"] == "qsfp28"
    assert cage["accepts"] == ["generic/qsfp-lc@1"]
