"""Two contracts, one model, one file - and the second used to win in silence.

A module type is written to `<manufacturer>/<model>.yaml`, so two contracts
carrying one `attrs.model` wrote one path. 55 contracts across 44 filenames were
overwritten, every run green (#267).

MOST OF IT IS DEDUPLICATION AND SHOULD BE. Forty of the forty-four are one
Juniper card drawn twice - horizontally for the MX240/MX480 and rotated for the
MX960 - and a DCIM orders a card, not an orientation. What was wrong is that the
right outcome arrived by accident: `sorted()` decided which twin's document
survived, so the committed DPCE-R-20GE-2XGE began `port-0-1, port-0-0, port-0-3`,
which is a vertical drawing's x-order and means nothing to a DCIM. Renaming a
contract would have changed the export and nothing would have said so.

Two things fixed that. Port lists are now in natural order by NAME, which is what
made 26 of the twins produce the same document rather than two orderings of it;
and a collapsed group's version stamp names every author, so the surviving
document is a function of the whole group instead of of iteration order.

What is left over is named, here, one line each.
"""
import collections
import functools
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"

from portrayal import dcim_export as dx

# EVERY GROUP WHOSE AUTHORS STILL DISAGREE, AND WHOSE PROBLEM IT IS.
#
# Each of these loses a document: the first contract's is written and the
# other's is not. That is better than the silence it replaces and worse than
# resolving it, so the list is pinned and may only shrink.
KNOWN_DIVERGENT = {
    # The vertical author's description leads with how the card is DRAWN - "as
    # mounted in the MX960" - where its forty siblings lead with the card and
    # put the orientation in a second sentence, which `build_module` never
    # reads. Prose about our model, not about the hardware. #261 collapses the
    # twins properly.
    ("Juniper", "DPC-R-4XGE-XFP"): "juniper/dpc-r-4xge-xfp-v",
    ("Juniper", "RE-S-1300-2048"): "juniper/re-s-1300-v",
    ("Juniper", "SCB-MX"): "juniper/scb-mx960-v",
    # The same. The NUMBERING half of this one is fixed: the vertical author's
    # flat `port-0..port-39` became `port-0-0..port-3-9` at @2, the scheme the
    # horizontal author's description names ("numbered per PIC, x/0..x/9, four
    # PICs"), and every one of the forty kept its position. What still pins the
    # entry is the description, exactly as for the three above - so #293 did
    # NOT take it off this list, and #261 is still what collapses the twins.
    ("Juniper", "DPCE-R-40GE-SFP"): "juniper/dpce-r-40ge-sfp-v",
    # ONE SKU MODELLED TWICE, at 80 mm and 82.5 mm - a real duplicate rather
    # than two authors of one card, and roc-ops/Portrayal#266 is where it is resolved.
    ("UfiSpace", "FAN-803816-HI"): "ufispace/fan-803816-hi",
}


@functools.lru_cache(maxsize=1)
def _groups():
    """(manufacturer, model) -> [(doc, ref)], built the way the exporter builds."""
    if not (DIST / "components.json").exists():
        pytest.skip("no build; run ./build.sh")
    from portrayal.artifacts import Dist
    dist = Dist(DIST)
    out = collections.defaultdict(list)
    for c in sorted(dist.modules(), key=lambda c: (c.get("ns") or "", c.get("name") or "")):
        man = dist.manufacturer_of(c.get("ns"))
        if not man:
            continue
        doc = dx.build_module(c, man, dist.component_by_ref)
        out[(man, doc["model"])].append((doc, f"{c['ns']}/{c['name']}"))
    return dict(out)


def _divergent():
    """Groups whose authors do not agree on what a DCIM reads."""
    bad = {}
    for key, members in _groups().items():
        first = dx.dcim_significant(members[0][0])
        for doc, ref in members[1:]:
            if dx.dcim_significant(doc) != first:
                bad[key] = ref
    return bad


def test_the_divergent_list_is_exactly_what_is_pinned():
    """Both directions. A NEW divergence is a part quietly not exported, which
    is the defect; a divergence that has been RESOLVED must come off the list,
    or it decays into a record of things that were once true - the failure mode
    of every hand-maintained exception list, and the reason NOT_A_DCIM_PORT is
    held from both ends too.
    """
    found = _divergent()
    new = {k: v for k, v in found.items() if k not in KNOWN_DIVERGENT}
    gone = {k: v for k, v in KNOWN_DIVERGENT.items() if k not in found}
    assert not new, (
        "these contracts share a model and export different documents, so one of "
        f"them is silently not written: {new}")
    assert not gone, (
        f"these no longer diverge and must come off KNOWN_DIVERGENT: {gone}")


def test_every_other_collision_is_a_real_collapse():
    """The forty twins. They share a model AND produce the same document, so
    writing one file is deduplication rather than loss - which is only true
    because the port order stopped depending on which way the card was drawn."""
    collapsing = {k: [r for _d, r in v] for k, v in _groups().items()
                  if len(v) > 1 and k not in KNOWN_DIVERGENT}
    assert len(collapsing) >= 35, f"only {len(collapsing)} group(s) collapse cleanly"
    for key, refs in collapsing.items():
        docs = [dx.dcim_significant(d) for d, _r in _groups()[key]]
        assert all(d == docs[0] for d in docs), f"{key} does not actually agree"


def test_a_collapsed_type_names_every_author():
    """The surviving document is a function of the whole group, not of which
    contract `sorted()` happened to reach first. The stamp is where that shows."""
    p = LIB / "exports/netbox/module-types/Juniper/MPC7E-MRATE.yaml"
    if not p.exists():
        pytest.skip("the MPC7E-MRATE export is not in this library")
    comments = (yaml.safe_load(p.read_text()) or {}).get("comments") or ""
    for author in ("juniper/mpc7e-mrate)", "juniper/mpc7e-mrate-v960)",
                   "juniper/mpc7e-mrate-v2k)"):
        assert author in comments, f"{author} is not named in the stamp:\n{comments}"


def test_ports_are_ordered_by_name_not_by_where_they_are_drawn():
    """The committed DPCE-R-20GE-2XGE used to begin `port-0-1, port-0-0,
    port-0-3` - the vertical twin's x-order, and a fact about a drawing rather
    than about a card."""
    p = LIB / "exports/netbox/module-types/Juniper/DPCE-R-20GE-2XGE.yaml"
    if not p.exists():
        pytest.skip("the DPCE-R-20GE-2XGE export is not in this library")
    names = [i["name"] for i in (yaml.safe_load(p.read_text()) or {}).get("interfaces") or []]
    assert names[:4] == [dx.module_scoped(f"port-0-{i}") for i in range(4)], names[:4]
    assert names == sorted(names, key=dx._natural)


def test_port_2_sorts_before_port_10():
    """Natural order, or a card with more than nine ports reads wrong."""
    assert sorted(["port-10", "port-2", "port-1"], key=dx._natural) == \
        ["port-1", "port-2", "port-10"]


def test_the_number_of_files_equals_the_number_of_models():
    """#267's third bullet. Every written file is one group, and no group writes
    two files - so a collision can never again be invisible in the count."""
    written = sorted((LIB / "exports/netbox/module-types").glob("*/*.yaml"))
    if not written:
        pytest.skip("no exports; run ./publish.sh")
    models = {(p.parent.name, (yaml.safe_load(p.read_text()) or {}).get("model"))
              for p in written}
    assert len(models) == len(written), "two files claim one model"
    assert len(written) == len(_groups()), (
        f"{len(written)} file(s) written for {len(_groups())} model group(s)")
