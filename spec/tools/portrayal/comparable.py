#!/usr/bin/env python3
"""Comparable facts: one name per measurement, derived, never authored.

WHY THIS EXISTS, in one example. A side-by-side of the MX204 and the S9510-28DC
printed "Max draw: 280 vs 137" - which reads as the UfiSpace box drawing half
what the Juniper does. It draws more. 137 is its TYPICAL figure; its maximum is
306 W on DC and 301.2 W on AC, under `power-max-dc-w` and `power-max-ac-w`. The
comparison asked for `power-max-w`, did not find it, and reached for the nearest
key that looked close. Nobody reading that page could have known.

That is the failure this module is built against, and it is worth naming
precisely: the defect was not a missing number. It was a WRONG number, produced
by a lookup that preferred an answer to no answer.

THE DEVICE FILES ARE NOT NORMALISED, AND MUST NOT BE
----------------------------------------------------
The vendor's own words are the asset. "10.3 kg fully loaded, AC-powered chassis
(Table 19)" is worth more than `10.3`, because the qualifier is what makes it
true - and the same instinct that would flatten it is the one that would file
the S9510 under a series UfiSpace does not publish. So nothing here edits a
manifest. This is a DERIVED layer: it reads what the authors wrote, in whatever
spelling they wrote it, and publishes a second view with one name per fact and
the vendor's original string carried alongside every value.

THE THREE RULES, each one a bug from that CSV
---------------------------------------------
1. NEVER FALL BACK ACROSS CONCEPTS. A fact lists only its own spellings. Absent
   means absent. `typical` is not a stand-in for `max`, ever, and the structure
   here makes that unsayable rather than merely discouraged - there is no path
   from one fact's sources to another's.

2. STRUCTURED BEATS PROSE. `groups.psus.attrs.redundancy` is `1+1` on both of
   those devices, and the comparison showed "fully-configured" against a blank.
   `fully-configured` is the value of `power-envelope`, a scope qualifier for
   the max figure; it is not a redundancy and never was. A key that merely
   CONTAINS a matching word is not the fact.

3. UNLIKE FACTS STAY UNLIKE. `throughput` and `switching-capacity` are
   different measurements, and in this library they are also disjoint: four
   devices state throughput, all of them Juniper MX, and fifty-one state
   switching capacity, with no device stating both. Merging them into one row
   would compare a forwarding rate against a line-rate sum and call the
   difference a fact about the hardware. They get separate names, and a
   comparison shows two rows with a blank where a vendor publishes no figure.

A READING, NOT A VALUE
----------------------
Several facts legitimately have more than one answer at once - a box has an AC
maximum and a DC maximum, and neither is "the" maximum. So a fact resolves to a
LIST of readings, each carrying its own basis. A consumer comparing two devices
matches readings by basis and shows what it cannot match, rather than silently
picking one.
"""
import re

# Every fact: the canonical name, its unit, and the ONLY places it may come
# from. The source list is exhaustive by design - see rule 1 - so adding a
# spelling here is a deliberate act and the lint rule below reports spellings
# that no fact claims.
#
# `basis` distinguishes readings that coexist rather than compete: a chassis
# has an AC maximum and a DC maximum and both are true. `qualifier` marks a
# reading that is real but not the headline - a shipping weight, an empty
# weight - so a consumer can prefer the unqualified one and still show the rest.

NUMBER = "number"
TEXT = "text"


class Fact:
    def __init__(self, name, section, unit, kind, sources, note=None):
        self.name = name
        self.section = section
        self.unit = unit
        self.kind = kind
        self.sources = sources          # list of (attrs-key, basis, qualifier)
        self.note = note

    def __repr__(self):                 # pragma: no cover - debugging only
        return f"<Fact {self.name}>"


def A(key, basis=None, qualifier=None):
    return (key, basis, qualifier)


FACTS = [
    # ---- the box -----------------------------------------------------------
    Fact("rack-units", "physical", "RU", NUMBER, []),          # from chassis
    Fact("width-mm", "physical", "mm", NUMBER, []),
    Fact("height-mm", "physical", "mm", NUMBER, []),
    Fact("depth-mm", "physical", "mm", NUMBER, []),
    Fact("weight-kg", "physical", "kg", NUMBER, [
        # chassis.weight-kg is consulted first, in resolve(). These are the
        # attrs spellings, and most are QUALIFIED weights rather than rival
        # answers to the same question - an empty chassis and a fully loaded
        # one are both true and are not the same number.
        A("weight"), A("weight-kg"),
        A("weight-configured-kg", qualifier="configured"),
        A("weight-full-ac-kg", basis="ac", qualifier="fully-loaded"),
        A("weight-full-dc-kg", basis="dc", qualifier="fully-loaded"),
        A("weight-empty-kg", qualifier="empty"),
        A("weight-base-kg", qualifier="base"),
        A("weight-premium-kg", qualifier="premium"),
        A("weight-max-kg", qualifier="maximum"),
        A("weight-shipping-kg", qualifier="shipping"),
        A("weight-with-two-mpas-kg", qualifier="with-two-mpas"),
    ]),
    Fact("depth-over-handles-mm", "physical", "mm", NUMBER, [
        A("depth-with-handles"), A("depth-with-brackets", qualifier="brackets"),
        A("depth-with-cable-management-mm", qualifier="cable-management"),
        A("depth-with-front-doors-mm", qualifier="front-doors"),
        A("depth-total", qualifier="total"),
    ], note="the body plus whatever sticks out of it; not the chassis depth"),

    # ---- what it costs to run ---------------------------------------------
    Fact("peak-power-w", "power", "W", NUMBER, [
        A("power-max-w"),
        A("power-max-ac-w", basis="ac"), A("power-max-w-ac", basis="ac"),
        A("power-max-dc-w", basis="dc"),
        A("power-max-ac-msa-w", basis="ac", qualifier="msa-optics"),
        A("power-max-ac-zr-w", basis="ac", qualifier="zr-optics"),
        A("power-max-dc-msa-w", basis="dc", qualifier="msa-optics"),
        A("power-max-dc-zr-w", basis="dc", qualifier="zr-optics"),
        A("power-max-no-poe-w", qualifier="no-poe"),
        A("power-self-max-w", qualifier="self"),
    ], note="NOT typical draw. See rule 1 - there is no fallback between them"),
    Fact("typical-power-w", "power", "W", NUMBER, [
        A("power-typical-w"), A("typical-draw-w"),
    ]),
    Fact("minimum-power-w", "power", "W", NUMBER, [
        A("power-min-w"), A("power-min-ac-w", basis="ac"),
    ]),
    Fact("ac-input", "power", None, TEXT, [
        A("power-input-ac"), A("ac-input"), A("input-ac"),
        A("psu-ac-input"), A("psu-input-ac"), A("power-ac-input-voltage"),
    ]),
    Fact("dc-input", "power", None, TEXT, [
        A("power-input-dc"), A("dc-input"), A("input-dc"),
        A("psu-dc-input"), A("psu-input-dc"), A("power-dc-input-voltage"),
    ]),

    # ---- keeping it alive --------------------------------------------------
    #
    # psu-redundancy and fan-redundancy take NO attrs sources at all. Both are
    # resolved from the group that holds the bays, which is where the convention
    # put them and where the answer is a form rather than a sentence. Listing
    # `power-envelope` or `psus` here is exactly the mistake that produced
    # "fully-configured" in a redundancy column.
    Fact("psu-redundancy", "power", None, TEXT, []),
    Fact("fan-redundancy", "thermal", None, TEXT, []),
    Fact("max-thermal-output", "thermal", None, TEXT, [
        A("max-thermal-output"),
    ]),
    Fact("airflow", "thermal", None, TEXT, [A("airflow"), A("cooling-path")]),

    # ---- where it can live -------------------------------------------------
    Fact("operating-temperature", "environmental", None, TEXT, [
        A("operating-temp"), A("operating-temp-c"), A("temperature-operating"),
        A("operating-temp-front-to-back", basis="front-to-back"),
        A("operating-temp-back-to-front", basis="back-to-front"),
        A("operating-temp-f2b", basis="front-to-back"),
        A("operating-temp-b2f", basis="back-to-front"),
        A("operating-temp-short-term", qualifier="short-term"),
    ]),
    Fact("storage-temperature", "environmental", None, TEXT, [
        A("storage-temp"), A("storage-temp-c"), A("temperature-storage"),
    ]),
    Fact("humidity", "environmental", None, TEXT, [
        A("humidity"), A("humidity-operating"), A("operating-humidity"),
        A("humidity-non-operating", qualifier="non-operating"),
        A("storage-humidity", qualifier="storage"),
    ]),
    Fact("altitude", "environmental", None, TEXT, [
        A("altitude"), A("altitude-operating"),
        A("altitude-non-operating", qualifier="non-operating"),
    ]),

    # ---- what it does ------------------------------------------------------
    #
    # THESE THREE ARE DELIBERATELY SEPARATE. See rule 3.
    Fact("switching-capacity-gbps", "performance", "Gbps", NUMBER, [
        A("switching-capacity"), A("switching-rate"), A("fabric-capacity"),
        A("fabric-bandwidth", qualifier="fabric"),
        A("cluster-capacity", qualifier="cluster"),
    ]),
    Fact("throughput-gbps", "performance", "Gbps", NUMBER, [
        A("throughput"), A("packet-throughput", qualifier="packets"),
    ], note="a forwarding figure, not a line-rate sum - never merge with "
            "switching-capacity-gbps"),
    Fact("forwarding-rate", "performance", None, TEXT, [
        A("forwarding-rate"), A("forwarding"),
    ]),
    Fact("packet-buffer", "performance", None, TEXT, [
        A("packet-buffer"), A("deep-buffer", qualifier="deep"),
    ]),

    # ---- what it is made of ------------------------------------------------
    Fact("asic", "platform", None, TEXT, [A("asic")]),
    Fact("cpu", "platform", None, TEXT, [A("cpu")]),
    Fact("memory", "platform", None, TEXT, [A("memory")]),
    Fact("storage", "platform", None, TEXT, [A("storage"), A("storage-ssd")]),

    # ---- the paperwork -----------------------------------------------------
    Fact("eol", "lifecycle", None, TEXT, [A("eol")]),
    Fact("end-of-sale", "lifecycle", None, TEXT, [A("end-of-sale")]),
    Fact("end-of-support", "lifecycle", None, TEXT, [A("end-of-support")]),
]

BY_NAME = {f.name: f for f in FACTS}

# Every attrs spelling any fact claims. The lint rule reports the ones nothing
# claims, which is how the vocabulary gets harvested instead of designed - the
# same stance L40 takes for optics.
CLAIMED = {k for f in FACTS for (k, _, _) in f.sources}

# Facts that resolve from somewhere other than attrs, so "no sources" is
# correct rather than an omission.
DERIVED = {"rack-units", "width-mm", "height-mm", "depth-mm",
           "psu-redundancy", "fan-redundancy"}

POWER_WORDS = ("psu", "power", "pem")
FAN_WORDS = ("fan", "cooling")

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _flat(doc):
    """attrs as {key: (section, value)} - the section is kept so a reading can
    cite where the author filed it, which is what makes drift visible."""
    out = {}
    for section, body in (doc.get("attrs") or {}).items():
        if isinstance(body, dict):
            for k, v in body.items():
                out[k] = (section, v)
        else:
            out[section] = (None, body)
    return out


def _number(raw):
    """The leading number, or None. `None` is a real answer and is kept as one:
    a reading with no number still carries the vendor's words, so a fact that
    cannot be plotted can still be read."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    m = _NUM.search(str(raw))
    return float(m.group(0)) if m else None


def _reading(value, raw, frm, basis=None, qualifier=None):
    r = {"value": value, "from": frm, "vendor": str(raw)}
    if basis:
        r["basis"] = basis
    if qualifier:
        r["qualifier"] = qualifier
    return r


def _group_readings(doc, words):
    """Redundancy off the group that holds the bays. Whole words only - `re` is
    inside "furniture" and `fan` is inside "fanless"."""
    out = []
    for name, g in (doc.get("groups") or {}).items():
        g = g or {}
        attrs = g.get("attrs") or {}
        form = str(attrs.get("redundancy") or "").strip()
        if not form:
            continue
        tokens = set(re.split(r"[^a-z0-9]+", f"{name} {g.get('term') or ''}".lower()))
        if not tokens & set(words):
            continue
        out.append(_reading(form, attrs.get("redundancy-note") or form,
                            f"groups.{name}.attrs.redundancy"))
    return out


def resolve(doc):
    """Every comparable fact this device states, as canonical name -> readings.

    A fact with no readings is OMITTED rather than emitted empty: "we did not
    find one" and "the vendor publishes none" are different claims and this
    layer is not entitled to make the second.
    """
    flat = _flat(doc)
    chassis = doc.get("chassis") or {}
    facts = {}

    def put(name, readings):
        if readings:
            f = BY_NAME[name]
            entry = {"unit": f.unit, "section": f.section, "readings": readings}
            if f.note:
                entry["note"] = f.note
            facts[name] = entry

    # the chassis block is structural and needs no spelling rules
    for name, key in (("rack-units", "ru"), ("width-mm", "width"),
                      ("height-mm", "height"), ("depth-mm", "depth")):
        v = chassis.get(key)
        if v is not None:
            put(name, [_reading(_number(v), v, f"chassis.{key}")])

    # WEIGHT HAS TWO HOMES and chassis wins. 58 devices carry chassis.weight-kg
    # and 25 more carry an attrs spelling; treating them as rivals is how one
    # device compares its shipping weight against another's empty one.
    weight = []
    if chassis.get("weight-kg") is not None:
        weight.append(_reading(_number(chassis["weight-kg"]), chassis["weight-kg"],
                               "chassis.weight-kg"))

    for f in FACTS:
        if f.name in DERIVED:
            continue
        readings = weight if f.name == "weight-kg" else []
        readings = list(readings)
        for key, basis, qualifier in f.sources:
            if key not in flat:
                continue
            section, raw = flat[key]
            if raw is None or str(raw).strip() == "":
                continue
            value = _number(raw) if f.kind is NUMBER else str(raw)
            frm = f"{section}/{key}" if section else key
            readings.append(_reading(value, raw, frm, basis, qualifier))
        put(f.name, readings)

    put("psu-redundancy", _group_readings(doc, POWER_WORDS))
    put("fan-redundancy", _group_readings(doc, FAN_WORDS))
    return facts


def unclaimed(doc):
    """attrs spellings no fact claims, for the harvest rule. Not a complaint -
    a census, so the tail cannot go quiet."""
    return sorted(k for k in _flat(doc) if k not in CLAIMED)
