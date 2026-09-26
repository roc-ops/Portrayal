#!/usr/bin/env python3
"""Export a Portrayal device manifest as DCIM device types, for NetBox and Nautobot.

Portrayal is the source of truth for the physical facts; a DCIM is one consumer
of them. This emits the schema shared by netbox-community/devicetype-library and
nautobot/devicetype-library so a device modelled here loads into either without
anyone re-typing port counts by hand.

THREE THINGS THIS DOES THAT THE NAUTOBOT-ONLY EXPORTER DID NOT.

One device type per CONFIGURATION, not per device. A configuration is a real
SKU with its own part number and airflow - 7726-32X-O-AC-F against
7726-32X-O-AC-B - and that is exactly the granularity both libraries model:
their own Edgecore entries are filed as `5912-54X-O-AC-F.yaml`. Collapsing them
lost the part number, forced `airflow` to be dropped whenever two configurations
disagreed, and left no honest way to attach an image, because an AC
front-to-back and a DC back-to-front are not the same picture.

A NOS is optional. The old exporter emitted a file only once it could resolve
switch interfaces for a NOS profile, so a CCAP chassis or an optical shelf -
whose ports are line-card bays, and which run neither ArcOS nor SONiC -
produced nothing at all, despite having console ports, module bays, a weight
and a part number. Not every device takes a NOS; that is a fact about the
device, not a reason to refuse to export it.

A NOS is data. What ArcOS calls a port is stated once, in the device's overlay
(`overlays/arcos.yaml`, `interfaces:`), and the exporter reads it from there -
it does not know any NOS by name. Every device exports under its manufacturer
with ports named by their faceplate id; a device whose overlay declares a NOS
asked for with `--nos` exports a second type with that NOS's names, filed
under the software vendor when the overlay carries an `identity:`. A `--nos`
that no overlay in the build declares is refused.

Nothing is dropped on the floor. What the target schema has no field for goes
into `comments` rather than being lost: the datasheet, the maturity this model
claims, and the attrs that have no home - power envelope, ASIC, CPU. A bay's
`accepts` list goes in its description, because neither library can yet express
it as data (netbox-community/devicetype-library#4497,
nautobot/devicetype-library#24).

  python3 dcim_export.py DEVICE_YAML --out DIR [--nos arcos] [--dist DIR]
"""
import argparse
import re
import pathlib
from pathlib import Path

import yaml

from portrayal.artifacts import Dist

from portrayal.manifest import view_parts, alias_names, config_airflow
from portrayal import optical_ports
from portrayal.faces import face_ref

# Portrayal media/speed -> DCIM interface type. Every value here is valid in
# both libraries: NetBox's enum is a strict superset of Nautobot's (227 types
# against 115) and there is nothing Nautobot accepts that NetBox does not.
# THE CAGE FAMILY AND WHAT IT RUNS AT. Every entry below is corroborated by the
# devices that place it - each one declares the cage in its own `media` attr, and
# the speed decides which member of the family it is.
#
# 773 placements used to fall out of the exports for want of a row here, in the
# same silence the `port-` prefix caused: 400 QSFP-DD at 800G, 192 OSFP at 800G,
# 80 QSFP56, 72 SFP56. An absent row reads exactly like a port that does not
# exist.
#
# THE MX304's GM/PTP PORT NOW TYPES, and that is the speed vocabulary's doing.
# It used to declare "1g/10g (reserved for future use per the guide)", which
# matched no row, and this comment called the miss correct. It is an SFP cage
# that takes 1-GbE and 10-GbE optics in a `management`-role group, so under the
# closed set it is `10g` - the caveat moved to its description - and it exports
# as a management-only 10gbase-x-sfpp, which is what the metal is. That Juniper
# does not yet support it is a fact about the software, not the port.
#
# ONE SPELLING PER RATE (#512). The keys below are spelled from the closed set in
# spec/schemas/speeds.yaml, which lint L110 holds the library to and a test holds
# this table to. A second spelling of 1G copper used to need its own row here,
# and `100/1000base-t` never got one - so the CSR180's and CSR200's eight 1G
# copper ports exported nothing.
IFACE_TYPE = {
    ("sfp", "50g"): "50gbase-x-sfp56",      # s9620-40dg, s9620-54dc: media sfp56
    ("sfp", "25g"): "25gbase-x-sfp28",
    ("sfp", "10g"): "10gbase-x-sfpp",
    ("sfp", "1g"): "1000base-x-sfp",
    ("osfp", "800g"): "800gbase-x-osfp",    # s9321-64eo - the 'o' in the model
    ("qsfp", "800g"): "800gbase-x-qsfpdd",  # every 800G qsfp here is std/qsfp-dd
    ("qsfp", "400g"): "400gbase-x-qsfpdd",
    ("qsfp", "200g"): "200gbase-x-qsfp56",  # s9301-32db, s9601-104bc: media qsfp56
    ("qsfp", "100g"): "100gbase-x-qsfp28",
    ("qsfp", "40g"): "40gbase-x-qsfpp",
    # A 20G QSFP+ IS STILL A QSFP+ CAGE. The ECS4530-54CSFP's two uplinks are sold as
    # '20G QSFP+ Uplink' - a 40G-class cage the switch runs at half rate - and a DCIM
    # interface type names the slot's standard, not the rate a vendor configures in it,
    # which is why every other QSFP+ here is 40gbase-x-qsfpp too. There is no 20G QSFP
    # standard to name instead.
    ("qsfp", "20g"): "40gbase-x-qsfpp",
    # XFP predates SFP+ and is nobody's substring, so the family test simply did
    # not look for it and the MX80's ports never typed. PART_IFACE has spelled it
    # this way all along for module ports; a test holds the two in step.
    ("xfp", "10g"): "10gbase-x-xfp",
    ("rj45", "10g"): "10gbase-t",
    ("rj45", "2.5g"): "2.5gbase-t",
    ("rj45", "1g"): "1000base-t",           # a 10/100/1000 port is `1g`, so 1000base-t
    # A 10/100 JACK IS FAST ETHERNET, and upstream names it. The ASR 9001's and
    # 9901's IEEE 1588 service LAN ports are 10/100 Mb/s by the install guide's
    # own port table (#511); before they stated a speed the default above typed
    # them 1000base-t, and without this row stating the true one would have
    # dropped them from the export instead.
    ("rj45", "100m"): "100base-tx",
    # A 10BASE-T JACK HAS NO TYPE OF ITS OWN UPSTREAM. The CommScope CX3002's IN and
    # OUT management ports are 10BASE-T by its data sheet and fell to 1000base-t the
    # same way. Neither target defines 10base-t: copper Ethernet starts at
    # `100base-tx`, which both label "100BASE-TX (10/100ME)" (NetBox dcim/choices.py
    # TYPE_100ME_FIXED at facc4235; Nautobot TYPE_100ME_FIXED at 6e55bf7c) - so a
    # 10 Mb/s jack takes that, the type whose label covers it.
    ("rj45", "10m"): "100base-tx",
}
AIRFLOW = {"front-to-back": "front-to-rear", "back-to-front": "rear-to-front"}

# A module's ports are its `parts`. Mapped by component ref, because a cage's
# ref says what the cage IS while the speed it runs at is a property of the card
# - a9k-40ge-b's forty std/sfp-ganged are SFP+, and the attrs say so.
PART_IFACE = {
    "std/sfp-ganged": "10gbase-x-sfpp",
    "common/sfp-plus-cage": "10gbase-x-sfpp",
    "std/sfp": "1000base-x-sfp",
    "std/xfp": "10gbase-x-xfp",
    "std/qsfp-ganged": "40gbase-x-qsfpp",
    "std/qsfp28": "100gbase-x-qsfp28",
    # THE NEWER CAGES HAD NO DEFAULT, so a card that did not type one dropped it
    # from the export entirely - sixteen ConnectX QSFP56 ports did (the
    # silent-drops census). Each default is the cage's own top rate; a card or
    # placement that runs it lower says so. Slugs in both targets (NetBox
    # 9bcfd739, Nautobot f9cdca3d).
    "std/qsfp56": "200gbase-x-qsfp56",
    "std/osfp": "400gbase-x-osfp",
    "std/qsfp-dd": "400gbase-x-qsfpdd",
    # CFP, CFP2 AND CXP ARE NOBODY'S SUBSTRING, exactly as XFP was not, and for
    # the same reason they were absent here: the family test in `iface_type`
    # reads the ref for "sfp", and a form factor whose name does not contain it
    # has to be named. Twenty-four 100GbE ports on fourteen Juniper MICs and
    # MPCs exported nothing at all - MIC3-3D-1X100GE-CFP, MIC3-100G-DWDM,
    # MIC6-100G-CFP2, MIC6-100G-CXP, MPC4E-3D-2CGE-8XGE, MPC5E-100G10G and
    # their vertical authors. Every one of them says 100GbE in its own
    # description, so the speed is the library's and not a guess, and all three
    # slugs are in netbox-community/netbox and nautobot/nautobot alike.
    "std/cfp": "100gbase-x-cfp",
    "std/cfp2": "100gbase-x-cfp2",
    "std/cfp4": "100gbase-x-cfp4",
    "std/cxp": "100gbase-x-cxp",
}
# What a cage RUNS AT is a property of the card, not of the cage. So the cage ref
# gives the family and the card's attrs give the speed within it.
#
# Matching by family matters because twelve modules declare more than one: an
# A9K-8HG-FLEX-TR is qsfp-dd AND qsfp28, in std/qsfp-dd and std/qsfp-ganged
# cages respectively, and an SMM 300G is qsfp28 in its QSFP cages and sfp-plus
# in its SFP ones. Applying one declared media to every cage on the card would
# retype half of them.
#
# Two earlier versions of this were wrong in opposite directions. Keeping the
# cage default unless the attr looked "faster" - compared as strings, which is
# not an ordering - meant A9K-40GE-B still exported forty 10G interfaces after
# its contract was corrected to `sfp: 40` (roc-ops/Portrayal#23). Letting the attr win
# outright then retyped every QSFP cage on the mixed cards.
CAGE_FAMILY = {
    "std/sfp-ganged": "sfp",
    "common/sfp-plus-cage": "sfp",
    "std/sfp": "sfp",
    "std/qsfp-ganged": "qsfp",
    "std/qsfp28": "qsfp",
    "std/qsfp56": "qsfp",
    "std/qsfp-dd": "qsfp-dd",
    "std/xfp": "xfp",
}
# Most specific first: a card declaring both qsfp28 and qsfp is 100G in a QSFP
# cage, because a QSFP28 cage takes a 40G optic too.
#
# AND AN SFP CAGE IS NOT ONLY AN ETHERNET CAGE. Twenty-seven SONET, ATM and
# channelized cards put an SFP in front of an OC-3, OC-12 or OC-48 port - fifteen
# Cisco SIP-700 SPAs and six Juniper MICs with their vertical authors - and
# because the only rates this table knew were Ethernet ones, all of them fell to
# the cage default and exported as Gigabit Ethernet. ~90 ports (#296).
#
# The Ethernet pair stays first so nothing about an Ethernet card changes; the
# SONET rates follow, highest first, in the same most-specific-first order.
#
# ATM TAKES ITS SONET TYPE AND THAT IS NOT A COMPROMISE. Upstream's "ATM" group
# contains exactly one choice, `xdsl`, so there is no ATM interface type to
# reach for - and there should not be. `type` names the PHYSICAL interface; ATM
# is the framing that runs over it, the way POS and channelized DS0 are. An
# OC-3 ATM port is an OC-3 port.
#
# NOR IS AN SFP OR XFP CAGE ONLY ETHERNET OR SONET: A PON OLT PORT IS NEITHER.
# The Nokia 7360 ISAM FX line cards put GPON, XGS-PON, NG-PON2 and 10G-EPON OLT
# optics in SFP and XFP cages - 112 cages on ten cards - and with only Ethernet
# and SONET rates here every one fell to the cage default: a GPON OLT port
# exported as 1000BASE-X, a 10G-EPON one as 10GBASE-X. The attr is named for the
# PON flavour and carries the port count, as `sfp: 40` does.
#
# ONLY THE FLAVOURS BOTH TARGETS DEFINE. One document is written to both trees,
# so a type either library refuses fails on import. InterfaceTypeChoices has all
# six below in netbox-community/netbox (netbox/dcim/choices.py, TYPE_EPON ..
# TYPE_NG_PON2, at 64ce9e2d) and in nautobot/nautobot (nautobot/dcim/choices.py,
# the "PON" group, at 3edb1fca). NetBox also has `bpon`, `25g-pon` and `50g-pon`;
# Nautobot has none of the three, so they are NOT here - an FGUT-A's even ports
# run 25GS-PON as well, and export as the XGS-PON every one of its ports runs.
#
# AFTER THE ETHERNET PAIR AND THE SONET RATES, so no card that already declares
# a rate changes. Among themselves, most capable first: a Multi-PON card that
# states both `xgs-pon` and `gpon` is an XGS-PON port that also runs GPON, and a
# U-NGPON card that states `ng-pon2` runs XGS-PON too.
PON_ATTRS = (("ng-pon2", "ng-pon2"), ("xgs-pon", "xgs-pon"), ("xg-pon", "xg-pon"),
             ("10g-epon", "10g-epon"), ("gpon", "gpon"), ("epon", "epon"))
PON_TYPES = frozenset(t for _a, t in PON_ATTRS)
# AN SFP112 PORT IS `other`, BECAUSE ONLY ONE TARGET NAMES IT. `sfp112` is a
# rung of the SFP ladder (spec/schemas/pluggables.yaml), and NetBox has
# TYPE_100GE_SFP112 = '100gbase-x-sfp112' (netbox-community/netbox
# netbox/dcim/choices.py at 6a009845) - but Nautobot does not: nautobot/nautobot
# nautobot/dcim/choices.py at 38953ac3 has 400gbase-x-qsfp112 and no SFP112.
# One document is written to both trees, so that slug would fail every Nautobot
# import of a card carrying it - the reason `25gs-pon` has no row either.
#
# BUT A CARD THAT STATES `sfp112` HAS STATED ITS RATE, and leaving the row out
# sent it to the cage default: sixteen 100G ports exported as 10GBASE-X SFP+,
# the #267 defect, with L96 accusing the card of a silence it did not keep.
# `other` is valid in both and says "a thing this schema has no name for",
# which for Nautobot is exactly true - the treatment PART_MEDIA already gives
# rj45-telemetry. When Nautobot adds 100gbase-x-sfp112 this becomes that slug.
#
# FIRST IN THE SFP FAMILY, as the most capable rate: an SFP112 cage takes SFP56
# and SFP28 too, so a card stating `sfp112` beside a lower rate is an SFP112
# card. No card stated it before, so nothing that exported already changes.
SFP112_ATTR = ("sfp112", "other")
# WHAT AN `other` PORT IS LABELLED WITH, by media. `other` says the schema has no
# name for the thing, so the label is the only place the connector survives -
# and it was hardcoded "RJ45", written for the Casa rj45-telemetry port, until
# the Nokia MDA2-e-XP exported 24 SFP112 cages as copper jacks (#558 review).
OTHER_LABEL = {"rj45-telemetry": "RJ45", "sfp112": "SFP112"}
# A T1/E1 JACK IS NOT ETHERNET, whichever RJ45 part draws it. The TM-3312's eight
# CES ports are traffic ports (group role `traffic`) on the bare RJ45 part, so the
# guard in iface_type let them through and the 1g default typed them 1000base-t.
# `rj48` is the library's media name for an RJ-48C jack, and every placement that
# states it carries DS1 or E1. Both targets have `t1` and `e1`, but a CES port
# takes either line (the data sheet's "8xT1/E1 CES") and nothing fixes which, so it
# is `other`, labelled with both - "a thing this schema has no name for" is less
# true here than for SMB, but naming one of the two would be a guess. A jack whose
# words name a timing function (juniper/mx204's BITS, also rj48) is caught by the
# timing path before this is asked.
TDM_LABEL = {"rj48": "T1/E1"}
# AN SFP CAGE IS NOT ALWAYS A STANDARD PORT AT ALL. The CommScope BP3400C's eight
# cages hold RR40x0 / RR36x0 digital-return receiver SFPs, the far end of a
# proprietary link from a node's DT4250N / DT4600N transmitter - not Ethernet,
# SONET or PON, so no rate in FAMILY_ATTRS is true of them, and with none stated
# they took the cage default and exported as 10GBASE-X SFP+.
#
# ON THE PLACEMENT, NOT THE CARD, and that is the point. A card-level attr covers
# every cage of its family, which is the limit SFP28_ATTR's comment records; the
# BP3400C's ninth SFP-family cage is a data port nobody documents, and a
# card-level declaration would have typed it as the digital-return link too.
# `proprietary-link: <label>` goes on each cage that carries one - or on a
# component group those cages join, which `effective_part` merges in - and
# exports as `other` labelled with its value. Like every rate statement it is
# explicit: a cage that says nothing still takes the default, and L96 still asks.
#
# THE VALUE IS THE LABEL, so it is a DCIM label: a non-empty string that fits
# NetBox's and Nautobot's 64-character `label`. Anything else is not a
# declaration, and the cage is treated as silent.
#
# ONLY A PLUGGABLE CAGE CARRIES ONE. A group is the natural way to declare it
# once, and a receiver's group holds its F-type RF outputs beside its cage; read
# on every member, the declaration retyped those jacks from `docsis` to the
# digital-return link. `pluggable_cage` is the test, and L96 names a non-cage
# part that carries the attr, since the export ignores it there.
#
# ON A DEVICE TOO. A device's own cage placement or group can say it, and
# `build` types that port the same way `build_module` types a card's.
PROPRIETARY_LINK = "proprietary-link"
LABEL_MAX = 64


def pluggable_cage(ref):
    """Is this ref a pluggable cage - the only thing a proprietary link sits in?
    PART_IFACE names the library's cages; the substrings are `iface_type`'s own
    family test, which is how a device's vendor-wrapped cages are recognised
    (OSFP and QSFP contain "sfp"; CFP and CXP are nobody's substring)."""
    r = (ref or "").split("@")[0]
    return r in PART_IFACE or any(f in r for f in ("sfp", "xfp", "cfp", "cxp"))


def proprietary_link(part_attrs):
    """The label of the proprietary link a placement declares, or None."""
    v = (part_attrs or {}).get(PROPRIETARY_LINK)
    if isinstance(v, str) and v.strip() and len(v.strip()) <= LABEL_MAX:
        return v.strip()
    return None


def other_label(part):
    """What an `other` interface placed by `placed_type` is labelled with."""
    part_attrs = part.get("attrs") or {}
    link = proprietary_link(part_attrs)
    if link and pluggable_cage(part.get("ref")):
        return link
    media = part_attrs["media"]
    return OTHER_LABEL.get(media, media.upper())
# AN 800G QSFP-DD PORT IS NOT A 400G ONE, and with only the `qsfp-dd` row the
# Nokia MDA2-e-XP's QSFP-DD800 ports would have exported as 400GBASE-X.
# `800gbase-x-qsfpdd` is in both targets (NetBox TYPE_800GE_QSFP_DD at 6a009845;
# Nautobot TYPE_800GE_QSFP_DD at 38953ac3), and IFACE_TYPE already writes it for
# a device's 800G QSFP-DD groups. The card attr is `qsfp-dd-800g`, NOT
# `qsfp-dd800`: the port's media stays `qsfp-dd` with `speed: 800g` (QSFP-DD
# HW 6.3 covers QSFP-DD800 in the same cage), and `qsfp-dd800` is kept out of
# the media vocabulary on purpose - see spec/schemas/pluggables.yaml. A card
# attr is a rate statement, as `oc48` and `xgs-pon` are, not a media value.
# FIRST, so a card stating it wins; every 400G card states only `qsfp-dd` and
# is unchanged.
QDD800_ATTR = ("qsfp-dd-800g", "800gbase-x-qsfpdd")
# AN SFP28 CARD WAS EXPORTING AS SFP+, because the family knew no 25G rate: a
# card stating only `sfp28` fell to the cage default. `25gbase-x-sfp28` is in
# both targets (NetBox TYPE_25GE_SFP28 at 6a009845, Nautobot at 38953ac3) and
# IFACE_TYPE already writes it for a device's 25G SFP groups.
# AFTER `sfp-plus`, NOT BEFORE IT, and that is deliberate. Five Cisco cards -
# the four A9K/A99-4HG-FLEX and the A9903-8HG-PEC - state `sfp-plus` AND
# `sfp28` on one strip of std/sfp-ganged cages, and one card-level attr cannot
# say which cage is which; placed first, this row would retype all of their
# SFP+ ports as SFP28. Placed here they keep exporting exactly what they did.
SFP28_ATTR = ("sfp28", "25gbase-x-sfp28")
# AN ETHERNET XFP CARD HAD NOTHING TO STATE. The family listed OC-192 and the PON
# flavours, so L96 asked twenty-one 10GbE cards - the ASR 9000 A9K-4T/8T line
# cards and 10GE MPAs, the Juniper DPC/DPCE and MIC-3D XFP cards - for a rate
# none of them could give, and the only way to quiet it was a baseline entry
# that read like an unanswered question.
#
# THE ATTR IS `xfp-10g`, spelled as `qsfp-dd-800g` is: the cage media, then the
# rate from spec/schemas/speeds.yaml. NOT `xfp`, which every XFP card already
# uses to COUNT its cages - the PON cards state `xfp: 4` beside their flavour,
# and reading that as a rate would retype their OLT ports as 10GbE. A card attr
# is a rate statement, as `oc192` and `xgs-pon` are, not a media value.
#
# NOR A PART_MEDIA ROW for ("xfp", "10g"). The FWLT-A places its cages as
# `media: xfp, speed: 10g` with no `pon`, and a placement's own type outranks
# the card's - so that row would type its XGS-PON ports as Ethernet.
#
# `10gbase-x-xfp` is in both targets (NetBox TYPE_10GE_XFP at 785d0b90,
# Nautobot TYPE_10GE_XFP at 6e55bf7c), and it is the cage default already, so
# stating it changes no export - it turns a default into a fact.
#
# LAST IN THE FAMILY, after OC-192 and the PON flavours, so no card that already
# states a rate changes, as PON_ATTRS was placed after the Ethernet pair.
XFP10G_ATTR = ("xfp-10g", "10gbase-x-xfp")
FAMILY_ATTRS = {
    "sfp": (SFP112_ATTR,
            ("sfp-plus", "10gbase-x-sfpp"), SFP28_ATTR, ("sfp", "1000base-x-sfp"),
            ("oc48", "sonet-oc48"), ("oc12", "sonet-oc12"), ("oc3", "sonet-oc3"))
           + PON_ATTRS,
    "qsfp": (("qsfp28", "100gbase-x-qsfp28"), ("qsfp", "40gbase-x-qsfpp")),
    "qsfp-dd": (QDD800_ATTR, ("qsfp-dd", "400gbase-x-qsfpdd")),
    # AN XFP CAGE IS NOT ONE RATE EITHER, and this entry said it was - the empty
    # tuple meant "nothing to declare", so L96 never asked and the cards below
    # were not even in #296's census. The sweep over the committed exports found
    # them: SPA-OC192POS-XFP and MIC-3D-1OC192-XFP put an OC-192 port behind an
    # XFP, exporting as 10GbE. Both are ~10 Gb/s and the framing is what differs,
    # which is exactly why the cage cannot say.
    #
    # An XFP card that states nothing takes the 10GbE default as before, and an
    # `xfp` row would read a PON card's `xfp: 4` as 10GbE - the FWLT-A (NG-PON2)
    # and FPXT-A/B (10G-EPON) state their flavour instead. An Ethernet card
    # states `xfp-10g` (XFP10G_ATTR).
    "xfp": (("oc192", "sonet-oc192"),) + PON_ATTRS + (XFP10G_ATTR,),
}


def cage_family_needs_a_rate(ref, attrs, part_attrs=None):
    """Is this cage about to be typed by the TABLE rather than by the card?

    `cage_type` falls back to PART_IFACE when a card declares no media attr for
    its cage's family, and that fallback is a default standing in for a fact.
    1215 placements across 114 cards reached it, and at least seven cards were
    typed wrong by it - `dpce-r-40ge-sfp` exported forty 10G interfaces on a
    40x1GbE card (#267), `mic3-3d-2x40ge-qsfpp` two 100G on a 40GbE MIC, and
    `roc-ops/Portrayal#23` is the same defect three years earlier. It returned because
    nothing counted how often the default was reached.

    L96 asks this question of every module; `export_modules` prints the count.
    A family with no attrs to declare is not a gap. XFP used to be counted as
    one, and is not: OC-192, PON and 10GbE all run in the same cage.

    `part_attrs` are the placement's effective attrs: a cage that declares
    `proprietary-link` has said what runs in it, and `placed_type` types it
    before the table is ever reached.
    """
    if proprietary_link(part_attrs):
        return False
    # NOR A CAGE ITS OWN PLACEMENT TYPES. `route_part` asks `placed_type` before
    # the table, so a cage whose effective attrs name a PART_MEDIA row - a
    # ConnectX card's SFP56 group, `media: sfp56, speed: 50g` - never reaches the
    # default this question is about.
    if part_attrs and placed_type({"ref": ref, "attrs": part_attrs}):
        return False
    wants = FAMILY_ATTRS.get(CAGE_FAMILY.get(ref, ""), ())
    return bool(wants) and not any(attrs.get(a) for a, _t in wants)


def cage_type(ref, attrs):
    """The interface type for one cage on one card."""
    for attr, t in FAMILY_ATTRS.get(CAGE_FAMILY.get(ref, ""), ()):
        if attrs.get(attr):
            return t
    return PART_IFACE.get(ref)


PART_CONSOLE = {"std/rj45-ganged": "rj-45", "common/rj45-shielded": "rj-45",
                "std/usb-a": "usb-a"}

# The four-part RJ45 family (sweep_rj45.py / docs/rj45-family-design.md), keyed
# by the FULL ref including @major because a version bump inside this family
# changes what the jack IS, not just its shape: std/rj45@2 and
# std/rj45-ganged@2 are the swept bare jack (console/aux/timing, no lamps);
# common/rj45-eth@1 and common/rj45-ganged-eth@1 are the swept lamped jack
# (Ethernet). Checked in build_module BEFORE the version-less PART_CONSOLE/
# PART_IFACE maps below, on the un-stripped ref, so an unswept std/rj45@1 -
# RE-S-2000, JNP10K-RE1, the MX2000 RCBs, and every other Juniper RE card
# still on the old bare ref - keeps falling through exactly as it always did,
# rather than an id-blind version-less "std/rj45" key exporting its Ethernet
# management jack as a console port (the rj45-common fix round). std/rj45@1
# and std/rj45-ganged@1 old refs are unaffected: the ganged one was already
# in PART_CONSOLE version-less (both its versions read the same either way);
# the plain one still drops out of export, as before this family existed.
FAMILY_PART = {
    "std/rj45@2": ("console", "rj-45"),
    "std/rj45-ganged@2": ("console", "rj-45"),
    "common/rj45-eth@1": ("iface", "1000base-t"),
    "common/rj45-ganged-eth@1": ("iface", "1000base-t"),
}

# ...AND FAMILY_PART IS A FALLBACK, NOT A DECISION. #125 gave std/rj45@2 seven
# jobs - console, aux, serial; ToD, BITS, 1PPS, sync; telemetry - so the ref can
# no longer carry the DCIM type, which is the lesson recorded a few lines below
# and learned twice already (roc-ops/Portrayal#27, #29). Reading the ref alone exported seven
# Juniper timing jacks as CONSOLE PORTS. So the placement's own words are read
# first: an id, role or media naming a timing function makes an `other` interface
# labelled with that function - the treatment PART_RF already gives an SMB timing
# input, which says "a thing this schema has no name for" instead of naming a
# neighbour - and one naming a console keeps the console path. Anchored on
# whitespace or a hyphen so a token cannot fire inside an unrelated word
# ("contact", "topology"), the same anchoring lint.RJ45_BARE uses.
RJ45_TIMING = re.compile(
    r"(^|[\s-])(gm-ptp|1588|bits|tod|pps|sync|ptp|ics|clk)([\s-]|$)", re.I)
RJ45_CONSOLE = re.compile(r"console|aux|serial|(^|[\s-])con([\s-]|$)", re.I)

# A D-SUB CONSOLE. common/db9-receptacle is mostly alarm-out and stays in
# NOT_A_DCIM_PORT, but the 7750 SF/CPM4 cards seat one as the RS-232 Console
# (SR12 Table 6), and dropping it left their reserved AUX jack as the only
# console port. Narrower than RJ45_CONSOLE on purpose: `aux`, `craft` and
# `serial` D-subs are not claimed here, only a placement that says `console`.
DB9_CONSOLE_REF = "common/db9-receptacle"
DB9_CONSOLE = re.compile(r"(^|[\s-])console([\s-]|$)", re.I)


def db9_words(part):
    a = part.get("attrs") or {}
    return f"{part.get('id') or ''} {a.get('role') or ''} {a.get('function') or ''}"


def rj45_words(part):
    a = part.get("attrs") or {}
    return f"{part.get('id') or ''} {a.get('role') or ''} {a.get('function') or ''} " \
           f"{a.get('media') or ''} {part.get('group') or ''}"


def rj45_timing_label(part):
    """The timing function this RJ45 placement names, upper-cased, or None."""
    m = RJ45_TIMING.search(rj45_words(part))
    return m.group(2).upper() if m else None

# RF and timing connectors. These are INTERFACES, not front ports: a front port
# in both libraries is a patch-panel pass-through and requires a rear_port to
# terminate on, which a connector on a line card does not have. Emitting them as
# front ports made 21 module types invalid before this was noticed.
#
# The connector is not the signal. Casa's 6+12 I/O cards carry DOCSIS on MCX and
# its QAM/US I/O cards carry it on F, so both are `docsis` and the label records
# which connector. The SMB ports on Cisco route processors are gps-10mhz and
# gps-1pps - timing inputs, not network interfaces - so they take `other`, which
# says "a thing this schema has no name for" rather than naming a neighbour.
# An appliance inlet that accepts a C13 cord is a C14 on the equipment side, and
# both DCIMs name it from the inlet.
#
# c20-inlet is here before anything places it. Nothing in the library uses it
# yet, so the entry is unreachable today - but an unmapped inlet does not raise,
# it just drops the power port, and a port that disappears without an error is
# the worst way to find out about a part somebody added.
PART_POWER = {
    "std/c14-inlet": "iec-60320-c14",
    "std/c20-inlet": "iec-60320-c20",
    # NOT AN IEC CONNECTOR, AND UPSTREAM HAS A ROW FOR IT ANYWAY. Anderson's
    # Saf-D-Grid takes 20 A at 600 V through the space an IEC C14 uses for 10 A
    # at 250, which is why Cisco's 1600 W ASR 9901 supply takes one and why
    # Juniper and Dell both list it. `saf-d-grid` is NetBox's own
    # PowerPortTypeChoices value, label "Saf-D-Grid", and nautobot mirrors it -
    # so this needs none of the `other` hedging common/dc-barrel gets.
    "std/saf-d-grid": "saf-d-grid",
    # A DC SUPPLY HAS AN INLET TOO, and this one had no row, so
    # dell/psu-1100w-dc-14g exported no power port at all while its two AC
    # siblings in the same family each exported theirs. Nothing distinguished
    # that from a supply drawn without an inlet. `dc-terminal` is a power-port
    # type in netbox and nautobot alike; the part is the -48 V receptacle taking
    # Dell 6RYJ9, which is why it is a dell/ part and not a std/ one.
    "dell/dc-terminal-6ryj9": "dc-terminal",
    # AND SO DOES A FIXED-SUPPLY CHASSIS, where the terminal block IS the inlet
    # and there is no module between it and the metal. The Edgecore CSR200 and
    # CSR180 land -48 V on two three-pole barrier strips bolted to the faceplate,
    # so the same `dc-terminal` row applies for the same reason it applies to the
    # Dell receptacle - it is where a supply's wire is landed, and upstream has a
    # name for exactly that.
    "common/dc-terminal-27": "dc-terminal",
    "common/dc-terminal-24": "dc-terminal",
    # A PLUGGABLE TWO-POLE BLOCK IS WHERE THE WIRE LANDS TOO, so the same row: the
    # ECS4530-54CSFP-DC-I takes -48 V in a screw-clamp plug seated in a header, the
    # plug pulled out whole rather than lugs lifted off screws.
    "common/dc-terminal-plug-2": "dc-terminal",
    # AND A FOUR-POLE ONE CARRYING TWO FEEDS: the TM-7124S lands -48 V A and B
    # (-48VA RETA -48VB RETB) in one pluggable screw-clamp header on the chassis
    # face. It is still where a supply's wire is landed, so the same row.
    "telco-systems/tm-7124s-dc-feed": "dc-terminal",
    # AND THE XM-8424H's DC SUPPLY MODULE: a smaller two-pole screw-clamp plug (20.1 mm
    # against the ECS4530's 32.1), so its own part, landing the -36 to -72 V feed. The same row.
    "telco-systems/xm8424-dc-plug": "dc-terminal",
    # AND THE XM-3352's DC SUPPLY: a three-pole screw-clamp plug, the same row.
    "telco-systems/xm3352-dc-plug": "dc-terminal",
    # THE XM-3352's AC SUPPLY TAKES A C5 CORD IN A CLOVERLEAF C6 INLET. `iec-60320-c6` is a
    # PowerPortTypeChoices value in both targets, as `iec-60320-c14` is.
    "telco-systems/xm3352-ac-inlet": "iec-60320-c6",
    # A BARREL JACK IS NOT A TERMINAL BLOCK, and upstream has no row for one, so
    # this takes `other` - the treatment PART_RF gives an SMB timing input, which
    # says "a thing this schema has no name for" instead of naming a neighbour.
    # Calling it `dc-terminal` would put a 12 V coaxial jack in a DCIM as a -48 V
    # lug pair, which is a wrong answer where this is merely an unnamed one.
    "common/dc-barrel": "other",
}

# ...AND WHAT A SUPPLY SAYS WHEN IT DRAWS NO INLET.
#
# PART_POWER reads a COMPOSED inlet, which is the strong form and the one to
# prefer: the part carries a panel cutout, a standard and a size. But half the
# PSU catalogue draws no inlet part at all - 31 of 61 - and they are not 31
# oversights. Most are DC supplies whose power entry is a screw-terminal block,
# and the library has one DC terminal component against two IEC ones, so the
# studs were drawn as ELEMENTS in the skin instead. Their contracts say so in
# prose ("two-stud screw-terminal block under a hinged plastic cover") and the
# element is right there, named `terminal-block` or `terminals` or `dc-input`
# depending on who typed it - which is a spelling convention, not a fact, and
# reading it would be the `port-` prefix defect again (#251).
#
# So the supply DECLARES it, in one attr, from a closed vocabulary. `attrs.inlet`
# is not new: the three Dell supplies have carried `c14`, `c20` and `dc-terminal`
# since they were modelled, agreeing with the part each of them also composes.
# This makes the token answer on its own when there is no part to compose.
#
# `none` IS A CLAIM, NOT A BLANK. It says the supply has no inlet because the
# CHASSIS carries it - true of the MX960, whose four C20 receptacles sit on an
# inlet strip above the supplies and are exported by `build` (#286). A supply
# that simply has not been looked at says nothing, and L95 counts it.
#
# `other` IS FOR A REAL INLET UPSTREAM CANNOT NAME, the treatment PART_RF gives
# an SMB. It is NOT for one we have not identified: the MX240's supply says "one
# C-type appliance inlet", which is some IEC 60320 receptacle and therefore
# something upstream DOES have a type for - so it stays unanswered and counted
# rather than filed as `other`, which would be a wrong answer dressed as a
# modest one.
INLET_TYPE = {
    "c14": "iec-60320-c14",
    "c20": "iec-60320-c20",
    "dc-terminal": "dc-terminal",
    "other": "other",
    "none": None,
}

# What the PLACEMENT says runs through the connector, when it says.
#
# A housing cannot carry this. Ten identical `common/sfp-plus-cage` can be eight
# 1G and two 10G, and an 8P8C shell is equally an Ethernet port, a console and a
# telemetry link - roc-ops/Portrayal#27 and #29 are the same defect seen twice. The
# library answers both the same way: `attrs` on the placement, which thirty-odd
# parts already carried before either issue was filed.
#
# Keyed (media, speed) and falling back to (media, None), because a medium that
# runs at one rate does not repeat it - rj45-telemetry has no speed to give.
#
# rj45-telemetry is `other` deliberately. It is the Casa switch BDM's link to a
# rectifier shelf: an 8P8C housing carrying a proprietary monitoring protocol,
# which is neither Ethernet nor a console. `other` says "a thing this schema has
# no name for", and that is exactly true; typing it rj-45 console would invite
# somebody to patch it into a terminal server.
PART_MEDIA = {
    ("sfp", "1g"): "1000base-x-sfp",
    ("sfp-plus", "10g"): "10gbase-x-sfpp",
    ("qsfp", "40g"): "40gbase-x-qsfpp",
    ("qsfp28", "100g"): "100gbase-x-qsfp28",
    ("qsfp-dd", "400g"): "400gbase-x-qsfpdd",
    # A PLACEMENT'S OWN 800G, so a QSFP-DD800 port that says so types from
    # itself; the card's `qsfp-dd-800g` gives the same answer (QDD800_ATTR).
    ("qsfp-dd", "800g"): "800gbase-x-qsfpdd",
    ("sfp112", "100g"): "other",
    ("rj45-telemetry", None): "other",
    # COPPER ETHERNET AT A STATED RATE. An 8P8C shell says nothing about speed,
    # so these only ever apply where the PLACEMENT declares one - which is the
    # whole point of this table. The R740xd's NDC is the case: four identical
    # dell/rj45-port-14g of which two are 10GBASE-T, and no housing, ref or
    # family fallback can tell them apart. #287.
    ("rj45", "10g"): "10gbase-t",
    ("rj45", "1g"): "1000base-t",
    # AN MRJ21 IS SIX COPPER GIGABIT PORTS BEHIND ONE CONNECTOR. Neither library has
    # an MRJ21 type, and needs none: an interface type names the signal, and each
    # port is 10/100/1000 copper. The placement says `media: mrj21, speed: 1g` and
    # lists its six ports in `interfaces:` (the Nokia 7750 M48-1GB-XP-TX's eight
    # connectors, 48 x 1000base-t); a connector without that list would export as
    # one port and undercount by five.
    ("mrj21", "1g"): "1000base-t",
    # THE 10/100 ROW IFACE_TYPE ALREADY HAS, for a card. Without it a card's
    # stated `speed: 100m` fell through to FAMILY_PART, whose answer for an
    # Ethernet jack is 1000base-t - the Nokia CCM-e's mgmt and OES ports.
    ("rj45", "100m"): "100base-tx",
    ("rj45", "10m"): "100base-tx",          # the CX3002's 10BASE-T ports; see IFACE_TYPE
    # A CFP2 STATING 200G IS NOT THE CAGE'S 100G. With no row the Nokia
    # ME3-200GB-CFP2-DCO's ports fell to PART_IFACE's std/cfp2 default and
    # exported as 100gbase-x-cfp2. Unlike SFP112 the slug is in both targets:
    # NetBox TYPE_200GE_CFP2 at 6a009845, Nautobot TYPE_200GE_CFP2 at 38953ac3.
    ("cfp2", "200g"): "200gbase-x-cfp2",
    # A CARD'S NEWER CAGES TYPE FROM ITS GROUP. An NVIDIA ConnectX card states
    # `media: sfp56, speed: 50g` (or qsfp56 / qsfp112 / osfp) on the group its
    # cages join, and with no row here they fell to the cage default - an SFP56
    # port exported as 1000base-x-sfp. The card-level attrs in FAMILY_ATTRS name
    # rates by the older cage generations only. Every slug below is in both
    # targets: NetBox dcim/choices.py at 9bcfd739, Nautobot at f9cdca3d.
    # NO ("sfp28", "25g") ROW, on purpose: a PON port whose flavour has no type
    # (the FGUT-A's and FWLT-C's `pon: 25gs-pon` on `media: sfp28`) falls through
    # to its media, and that row would export it as 25G Ethernet where the card's
    # own `xgs-pon` now answers. An SFP28 card states the card attr `sfp28: N`.
    ("sfp56", "50g"): "50gbase-x-sfp56",
    ("qsfp56", "200g"): "200gbase-x-qsfp56",
    ("qsfp112", "400g"): "400gbase-x-qsfp112",
    ("osfp", "400g"): "400gbase-x-osfp",
    ("osfp", "800g"): "800gbase-x-osfp",
    # A CAGE RUN BELOW ITS TOP RATE TYPES BY THE MODULES IT TAKES. Neither
    # target has a 100G-QSFP56 or a 200G-QSFP112 type; a QSFP56 cage at 100GbE
    # runs QSFP28 modules (MCX623106A) and a QSFP112 cage at 200GbE QSFP56 ones
    # (MCX713106A, MCX755106A), and those are the types that exist.
    ("qsfp56", "100g"): "100gbase-x-qsfp28",
    ("qsfp112", "200g"): "200gbase-x-qsfp56",
    # A 50GbE QSFP28 PORT - the MCX4131A, a 40/50GbE card in a QSFP28 cage - is
    # TYPE_50GE_QSFP28, "QSFP28 (50GE)", in both targets; its slug really is
    # spelled `50gbase-x-sfp28` (NetBox 9bcfd739, Nautobot f9cdca3d). Without the
    # row the card fell to the QSFP family's 100G.
    ("qsfp28", "50g"): "50gbase-x-sfp28",
}


def placed_type(part):
    """The interface type the placement itself declares, or None."""
    a = part.get("attrs") or {}
    # A PROPRIETARY LINK OUTRANKS EVERYTHING, media included: it says the cage
    # carries no standard port, so no media or speed row can be true of it. On a
    # cage only - see PROPRIETARY_LINK.
    if proprietary_link(a) and pluggable_cage(part.get("ref")):
        return "other"
    media = a.get("media")
    if not media:
        return None
    # A PON PORT'S FLAVOUR IS `pon`, BESIDE ITS MEDIA AND LINE RATE (the rule
    # spec/schemas/speeds.yaml states), and it outranks them: the FGUT-A's odd
    # ports are `media: sfp-plus, speed: 10g, pon: xgs-pon`, and reading only
    # the first two exported eight XGS-PON OLT ports as 10GBASE-X SFP+. A flavour
    # neither target defines (`25gs-pon`) falls through to the media as before.
    if a.get("pon") in PON_TYPES:
        return a["pon"]
    speed = a.get("speed")
    return PART_MEDIA.get((media, speed)) or PART_MEDIA.get((media, None))


PART_RF = {
    "std/f-type": ("docsis", "F"),
    "std/mcx": ("docsis", "MCX"),
    "std/smb": ("other", "SMB"),
    "std/sma": ("other", "SMA"),
    # THE PANEL-MOUNT SIBLINGS, WHICH ARE LISTED AND NOT DERIVED. Each is a
    # bezel around a core that is already here - `common/smb-jack` is "a gold nut
    # around a std/smb core" in its own words - and following composition to
    # classify a wrapper is a rule that looks right and is not. Six class:port
    # parts compose a classified core, and it would be WRONG on three of them:
    # `common/rj45-ganged-eth` composes `std/rj45-ganged`, which PART_CONSOLE
    # calls a console, and inheriting that would file every Ethernet jack in the
    # library as a console port - #27 and #29, for a third time. `common/usb-a`
    # composes a console and is a storage port. `casa/c40g-ac-inlet-panel`
    # composes FOUR inlets and would inherit one.
    "common/smb-jack": ("other", "SMB"),
    "common/sma-jack": ("other", "SMA"),
}

# std/lc-bore is the rx/tx bore of a QSFP transceiver, not a port on a device:
# the transceiver IS the module. A pull tab is furniture.
PART_SKIP = {"common/qsfp-pull-tab", "std/lc-bore"}

# EVERY PORT-CLASS PART THIS EXPORTER NEVER EMITS, AND WHY IT DOES NOT.
#
# THE TABLES ABOVE SAY WHAT A PART IS. This says what the silence means for the
# parts none of them name, and it exists because the two are indistinguishable
# from outside: a 76-port router exporting nothing and a device with no ports
# produce the same document, and it took a person reading an output and asking
# "is that number right?" to tell them apart (#251). A count cannot do that and
# neither can a green gate. A NAME can.
#
# THE ENTRY CONDITION IS MEASURED, NOT GUESSED: a part whose `class` is `port`
# or `inlet` and not ONE of whose placements anywhere in the library reaches
# either export. A part that types on some placements and not others is not
# here - `std/rj45` types 32 of its 178 and the other 146 are timing and serial
# jacks it is right to refuse, which is `iface_type`'s own rule and not silence.
#
# test_silent_drops.py holds this exhaustive. A new port-class part that exports
# nothing fails that test until whoever added it either gives it a row above or
# writes down here why it has none - which is the whole of what was missing when
# XFP, OSFP and 800G each cost the library several hundred interfaces in a row.
# Writing a reason is cheap; ten of these say "upstream has no type for this",
# which is a fine reason and a very different one from "nobody noticed".
NOT_A_DCIM_PORT = {
    # --- fibre: deferred, with a design note rather than a gap ---------------
    # A front port in both libraries requires a rear port to terminate on, and
    # nothing in a contract says which of a single-faced module's parts is the
    # trunk - exporting front ports with no rear counterpart is the shape
    # netbox#21830 rejected outright. See build_module's `rear-ports` comment
    # and docs/optical-paths-design.md C3.
    #
    # ONE ADAPTER, AND THE TWO THAT ARE NOT HERE ARE THE POINT. The FS
    # cassettes' lc-duplex-v and sc-duplex adapters export their whole fibre
    # list, because those modules declare a rear face - so they were wrong to be
    # listed here, and the register's own stale-entry test is what threw them
    # out. What is left is the single-faced case: a Smartoptics PPM coupler's
    # paths run front-to-front, so there is no trunk, plus the 117 placements on
    # DCP chassis, where the device pass has no fibre path at all.
    "common/lc-duplex-adapter": "single-faced modules have no trunk to terminate on, and the "
                                "device pass has no fibre path; optical-paths-design.md C3",
    "std/lc-bore": "the rx/tx bore of a transceiver, not a port on anything - see PART_SKIP",
    "std/sc-bore": "the SC/APC optical ports of single-faced CH3000 back plates (commscope/bp-a5, "
                   "bp-f2, bp-f4) and the half-depth passives and switch (np3*, op3*, "
                   "os32m2b); no trunk to terminate on, the same case as "
                   "common/lc-duplex-adapter",
    "common/sc-apc": "PON; the connector is the same ferrule for xg-pon (10G/2.5G) and "
                     "xgs-pon (10G/10G), which upstream separates, so the ref cannot pick one",

    # --- USB: real ports, no device-type field to put them in ----------------
    # A DCIM device type has console ports, power ports and interfaces. A USB
    # data port is none of those unless it is a console, which std/usb-a is on
    # the 26 placements PART_CONSOLE catches. The rest are storage, maintenance
    # and iDRAC Direct, and there is nowhere honest to put them.
    "std/micro-usb": "USB maintenance port (iDRAC Direct); not a console, and no device-type field fits",
    "common/usb-a": "USB storage/maintenance port; not a console - std/usb-a's console placements type via PART_CONSOLE",
    "common/usb-a-bezel": "the same USB storage/maintenance port as common/usb-a, in a taller panel bezel; split out of that name's @3 in #264 and it needs its own entry because this register keys on the NAME, not the major",
    "std/usb-c": "USB-C power input on the GL-8xEP, group `usbc-power`; power in, not a port",

    # --- connectors upstream has no type for ---------------------------------
    "common/db9-receptacle": "the placements left here are alarm relays, status and craft ports - "
                             "a dry-contact relay or a monitoring link, not an RS-232 console. Neither "
                             "library has an alarm port, and `de-9` would read as a console. A placement "
                             "that IS a console (id, role or function `console`) exports as `de-9` "
                             "through DB9_CONSOLE",
    "std/da15": "the 7750 SR-e CCM-e alarm connector - dry-contact relays and alarm inputs on a "
                "DA-15, not RS-232. Neither library has an alarm port, and no console type is a DA-15",
    "std/db25": "the 7750 SR-12 DC PEM-3 AC Supply Status port - an AC rectifier shelf's status "
                "signalling on a female DB-25, not RS-232. `db-25` upstream is a CONSOLE type and "
                "this is not a console; neither library has an alarm or status port",
    "std/vga": "VGA; neither library has a video port type",
    "common/vhdci-receptacle": "a VHDCI fan-out carrying sixteen timing outputs to a patch panel "
                               "over one cable; neither library has a type for it, and one row "
                               "could not stand for the sixteen outputs it carries",
    "common/vga-receptacle": "VGA; neither library has a video port type",
    "common/rj11-jack": "FXS analogue telephone line. `rj-11` upstream is a CONSOLE type; "
                        "an FXS line is not a console and must not read as one",

    # The three timing jacks were here until #285 gave `build` a PART_RF path
    # and added them to it. They now export as `other` with their connector,
    # and the register's stale-entry test is what took them off.

    # --- power entry on a chassis ---------------------------------------------
    # `common/dc-barrel` was here until #286 gave `build` a power path; it now
    # exports, and the register's stale-entry test is what says so.
    "nokia/sr-1-dc-terminal-block": "the 7750 SR-1 DC chassis's fixed -48 V terminal block - a "
                                    "barrier strip with its switch and cover, bolted to the rear. "
                                    "Its feeds are the chassis power inputs, stated in the "
                                    "device's power attrs; no connector here has a DCIM type",
    "casa/c40g-ac-inlet-panel": "an inlet PANEL - a bolted assembly carrying the receptacles, "
                                "not a connector; the C40G's own inlets are not modelled yet",

    # `dell/rj45-port-14g` USED TO BE HERE, as "a modelling gap, not an exporter
    # one": the NDC's four jacks carried no speed, so the exporter could not say
    # which two were 10GBASE-T and rightly refused to guess. #287 closed it by
    # reading the labels Dell's own master prints between the jacks, and the four
    # placements now declare their speed. The entry had to go with it - a register
    # of parts that export nothing is wrong about one that does.
}

# Both libraries take the same device-type document. They differ only in what
# they REQUIRE - NetBox also demands u_height and is_full_depth, which we always
# write - and in the airflow enum, where NetBox allows three values we never
# emit. So one document is written to both trees, and each is validated against
# its own schema so a divergence is caught rather than assumed away.
TARGETS = ("netbox", "nautobot")


def _natural(name):
    """`port-2` before `port-10`, and a missing name last rather than crashing."""
    return tuple((int(t), "") if t.isdigit() else (0, t)
                 for t in re.split(r"(\d+)", str(name or "")))


# THE DESCRIPTION FIELD IS 200 CHARACTERS AND THE CUT USED TO LAND WHEREVER IT
# LANDED. 266 exported descriptions across the two trees ended mid-word - "120
# Gbps of fab", "a red 'E' exh", "a9k-40ge-l, a" - and that is what a DCIM user
# reads on the device-type page, with no way to tell a truncation from a typo
# (#187).
#
# ASCII "...", NOT AN ELLIPSIS CHARACTER. Every byte of the two export trees is
# ASCII today; introducing one non-ASCII character here would make this the file
# that broke that, for one glyph's worth of neatness.
LIMIT = 200
MORE = "..."


def first_sentence(text):
    """The first sentence, with any issue citation taken off the end.

    A CITATION IS A FACT ABOUT OUR MODEL, NOT ABOUT THE HARDWARE. `(#34)` on a
    device-type page means nothing to the person reading it, and the sentence it
    sits in is carried whole in `comments` a few lines below - so the reference
    is not lost, it is where a reader who wants it will be. One description in
    the library ends this way today; the rule is here so the next one does not
    have to be noticed (#187).
    """
    text = " ".join(str(text or "").split())
    # A SENTENCE ENDS WITH A DOT AND A SPACE, OR WITH THE TEXT. `split(".")[0]`
    # ends it at the first dot of any kind, and 62 descriptions in the library
    # contain a decimal before their first full stop: the MX104's device-type
    # page read "Juniper MX104 - a 3", the MX480's "an 8RU, 7", the S9321-64E's
    # "Tomahawk5 BCM78900 at 51". That is a worse cut than the mid-word one
    # #187 was filed for, and it was on the same line.
    m = re.search(r"\.(?:\s|$)", text)
    first = text[:m.start()] if m else text
    return re.sub(r"\s*\((?:[\w.-]+/[\w.-]+)?#\d+\)\s*$", "", first)


def fit(text, limit=LIMIT):
    """`text` cut to `limit`, at the last word boundary that fits.

    A cut that lands inside a word reads as a typo; one that lands after a word
    reads as what it is. Returns the text unchanged when it fits, so the vast
    majority of descriptions are untouched.
    """
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    head = text[:limit - len(MORE)]
    # rsplit on whitespace rather than a regex: the boundary that matters is
    # where a reader sees one, and a hyphenated part number is one word.
    cut = head.rsplit(" ", 1)[0] if " " in head else head
    return cut.rstrip(" ,;:-") + MORE


def fit_items(prefix, items, limit=LIMIT):
    """`prefix` plus as many comma-separated items as fit, then how many did not.

    A word-boundary cut through a LIST still reads as a typo - "a9k-40ge-b,
    a9k-40ge-e, a" is a truncation pretending to be an entry. 158 of the 266
    were bay `Accepts:` lists, which is why this exists separately: the boundary
    a reader sees in a list is the comma, and the count is worth more than the
    two entries it replaces.
    """
    items = [str(i) for i in items]
    whole = prefix + ", ".join(items)
    if len(whole) <= limit:
        return whole
    kept = []
    for n, item in enumerate(items):
        tail = f" (+{len(items) - n - 1} more)"
        trial = prefix + ", ".join(kept + [item]) + (tail if n < len(items) - 1 else "")
        if len(trial) > limit:
            break
        kept.append(item)
    if not kept:
        return fit(whole, limit)
    return prefix + ", ".join(kept) + f" (+{len(items) - len(kept)} more)"


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s).lower())).strip("-")


def _index_expr(expr, n):
    """`{n}`, `{(n-1)*4}`: arithmetic over the port index, and nothing else.

    The overlay schema's own example for a name pattern is SONiC's
    `Ethernet{(n-1)*4}`, so the braces have to admit an expression - and an
    expression read from a data file is not something to hand to eval() whole.
    Only literals, `n` and the arithmetic operators pass; anything else is the
    overlay's mistake and is refused by name.
    """
    import ast
    tree = ast.parse(expr.strip(), mode="eval")
    ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
          ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if not isinstance(node, ok) or (isinstance(node, ast.Name) and node.id != "n"):
            raise SystemExit(f"overlay interface name {{{expr}}}: only arithmetic over n "
                             f"is allowed in a name pattern")
    return int(eval(compile(tree, "<overlay>", "eval"), {"__builtins__": {}}, {"n": n}))


def _expand(pattern, n):
    """Fill every `{...}` in a name pattern for port n. `{i}` - the breakout
    child index - is not known at the port and is left standing."""
    return re.sub(r"\{([^{}]*)\}",
                  lambda m: m.group(0) if m.group(1).strip() == "i"
                  else str(_index_expr(m.group(1), n)),
                  pattern)


def overlay_names(overlay):
    """physical id -> (NOS interface name, breakout rule or None).

    THE OVERLAY IS THE ONLY SOURCE OF A NOS NAME. This used to be a Python
    function with `if profile == "arcos"` and `if profile == "sonic"` in it,
    while the ArcOS overlay stated the same rule as data with breakout modes the
    Python never read (#63, #56). Two statements of one fact drift, and the code
    won silently. Now the exporter reads `interfaces:` - `physical` with `{n}`
    over `range`, `name` with `{n}` or arithmetic on it - and a NOS with no
    overlay has no names, rather than invented ones.
    """
    out = {}
    for rule in (overlay or {}).get("interfaces") or []:
        phys, name = rule["physical"], rule["name"]
        if "{n}" in phys:
            if not rule.get("range"):
                raise SystemExit(f"overlay interface {phys!r} has {{n}} and no range")
            lo, hi = (int(x) for x in str(rule["range"]).split("-", 1))
            for n in range(lo, hi + 1):
                out[phys.replace("{n}", str(n))] = (_expand(name, n), rule.get("breakout"))
        else:
            out[phys] = (name, rule.get("breakout"))
    return out


def breakout_note(breakout, n):
    """What the overlay says a port can be split into, as prose on the interface.

    A device type lists the ports the metal has. The 4x25G children a breakout
    makes are how a DEVICE is configured, not a fact about the type - so they go
    in the description, modes and the child naming pattern for port n, rather
    than as 96 interfaces the faceplate has not got.
    """
    modes = ", ".join(breakout.get("modes") or [])
    child = breakout.get("child-name")
    parts = [f"Breakout: {modes}" if modes else "Breakout capable"]
    if child:
        parts.append(f"children {_expand(child, n)}")
    return fit("; ".join(parts))


# WHICH GROUPS HOLD PORTS. A group states its `role`, and that is the structural
# answer to "is this placement a network interface" - the question the exporter
# used to answer by asking whether the id started with `port-`.
#
# That spelling test dropped, in silence and with no rule anywhere to catch it:
# every one of the S9710-76D's 76 ports, because they are `fab-N` and `svc-N`
# (the export carried ZERO interfaces for a 76-port router); the ASR-9001's
# `sfp-plus-N` and `cluster-N`; the MX104's and MX150's `xe-N`; and the MaiaEdge
# Port Extender's eight 100G uplinks, which is how it was found. 271 ports on 13
# devices.
#
# THE TWO SETS ARE EXHAUSTIVE OVER THE SCHEMA'S ENUM, and a test holds that. A
# sixth role must be classified by whoever adds it rather than falling silently
# to one side - which is the whole defect this replaced, one level up.
#
# `fabric` IS A PORT ROLE (#510). The interconnect ports on a distributed
# chassis - a DDC line-card box's uplinks to its fabric boxes, and every port on
# the fabric box - are cabled like any other port, so a DCIM that tracks cables
# needs them as interfaces. They export exactly as they did when they sat in
# `traffic`: typed from the cage and speed, and not `mgmt_only`, because the
# fabric is the data path, not the way you reach the box.
PORT_ROLES = {"traffic", "fabric", "management", "service"}
NON_PORT_ROLES = {"indicator", "furniture"}


def iface_type(p, attrs, group_role=None):
    """DCIM interface type for a port placement, or None when it cannot be
    known. Family from the cage ref, speed from the attrs; an unknown
    combination is skipped rather than guessed.

    AN RJ45 IS NOT AUTOMATICALLY AN ETHERNET PORT, and this is the one family
    where the ref alone cannot say. `common/rj45-eth@1` and its ganged sibling
    are Ethernet jacks by name - that is the split docs/rj45-family-design.md
    draws and L76 polices. The bare `std/rj45@2` housing carries ToD, BITS, PPS,
    SYNC, an external reference clock, a console or an AUX port on 65 of the 73
    placements in the library, and typing those 1000base-t would put a timing
    input in a DCIM as a gigabit interface.

    The exceptions are the devices that fit an Ethernet port on the bare part, so
    the test is what the DEVICE says rather than the part alone. A bare RJ45
    counts when either holds:

      - its group's role is `traffic` - the ReadyLinks GL-8xEP's eight PoE ports,
        group `gbe-poe`, media rj45 / speed 1g / PoE; or
      - the device states an Ethernet SPEED for it. Exactly one placement in the
        library does, the S9110-32X's out-of-band management jack at 1g,
        and all 64 timing and serial jacks state none - a ToD or BITS input has
        no Ethernet speed to give. The port is modelled on the bare part BY
        DESIGN, with its two lamps placed separately above the jack where a
        photograph puts them and carrying the HIG's own state table; fitting the
        `-eth` part instead would add two more lamps inside the jack, where the
        hardware has none.
    """
    ref = p["ref"]
    # OSFP BEFORE SFP, AND THAT ORDER IS THE WHOLE POINT: "osfp" contains "sfp",
    # so an OSFP cage read as an SFP one. It silently cost the S9321-64EO all 192
    # of its 800G ports, and had any of them been declared at 25g it would have
    # exported them as SFP28 instead - a wrong answer rather than a missing one.
    fam = ("osfp" if "osfp" in ref else
           "qsfp" if "qsfp" in ref else
           "rj45" if "rj45" in ref else
           "xfp" if "xfp" in ref else
           "sfp" if "sfp" in ref else None)
    if fam is None:
        return None
    # A MANAGEMENT JACK IS ETHERNET ON THE DEVICE'S WORD, BEFORE THE GUARD BELOW.
    # The guard keeps ToD, BITS and serial jacks on the bare part out of the DCIM,
    # and it asks for a speed because a timing input has none to give. `role: mgmt`
    # is a stronger statement than a speed - it says what the jack is FOR - and the
    # AS5912-54X and CSR310 say it with no speed, so behind the guard they never
    # typed at all.
    #
    # BUT ONLY WHEN IT STATES NO SPEED. A stated speed is the device's own word
    # on the rate, and returning 1G ahead of it typed the Nokia SR-1's 10/100
    # `mgmt` jack 1000base-t while `oes-1` beside it, identical but for its
    # role, gave 100base-tx. A mgmt jack that states one takes the path below,
    # where the guard lets it through because it has a speed.
    if fam == "rj45" and attrs.get("role") == "mgmt" and not attrs.get("speed"):
        return "1000base-t"                    # a copper management port is 1G
    if (fam == "rj45" and "-eth" not in ref
            and group_role != "traffic" and not attrs.get("speed")):
        return None
    # AFTER THE GUARD, NOT BEFORE IT: only a jack the guard already lets through is
    # retyped. Ahead of it this reached juniper/mx104's ext-ref-clock, a bare rj48
    # timing input in no traffic group that has never exported, and invented it.
    if fam == "rj45" and attrs.get("media") in TDM_LABEL:
        return "other"                         # T1/E1, see TDM_LABEL
    # A DEFAULT IS A GUESS, so only the families that have a settled one carry it.
    # An OSFP is 400G or 800G and nothing makes one likelier, so an OSFP that does
    # not say its speed does not type - which is this function's own rule.
    speed = attrs.get("speed") or {"qsfp": "100g", "sfp": "25g", "rj45": "1g"}.get(fam)
    return IFACE_TYPE.get((fam, speed)) if speed else None


def mgmt_only(attrs, group_role):
    """Is this port management-only? EITHER WAY OF SAYING IT COUNTS: the
    per-port `attrs.role: mgmt`, or a group whose `role` is `management`. One
    rule for a device port (`build`) and a card's port (`build_module`)."""
    return attrs.get("role") == "mgmt" or group_role == "management"


def effective_part(part, groups):
    """A card's `parts:` entry as the exporter reads it, and its group's role:
    (the part with its group's attrs merged under its own, role or None).
    The same precedence `build`'s attrs_of gives a device placement - and
    render.py's group_merged_attrs gives the drawing - so the export types a
    port from what the drawing says it is."""
    grp = (groups or {}).get(part.get("group")) or {}
    if not grp:
        return part, None
    return ({**part, "attrs": {**(grp.get("attrs") or {}), **(part.get("attrs") or {})}},
            grp.get("role"))


def route_part(part, attrs, defaulted=None):
    """Where `build_module` files one card part: (kind, row).

    kind is `network`, `timing`, `rf`, `console`, `power`, `skip` (PART_SKIP)
    or None (no branch matched - the caller's `dropped`). Only a `network` row
    is a port a DCIM would cable as a switch interface, so only it can carry
    mgmt_only or be split by `interfaces:` (#443) - and L105 asks this same
    function, so a part that declares interfaces and routes anywhere else is a
    lint error rather than a declaration the export drops without a word.

    `part` is the EFFECTIVE part (effective_part); `attrs` is the contract's.
    """
    full_ref = part["ref"]
    ref = full_ref.split("@")[0]
    pid = str(part.get("id") or "")
    if ref in PART_SKIP:
        return "skip", None
    # The placement is more specific than the ref, so it is checked first.
    # Reaching PART_CONSOLE with an rj45-telemetry part would file a
    # rectifier link as a console port, which is how #29 read before.
    placed = placed_type(part)
    if placed:
        iface = {"name": pid, "type": placed}
        if placed == "other":
            iface["label"] = other_label(part)
        return "network", iface
    if full_ref in FAMILY_PART:
        # Checked on the un-stripped ref, before PART_CONSOLE/PART_IFACE
        # below drop the @major and would otherwise catch every version of
        # std/rj45 alike - see FAMILY_PART's comment for why that is wrong.
        # What the PLACEMENT says beats what the ref says, both ways round.
        timing = rj45_timing_label(part)
        if timing:
            return "timing", {"name": pid, "type": "other", "label": timing}
        if RJ45_CONSOLE.search(rj45_words(part)):
            return "console", {"name": pid or "Console", "type": "rj-45"}
        kind, t = FAMILY_PART[full_ref]
        if kind == "console":
            return "console", {"name": pid or "Console", "type": t}
        return "network", {"name": pid, "type": t}
    if ref == DB9_CONSOLE_REF and DB9_CONSOLE.search(db9_words(part)):
        return "console", {"name": pid, "type": "de-9"}
    if ref in PART_POWER:
        return "power", {"name": pid or "Inlet", "type": PART_POWER[ref]}
    if ref in PART_CONSOLE:
        return "console", {"name": pid or "Console", "type": PART_CONSOLE[ref]}
    if ref in PART_RF:
        t, connector = PART_RF[ref]
        # The type says what the signal is; the label keeps the connector,
        # which is the part the type cannot express.
        return "rf", {"name": pid or t, "type": t, "label": connector}
    if ref in PART_IFACE:
        if defaulted is not None and cage_family_needs_a_rate(ref, attrs):
            defaulted[ref] = defaulted.get(ref, 0) + 1
        network = {"name": pid, "type": cage_type(ref, attrs)}
        # The one FAMILY_ATTRS row that writes `other` is SFP112_ATTR.
        if network["type"] == "other":
            network["label"] = OTHER_LABEL[SFP112_ATTR[0]]
        return "network", network
    return None, None


def device_timing_row(p, a):
    """The row `build` lists a device placement under as a timing or RF input,
    or None. `a` is the placement's attrs with its group's merged under them."""
    rf_ref = p["ref"].split("@")[0]
    if rf_ref in PART_RF:
        t, connector = PART_RF[rf_ref]
        return {"name": p.get("id") or t, "type": t, "label": connector}
    if p["ref"] in FAMILY_PART:
        # A BARE RJ45 THAT NAMES A TIMING FUNCTION, read from the
        # placement's own words rather than from the ref - #125 gave
        # std/rj45@2 seven jobs, so the ref cannot carry the answer and
        # the device says which one this is. Console jacks are NOT taken
        # here: `build` already has a console path with its own test,
        # and widening this to RJ45_CONSOLE would be a different change.
        label = rj45_timing_label({**p, "attrs": a})
        if label:
            return {"name": p.get("id"), "type": "other", "label": label}
    return None


def device_port_type(p, a, group_role, names=None):
    """What `build` exports a device placement as when it is a switch port:
    (type, label, None), or (None, None, why) when it is not one.

    `names` is the overlay's (overlay_names) or None for the hardware's own
    document. L105 asks this with None, so a placement that declares
    `interfaces:` and would not export as a port is an error there instead of
    a declaration `build` drops without a word.
    """
    if device_timing_row(p, a):
        return None, None, "a timing or RF input"
    if names is None and a.get("role") == "console":
        return None, None, "a console port"
    if names is None and group_role not in PORT_ROLES:
        return None, None, f"in a group whose role is {group_role!r}, not a port role"
    if names is None and a.get("role") == "mgmt" and a.get("speed") == "10g":
        return None, None, "a 10G management SFP, listed apart from the interfaces"
    # A CAGE THAT CARRIES A PROPRIETARY LINK says what runs in it, as a
    # card's does in `placed_type`, and no speed row can be true of it.
    link = proprietary_link(a) if pluggable_cage(p["ref"]) else None
    t = "other" if link else iface_type(p, a, group_role)
    if t is None:                      # unknown combination: skip, do not guess
        return None, None, "a port the exporter cannot type"
    if link:
        return t, link, None
    if t == "other" and a.get("media") in TDM_LABEL:
        return t, TDM_LABEL[a["media"]], None
    return t, None, None


def flatten(section, prefix=""):
    """attrs are nested a section deep and sometimes deeper. Read them flat."""
    out = {}
    for k, v in (section or {}).items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and not {"value", "unit"} & set(v):
            out.update(flatten(v, f"{key}."))
        else:
            out[key] = v
    return out


def comments_for(dev, cfg_name, cfg):
    """Everything true about the device that the target schema has no field for.

    A DCIM that cannot hold a fact should still be able to show it to whoever
    opens the record, so this is prose rather than nothing.
    """
    lines = []
    if dev.get("description"):
        lines += [dev["description"].strip(), ""]
    if cfg and cfg.get("description"):
        lines += [f"Configuration `{cfg_name}`: {cfg['description'].strip()}", ""]
    # THE OTHER NAMES A DCIM USER MIGHT SEARCH FOR - the AS number, the
    # marketing name, the OEM's name (#514). NetBox and Nautobot device types
    # have one `model`, so the rest go where a reader of the record sees them.
    if alias_names(dev):
        lines += ["Also sold or listed as: " + ", ".join(alias_names(dev)), ""]

    ds = dev.get("datasheet") or {}
    if ds.get("url"):
        lines.append(f"Datasheet: {ds.get('title') or ds['url']}")
        if ds.get("title"):
            lines.append(f"  {ds['url']}")
        lines.append("")

    facts = []
    for section, vals in (dev.get("attrs") or {}).items():
        flat = flatten(vals)
        for k, v in flat.items():
            if isinstance(v, (str, int, float)) and str(v).strip():
                facts.append(f"- {section}.{k}: {v}")
    if facts:
        lines.append("Facts carried in the model that this schema has no field for:")
        lines += facts
        lines.append("")

    # WHICH DRAWING THIS RECORD CAME FROM. #48 made a device's version move when
    # its model does, and classifies a moved slot or a renamed id as a MAJOR -
    # which is exactly what invalidates a coordinate or a reference somebody
    # took out of an earlier export. A DCIM record outlives the export that made
    # it, so without this a holder cannot tell a current type from a stale one.
    if dev.get("version"):
        lines.append(f"Drawing version {dev['version']}. A major bump means a "
                     f"slot moved or an id was renamed, so anything cached from "
                     f"an earlier export may no longer line up.")
    if dev.get("maturity"):
        lines.append(f"Model maturity: {dev['maturity']}. Every dimension in the "
                     f"source records where it came from.")
    return "\n".join(lines).strip()


def module_models(dist):
    """Every model the library carries as a MODULE, for telling a FRU part
    number from a chassis one.

    Reads components.json rather than globbing contracts: the index carries
    `kind` and `attrs` for every component, which is all this needs, and it is
    published where a checkout is not."""
    return dist.module_models()


def scoped(items, cfg_name):
    """The items a configuration actually has.

    `only-in: [config, ...]` names the configurations a bay or placement exists
    in; absent means all of them, which is still the answer almost everywhere.
    The renderer filters both lists before anything reads them, and an export
    that does not do the same emits bays the chassis has not got.
    """
    out = []
    for it in items:
        only = it.get("only-in") if isinstance(it, dict) else None
        if only and cfg_name not in only:
            continue
        out.append(it)
    return out


def views_for(dev, cfg_name):
    """The views one configuration actually wears.

    A view carrying `face:` is a VARIANT and belongs only to configurations that
    bind it through `configurations.<name>.views`. Walking every view instead
    put `front-lff-12`'s twelve LFF bays into the 24-bay `base` device type -
    the bays carry no `only-in`, because the binding is what scopes them, so
    `scoped()` had nothing to filter on.

    Same rule as render.resolve_views. A device with no bindings is unaffected.
    """
    views = dev.get("views") or {}
    cfg = ((dev.get("configurations") or {}).get(cfg_name) or {})
    # A BOUND VARIANT REPLACES THE DEFAULT VIEW FOR ITS FACE - it does not join
    # it. Merely adding gave `lff-12` twelve LFF bays AND the twenty-four SFF
    # ones, which is a front this chassis cannot be built with. render.py keys
    # `resolve_views` by FACE for exactly this reason, so the view named after
    # the face drops out when something is bound to it.
    bound = {face: n for face, n in (cfg.get("views") or {}).items()
             if n in views}
    out = [views[n] for n in bound.values()]
    for n, v in views.items():
        if (v or {}).get("face") or n in bound:
            continue
        out.append(v)
    return out


def bay_signature(dev, cfg_name):
    """Which bays this configuration renders, as a comparable key.

    Two configurations are the same device type only if they are the same
    CHASSIS. Before `only-in` that could be assumed - configurations differed
    only in what was seated - but a C40G's `ac-power` genuinely has no pem-1 or
    pem-2, so collapsing it with the DC configurations would give the AC SKU two
    module bays that are not on it.
    """
    ids = []
    for view in views_for(dev, cfg_name):
        for b in scoped(view_parts(view)["bays"], cfg_name):
            ids.append(str(b.get("id") or ""))
    return tuple(sorted(ids))


def build(dev, cfg_name, cfg, overlay, dist=None, frus=None, label=None):
    ch = dev.get("chassis", {})
    cfg = cfg or {}

    # The SKU is the model, which is how both libraries file these: their own
    # Edgecore entries are 5912-54X-O-AC-F rather than one AS5912-54X.
    #
    # A `part-numbers` map does not say which of its keys is the CHASSIS. Taking
    # the alphabetically first exported the S9510-28DC as `FAN-402825-HD`: that
    # device lists only FRUs - a fan and a PSU - and the fan sorts first, so a
    # fan tray became a chassis and the switch vanished from both libraries.
    #
    # No string rule can separate the two. Edgecore's chassis SKU for the
    # AS7726-32X is `7726-32X-O-AC-F` and Celestica's for the ES1010 is
    # `R4048-F91L9-A1`; neither contains the model, and matching on the name
    # would reject both. What IS knowable is the other side: a part number that
    # names a module the library already models is a FRU. Drop those, and if
    # nothing is left fall back to the device's own model - unspecific, but a
    # switch rather than a fan. model/slug is the one field a DCIM import cannot
    # recover from; it is the primary key on both sides.
    pns = cfg.get("part-numbers") or {}
    chassis_pns = [k for k in pns if k not in (frus or ())]
    # PREFER THE CORDLESS SKU, which is the rule render.py:519 already uses to
    # stamp `data-sku` on the faceplate. The two disagreed: render named the
    # variant that ships without a cord - the chassis itself - while this took
    # whichever sorted first, so one drawing and its device type could carry
    # different part numbers for the same thing.
    #
    # Where every SKU in a configuration carries a cord, as on the AS5912-54X
    # whose AC variants are all regional, there is no cordless one to prefer and
    # the first sorted stands. That names the type after a region, which is
    # arbitrary but ORDERABLE - and orderable was the whole complaint.
    cordless = [m for m in chassis_pns
                if ((pns.get(m) or {}) if isinstance(pns.get(m), dict) else {})
                .get("power-cord") in (None, "", "none")]
    sku = (sorted(cordless) or sorted(chassis_pns) or
           [dev["model"].split(" (")[0]])[0]
    part = pns.get(sku)
    if isinstance(part, dict):
        part = part.get("part")

    model = f"{sku} {label}" if label else sku
    out = {
        "manufacturer": dev["manufacturer"],
        "model": model,
        "slug": slugify(f"{dev['manufacturer']}-{model}"),
        "u_height": float(ch.get("ru", 1)),
        "is_full_depth": True,
    }
    if part:
        out["part_number"] = part

    weight = ch.get("weight-kg")
    if weight:
        # Both schemas require a multiple of 0.01. The ASR 9910 is modelled at
        # 64.915 kg and float arithmetic turns 39.69 into 39.690000000000005,
        # so round rather than hand either straight through.
        out["weight"] = round(float(weight), 2)
        out["weight_unit"] = "kg"

    # THE CHASSIS IS WHERE AIRFLOW LIVES UNLESS A CONFIGURATION DIFFERS, which is
    # the fallback the drawing's `data-airflow` has always used
    # (manifest.config_airflow) and this did not. Eighteen
    # configurations across ten devices stated airflow only on the chassis - the
    # ASR 9000s, the fanless FS enclosure, the S9502 - and exported none at all:
    # `cfg.get` returned nothing and the key was quietly dropped. Seven of those
    # are `front-to-back` and land now; the rest are `side` and `passive`, which
    # the chassis enum allows and this map has no entry for (roc-ops/Portrayal#171).
    air = AIRFLOW.get(config_airflow(dev, cfg))
    if air:
        out["airflow"] = air

    if dev.get("description"):
        out["description"] = fit(first_sentence(dev["description"]))

    # Images, if this configuration has been rendered. front_image/rear_image are
    # booleans; the file itself is matched by slug from elevation-images/.
    if dist:
        for face in ("front", "rear"):
            if (Path(dist) / f"{dev['name']}.{cfg_name}.{face}.svg").exists():
                out[f"{face}_image"] = True

    dev_groups = dev.get("groups") or {}

    def attrs_of(p):
        g = dev_groups.get(p.get("group")) or {}
        return {**(g.get("attrs") or {}), **(p.get("attrs") or {})}

    def group_role(p):
        return (dev_groups.get(p.get("group")) or {}).get("role")

    # WHAT THE NOS CALLS EACH PORT comes from the overlay's `interfaces:` rules
    # and from nowhere else. None means no NOS: the document is the hardware's
    # own, and names its ports by the id on the faceplate.
    names = overlay_names(overlay) if overlay is not None else None

    console, mgmt_sfp, bays, powers, timing = [], [], [], {}, {}
    for view in views_for(dev, cfg_name):
        parts = view_parts(view)
        for p in scoped(parts["placements"], cfg_name):
            a = attrs_of(p)
            role, media = a.get("role"), a.get("media")
            # WHERE THE CORD GOES IN, when it goes into the chassis rather than
            # into a supply. `power-ports` used to be written in exactly one
            # place - build_module - so a device type carried none at all, and
            # a DCIM built from these exports showed the MX150 drawing power
            # from nothing. See the block above `powers` below for why that is
            # right for 39 devices and wrong for these.
            #
            # KEYED ON THE REF, exactly as build_module keys it, and not on the
            # group or the id. The two devices that place an inlet spell the
            # surrounding model differently - the MX960 puts its four C20s in
            # an `inlets` group whose term is `Inlet`, the MX150 puts its C14
            # in `mgmt` beside the console and the USB - and a rule built on
            # either spelling would have caught one of them. What the part IS
            # does not depend on which region of the faceplate it sits in.
            # RF AND TIMING, the same treatment build_module gives them.
            #
            # A 10 MHz input, a BITS port and a ToD jack are not network
            # interfaces, and `iface_type` is right to refuse them - but
            # refusing them is not the same as having nothing to say. On a CARD
            # they have exported as `other` carrying the connector or the
            # function as a label since PART_RF was written, which is the
            # schema's way of saying "a thing it has no name for". On a CHASSIS
            # they exported nothing, because `build` had no path to PART_RF at
            # all: the same jack, two answers, and only one of them decided
            # (#285). 263 placements across 33 devices.
            #
            # The label is the whole point. `other` alone says a port exists and
            # nothing else; `other` + BITS says what to plug into it.
            row = device_timing_row(p, a)
            if row:
                timing.setdefault(p["id"], row)
            if p["ref"].split("@")[0] in PART_POWER:
                powers.setdefault(p["id"], {
                    "name": p["id"] or "Inlet",
                    "type": PART_POWER[p["ref"].split("@")[0]]})
            if role == "console" and media == "rj45-serial":
                console.append({"name": "Console", "type": "rj-45"})
            elif role == "console" and p["ref"].startswith("std/usb-c"):
                console.append({"name": "Console (USB-C)", "type": "usb-c"})
            # A USB-A CONSOLE BESIDE THE RJ45 ONE: the XM-8424H prints CONSOLE over both, and the
            # data sheet lists a "USB console". `usb-a` is a console-port type in both targets.
            elif role == "console" and p["ref"].startswith("std/usb-a"):
                console.append({"name": "Console (USB-A)", "type": "usb-a"})
            elif (role == "mgmt" and a.get("speed") == "10g"
                  and not (names and p["id"] in names)):
                mgmt_sfp.append({"name": p["id"].replace("port-", ""),
                                 "type": "10gbase-x-sfpp", "mgmt_only": True,
                                 "description": "10G management port (faceplate label; "
                                                "not presented as a switch interface)"})
        for b in scoped(parts["bays"], cfg_name):
            name = (b["id"].replace("psu-", "PSU ").replace("fan-", "Fan ")
                    .replace("front-", "Front ").replace("rear-", "Rear "))
            bay = {"name": name, "position": b["id"].rsplit("-", 1)[-1]}
            # Neither library can express what a bay accepts as data yet, so it
            # goes where a person will still see it. Truncated to the 200 the
            # NetBox schema allows on a bay description.
            acc = b.get("accepts") or []
            if acc:
                bay["description"] = fit_items(
                    "Accepts: ", [a.split("/")[-1].split("@")[0] for a in acc])
            bays.append(bay)

    # Switch and management interfaces. With an overlay, a placement is an
    # interface exactly when a rule names it - `mgmt-eth` becomes `ma1` because
    # the overlay says so, not because a media attr happened to match. Without
    # one, every port that is not a console is an interface under its faceplate
    # id: unspecific, but a fact about the metal rather than a convention borrowed
    # from a NOS the box may not run.
    #
    # MANAGEMENT PORTS INCLUDED, however the device spells them. This loop used to
    # skip `attrs.role: mgmt` while the lines below mark a `management` group's
    # ports mgmt_only - two spellings of one fact, one exported and one dropped.
    # 99 management ports on 70 devices were missing for it. The 10G management
    # SFPs are the exception: `mgmt_sfp` above already lists them, with a note that
    # the faceplate port is not a switch interface, so they are not listed twice.
    listed_sfp = {i["name"] for i in mgmt_sfp}
    ports = {}
    for view in views_for(dev, cfg_name):
        for p in scoped(view_parts(view)["placements"], cfg_name):
            pid = p["id"]
            a = attrs_of(p)
            # A JACK THAT ALREADY EXPORTED AS A TIMING INPUT DOES NOT ALSO EXPORT
            # AS AN INTERFACE. build_module has had this rule since #285 - "what
            # the PLACEMENT says beats what the ref says, both ways round" - as an
            # if/elif chain that can only take one branch. This loop is a second
            # pass over the same placements and had no such guard, so a jack whose
            # words name a timing function AND whose part is in FAMILY_PART came
            # out twice under one name. It took a lamped BITS jack to show it: the
            # bare timing jacks that fill this corpus are PART_CONSOLE, which
            # iface_type declines, so the collision could not happen until a
            # timing jack was drawn with an Ethernet part.
            if pid in timing:
                continue
            if names is None and a.get("role") == "mgmt" and pid.replace("port-", "") in listed_sfp:
                continue
            # The rest of what makes a placement a switch port is one function,
            # device_port_type, because L105 asks it too: a placement declaring
            # `interfaces:` that it turns away is a lint error, not a silence.
            t, iface_label, _why = device_port_type(p, a, group_role(p), names)
            if t is None:
                continue
            # ONE CAGE, SEVERAL INTERFACES (#443). A CSFP cage presents two BiDi
            # interfaces and says so with `interfaces:`; each is exported, typed
            # from the cage, and the cage itself is not - it is where they live,
            # not one of them. Everything else presents exactly itself.
            for iid in p.get("interfaces") or [pid]:
                if names is not None:
                    if iid not in names:
                        continue
                    name, breakout = names[iid]
                else:
                    name, breakout = iid, None
                iface = {"name": name, "type": t}
                if iface_label:
                    iface["label"] = iface_label
                # EITHER WAY OF SAYING IT COUNTS. `attrs.role: mgmt` is the per-port
                # spelling; a group whose own role is `management` says the same
                # thing about every port in it, and six devices only say it that way.
                if mgmt_only(a, group_role(p)):
                    iface["mgmt_only"] = True
                if breakout:
                    iface["description"] = breakout_note(breakout, _num(iid.rsplit("-", 1)[-1]))
                # management first, then by faceplate number - the order a person
                # reads the front panel in
                ports.setdefault(name, ((0 if iface.get("mgmt_only") else 1),
                                        _num(iid.rsplit("-", 1)[-1]), iface))

    ifaces = ([i for _, _, i in sorted(ports.values(), key=lambda k: k[:2]) if i.get("mgmt_only")]
              + sorted(mgmt_sfp, key=lambda i: i["name"])
              + [i for _, _, i in sorted(ports.values(), key=lambda k: k[:2]) if not i.get("mgmt_only")]
              # LAST, because they are not what anyone opens this list to find.
              # A person reading a device type wants its ports; the timing and
              # RF jacks are real and belong here, and they belong at the end.
              + [timing[k] for k in sorted(timing)])

    if console:
        out["console-ports"] = console
    if ifaces:
        out["interfaces"] = ifaces
    # A CHASSIS INLET AND A SUPPLY'S INLET ARE NOT THE SAME PORT, and the
    # library already distinguishes them - which is what makes emitting these
    # safe rather than a double count.
    #
    # On 39 devices the cord goes into the SUPPLY: the PSU is a module type
    # carrying its own `std/c14-inlet`, and a DCIM instantiates that port when
    # the module is seated in the bay. Those devices place no inlet and get
    # nothing here, correctly.
    #
    # On the MX960 the cord goes into the CHASSIS. Its four C20 receptacles sit
    # on an inlet strip above the supplies, one per PEM - the rear studio
    # photograph the model is measured from shows them, the device's `inlets`
    # group says "the inlet is the cord's end and stays with the chassis while
    # a PEM comes out", and `juniper/mx960-psu-ac` composes no inlet part
    # BECAUSE THE SUPPLY HAS NONE. So the four ports appear once, here, and
    # anything that later gives that supply an inlet would be describing
    # different hardware. The placements even name the supply they feed
    # (`for: pem0`), which is the fact a DCIM has no field for yet.
    if powers:
        out["power-ports"] = [powers[k] for k in sorted(powers)]
    if bays:
        out["module-bays"] = sorted(
            bays, key=lambda b: (b["name"].split()[0], _num(b["position"])))

    body = comments_for(dev, cfg_name, cfg)
    if body:
        out["comments"] = body
    return out


def contract_view(entry):
    """An index entry in the shape `optical.py` expects.

    components.json FLATTENS a face to its ref - `faces: {rear: "fs/x@1"}` -
    because the viewer resolves it against this same index and the nested form
    would cost bytes on every page load. `optical.capacities` goes through
    `face_ref`, which reads the contract's nested `{ref: ...}`. Re-nesting here
    is four lines; teaching the accessor to accept two shapes would put the
    difference into the one place that exists to hide it.
    """
    faces = {k: {"ref": v} for k, v in (entry.get("faces") or {}).items()}
    return {"parts": entry.get("parts") or [],
            "faces": faces,
            "optical": entry.get("optical") or {}}


def build_module(contract, manufacturer, load_ref=None, dropped=None,
                 defaulted=None):
    """A module contract as a DCIM module type.

    `dropped` is an optional dict the caller passes in to be told which part
    refs matched no branch, counted. `defaulted` is the same for cages typed by
    the table rather than by the card. See `export_modules`, which prints both.
    """
    load_ref = load_ref or (lambda _r: None)
    attrs = contract.get("attrs") or {}
    model = str(attrs.get("model") or contract["name"])
    out = {"manufacturer": manufacturer, "model": model}

    if attrs.get("weight-kg"):
        out["weight"] = round(float(attrs["weight-kg"]), 2)
        out["weight_unit"] = "kg"

    if contract.get("description"):
        out["description"] = fit(first_sentence(contract["description"]))

    # Which interface type this card's cages actually run at. The cage ref gives
    # the floor; an attr naming a faster media raises it.
    ifaces, consoles, powers = [], [], []
    # A CARD'S PORTS ARE READ THROUGH THE CARD'S OWN GROUPS (#511), the way a
    # device's placements are read through the device's: every table below
    # sees the part's EFFECTIVE attrs - its group's attrs under its own
    # (effective_part) - and a port in a `management` group is mgmt_only, the
    # same rule `build` applies to a device port.
    comp_groups = contract.get("groups") or {}
    for part in contract.get("parts") or []:
        if not isinstance(part, dict):
            continue
        part, part_role = effective_part(part, comp_groups)
        # Which list the part lands in is route_part's answer, and L105 asks
        # it too. A `network` row is the only kind mgmt_only is set on: a
        # timing or RF jack exports as `other` with its function as a label and
        # stays out of it, as it does on a device, where `build` lists those
        # jacks apart from the ports.
        kind, row = route_part(part, attrs, defaulted)
        if kind is None:
            if dropped is not None:
                # THE else THIS CHAIN DID NOT HAVE. A part matching no branch fell
                # out here with nothing written down, and an empty interface list is
                # indistinguishable from a card with no ports - which is how 24
                # 100GbE CFP, CFP2 and CXP ports sat missing across fourteen Juniper
                # cards through every green run this repo has ever had. The caller
                # decides what to do with the names; `None` opts out, for readers
                # that only want the document.
                ref = part["ref"].split("@")[0]
                dropped[ref] = dropped.get(ref, 0) + 1
            continue
        if kind == "console":
            consoles.append(row)
        elif kind == "power":
            powers.append(row)
        elif kind in ("timing", "rf"):
            ifaces.append(row)
        elif kind == "network":
            if mgmt_only(part.get("attrs") or {}, part_role):
                row["mgmt_only"] = True
            # ONE CAGE, SEVERAL INTERFACES - `build`'s #443 rule, on a card. A
            # FELT-B cage numbers two ports whether a CSFP or an SFP is seated, and
            # says so with `interfaces:`; each is exported, typed from the cage as
            # the one row would have been, and the cage itself is not. The rows
            # are built before anything is appended, so no other row can be
            # mistaken for this one. Only a network port presents interfaces, and
            # L105 fails a part that declares them and routes anywhere else.
            ifaces.extend([{**row, "name": iid} for iid in part["interfaces"]]
                          if part.get("interfaces") else [row])

    # THE DECLARED INLET, when no part draws one. Second, not first: a composed
    # part knows its own id and there may be several, so it wins wherever it
    # exists. The three Dell supplies carry both and are unaffected either way.
    if not powers and attrs.get("inlet"):
        declared = INLET_TYPE.get(attrs["inlet"])
        if declared:
            powers.append({"name": "Inlet", "type": declared})

    # BY NAME, NOT BY WHERE THE JACK IS DRAWN.
    #
    # The order used to be the order the parts are listed in, which is the order
    # they sit across the FACE - and half these cards are authored twice, once
    # horizontally for the MX240/MX480 and once rotated for the MX960. Both
    # write one module type, so whichever sorted last handed the DCIM ITS port
    # order: the committed DPCE-R-20GE-2XGE begins `port-0-1, port-0-0,
    # port-0-3`, which is a vertical drawing's x-order and means nothing to a
    # DCIM. 26 of the 44 colliding pairs differed in nothing else (#267).
    #
    # Natural order, so port-2 precedes port-10.
    for lst in (consoles, ifaces, powers):
        lst.sort(key=lambda i: _natural(i.get("name")))
    if consoles:
        out["console-ports"] = consoles
    if ifaces:
        out["interfaces"] = ifaces
    if powers:
        out["power-ports"] = powers

    # THE GLASS, IF THIS MODULE CARRIES ANY. A fibre cassette has no interfaces
    # in the DCIM sense - nothing terminates electrically - so these are its
    # entire port list, and a module with no `optical` adds nothing here.
    #
    # GATED ON A DECLARED REAR FACE, not merely on having paths. Section C3
    # calls the rear connector "the trunk", but a single-faced module such as
    # a PPM coupler has no rear face at all - its paths run entirely between
    # parts drawn on its one face (`common.1 -> split.1/2` for an OCU coupler,
    # never a `rear:`-prefixed endpoint) - and nothing in the contract names
    # which of its parts is the trunk. `common` and `split` are part ids a
    # modeller chose, not declared roles, and path direction does not settle
    # it either: the cassette's own paths run FROM the front
    # (`lc1.1 -> rear:mtp.1`) while an OCU's run FROM what would be the trunk
    # (`common.1 -> split.n`) - opposite conventions, so a rule built on
    # either would invent a role the contract never states. Exporting every
    # fibre position of a single-faced module as a front port with no rear
    # counterpart is exactly the shape netbox#21830 rejected ("We do not get
    # to omit rear ports"), so a single-faced module exports neither list and
    # waits for the vocabulary a future plan owes.
    view = contract_view(contract)
    if face_ref(view, "rear") and (contract.get("optical") or {}).get("paths"):
        fibre = optical_ports.ports(view, load_ref)
        if fibre["rear"]:
            out["rear-ports"] = fibre["rear"]
        if fibre["front"]:
            out["front-ports"] = fibre["front"]

    body = []
    if contract.get("description"):
        body += [contract["description"].strip(), ""]
    # `model` names the type and is not a leftover fact. `inlet` stops being one
    # THE MOMENT IT TYPES: the heading says "facts the schema has no field for",
    # and once the token has produced a power port the schema plainly has one.
    # It stays listed when it did not - `none`, or a token with no mapping -
    # because then the sentence is true again and a reader still wants it.
    typed = {"model"}
    if any(pp["type"] == INLET_TYPE.get(attrs.get("inlet")) for pp in powers):
        typed.add("inlet")
    facts = [f"- {k}: {v}" for k, v in attrs.items()
             if k not in typed and isinstance(v, (str, int, float))]
    if facts:
        body.append("Facts carried in the model that this schema has no field for:")
        body += facts
        body.append("")
    # Same reasoning as the device stamp: a module type is cached in a DCIM too,
    # and its faceplate can move under it.
    #
    # NAMED, because a module type can have more than one author. Forty Juniper
    # cards are drawn twice - once horizontally, once rotated - and both write
    # this one document, so a bare version number would be one of the two chosen
    # by `sorted()`. `export_modules` merges the stamps of every contract that
    # collapses here, which is what makes the collapsed document a function of
    # the whole group rather than of iteration order (#267).
    if contract.get("version"):
        out["_stamp"] = [f"{contract['version']} ({contract.get('ns')}/"
                         f"{contract.get('name')})"]
    if body:
        out["comments"] = "\n".join(body).strip()
    return out


def _num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


class Indented(yaml.SafeDumper):              # match the library's list indentation
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def overlay_identity(dist, ns, model, profile):
    """What the device is SOLD AS when it runs this NOS, or None.

    A disaggregated box is two products from two companies: Edgecore made the
    metal and the buyer's asset register may well say the software house, because
    that is who invoiced them. Modelling that by duplicating the hardware means
    keeping two full definitions in step forever, so the hardware is modelled once
    and the overlay carries only what the software changes - here, who sells it.

    Absence is meaningful and is the default: an overlay without `identity:` is a
    naming and mapping layer, and its export stays under the manufacturer of
    record exactly as before.
    """
    if not profile:
        return None
    ov = dist.overlay(ns, model, profile)
    return (ov or {}).get("identity") or None


def apply_identity(doc, identity, vendors):
    """Re-file a device type under the software vendor that sells it."""
    if not identity:
        return doc
    display = ((vendors.get(identity["vendor"]) or {}).get("display")
               or identity["vendor"])
    hw_model = doc["model"]
    name = identity["model"]
    if "{model}" in name:
        name = name.replace("{model}", hw_model)
    elif hw_model.lower() not in name.lower():
        # THE HARDWARE'S SKUs DO NOT COLLAPSE. One device can be four orderable
        # things - AC and 48 V, front-to-back and back-to-front - and they are
        # four device types on the hardware side. A NOS identity that names none
        # of them would write four documents to one filename, keeping whichever
        # happened to be last. Appending the hardware model is not elegant; it is
        # the option that loses nothing, and `{model}` exists so an author who
        # cares about the phrasing never reaches this branch.
        name = f"{name} ({hw_model})"
    doc["manufacturer"] = display
    doc["model"] = name
    doc["slug"] = slugify(f"{display}-{name}")
    if identity.get("part-number"):
        doc["part_number"] = identity["part-number"]
    else:
        # The hardware's part number is the METAL's, and this document is no
        # longer about the metal alone. Leaving it would attribute an Edgecore
        # SKU to an Arrcus product.
        doc.pop("part_number", None)
    return doc


def load_vendors(dist):
    """The vendor registry, as published. `vendors.json` is the same content as
    spec/schemas/vendors.yaml and is in the build."""
    return dist.vendors


def write(doc, root, target, nos):
    d = Path(root) / target / "device-types" / doc["manufacturer"]
    d.mkdir(parents=True, exist_ok=True)
    name = doc["model"] + (f"-{nos}" if nos else "") + ".yaml"
    f = d / name
    f.write_text("---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                     width=100, default_flow_style=False))
    return f


def rasterize(src, png, scale):
    """One compiled drawing to one PNG. None if the drawing or cairosvg is absent.

    Resolves the custom properties first, which cairosvg has no support for -
    it reads `var(--led-color, #3a3f44)` as a hex literal beginning "ar". Every
    use in the compiled output is a lamp colour and every one carries a
    fallback, so taking the fallback yields the unlit faceplate. That is the
    right picture for a type either way: a type has no live state to show.
    """
    if not src.exists():
        return None
    try:
        import cairosvg
    except ImportError:
        return None
    svg = re.sub(r"var\(\s*--[\w-]+\s*,\s*([^)]*)\)", r"\1", src.read_text())
    png.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(png), scale=scale)
    return png


# TWO JOBS, ONE FLAG, UNTIL NOW. `--images` both wrote `front_image: true` into
# the YAML and rasterised the PNG behind it. The boolean means "a rendered face
# exists in dist", which is true whenever the build ran; the rasterisation is
# 1104 pictures and about two minutes. CI needs the first and throws the second
# away - every PNG under library/exports is gitignored - but dropping `--images`
# to save the time also deleted 692 lines of tracked YAML across 346 files,
# because one switch drove both. `--no-raster` separates them.
RASTER = True


def render_image(dist, root, target, doc, dev_name, cfg_name, face):
    """Rasterise a compiled face into the library's elevation-images tree."""
    # 2 px/mm. A 440 mm faceplate lands near 880 px, which is the range the
    # libraries' own elevation images sit in - theirs run 37 KB to 350 KB. At 4
    # px/mm the 13 RU C100G alone came to 1.9 MB, and a contribution that ships
    # 29 MB of PNG is not one anybody wants to merge.
    return rasterize(Path(dist) / f"{dev_name}.{cfg_name}.{face}.svg",
                     Path(root) / target / "elevation-images" / doc["manufacturer"]
                     / f"{doc['slug']}.{face}.png", 2)


def render_module_image(dist, root, target, doc, ns, name, ver):
    """Rasterise a module's faceplate into the library's module-images tree.

    Keyed by MODEL, not by slug: a module type has no slug property in either
    schema, and the libraries' own trees are named for the model. The filename
    is sanitised the same way the YAML's is, so the pair always agree.

    The drawing keeps its own orientation. A card is drawn as the skin draws it,
    and which way up it ends up is a property of the chassis it is seated in -
    an A9K line card is horizontal in a 9010 and vertical in a 9910 - so there
    is no one rotation that is true of the part itself.
    """
    # Scale 1: the drawing at its own size. cairosvg's scale multiplies the CSS
    # pixel size, so a 41 mm x 396 mm card renders 157 x 1496 - an SFP cage
    # lands near 53 x 30 px, which reads at thumbnail size. It also keeps the
    # files in the range the libraries' own module images occupy: theirs average
    # 58 KB and the Cisco A9K ones are 7 KB, and these come out 10-80 KB. Going
    # up one stop tripled that for detail nothing displays.
    return rasterize(Path(dist) / "components" / f"{ns}--{name}--{ver}--default.svg",
                     Path(root) / target / "module-images" / doc["manufacturer"]
                     / (doc["model"].replace("/", "-") + ".front.png"), 1)


def dcim_significant(doc):
    """What a DCIM READS, which is everything but the comments.

    Two authors of one card carry their own version numbers and their own
    sentence about which way it was drawn, and neither is a difference in the
    hardware. Comparing whole rendered files instead called all 52 Juniper twins
    a loss, which would have buried the two that are.

    One function rather than a rule written twice, because the test that pins
    the collision list has to ask the same question the exporter asks - a second
    copy of it would drift, and this file's own history is that a mirror of a
    tool is wrong about it within a commit or two.
    """
    return {k: v for k, v in doc.items() if k not in ("comments", "_stamp")}


def export_modules(dist, root, images=None):
    """Every module contract in the library, as module types for both targets.

    A module type is an orderable part, so it needs a manufacturer. The
    namespace gives it - learned from the devices, which are the only place the
    library states a manufacturer - and the generic `common/` namespace is
    skipped: a part with no vendor is not something a DCIM can order.

    TWO PASSES, BECAUSE A MODEL CAN HAVE MORE THAN ONE AUTHOR. A module type is
    written to <manufacturer>/<model>.yaml, so two contracts carrying one
    `attrs.model` used to write one path and the second silently won - 55
    contracts overwritten across 44 filenames, every run green (#267).

    Most of that is deduplication and should be: 40 of the 44 are one Juniper
    card drawn twice, horizontally for the MX240/MX480 and rotated for the
    MX960, and a DCIM orders a card rather than an orientation. What was wrong
    is that the right outcome arrived BY ACCIDENT - `sorted()` decided which
    twin's document survived, so renaming a contract changed the export and
    nothing said so.

    So the first pass builds; the second writes. A group whose documents agree
    collapses DELIBERATELY into one whose version stamp names every author. A
    group whose documents differ keeps the first, and every loss is printed by
    name - test_module_collisions.py pins that list so a new one fails.
    """
    skipped = 0
    imaged = set()
    dropped = {}
    defaulted = {}
    # components.json in place of a glob over contracts, and devices.json in
    # place of one over manifests. The index carries `ns` on both sides, which is
    # what the namespace-to-manufacturer join needs and what a checkout used to
    # be opened for.
    built = []                                   # (man, doc, contract)
    for contract in sorted(dist.modules(), key=lambda c: (c.get("ns") or "", c.get("name") or "")):
        man = dist.manufacturer_of(contract.get("ns"))
        if not man:
            skipped += 1
            continue
        built.append((man, build_module(contract, man, dist.component_by_ref, dropped,
                                        defaulted), contract))

    groups = {}
    for man, doc, contract in built:
        groups.setdefault((man, doc["model"]), []).append((doc, contract))

    wrote = 0
    collisions = []                              # ((man, model), ref, kind)
    for (man, model), members in sorted(groups.items()):
        doc, contract = members[0]
        first = f"{contract.get('ns')}/{contract.get('name')}"
        stamps = list(doc.pop("_stamp", []))
        for other, oc in members[1:]:
            ref = f"{oc.get('ns')}/{oc.get('name')}"
            stamp = other.pop("_stamp", [])
            # WHAT A DCIM READS, which is everything but the comments. Two
            # authors of one card carry their own version numbers and their own
            # sentence about which way it was drawn, and neither is a difference
            # in the hardware. Comparing the whole rendered file instead called
            # all 52 twins a loss, which would have buried the two that are.
            if dcim_significant(other) == dcim_significant(doc):
                collisions.append(((man, model), ref, "identical"))
                stamps += stamp
            else:
                collisions.append(((man, model), ref, "differs"))
        if stamps:
            body = (doc.get("comments") or "").rsplit("Contract version", 1)[0].rstrip()
            doc["comments"] = (body + "\n" + "Contract version "
                               + ", ".join(stamps) + ".").strip()
        doc.pop("_stamp", None)

        body_text = "---\n" + yaml.dump(doc, Dumper=Indented, sort_keys=False,
                                        width=100, default_flow_style=False)
        # `major` ARRIVES PREFIXED. It is the version directory's own name, so
        # components.json carries `v1` and not `1` - every other reader strips
        # with `major[1:]` rather than adding. Prefixing again asked for
        # `casa--oob-2p8--vv1--default.svg`, which no build produces, and
        # `rasterize` answers None for an absent drawing rather than raising,
        # so all 376 module images stopped rendering without a word.
        name, ver, ns = contract.get("name"), contract.get("major"), contract.get("ns")
        for target in TARGETS:
            d = Path(root) / target / "module-types" / man
            d.mkdir(parents=True, exist_ok=True)
            # Cisco ships part numbers with slashes in them - A9K-16T/8-B - and
            # a slash is a path separator, not a character. The model keeps the
            # real name; only the filename is sanitised.
            (d / (model.replace("/", "-") + ".yaml")).write_text(body_text)
            if images and RASTER:
                if render_module_image(images, root, target, doc, ns, name, ver):
                    imaged.add(model)

        # THE FIBRE MAP, gated the same way build_module gates rear-ports: on a
        # declared rear face, not merely on having paths. A single-faced module
        # (a PPM coupler) has paths that run front-to-front, so `_row` answers
        # None for every leg and a map for it would be all rows and no ports -
        # the same shape netbox#21830 rejected for the port lists themselves.
        # It sits beside `netbox/` and `nautobot/` rather than inside either,
        # because it is not a document of either schema - it is the artefact
        # this project defines, and both targets consume the same rows. Written
        # once per MODEL for the same reason the type is: its filename is the
        # model too, so it collided in exactly the same silence.
        view = contract_view(contract)
        if face_ref(view, "rear") and (contract.get("optical") or {}).get("paths"):
            m = optical_ports.fibre_map(view, dist.component_by_ref, model)
            d = Path(root) / "fibre-maps" / man
            d.mkdir(parents=True, exist_ok=True)
            (d / (model.replace("/", "-") + ".yaml")).write_text(
                "---\n" + yaml.dump(m, Dumper=Indented, sort_keys=False,
                                    width=100, default_flow_style=False))

        wrote += 1
        print(f"{model}  ({len(doc.get('interfaces', []))} interfaces, "
              f"{len(doc.get('power-ports', []))} power ports)")

    print(f"module types: {wrote} written from {len(built)} contract(s), "
          f"{skipped} skipped for having no manufacturer")
    # NAMED, NOT COUNTED. A number here would be the instrument that failed in
    # #183: it cannot tell one part quietly vanishing from forty twins
    # collapsing the way they are meant to.
    if collisions:
        same = [c for c in collisions if c[2] == "identical"]
        diff = [c for c in collisions if c[2] == "differs"]
        print(f"model collisions: {len(collisions)} contract(s) share a model - "
              f"{len(same)} collapsed (same document, stamps merged), "
              f"{len(diff)} DIFFER and were not written")
        for (man, model), ref, kind in diff:
            first = next(f"{c.get('ns')}/{c.get('name')}"
                         for _d, c in groups[(man, model)][:1])
            print(f"    {man}/{model}: {ref} differs from {first}, not written")
    # HOW MANY PORTS WERE TYPED BY THE TABLE AND NOT BY THE CARD. Cheap, and it
    # is the line that would have made `dpce-r-40ge-sfp` findable: forty 10G
    # interfaces on a 40x1GbE card, for want of `sfp: 40`. L96 names them one by
    # one; this says how big the heap is without reading a lint run.
    if defaulted:
        print(f"cage rate from the table, not the card: {sum(defaulted.values())} "
              f"placement(s) (L96 names them)")
        for ref, n in sorted(defaulted.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {n:5d}  {ref} -> {PART_IFACE.get(ref)}")
    if dropped:
        print(f"unclassified parts: {sum(dropped.values())} placement(s) across "
              f"{len(dropped)} ref(s) matched no branch in build_module")
        for ref, n in sorted(dropped.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {n:5d}  {ref}")
    if images and RASTER:
        print(f"module images: {len(imaged)} of {wrote} rendered")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    # THE INPUT IS A PUBLISHED BUILD, NOT A CHECKOUT. Everything this reads is in
    # `dist/`: the compiled SVG carries the device manifest, components.json the
    # contract fields, vendors.json and overlays.json the registries. That is
    # what lets the export live outside the repository that produces them.
    ap.add_argument("--dist", required=True, help="a published build (library/dist)")
    ap.add_argument("--out", required=True, help="root of the exports tree")
    ap.add_argument("--device", help="one device by name; default is every device")
    ap.add_argument("--modules", action="store_true", help="export module types instead")
    ap.add_argument("--nos", action="append", default=[],
                    help="NOS profile to name interfaces for; repeatable")
    ap.add_argument("--no-raster", action="store_true",
                    help="write the image booleans but skip rendering the PNGs "
                         "behind them. What CI wants: the YAML is tracked, the "
                         "pictures are gitignored")
    ap.add_argument("--images", action="store_true",
                    help="rasterise elevations and module faces from the same build")
    args = ap.parse_args()

    dist = Dist(args.dist)
    # A NOS NOBODY DESCRIBES IS AN ERROR, NOT A DEFAULT. `--nos sonic` used to
    # answer from a Python branch and wrote 144 device types for a NOS with no
    # overlay anywhere; now the only source of a NOS name is an overlay, so a
    # profile no overlay declares has nothing to say and the run stops here,
    # before a file is written, naming where the overlay would go.
    known = dist.profiles()
    for p in args.nos:
        if p not in known:
            raise SystemExit(f"--nos {p}: no overlay in {args.dist} declares it. A NOS is "
                             f"described by devices/<vendor>/<model>/overlays/{p}.yaml, "
                             f"with `interfaces:` rules for its names"
                             + (f"; known: {', '.join(sorted(known))}" if known else ""))
    global RASTER
    RASTER = not args.no_raster
    images = args.dist if args.images else None

    if args.modules:
        export_modules(dist, args.out, images)
        return

    names = [args.device] if args.device else [d["name"] for d in dist.devices]
    for name in names:
        export_device(dist, name, args.out, args.nos, images)


def _config_rank(cfg):
    """Which of two collapsing configurations should name the device type.

    Lower wins, and ties keep the one already there so the order inside a rank
    is still the file's. A device states its own default; failing that, `base` is
    the chassis-as-you-order-it and the next best answer.
    """
    cfg = cfg or {}
    if cfg.get("default"):
        return 0
    if cfg.get("kind") == "base":
        return 1
    return 2


def export_device(dist, device_name, out_root, nos, images):
    dev = dist.manifest(device_name)
    frus = module_models(dist)

    # One device type per SKU, not per configuration.
    #
    # A device type is the empty chassis; what is seated in a bay is a property
    # of the DEVICE. So configurations carrying their own part number are
    # separate types - an AC front-to-back and a DC back-to-front are different
    # things to order - while configurations differing only in how the bays are
    # populated are one type with one picture. The C100G's `bdm2m-11plus1` and
    # `docsis-classic` are two redundancy schemes for one chassis, and treating
    # them as two device types wrote the same file twice.
    #
    # The key has to be the SAME sku build() will name the type after, FRUs
    # filtered out - otherwise two configurations collapse under one key and
    # then get written under two different models, or the reverse.
    #
    # Keyed on the SKU and on which bays the configuration renders. The SKU
    # alone was enough while configurations differed only in what was seated;
    # `only-in` means they can now differ in which bays EXIST, and a C40G's
    # `ac-power` has neither pem-1 nor pem-2. Collapsing on the SKU alone hands
    # the AC chassis two module bays it has not got.
    cfgs = dev.get("configurations") or {}
    # AN ILLUSTRATION IS NOT A DEVICE TYPE. `kind: example` is a redundancy
    # scheme or a worked population - a picture, not a thing anyone can order -
    # and before configurations said which they were, the C40G exported a device
    # type called "C40G bdm-3plus1", named after whichever drawing happened to be
    # listed second while two others collapsed into it silently.
    #
    # Kept for rendering: the elevation images still come from every
    # configuration, because "here is a C40G wired for classic DOCSIS" is worth
    # looking at. It is only the ORDERABLE identity that examples must not claim.
    orderable = {n: c for n, c in cfgs.items()
                 if (c or {}).get("kind") in (None, "base", "orderable", "model")}
    cfgs = orderable or cfgs
    # A CONFIGURATION WITH NO SKU, ON A DEVICE THAT HAS THEM, IS NOT A PRODUCT.
    # The ASR 9006's `base` carries no part number of its own - you order the AC
    # chassis or the DC one - so it fell back to the model name and emitted a
    # second device type called "ASR 9006", for the same hardware, under a name
    # nobody can order. That is the complaint this whole issue is about, arriving
    # by a different route.
    #
    # Only when SOMETHING here has a SKU. A device whose configurations carry no
    # part numbers at all still exports, under its model, because a descriptive
    # name beats no device type.
    with_sku = {n: c for n, c in cfgs.items() if (c or {}).get("part-numbers")}
    if with_sku and len(with_sku) < len(cfgs):
        cfgs = with_sku
    by_sku = {}
    for name, cfg in cfgs.items():
        chassis = sorted(k for k in (cfg.get("part-numbers") or {}) if k not in frus)
        key = (chassis[0] if chassis else None, bay_signature(dev, name))
        # WHEN SEVERAL CONFIGURATIONS COLLAPSE, THE DEFAULT ONE NAMES THE TYPE.
        # They share a SKU and share their bays, so the exporter is right to emit
        # one type - but they can still differ in what the type SAYS, and the
        # S7801-54XS is the case: `base` is front-to-rear and `ac-back-to-front`
        # is not, so whichever won supplied the airflow. That was decided by dict
        # order, which is the source file's key order, which is not a decision at
        # all - and it changed the moment the manifest arrived sorted.
        # `default` is the device's own answer to "which one is this, normally".
        prev = by_sku.get(key)
        if prev is None or _config_rank(cfg) < _config_rank(prev[1]):
            by_sku[key] = (name, cfg)
    if not by_sku:
        by_sku = {(None, ()): (None, {})}

    # When one SKU yields more than one chassis, the model has to say which -
    # two files cannot share a name. There is nothing better to name them by:
    # the C40G's four configurations carry no part numbers at all, so the
    # configuration name is what is left. A device whose configurations DO carry
    # part numbers never reaches this and keeps its real SKU as its model.
    per_sku = {}
    for sku, _ in by_sku:
        per_sku[sku] = per_sku.get(sku, 0) + 1
    labels = {key: (key[1] and by_sku[key][0]) if per_sku[key[0]] > 1 else None
              for key in by_sku}

    wrote = 0
    vendors = load_vendors(dist)
    for key, (cfg_name, cfg) in by_sku.items():
        label = labels[key]
        # THE HARDWARE'S OWN DOCUMENT, ALWAYS; A NOS DOCUMENT ONLY WHERE AN
        # OVERLAY DECLARES THAT NOS FOR THIS DEVICE. Asking for `--nos arcos`
        # used to write an ArcOS type for every switch in the library with names
        # made up in Python, UfiSpace and Juniper included, and `--nos sonic` did
        # the same for a NOS no overlay describes (#63, #56). A device with no
        # overlay for a profile now gets nothing for it - the neutral type names
        # its ports by the faceplate and says no more than it knows.
        ns = dev.get("ns")
        profiles = [None] + [p for p in nos if dist.overlay(ns, device_name, p)]

        for profile in profiles:
            overlay = dist.overlay(ns, device_name, profile) if profile else None
            doc = build(dev, cfg_name, cfg, overlay, images, frus, label)
            # DEVICE name, not the configuration's. `name` is rebound by the
            # by-SKU loop above and means a configuration from there on, which
            # silently looked up an overlay that does not exist and filed every
            # ArcOS box under Edgecore instead of Arrcus.
            ident = overlay_identity(dist, dev.get("ns"), device_name, profile)
            doc = apply_identity(doc, ident, vendors)
            if not any(k in doc for k in
                       ("console-ports", "interfaces", "module-bays")):
                continue                       # nothing but a header: not worth a file
            for target in TARGETS:
                f = write(doc, out_root, target, None if ident else profile)
                for face in ("front", "rear"):
                    if doc.get(f"{face}_image") and RASTER:
                        render_image(images, out_root, target, doc,
                                     dev["name"], cfg_name, face)
                wrote += 1
                print(f"{f}  ({len(doc.get('interfaces', []))} interfaces, "
                      f"{len(doc.get('module-bays', []))} bays)")
    if not wrote:
        print(f"skip {dev['name']}: nothing to export")


if __name__ == "__main__":
    main()
