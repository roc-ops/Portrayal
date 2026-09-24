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

from portrayal.manifest import device_options

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
    def __init__(self, name, section, unit, kind, sources, note=None, scopes=()):
        self.name = name
        self.section = section
        self.unit = unit
        self.kind = kind
        self.sources = sources          # list of (attrs-key, basis, qualifier)
        self.note = note
        # A SCOPE IS NOT A FACT. `power-envelope` is on 52 devices and says
        # whether a power figure is for a bare chassis, a fully-configured one,
        # or was never qualified - which changes what the number MEANS without
        # being a measurement of its own. Given a column it would invite exactly
        # the mistake that started all this, where "fully-configured" turned up
        # under PSU redundancy. So it annotates the fact it qualifies instead.
        self.scopes = scopes

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
    ], note="NOT typical draw. See rule 1 - there is no fallback between them",
       scopes=("power-max-scope", "power-envelope")),
    Fact("typical-power-w", "power", "W", NUMBER, [
        A("power-typical-w"), A("typical-draw-w"),
    ], scopes=("power-typical-scope", "power-envelope")),
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
    # THE STRUCTURED FIELD IS READ FIRST, in resolve(): `chassis.airflow` and
    # each configuration's, one reading per direction a buyer can order. These
    # attrs spellings are the prose some devices also carry ("front to back;
    # both listed SKUs are F"), kept as readings behind it rather than dropped.
    Fact("airflow", "thermal", None, TEXT, [A("airflow"), A("cooling-path")]),
    # WHAT THE BOX IS FED WITH - `ac`, `dc`, `hvdc` - one reading per feed its
    # offered builds resolve to (`manifest.device_options`). No attrs source:
    # `input-ac` says what an AC supply accepts, which is a different question
    # from whether an AC build exists, and reading the one as the other is how
    # a DC-only box with an AC figure in its datasheet footnote would list both.
    Fact("power-feed", "power", None, TEXT, []),

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

    # ---- what it plugs into ------------------------------------------------
    #
    # Promoted from the unclaimed census, which is what the tail is for: these
    # recur on 20 to 46 devices each, so a comparison that cannot line them up
    # is leaving real answers on the floor. The long tail stays unclaimed - 102
    # of 211 spellings appear on exactly one device, and a fact per one-off is
    # a taxonomy of nothing.
    Fact("console", "management", None, TEXT, [
        A("console"), A("console-serial"),
    ]),
    Fact("oob-management", "management", None, TEXT, [
        A("oob"), A("oob-sfp", qualifier="sfp"),
    ]),
    Fact("bmc", "platform", None, TEXT, [A("bmc")]),

    # ---- timing, which is the whole point on a cell-site router -------------
    Fact("timing", "features", None, TEXT, [A("timing"), A("timing-support")]),
    Fact("timing-interfaces", "features", None, TEXT, [A("timing-interfaces")]),
    Fact("gnss", "features", None, TEXT, [A("gnss")]),

    # ---- the paperwork a reader actually compares --------------------------
    Fact("emc", "compliance", None, TEXT, [A("emc")]),
    Fact("safety", "compliance", None, TEXT, [A("safety")]),
    Fact("nebs", "compliance", None, TEXT, [A("nebs")]),
    Fact("environmental-directives", "compliance", None, TEXT, [
        A("environment"), A("rohs"),
    ], note="RoHS, WEEE and the like - not the operating environment, which is "
            "operating-temperature and its neighbours"),

    # ---- which optics actually light up ------------------------------------
    #
    # One fact per media, because that is the axis a reader compares on: two
    # boxes both have SFP28 cages and the question is what runs in them. L40
    # already governs these keys; this makes them reachable.
    Fact("optics-sfp", "features", None, TEXT, [A("optics-sfp")]),
    Fact("optics-sfp-plus", "features", None, TEXT, [A("optics-sfp-plus")]),
    Fact("optics-sfp28", "features", None, TEXT, [A("optics-sfp28")]),
    Fact("optics-qsfp28", "features", None, TEXT, [A("optics-qsfp28")]),
    Fact("optics-qsfp56", "features", None, TEXT, [A("optics-qsfp56")]),
    Fact("optics-qsfp-dd", "features", None, TEXT, [A("optics-qsfp-dd")]),
    Fact("optics-osfp", "features", None, TEXT, [A("optics-osfp")]),
]

BY_NAME = {f.name: f for f in FACTS}

# Every attrs spelling any fact claims. The lint rule reports the ones nothing
# claims, which is how the vocabulary gets harvested instead of designed - the
# same stance L40 takes for optics.
CLAIMED = ({k for f in FACTS for (k, _, _) in f.sources}
           | {k for f in FACTS for k in f.scopes})

# SUPERSEDED, AND DELIBERATELY UNCLAIMABLE. These are the prose forms of facts
# that are now read structurally off the groups, and rule 2 forbids reaching
# them. Left in the plain census they would sit at the TOP of it - 23 devices
# each - nominating themselves for a column they must never have, and the next
# person to work through the list would promote them and quietly undo the rule.
# So they are named here, counted separately, and excluded from the tail.
SUPERSEDED = {
    "psu-redundancy": "psu-redundancy (from groups.*.attrs.redundancy)",
    "psus": "psu-redundancy (from groups.*.attrs.redundancy)",
    "psu-options": "psu-redundancy (from groups.*.attrs.redundancy)",
    "power-ac-redundancy": "psu-redundancy (from groups.*.attrs.redundancy)",
    "fan-redundancy": "fan-redundancy (from groups.*.attrs.redundancy)",
    "fans": "fan-redundancy (from groups.*.attrs.redundancy)",
    "fan-options": "fan-redundancy (from groups.*.attrs.redundancy)",
    "fan-controller-redundancy": "fan-redundancy (from groups.*.attrs.redundancy)",
    "redundancy": "psu-redundancy and fan-redundancy, stated per group",
}

# Facts that resolve from somewhere other than attrs, so "no sources" is
# correct rather than an omission.
DERIVED = {"rack-units", "width-mm", "height-mm", "depth-mm",
           "psu-redundancy", "fan-redundancy", "power-feed"}

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


SILENT_SCOPE = "fact:"


def declared_silence(doc):
    """Facts a person has recorded the vendor as not publishing.

    THE THIRD STATE. A blank in a comparison meant two different things and
    looked identical: the vendor publishes no figure, or nobody has looked yet.
    Six ASR 9000 chassis carry the first case in their provenance - "Cisco
    publishes NO chassis-level power draw for any ASR 9000 ... this is the
    vendor being silent, not this model being thin" - which is a real finding,
    written down, that no consumer could reach.

    It rides on `gaps`, which already exists for exactly this and already
    carries `vendor-silent` on 190 entries. A gap claims a fact by scoping
    itself `fact:<name>`; the prefix keeps it apart from the group, view and
    component-ref scopes that are already in there.
    """
    out = {}
    for g in doc.get("gaps") or []:
        if (g or {}).get("reason") != "vendor-silent":
            continue
        for s in g.get("scope") or []:
            if not str(s).startswith(SILENT_SCOPE):
                continue
            name = str(s)[len(SILENT_SCOPE):]
            out.setdefault(name, {"reason": "vendor-silent",
                                  "what": g.get("what"),
                                  "note": g.get("note") or "",
                                  "wanted": g.get("wanted") or ""})
    return out


def resolve(doc):
    """Every comparable fact this device states, as canonical name -> readings.

    THREE STATES, and keeping them apart is the point:

      readings          the device states it
      absent            somebody looked and the vendor publishes none, per a
                        `vendor-silent` gap scoped `fact:<name>`
      omitted entirely  nobody has looked yet

    A fact with neither readings nor a declared silence is OMITTED rather than
    emitted empty. "We did not find one" and "the vendor publishes none" are
    different claims, and this layer may only make the second when a person
    has already made it.
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
            # the first scope key present wins: a per-figure scope is more
            # specific than the chassis-wide envelope and is listed first
            for key in f.scopes:
                if key in flat and str(flat[key][1]).strip():
                    section, raw = flat[key]
                    entry["scope"] = {"value": str(raw),
                                      "from": f"{section}/{key}" if section else key}
                    break
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

    # AIRFLOW AND FEED HAVE A STRUCTURED HOME (#513), and it was never read
    # here: the comparable `airflow` came only from attrs prose, so the 70-odd
    # devices that state it properly - on the chassis or per configuration -
    # compared as if they said nothing. One reading per option, each citing
    # where it resolved from.
    opts = device_options(doc)
    structured = {"airflow": [], "power-feed": []}
    for name, key in (("airflow", "airflow"), ("power-feed", "power")):
        home = f"chassis.{key}" if chassis.get(key) else f"configurations.*.{key}"
        structured[name] = [_reading(v, v, home) for v in opts[key]]
    put("power-feed", structured["power-feed"])

    for f in FACTS:
        if f.name in DERIVED:
            continue
        readings = weight if f.name == "weight-kg" else \
            structured.get(f.name) or []
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

    # A DECLARED SILENCE NEVER OVERWRITES A READING. If both are present the
    # device contradicts itself, and the linter says so rather than this
    # quietly preferring one - a fact that is both stated and unpublished is a
    # question for a person.
    for name, why in declared_silence(doc).items():
        f = BY_NAME.get(name)
        if f is None or name in facts:
            continue
        facts[name] = {"unit": f.unit, "section": f.section,
                       "readings": [], "absent": why}
    return facts


def unclaimed(doc):
    """attrs spellings no fact claims, for the harvest rule. Not a complaint -
    a census, so the tail cannot go quiet.

    Superseded keys are excluded: they are claimed, by a fact that reads them
    from somewhere better."""
    return sorted(k for k in _flat(doc) if k not in CLAIMED and k not in SUPERSEDED)


def superseded(doc):
    """Prose this device still carries for a fact now read off its groups. Kept
    visible - it is not wrong to have the sentence, only wrong to compare on
    it - and worth watching in case the prose and the structured form ever
    disagree."""
    return sorted(k for k in _flat(doc) if k in SUPERSEDED)
