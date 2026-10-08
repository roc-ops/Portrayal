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
    # The four Juniper MX entries that stood here (DPC-R-4XGE-XFP, RE-S-1300-2048,
    # SCB-MX, DPCE-R-40GE-SFP) were vertical MX960 twins whose descriptions led with
    # how the card is drawn. #261 replaced the twins: the MX960 seats the horizontal
    # card at `rotate: 90`, so each of those models has one live author and nothing
    # to disagree with (part 2's retired twins carry `superseded-by` and are not
    # exported).
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
        # A retired major (`superseded-by`) is not exported, so it authors nothing.
        if c.get("superseded-by"):
            continue
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
    """No two live contracts share a model outside KNOWN_DIVERGENT. There were
    31 such groups, every one a Juniper MX card drawn twice (MX960 `-v`/`-v960`
    twins, then MX2000 `-v2k` cards and vertical MICs). #261 seats the
    horizontal card turned instead, and the twins it kept are retired
    (`superseded-by`), which the exporter leaves out - so the count is zero,
    and a new group means a new second author, which must be looked at."""
    collapsing = {k: [r for _d, r in v] for k, v in _groups().items()
                  if len(v) > 1 and k not in KNOWN_DIVERGENT}
    assert collapsing == {}, collapsing


def test_a_collapsed_type_names_every_author(tmp_path):
    """The surviving document is a function of the whole group, not of which
    contract `sorted()` happened to reach first. The stamp is where that shows.

    A BUILT FIXTURE, because the library no longer has a live model with two
    authors (see above): two copies of one real card under one model, through
    `export_modules`, and both names must be in the one file's stamp."""
    import copy
    if not (DIST / "components.json").exists():
        pytest.skip("no build; run ./build.sh")
    from portrayal.artifacts import Dist
    dist = Dist(DIST)
    base = dist.component_by_ref("juniper/mpc7e-mrate@2")
    assert base is not None, "juniper/mpc7e-mrate@2 is the fixture's template"
    twins = []
    for name, version in (("fixture-twin-a", "1.0.0"), ("fixture-twin-b", "1.0.1")):
        c = copy.deepcopy(base)
        c.update({"name": name, "major": "v1", "version": version})
        c["attrs"] = dict(c.get("attrs") or {}, model="FIXTURE-TWIN")
        twins.append(c)

    class Only:
        def modules(self):
            return twins

        def __getattr__(self, name):
            return getattr(dist, name)

    dx.export_modules(Only(), str(tmp_path))
    written = sorted(tmp_path.rglob("FIXTURE-TWIN.yaml"))
    assert [p.parent.parent.parent.name for p in written] == ["nautobot", "netbox"], written
    for p in written:
        comments = (yaml.safe_load(p.read_text()) or {}).get("comments") or ""
        for c in twins:
            ref = f"{c['ns']}/{c['name']}"
            assert f"({ref})" in comments, f"{ref} is not named in the stamp:\n{comments}"


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
