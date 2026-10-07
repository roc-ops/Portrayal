"""The cage says what FITS; the card says what RUNS - and when the card is silent
the table answers for it.

An SFP housing takes a 1G optic and a 10G one. So `cage_type` reads the family
from the cage ref and the rate from a media attr on the card, and falls back to a
per-cage default in `PART_IFACE` when the card declares none. That fallback is a
default standing in for a fact, and **1215 placements across 114 cards reached
it** with nothing anywhere to say so.

It has been wrong at least seven times:

  - `dpce-r-40ge-sfp` exported forty 10G interfaces on a card whose model number
    and description both say 40x1GbE (found by #267)
  - `mic3-3d-2x40ge-qsfpp` exported two 100G ports on a 40GbE MIC
  - `A9K-40GE-B` did the identical thing in roc-ops/Portrayal#23, three years earlier, and was
    fixed the same way - by stating `sfp: 40`

The defect came back because nothing counted the fallback. L96 counts it now, and
`export_modules` prints the total; these tests hold the counter honest and pin
the ones that have been resolved so they cannot silently regress.
"""
import functools
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import dcim_export as dx
from portrayal import lint
from portrayal import libwalk


@functools.lru_cache(maxsize=1)
def _modules():
    out = {}
    for cf in libwalk.iter_components([LIB]):
        d = yaml.safe_load(cf.read_text()) or {}
        if d.get("kind") == "module":
            out[f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"] = d
    return out


def _defaulting():
    """ref -> how many of its cages are typed by the table."""
    out = {}
    for ref, d in _modules().items():
        attrs = d.get("attrs") or {}
        groups = d.get("groups") or {}
        n = sum(1 for p in (d.get("parts") or [])
                if isinstance(p, dict) and "ref" in p
                and dx.cage_family_needs_a_rate(
                    p["ref"].split("@")[0], attrs,
                    dx.effective_part(p, groups)[0].get("attrs")))
        if n:
            out[ref] = n
    return out


# --- the rule asks the exporter's own question -------------------------------

def test_l96_is_registered_as_a_component_rule():
    assert lint.RULES["L96"][0] == "component"


def test_an_xfp_cage_is_not_one_rate_either():
    """THIS ENTRY USED TO BE EMPTY, meaning "nothing to declare" - so L96 never
    asked an XFP card anything and #296's census excluded them by construction.

    The sweep over the committed exports is what found them:
    `SPA-OC192POS-XFP` and `MIC-3D-1OC192-XFP` put an OC-192 port behind an XFP
    and exported 10GbE. Both are ~10 Gb/s; the framing is what differs, which is
    exactly why the cage cannot say and the card must.
    """
    assert dx.FAMILY_ATTRS["xfp"][0] == ("oc192", "sonet-oc192")
    assert dx.FAMILY_ATTRS["xfp"][1:-1] == dx.PON_ATTRS
    assert dx.FAMILY_ATTRS["xfp"][-1] == dx.XFP10G_ATTR
    assert dx.cage_type("std/xfp", {}) == "10gbase-x-xfp"
    assert dx.cage_type("std/xfp", {"oc192": 1}) == "sonet-oc192"


def test_declaring_the_rate_answers_the_question():
    assert dx.cage_family_needs_a_rate("std/sfp-ganged", {})
    assert not dx.cage_family_needs_a_rate("std/sfp-ganged", {"sfp": 40})
    assert dx.cage_type("std/sfp-ganged", {"sfp": 40}) == "1000base-x-sfp"
    assert dx.cage_type("std/sfp-ganged", {}) == "10gbase-x-sfpp"


# --- what was wrong, pinned so it cannot come back ---------------------------

@pytest.mark.parametrize("ref,attr,count,expected", [
    # Each of these took a table default that its own description contradicts.
    ("juniper/dpce-r-40ge-sfp", "sfp", 40, "1000base-x-sfp"),     # "40x1GbE"
    ("juniper/dpce-r-40ge-sfp-v", "sfp", 40, "1000base-x-sfp"),
    ("juniper/dpce-q-20ge-sfp", "sfp", 20, "1000base-x-sfp"),     # "twenty SFP"
    ("juniper/mic-3d-20ge-sfp", "sfp", 20, "1000base-x-sfp"),     # "Gigabit Ethernet MIC"
    ("juniper/mic-macsec-20ge", "sfp", 20, "1000base-x-sfp"),     # "MACsec Gigabit Ethernet"
    ("juniper/dpce-20ge-2xge", "sfp", 20, "1000base-x-sfp"),      # "twenty SFP ... plus two XFP"
    ("cisco/a9k-mpa-1x40ge", "qsfp", 1, "40gbase-x-qsfpp"),       # "40 Gigabit ... QSFP+"
    ("cisco/a9k-mpa-2x40ge", "qsfp", 2, "40gbase-x-qsfpp"),
    ("juniper/mic3-3d-2x40ge-qsfpp", "qsfp", 2, "40gbase-x-qsfpp"),  # "40GbE ... QSFP+"
    ("juniper/jnp10003-lc2103", "qsfp", 6, "40gbase-x-qsfpp"),    # "six fixed QSFP+ ports"
])
def test_a_card_the_default_contradicted_now_states_its_rate(ref, attr, count, expected):
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get(attr) == count, f"{ref} lost its `{attr}: {count}`"
    cage = next(p["ref"].split("@")[0] for p in d["parts"]
                if isinstance(p, dict) and p["ref"].split("@")[0] in dx.CAGE_FAMILY)
    assert dx.cage_type(cage, attrs) == expected


def test_a_40g_card_does_not_export_100g_ports():
    """The end of the chain, read off the committed export rather than the
    contract - which is the reading that found the original defect."""
    p = LIB / "exports/netbox/module-types/Juniper/MIC3-3D-2X40GE-QSFPP.yaml"
    if not p.exists():
        pytest.skip("the MIC3-3D-2X40GE-QSFPP export is not in this library")
    types = {i["type"] for i in (yaml.safe_load(p.read_text()) or {}).get("interfaces") or []}
    assert types == {"40gbase-x-qsfpp"}, types


# --- the census, which is meant to shrink ------------------------------------

def test_the_backlog_is_counted_and_shrinking():
    """A CENSUS WARNING of the L92/L93 kind. Most of what it names is probably
    right - an SFP-ganged strip on a modern line card usually is SFP+ - and
    "probably right" is exactly what cannot be told from "wrong" without asking.

    An upper bound, not an equality: answering one is a good afternoon's work
    and must not fail the suite.
    """
    n = sum(_defaulting().values())
    assert n <= 865, f"{n} cage placements take the table default, up from 865"
    assert len(_modules()) >= 300, "the census did not find the module catalogue"


def test_the_census_and_the_rule_count_the_same_things():
    """The printed total and L96 have to be one question asked once. A second
    copy of "which cages need a rate" drifts from the table it is about - which
    is the mistake docs/failure-by-omission.md records twice already, so the
    rule imports the exporter rather than restating it."""
    import inspect
    src = inspect.getsource(lint.lint_component_cage_rate)
    assert "dcim_export.cage_family_needs_a_rate" in src


# --- an SFP cage is not only an Ethernet cage (#296) -------------------------
#
# Twenty-seven SONET, ATM and channelized cards put an SFP in front of an OC-3,
# OC-12 or OC-48 port - fifteen Cisco SIP-700 SPAs and six Juniper MICs with
# their vertical authors. `FAMILY_ATTRS` knew only Ethernet rates, so every one
# of them fell to the cage default and exported as Gigabit Ethernet: ~90 ports,
# and an OC-3 ATM port is not a Gigabit Ethernet interface.

SONET = {"oc3": "sonet-oc3", "oc12": "sonet-oc12", "oc48": "sonet-oc48"}


def test_the_sonet_rates_are_types_both_targets_have():
    """One document is written to both trees, so a type either library refuses
    would be rejected on import rather than by any gate here."""
    assert dict(dx.FAMILY_ATTRS["sfp"][4:7]) == \
        {"oc48": "sonet-oc48", "oc12": "sonet-oc12", "oc3": "sonet-oc3"}


def test_an_ethernet_card_is_unaffected_by_the_sonet_rates():
    """The Ethernet pair stays FIRST in the tuple after `sfp112` - which no card
    stated before it joined - so nothing about a card that declares `sfp` or
    `sfp-plus` changes."""
    assert dx.FAMILY_ATTRS["sfp"][0] == dx.SFP112_ATTR
    assert dx.FAMILY_ATTRS["sfp"][1:4] == (("sfp-plus", "10gbase-x-sfpp"),
                                          dx.SFP28_ATTR,
                                          ("sfp", "1000base-x-sfp"))
    assert dx.cage_type("std/sfp-ganged", {"sfp": 20}) == "1000base-x-sfp"
    assert dx.cage_type("std/sfp-ganged", {"sfp-plus": 16}) == "10gbase-x-sfpp"


@pytest.mark.parametrize("ref,attr,count", [
    ("cisco/spa-4xoc48pos-rpr", "oc48", 4),      # "4-Port OC-48/STM-16 POS/RPR SPA"
    ("cisco/spa-8xoc3-pos", "oc3", 8),           # "8-Port OC-3/STM-1 POS SPA"
    ("cisco/spa-1choc3-ce-atm", "oc3", 1),       # "1-Port Channelized OC-3 ATM CEoP SPA"
    ("juniper/mic-3d-8oc3-2oc12-atm", "oc3", 8), # "ATM MIC with SFP (eight ports)"
    ("juniper/mic-3d-8oc3oc12-4oc48", "oc12", 8),
])
def test_a_sonet_card_states_its_rate(ref, attr, count):
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get(attr) == count
    cage = next(p["ref"].split("@")[0] for p in d["parts"]
                if isinstance(p, dict) and p["ref"].split("@")[0] in dx.CAGE_FAMILY)
    assert dx.cage_type(cage, attrs) == SONET[attr]


def test_an_atm_port_takes_its_sonet_type():
    """UPSTREAM'S "ATM" GROUP CONTAINS ONE CHOICE, `xdsl`, so there is no ATM
    interface type to reach for - and there should not be. `type` names the
    PHYSICAL interface; ATM is the framing that runs over it, the way POS and
    channelized DS0 are. An OC-3 ATM port is an OC-3 port.
    """
    p = LIB / "exports/netbox/module-types/Juniper/MIC-3D-8OC3-2OC12-ATM.yaml"
    if not p.exists():
        pytest.skip("the ATM MIC export is not in this library")
    d = yaml.safe_load(p.read_text()) or {}
    assert "ATM" in (d.get("description") or ""), "this is still the ATM card"
    assert {i["type"] for i in d["interfaces"]} == {"sonet-oc3"}


def test_no_sonet_card_still_exports_ethernet():
    """The sweep, over the committed exports rather than the contracts. A card
    whose description names SONET, ATM, POS or a channelized rate must not carry
    a `base-` interface type - that is the defect, stated as a property."""
    import re
    words = re.compile(r"\b(OC-?\d+|STM-?\d+|ATM|POS|SONET|SDH|channeli[sz]ed)\b", re.I)
    bad, checked = [], 0
    for p in sorted((LIB / "exports/netbox/module-types").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if not words.search(str(d.get("description") or "")):
            continue
        checked += 1
        eth = {i["name"] for i in (d.get("interfaces") or [])
               if "base-" in i.get("type", "")}
        if eth:
            bad.append(f"{d.get('model')}: {sorted(eth)}")
    assert not bad, "\n".join(bad)
    # NOT VACUOUS. Run before this change it names fifteen Cisco SPAs and six
    # Juniper MICs; a sweep over an empty collection passes just as quietly.
    assert checked >= 20, f"only {checked} card(s) reached the sweep"


# --- nor is it only Ethernet or SONET: a PON OLT port is neither -------------
#
# The Nokia 7360 ISAM FX line cards put GPON, XGS-PON, NG-PON2 and 10G-EPON OLT
# optics in SFP and XFP cages. With only Ethernet and SONET rates to declare,
# 112 of those cages on ten cards fell to the cage default - a GPON OLT port
# exported as 1000BASE-X, a 10G-EPON one as 10GBASE-X.

PON = {"ng-pon2": "ng-pon2", "xgs-pon": "xgs-pon", "xg-pon": "xg-pon",
       "10g-epon": "10g-epon", "gpon": "gpon", "epon": "epon"}


def test_the_pon_rates_are_types_both_targets_have():
    """One document is written to both trees. NetBox also defines `bpon`,
    `25g-pon` and `50g-pon`; Nautobot defines none of them, so they must not
    appear here - an import into Nautobot would refuse the whole module type."""
    assert dict(dx.PON_ATTRS) == PON
    assert not {"bpon", "25g-pon", "50g-pon"} & {t for _a, t in dx.PON_ATTRS}


def test_the_pon_rates_follow_ethernet_and_sonet():
    """AFTER everything a card could already declare, so no existing card's
    export changes - the SFP family ends in them and the XFP family's OC-192
    stays first."""
    assert dx.FAMILY_ATTRS["sfp"][7:] == dx.PON_ATTRS
    assert dx.FAMILY_ATTRS["xfp"] == \
        (("oc192", "sonet-oc192"),) + dx.PON_ATTRS + (dx.XFP10G_ATTR,)
    assert dx.cage_type("std/sfp", {"sfp": 8, "gpon": 8}) == "1000base-x-sfp"
    assert dx.cage_type("std/xfp", {"oc192": 1, "10g-epon": 1}) == "sonet-oc192"


def test_a_multi_pon_card_takes_its_most_capable_flavour():
    assert dx.cage_type("std/sfp", {"gpon": 16, "xgs-pon": 16}) == "xgs-pon"
    assert dx.cage_type("std/xfp", {"xgs-pon": 4, "ng-pon2": 4}) == "ng-pon2"


def test_a_pon_attr_answers_the_census():
    assert not dx.cage_family_needs_a_rate("std/sfp", {"gpon": 16})
    assert not dx.cage_family_needs_a_rate("std/xfp", {"10g-epon": 4})
    # `xfp: 4` counts cages; it states no rate, so it answers nothing.
    assert dx.cage_family_needs_a_rate("std/xfp", {"xfp": 4})


@pytest.mark.parametrize("ref,attr,count", [
    ("nokia/fglt-a", "gpon", 16),     # "16-ports GPON LT"
    ("nokia/fglt-b", "gpon", 16),     # "16-ports GPON LT"
    ("nokia/fglt-d", "gpon", 16),     # "16-ports GPON LT"
    ("nokia/fglt-e", "gpon", 32),     # "32-ports GPON LT", two per cage
    ("nokia/fgut-a", "xgs-pon", 16),  # "XGS-PON ... on any of the ports"
    ("nokia/nglt-a", "gpon", 8),      # "eight GPON ports per board"
    ("nokia/nglt-c", "gpon", 8),      # "eight GPON ports per board"
    ("nokia/fwlt-a", "xgs-pon", 4),   # NG-PON2 named, but only XGS optics listed
    ("nokia/fpxt-a", "10g-epon", 4),  # "4 compliant IEEE802.3av EPON XFP ports"
    ("nokia/fpxt-b", "10g-epon", 8),  # "8p 10G EPON Line Termination unit"
    ("nokia/fwlt-b-aa", "xgs-pon", 8),  # "G.9807 XGS-PON on any of the eight ports"
    ("nokia/fwlt-b-ab", "xgs-pon", 8),  # NG-PON2 named, but only XGS optics listed
    ("nokia/fwlt-c", "xgs-pon", 16),    # "XGS-PON ... on any of the 16 ports"
])
def test_a_pon_card_states_its_rate(ref, attr, count):
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get(attr) == count
    cages = {p["ref"].split("@")[0] for p in d["parts"]
             if isinstance(p, dict) and p["ref"].split("@")[0] in dx.CAGE_FAMILY}
    assert cages and {dx.cage_type(c, attrs) for c in cages} == {PON[attr]}


# --- SFP112 and QSFP-DD800: two rates the Nokia MDA2-e-XP brought ------------

def test_sfp112_exports_as_other_because_nautobot_has_no_type_for_it():
    """NetBox has `100gbase-x-sfp112`; Nautobot does not (nautobot/dcim/
    choices.py at 38953ac3). One document is written to both trees, so the slug
    would fail a Nautobot import - the reason `25gs-pon` has no row. But a card
    stating `sfp112` HAS stated its rate, and without a row it fell to the cage
    default (10GBASE-X SFP+) with L96 accusing it. `other` is in both."""
    assert dx.SFP112_ATTR == ("sfp112", "other")
    written = ({t for fam in dx.FAMILY_ATTRS.values() for _a, t in fam}
               | set(dx.IFACE_TYPE.values()) | set(dx.PART_IFACE.values())
               | set(dx.PART_MEDIA.values()))
    assert "100gbase-x-sfp112" not in written
    assert not dx.cage_family_needs_a_rate("std/sfp-ganged", {"sfp112": 16})
    assert dx.cage_type("std/sfp-ganged", {"sfp112": 16}) == "other"
    assert dx.cage_type("std/sfp", {"sfp112": 8, "sfp28": 8}) == "other"
    part = {"ref": "std/sfp@1", "attrs": {"media": "sfp112", "speed": "100g"}}
    assert dx.placed_type(part) == "other"


def test_an_other_port_is_labelled_with_its_own_media():
    """`other` loses the connector, so the label carries it. It was hardcoded
    "RJ45" (for the Casa rj45-telemetry port) and the Nokia MDA2-e-XP's SFP112
    cages exported as copper jacks."""
    assert dx.OTHER_LABEL["sfp112"] == "SFP112"
    assert dx.OTHER_LABEL["rj45-telemetry"] == "RJ45"
    assert [a for fam in dx.FAMILY_ATTRS.values() for a, t in fam
            if t == "other"] == [dx.SFP112_ATTR[0]]
    labelled = [media for (media, _s), t in dx.PART_MEDIA.items() if t == "other"]
    assert labelled and all(m in dx.OTHER_LABEL for m in labelled)
    exports = pathlib.Path(__file__).resolve().parents[2] / "library" / "exports"
    sfp112 = list(exports.glob("*/module-types/Nokia/*SFP112*.yaml"))
    assert sfp112, "no SFP112 card export to check"
    for f in sfp112:
        assert "label: RJ45" not in f.read_text(), f


def test_an_800g_qsfp_dd_card_is_not_typed_400g():
    """`800gbase-x-qsfpdd` is in both targets (NetBox and Nautobot
    TYPE_800GE_QSFP_DD). The card attr is `qsfp-dd-800g` - a rate statement, not
    a media value: the port's media stays `qsfp-dd` and `qsfp-dd800` stays out
    of the vocabulary, as spec/schemas/pluggables.yaml rules."""
    assert dx.FAMILY_ATTRS["qsfp-dd"] == (
        ("qsfp-dd-800g", "800gbase-x-qsfpdd"), ("qsfp-dd", "400gbase-x-qsfpdd"))
    assert "qsfp-dd-800g" not in lint.PLUGGABLE_CAGES
    assert dx.cage_type("std/qsfp-dd", {"qsfp-dd-800g": 2}) == "800gbase-x-qsfpdd"
    assert dx.cage_type("std/qsfp-dd", {"qsfp-dd-800g": 2, "qsfp-dd": 2}) == \
        "800gbase-x-qsfpdd"
    assert not dx.cage_family_needs_a_rate("std/qsfp-dd", {"qsfp-dd-800g": 2})
    # Every 400G card states only `qsfp-dd`, and is unchanged.
    assert dx.cage_type("std/qsfp-dd", {"qsfp-dd": 6}) == "400gbase-x-qsfpdd"
    part = {"ref": "std/qsfp-dd@1", "attrs": {"media": "qsfp-dd", "speed": "800g"}}
    assert dx.placed_type(part) == "800gbase-x-qsfpdd"


def test_an_sfp28_card_exports_as_sfp28():
    """`25gbase-x-sfp28` is in both targets (NetBox and Nautobot
    TYPE_25GE_SFP28). A card stating only `sfp28` used to fall to the cage
    default and export as 10GBASE-X SFP+."""
    assert dx.SFP28_ATTR == ("sfp28", "25gbase-x-sfp28")
    assert dx.cage_type("std/sfp-ganged", {"sfp28": 16}) == "25gbase-x-sfp28"
    assert dx.cage_type("std/sfp", {"sfp28": 4, "sfp": 4}) == "25gbase-x-sfp28"
    assert not dx.cage_family_needs_a_rate("std/sfp-ganged", {"sfp28": 16})


@pytest.mark.parametrize("ref", ["cisco/a99-4hg-flex-se", "cisco/a99-4hg-flex-tr",
                                 "cisco/a9k-4hg-flex-se", "cisco/a9k-4hg-flex-tr",
                                 "cisco/a9903-8hg-pec"])
def test_a_mixed_sfp_plus_and_sfp28_card_is_unchanged(ref):
    """These state `sfp-plus` AND `sfp28` over one strip of std/sfp-ganged, and
    exported SFP+ before `sfp28` had a row. The row sits AFTER `sfp-plus` so
    they still do - one card-level attr cannot say which cage is which."""
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get("sfp-plus") and attrs.get("sfp28")
    assert dx.cage_type("std/sfp-ganged", attrs) == "10gbase-x-sfpp"


def test_no_existing_card_states_the_new_rates_before_its_card_lands():
    """Both rows sit FIRST in their families, which is only free if no card
    already states them - else that card's export changed under this commit."""
    stating = sorted(ref for ref, d in _modules().items()
                     if {"sfp112", "qsfp-dd-800g"} & set(d.get("attrs") or {}))
    nokia_mda2 = {"nokia/m5e2-100g-qsfp28-2-800g-qdd", "nokia/m5e8-100g-sfp112-2-800g-qdd",
                  "nokia/m5e16-100g-sfp112"}
    assert set(stating) <= nokia_mda2, stating


def test_a_placement_that_names_its_pon_flavour_takes_it():
    """The FGUT-A's odd ports are `media: sfp-plus, speed: 10g, pon: xgs-pon`.
    Read by media and speed alone they exported as 10GBASE-X SFP+ even after the
    card stated `xgs-pon: 16`, because the placement is read first."""
    part = {"ref": "std/sfp@1", "attrs": {"media": "sfp-plus", "speed": "10g",
                                          "pon": "xgs-pon"}}
    assert dx.placed_type(part) == "xgs-pon"
    # A flavour one target lacks falls through to the media, as before.
    part["attrs"]["pon"] = "25gs-pon"
    assert dx.placed_type(part) == "10gbase-x-sfpp"
    # And a `pon` with no media is not a CARD placement statement at all: on a
    # card the SC/APC ferrule stays in NOT_A_DCIM_PORT.
    assert dx.placed_type({"ref": "common/sc-apc@1", "attrs": {"pon": "xgs-pon"}}) is None


def test_a_device_pon_port_takes_its_flavour():
    """An ONT's uplink is a built-in SC/APC ferrule, not a cage, so iface_type
    has no family to read. The Halny HLX-TGV and both Nokia XS-010X ONTs
    exported their LAN jack and not the PON port they exist for."""
    sc = {"ref": "common/sc-apc@1", "id": "pon"}
    assert dx.device_port_type(sc, {"speed": "10g", "pon": "xgs-pon"}, "traffic") == (
        "xgs-pon", None, None)
    bore = {"ref": "std/sc-bore@1", "id": "pon"}
    assert dx.device_port_type(bore, {"media": "fiber", "pon": "gpon"}, "traffic")[0] == "gpon"
    # A flavour one target lacks is not a type, and the ferrule has no cage to
    # fall back on, so the port stays out rather than leaving as a guess.
    assert dx.device_port_type(sc, {"speed": "10g", "pon": "25gs-pon"}, "traffic")[0] is None
    # A ferrule in a group that is not a port role is still not a port.
    assert dx.device_port_type(sc, {"pon": "xgs-pon"}, "furniture")[0] is None


def test_a_lamp_in_a_pon_group_is_not_a_second_pon_port():
    """`pon` on a GROUP reaches every placement in it (nokia/xs-010x-r states it
    there). The flavour says what a port runs; it does not make a lamp or a
    label a port, and before #772 either would have exported as one."""
    dev = {"vendor": "acme", "manufacturer": "Acme", "name": "x", "model": "X1",
           "chassis": {"u": 1},
           "groups": {"pon": {"term": "Port", "role": "traffic",
                              "attrs": {"media": "fiber", "speed": "10g", "pon": "xgs-pon"}}},
           "views": {"rear": {"components": {"placements": [
               {"ref": "std/sc-bore@1", "id": "pon", "at": [0, 0], "group": "pon"},
               {"ref": "common/led-dot@1", "id": "led-pon", "at": [20, 0], "group": "pon",
                "for": "pon"},
               {"ref": "common/laser-warning@1", "id": "laser-mark", "at": [30, 0],
                "group": "pon"}]}}}}
    got = dx.build(dev, "base", {}, None)["interfaces"]
    assert got == [{"name": "pon", "type": "xgs-pon"}]
    lamp = {"ref": "common/led-dot@1", "id": "led-pon"}
    assert dx.device_port_type(lamp, {"pon": "xgs-pon"}, "traffic")[0] is None
    # With a listing (names given) the role guards are skipped, so the part
    # test is all that stands between the lamp and an interface.
    names = {"led-pon": ("pon0", None)}
    assert dx.device_port_type(lamp, {"pon": "xgs-pon"}, "traffic", names)[0] is None
    # A device's own pluggable cage that states the flavour still takes it.
    assert dx.device_port_type({"ref": "std/sfp@1", "id": "p1"}, {"pon": "gpon"},
                               "traffic")[0] == "gpon"


def test_a_multi_pon_card_exports_every_port_as_pon():
    p = LIB / "exports/netbox/module-types/Nokia/FGUT-A.yaml"
    if not p.exists():
        pytest.skip("the FGUT-A export is not in this library")
    d = yaml.safe_load(p.read_text()) or {}
    assert [i["type"] for i in d["interfaces"]] == ["xgs-pon"] * 16


@pytest.mark.parametrize("model", ["FWLT-B AA", "FWLT-B AB", "FWLT-C"])
def test_a_former_sfp_plus_pon_card_exports_as_pon(model):
    """These three stated `sfp-plus` for want of a PON type, and exported every
    OLT port as 10GBASE-X SFP+. The FWLT-C's odd ports state `pon: xgs-pon`
    and its even ports `pon: 25gs-pon`, which neither falls to Ethernet nor
    names a type Nautobot lacks: they export as the XGS-PON they also run."""
    p = LIB / f"exports/netbox/module-types/Nokia/{model}.yaml"
    if not p.exists():
        pytest.skip(f"the {model} export is not in this library")
    d = yaml.safe_load(p.read_text()) or {}
    assert {i["type"] for i in d["interfaces"]} == {"xgs-pon"}


# PON CARDS THAT STILL STATE AN ETHERNET RATE, named so the sweep below is not
# silent about them. The register is meant to shrink: FWLT-B AA, FWLT-B AB and
# FWLT-C were here until they stated `xgs-pon` in place of `sfp-plus`. The sweep
# fails when one is fixed and not removed from here, as well as when a new one
# appears.
STILL_ETHERNET = set()


def test_no_pon_card_still_exports_ethernet():
    """The sweep, over the committed exports. A card whose description names a
    PON flavour must not carry a `base-` interface type unless STILL_ETHERNET
    names it. NOT VACUOUS: `checked` counts the PON cards it read, and without
    the PON rates every one of the ten 7360 FX cards above, and the FPLT-A,
    exported a `base-` type."""
    import re
    words = re.compile(r"\b(GPON|XGS-PON|XG-PON|NG-?PON2|U-NGPON|10G[- ]?EPON|EPON|Multi-PON)\b", re.I)
    bad, known, checked = [], set(), 0
    for p in sorted((LIB / "exports/netbox/module-types").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if not words.search(str(d.get("description") or "")):
            continue
        checked += 1
        eth = {i["name"] for i in (d.get("interfaces") or [])
               if "base-" in i.get("type", "")}
        if eth and d.get("model") in STILL_ETHERNET:
            known.add(d.get("model"))
        elif eth:
            bad.append(f"{d.get('model')}: {sorted(eth)}")
    assert not bad, "\n".join(bad)
    assert known == STILL_ETHERNET, f"now clean, drop from STILL_ETHERNET: {STILL_ETHERNET - known}"
    assert checked >= 10, f"only {checked} card(s) reached the sweep"


# --- a stated rate wins: two gaps the Nokia 7750 SR-1 cards brought ----------

def test_a_cfp2_stating_200g_is_not_the_cage_default():
    """`200gbase-x-cfp2` is in both targets (NetBox and Nautobot TYPE_200GE_CFP2),
    so unlike SFP112 it needs no `other`. Without the row a CFP2 port stating
    200g fell to PART_IFACE's std/cfp2 default, 100gbase-x-cfp2."""
    part = {"ref": "std/cfp2@1", "attrs": {"media": "cfp2", "speed": "200g"}}
    assert dx.placed_type(part) == "200gbase-x-cfp2"
    assert dx.PART_IFACE["std/cfp2"] == "100gbase-x-cfp2"   # the default is unchanged


def test_a_card_rj45_stating_100m_is_fast_ethernet():
    """A card's placement says 10/100; FAMILY_PART's Ethernet answer is 1000base-t
    and must not be reached. PART_MEDIA and IFACE_TYPE agree on the slug."""
    part = {"ref": "common/rj45-ganged-eth@1", "attrs": {"media": "rj45", "speed": "100m"}}
    assert dx.placed_type(part) == "100base-tx"
    assert dx.PART_MEDIA[("rj45", "100m")] == dx.IFACE_TYPE[("rj45", "100m")]


def test_a_management_jack_that_states_its_speed_takes_it():
    """`role: mgmt` answered 1000base-t before the speed was read, so the SR-1's
    10/100 mgmt jack disagreed with `oes-1` beside it. Silent, it stays 1G."""
    eth = {"ref": "common/rj45-ganged-eth@1", "id": "mgmt"}
    bare = {"ref": "std/rj45@2", "id": "mgmt"}
    for p in (eth, bare):
        assert dx.iface_type(p, {"role": "mgmt", "speed": "100m"}, "management") == "100base-tx"
        assert dx.iface_type(p, {"role": "mgmt", "speed": "1g"}, "management") == "1000base-t"
        assert dx.iface_type(p, {"role": "mgmt"}, "management") == "1000base-t"
    assert (dx.iface_type(eth, {"role": "mgmt", "speed": "100m"}, "management")
            == dx.iface_type(eth, {"role": "oes-control", "speed": "100m"}, "management"))


def _nokia_export(kind, model):
    for p in sorted((LIB / f"exports/netbox/{kind}").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        if d.get("model") == model:
            # A card's names are bay-scoped in the file; the test reads the card's.
            return {i["name"].removeprefix(dx.module_scoped("")): i["type"]
                    for i in d.get("interfaces") or []}
    pytest.fail(f"no {kind} export with model {model!r}")


def test_the_me3_cfp2_dco_card_exports_200g():
    ifaces = _nokia_export("module-types", "ME3-200GB-CFP2-DCO")
    assert ifaces == {"c1": "200gbase-x-cfp2", "c2": "200gbase-x-cfp2",
                      "c3": "200gbase-x-cfp2"}


def test_the_ccm_e_mgmt_and_oes_ports_are_100base_tx():
    ifaces = _nokia_export("module-types", "7750 SR-e CCM-e")
    assert ifaces["mgmt"] == ifaces["oes"] == "100base-tx"
    assert not {n for n, t in ifaces.items() if t == "1000base-t"}


@pytest.mark.parametrize("model", ["7750 SR-1 AC", "7750 SR-1 DC"])
def test_the_sr1_mgmt_jack_agrees_with_its_siblings(model):
    ifaces = _nokia_export("device-types", model)
    assert ifaces["mgmt"] == ifaces["oes-1"] == "100base-tx"


# --- a cage that carries no standard port at all -----------------------------
#
# The CommScope BP3400C's eight SFP cages hold RR40x0 / RR36x0 digital-return
# receiver SFPs - a proprietary link from a node's transmitter, not Ethernet,
# SONET or PON. No FAMILY_ATTRS rate is true of them, so they took the table
# default and exported as 10GBASE-X SFP+. `proprietary-link: <label>` on the
# placement says so, and is as explicit as `sfp: 40`.

DR = "Digital return"


def _card(parts, groups=None, attrs=None):
    d = {"kind": "module", "name": "t", "attrs": {"model": "T", **(attrs or {})},
         "parts": parts}
    if groups:
        d["groups"] = groups
    return d


def _l96(doc):
    with lint.collecting() as found:
        lint.lint_component_cage_rate("t/contract.yaml", doc)
    return [w for w in found.warnings if "[L96]" in w]


def test_a_proprietary_link_answers_the_census():
    assert dx.PROPRIETARY_LINK == "proprietary-link"
    assert not dx.cage_family_needs_a_rate("std/sfp-ganged", {}, {"proprietary-link": DR})
    # Silent, it is still asked - a default that is right is indistinguishable
    # from one that is not.
    assert dx.cage_family_needs_a_rate("std/sfp-ganged", {}, {})
    assert dx.cage_family_needs_a_rate("std/sfp-ganged", {})


def test_a_proprietary_link_exports_as_other_with_its_label():
    part = {"ref": "std/sfp-ganged@1", "attrs": {"proprietary-link": DR}}
    assert dx.placed_type(part) == "other"
    # It outranks a media the placement also states.
    part["attrs"]["media"] = "sfp"
    part["attrs"]["speed"] = "1g"
    assert dx.placed_type(part) == "other"
    assert dx.other_label(part) == DR


@pytest.mark.parametrize("bad", ["", "   ", 7, True, ["x"], {"a": 1}, "x" * 65])
def test_a_proprietary_link_that_is_not_a_label_says_nothing(bad):
    a = {"proprietary-link": bad}
    assert dx.proprietary_link(a) is None
    assert dx.placed_type({"ref": "std/sfp@1", "attrs": a}) is None
    assert dx.cage_family_needs_a_rate("std/sfp", {}, a)


def test_only_the_cages_that_declare_it_are_retyped():
    """THE REASON IT IS ON THE PLACEMENT. The BP3400C's ninth SFP-family cage is
    a data port nobody documents; a card-level declaration covers every cage of
    the family and would have typed it as the digital-return link too."""
    doc = _card([
        {"ref": "std/sfp-ganged@1", "id": "in-a", "at": [0, 0],
         "attrs": {"proprietary-link": DR}},
        {"ref": "std/sfp-ganged@1", "id": "in-b", "at": [15, 0],
         "attrs": {"proprietary-link": DR}},
        {"ref": "std/sfp@1", "id": "data-port", "at": [30, 0]},
    ])
    defaulted = {}
    out = dx.build_module(doc, "T", defaulted=defaulted)
    assert {i["name"]: i for i in out["interfaces"]} == {
        "in-a": {"name": "in-a", "type": "other", "label": DR},
        "in-b": {"name": "in-b", "type": "other", "label": DR},
        "data-port": {"name": "data-port", "type": "1000base-x-sfp"},
    }
    assert defaulted == {"std/sfp": 1}
    got = _l96(doc)
    assert len(got) == 1 and "1 x std/sfp " in got[0], got


def test_a_group_can_declare_it_once():
    """Read through the card's groups, as the exporter reads the placement."""
    doc = _card(
        [{"ref": "std/sfp-ganged@1", "id": f"in-{i}", "group": "dr", "at": [15 * i, 0]}
         for i in range(4)],
        groups={"dr": {"term": "Input", "role": "data",
                       "attrs": {"proprietary-link": DR}}})
    assert _l96(doc) == []
    out = dx.build_module(doc, "T")
    assert {(i["type"], i.get("label")) for i in out["interfaces"]} == {("other", DR)}


def test_l96_names_a_declaration_that_is_not_a_label():
    doc = _card([{"ref": "std/sfp-ganged@1", "id": "in-a", "at": [0, 0],
                  "attrs": {"proprietary-link": 40}}])
    got = _l96(doc)
    assert any("not a label" in w for w in got), got
    assert any("nothing says what rate" in w for w in got), got


def test_only_a_pluggable_cage_carries_one():
    """A GROUP HOLDS A RECEIVER'S RF JACKS BESIDE ITS CAGE, and read on every
    member the declaration retyped an F-type output from `docsis` to the link."""
    assert dx.pluggable_cage("std/sfp-ganged@1") and dx.pluggable_cage("std/cfp2@1")
    assert dx.pluggable_cage("acme/osfp-cage@1")
    assert not dx.pluggable_cage("std/f-type@1")
    assert not dx.pluggable_cage("common/rj45-eth@1")
    doc = _card(
        [{"ref": "std/sfp-ganged@1", "id": "in-d", "group": "rx-d", "at": [0, 0]},
         {"ref": "std/f-type@1", "id": "rf-d-1", "group": "rx-d", "at": [0, 40]}],
        groups={"rx-d": {"term": "Port", "role": "data",
                         "attrs": {"proprietary-link": DR}}})
    out = {i["name"]: i for i in dx.build_module(doc, "T")["interfaces"]}
    assert out["in-d"] == {"name": "in-d", "type": "other", "label": DR}
    assert out["rf-d-1"] == {"name": "rf-d-1", "type": "docsis", "label": "F"}
    got = _l96(doc)
    assert len(got) == 1 and "rf-d-1" in got[0] and "not a pluggable cage" in got[0], got


def _device(groups, placements):
    return {"vendor": "acme", "manufacturer": "Acme", "name": "x", "model": "X1",
            "chassis": {"u": 1}, "groups": groups,
            "views": {"front": {"components": {"placements": placements}}}}


def test_a_device_cage_that_declares_one_exports_as_other():
    """NOT ONLY A CARD'S. L96's fix text says "on its placement", and a device
    placement that said it was silently typed from media and speed instead."""
    dev = _device(
        {"dr": {"term": "Port", "role": "traffic", "attrs": {"proprietary-link": DR}},
         "eth": {"term": "Port", "role": "traffic", "attrs": {"media": "sfp", "speed": "1g"}}},
        [{"ref": "std/sfp@1", "id": "port-1", "at": [0, 0], "group": "dr"},
         {"ref": "std/sfp@1", "id": "port-2", "at": [15, 0], "group": "eth",
          "attrs": {"proprietary-link": DR * 7}},          # not a label: says nothing
         {"ref": "std/f-type@1", "id": "rf-1", "at": [30, 0], "group": "dr"}])
    got = {i["name"]: i for i in dx.build(dev, "base", {}, None)["interfaces"]}
    assert got["port-1"] == {"name": "port-1", "type": "other", "label": DR}
    assert got["port-2"] == {"name": "port-2", "type": "1000base-x-sfp"}
    assert got["rf-1"] == {"name": "rf-1", "type": "docsis", "label": "F"}


# --- an Ethernet XFP card has a rate to state --------------------------------

ETHERNET_XFP = {
    # Cisco ASR 9000 Ethernet Line Card Installation Guide: "... with XFP"
    "cisco/a9k-4t-b": 4, "cisco/a9k-4t-e": 4, "cisco/a9k-4t-l": 4,
    "cisco/a9k-8t-4-b": 8, "cisco/a9k-8t-4-e": 8, "cisco/a9k-8t-4-l": 8,
    "cisco/a9k-8t-b": 8, "cisco/a9k-8t-e": 8, "cisco/a9k-8t-l": 8,
    "cisco/a9k-mpa-2x10ge": 2, "cisco/a9k-mpa-4x10ge": 4,
    # MX Series Interface Module Reference: "10-Gigabit Ethernet ... with XFP"
    "juniper/dpc-r-4xge-xfp": 4, "juniper/dpc-r-4xge-xfp-v": 4,
    "juniper/dpce-2xge-xfp": 2, "juniper/dpce-2xge-xfp-v960": 2,
    "juniper/dpce-20ge-2xge": 2, "juniper/dpce-20ge-2xge-v960": 2,
    "juniper/mic-3d-2xge-xfp": 2, "juniper/mic-3d-2xge-xfp-v": 2,
    "juniper/mic-3d-4xge-xfp": 4, "juniper/mic-3d-4xge-xfp-v": 4,
}


def test_the_ethernet_xfp_rate_is_a_type_both_targets_have():
    """`10gbase-x-xfp` is TYPE_10GE_XFP in netbox-community/netbox
    (netbox/dcim/choices.py at 785d0b90) and in nautobot/nautobot
    (nautobot/dcim/choices.py at 6e55bf7c). It is the cage default too, so
    stating it changes no export - it turns the default into a fact."""
    assert dx.XFP10G_ATTR == ("xfp-10g", "10gbase-x-xfp")
    assert dx.PART_IFACE["std/xfp"] == dx.XFP10G_ATTR[1]
    assert dx.cage_type("std/xfp", {"xfp-10g": 4}) == "10gbase-x-xfp"
    assert not dx.cage_family_needs_a_rate("std/xfp", {"xfp-10g": 4})


def test_the_ethernet_xfp_rate_is_last_so_no_stated_rate_changes():
    """A card stating OC-192 or a PON flavour keeps it; the new row is only
    reached by a card that states nothing else in the family."""
    assert dx.cage_type("std/xfp", {"oc192": 1, "xfp-10g": 1}) == "sonet-oc192"
    assert dx.cage_type("std/xfp", {"10g-epon": 4, "xfp-10g": 4}) == "10g-epon"


def test_the_xfp_cage_count_is_not_a_rate():
    """`xfp: N` counts cages on every XFP card, the PON ones included, so the
    rate attr is `xfp-10g` and not `xfp` - and there is no ("xfp", "10g")
    PART_MEDIA row, because the FWLT-A places its XGS-PON cages as
    `media: xfp, speed: 10g` and a placement's type outranks the card's."""
    assert "xfp" not in {a for a, _t in dx.FAMILY_ATTRS["xfp"]}
    assert ("xfp", "10g") not in dx.PART_MEDIA
    assert dx.placed_type({"ref": "std/xfp@1",
                           "attrs": {"media": "xfp", "speed": "10g"}}) is None


def test_the_ethernet_rate_is_not_a_media_value():
    """A card attr is a rate statement, as `qsfp-dd-800g` is."""
    assert "xfp-10g" not in lint.PLUGGABLE_CAGES
    assert "10g" in yaml.safe_load(
        (ROOT / "spec/schemas/speeds.yaml").read_text())["speeds"]


@pytest.mark.parametrize("ref,count", sorted(ETHERNET_XFP.items()))
def test_an_ethernet_xfp_card_states_its_rate(ref, count):
    d = _modules().get(ref)
    if d is None:
        pytest.skip(f"{ref} is not in this library")
    attrs = d.get("attrs") or {}
    assert attrs.get("xfp-10g") == count, f"{ref} lost its `xfp-10g: {count}`"
    n = sum(1 for p in d["parts"] if isinstance(p, dict)
            and p["ref"].split("@")[0] == "std/xfp")
    assert n == count
    assert dx.cage_type("std/xfp", attrs) == "10gbase-x-xfp"


def test_no_sonet_or_pon_card_states_the_ethernet_rate():
    """Checked against each card's source before it took the attr: a card whose
    XFPs run OC-192 or a PON flavour must not also claim 10GbE."""
    others = {a for a, _t in dx.FAMILY_ATTRS["xfp"]} - {"xfp-10g"}
    both = sorted(ref for ref, d in _modules().items()
                  if "xfp-10g" in (d.get("attrs") or {})
                  and others & set(d.get("attrs") or {}))
    assert not both, both


def test_the_fwlt_a_still_exports_xgs_pon():
    """The card whose placement attrs would have been retyped by a PART_MEDIA
    row, read off the committed export."""
    p = LIB / "exports/netbox/module-types/Nokia/FWLT-A.yaml"
    if not p.exists():
        pytest.skip("the FWLT-A export is not in this library")
    types = {i["type"] for i in (yaml.safe_load(p.read_text()) or {}).get("interfaces") or []}
    assert types == {"xgs-pon"}, types


@pytest.mark.parametrize("media,speed,expected", [
    ("sfp56", "50g", "50gbase-x-sfp56"),
    ("qsfp56", "200g", "200gbase-x-qsfp56"),
    ("qsfp112", "400g", "400gbase-x-qsfp112"),
    ("osfp", "400g", "400gbase-x-osfp"),
    ("osfp", "800g", "800gbase-x-osfp"),
])
def test_a_card_cage_that_states_its_media_types_from_it(media, speed, expected):
    """A ConnectX card's cages join a group stating `media` and `speed`, the way a
    device's placements do. The newer generations had no PART_MEDIA row, so an
    SFP56 port fell to the cage default and exported 1000base-x-sfp."""
    part = {"ref": "std/sfp@1", "attrs": {"media": media, "speed": speed}}
    assert dx.placed_type(part) == expected


def test_a_cage_its_placement_types_is_not_asked_for_a_rate():
    """L96 asks for a rate the export would otherwise take from the table. A cage
    whose effective attrs already type it - which route_part reads FIRST - has
    said what runs in it, as a proprietary link has; one whose media names no
    row is still asked."""
    assert not dx.cage_family_needs_a_rate("std/sfp", {}, {"media": "sfp56", "speed": "50g"})
    assert dx.cage_family_needs_a_rate("std/sfp", {}, {"media": "sfp56"})
    assert dx.cage_family_needs_a_rate("std/sfp", {}, {})


def test_no_sfp28_media_row_so_a_pon_port_stays_pon():
    """A 25GS-PON port on `media: sfp28, speed: 25g` must not type as Ethernet
    from its media; with no row the card's `xgs-pon` decides (FGUT-A, FWLT-C)."""
    assert ("sfp28", "25g") not in dx.PART_MEDIA
    part = {"ref": "std/sfp@1", "attrs": {"media": "sfp28", "speed": "25g", "pon": "25gs-pon"}}
    assert dx.placed_type(part) is None


@pytest.mark.parametrize("media,speed,expected", [
    # the rate names the modules the port takes; neither target has a
    # 100G-QSFP56 or a 200G-QSFP112 type
    ("qsfp56", "100g", "100gbase-x-qsfp28"),
    ("qsfp112", "200g", "200gbase-x-qsfp56"),
])
def test_a_cage_run_below_its_top_rate_types_by_the_modules_it_takes(media, speed, expected):
    """MCX623106A runs 100GbE in QSFP56 cages and MCX713106A 200GbE in QSFP112
    ones; with no row, and no std/qsfp56 default, their ports exported as
    nothing at all (test_silent_drops caught sixteen)."""
    part = {"ref": "std/qsfp56@1", "attrs": {"media": media, "speed": speed}}
    assert dx.placed_type(part) == expected


def test_newer_cages_have_a_family_and_a_default():
    """A QSFP56 or OSFP cage the card does not type falls to a default instead
    of out of the export, and a QSFP56 cage is asked L96's question."""
    assert dx.PART_IFACE["std/qsfp56"] == "200gbase-x-qsfp56"
    assert dx.PART_IFACE["std/osfp"] == "400gbase-x-osfp"
    assert dx.CAGE_FAMILY["std/qsfp56"] == "qsfp"


def test_a_50g_qsfp28_card_is_not_typed_100g():
    """MCX4131A is a 40/50GbE card in a QSFP28 cage. Its group states
    `media: qsfp28, speed: 50g`; with no row the card attr `qsfp28` typed it at
    the family's 100G."""
    part = {"ref": "std/qsfp28@1", "attrs": {"media": "qsfp28", "speed": "50g"}}
    assert dx.placed_type(part) == "50gbase-x-sfp28"
    for bracket in ("tall", "short"):
        p = LIB / f"exports/netbox/module-types/NVIDIA/MCX4131A {bracket} bracket.yaml"
        if not p.exists():
            pytest.skip("the MCX4131A export is not in this library")
        d = yaml.safe_load(p.read_text()) or {}
        assert [i["type"] for i in d["interfaces"]] == ["50gbase-x-sfp28"], bracket
