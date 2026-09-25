"""L69: a cooling group with more than one bay says how many fans it can lose.

The third of the family, after L66 for power and L67 for the cards that run and
switch the box. What made it worth its own pass is that the data was already in
the library and unreachable: the comparison layer resolved `fan-redundancy` on
0 of 84 devices while 23 carried the figure as `attrs.fan-redundancy` and 14
more had it in their own description. Prose is not a field.

The rollout also produced the clearest example yet of the trap this project
keeps walking into, so it is pinned below: four Edgecore chassis whose staged
datasheets hold TWO fan figures each, where exactly one fills the bay count.
Taking the one that fits would be arithmetic wearing a citation.
"""
import pathlib
import sys

import yaml

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint

LIB = ROOT / "library"


def run(doc):
    out = []
    real = lint.warn
    lint.warn = lambda p, r, m: out.append((r, m))
    try:
        lint.lint_device_fan_redundancy("t.yaml", doc)
    finally:
        lint.warn = real
    return out


def dev(bays, group=None, name="fans"):
    group = {"term": "Fan", "role": "service", **(group or {})}
    return {"kind": "device", "groups": {name: group},
            "views": {"rear": {"components": {
                "bays": [{"id": f"ft{i}", "group": name} for i in range(bays)]}}}}


# ---- the rule ---------------------------------------------------------------

def test_a_multi_bay_cooling_group_with_no_figure_is_flagged():
    assert [r for r, _ in run(dev(4))] == ["L69"]


def test_a_stated_group_is_silent():
    assert not run(dev(4, {"attrs": {"redundancy": "3+1"}}))


def test_one_fan_bay_needs_no_figure():
    assert not run(dev(1))


def test_a_fanless_group_is_not_a_fan_group():
    """Whole words. Several access switches in this library are fanless, and
    the substring is right there in the word."""
    assert not run(dev(4, {"term": "Port", "role": "traffic"}, name="fanless-ports"))


def test_the_vendors_own_spellings_all_count():
    for name, term in (("fans", "Fan"), ("cooling", "Fan Tray"),
                       ("fan-trays", "Fan Tray"), ("blowers", "Blower")):
        assert [r for r, _ in run(dev(2, {"term": term}, name=name))] == ["L69"], name


def test_a_psu_group_is_not_a_fan_group():
    """The contamination the whole family exists to prevent, in the other
    direction: L66 owns this group and L69 must not also claim it."""
    assert not run(dev(2, {"term": "PSU"}, name="psus"))


def test_the_rule_does_not_police_the_arithmetic():
    """A form is the vendor's claim; a bay count is ours. The ASR 9910 states
    6+1 for a five-bay cage because Cisco counts planes across the RSP pair -
    a rule demanding the sum would call that an error."""
    assert not run(dev(5, {"attrs": {"redundancy": "6+1"}}))


# ---- what the library says --------------------------------------------------

def devices():
    """Over the once-parsed library - see libdata."""
    return libdata.devices()


# A stated fan figure counts BAYS on every chassis here but one, and the one is
# named rather than exempted quietly. The pair is (device, group) -> the bay count
# the figure is allowed to disagree with, so a change to either number fails again.
FIGURE_IS_NOT_THE_BAY_COUNT = {
    ("edgecore/ais800-64d", "fans"): 4,
    ("edgecore/ais800-64o", "fans"): 4,
    # ZERO BAYS, AND ZERO IS THE RIGHT ANSWER. The Edgecore EPS121 and EPS122 state
    # "2+1 fixed redundant fans" over three fans that are NOT FRUs: the shared quick start
    # guide's FRU Replacement section covers the supplies only, there is no latch, handle
    # or seam on the rear elevation, and the Overview callouts say "fixed" in as many
    # words. So the three fans are PLACED, not bayed - a bay is this library's way of
    # saying a hand can take the part out - and a figure that counts rotors nobody swaps
    # fills no bays by construction.
    # This is a THIRD kind of entry in this table. The two AIS800 rows above are figures
    # that count ROTORS where the bays count TRAYS; these two are figures with no bays to
    # count at all. Both are "the figure is about something other than bays", which is what
    # this table is for.
    ("edgecore/eps121", "fans"): 0,
    ("edgecore/eps122", "fans"): 0,
    # AND THE EPS112 IS THE THIRD OF THAT SHELL, on the same terms and from a DIFFERENT
    # document, which is what makes it worth a line rather than a comma. The EPS121 and
    # EPS122 share one quick start guide, so their two entries above are one reading
    # counted twice. The EPS112 has its own six-page guide (md5
    # 569bbd26f865b2bae24a733d4046d669) and its own datasheet, and both of them say the
    # same thing independently: "Fixed 2+1 redundant fans" in the datasheet's key
    # features, "2+1 fixed redundant fans" in the guide's Overview callout 6, and an FRU
    # Replacement section that covers the supplies and has no fan procedure at all. Its
    # rear draws three ROUND openings where the siblings' guide draws rectangles, and
    # neither drawing gives a tray, a latch or a seam to take hold of.
    ("edgecore/eps112", "fans"): 0,
}


def test_every_stated_fan_figure_fills_its_bays():
    """Not policed by the rule, but true of all 55 stated here bar two, and worth
    knowing when it stops being true - a figure that no longer fills the tray is
    either a modelling error or a genuinely interesting chassis.

    THE AIS800-64D AND ITS OSFP TWIN THE AIS800-64O ARE THE INTERESTING CHASSIS, and
    they were the first ones this check found. They are ONE rear counted twice: the
    two guides' rear artwork is the same image file, identical to the hundredth of a
    pixel, and one fan part serves both - so the exemption is listed for each device
    because each device states the figure, not because there are two rears. Its datasheet says, twice, "4 hot-swappable fan modules
    (2 fans per module), 8 fans total with 7+1 redundancy", and its quick start's
    rear callout says "4 x fan trays"; the rear elevation and the datasheet's own
    rear photograph both show four trays, 81.6 mm wide on an 85.71 mm pitch. So
    the "7+1" counts the eight ROTORS and the rear holds four BAYS, and both
    numbers are the vendor's.

    That is why the exemption is keyed to the bay count as well as the device: if
    the rear is ever remodelled with a different number of trays, or the figure is
    ever re-read, this fails again and asks. Every other chassis here still has
    one fan per tray, including the AIS800-32D two rows above it in this census,
    whose "6+1" fills seven single-fan bays exactly."""
    odd = []
    for slug, d in devices():
        bays = {}
        for v in (d.get("views") or {}).values():
            for b in ((v.get("components") or {}).get("bays") or []):
                if b.get("group"):
                    bays[b["group"]] = bays.get(b["group"], 0) + 1
        for name, g in (d.get("groups") or {}).items():
            form = (((g or {}).get("attrs") or {}).get("redundancy") or "")
            if not form or not (lint._group_words(name, str((g or {}).get("term") or "")) & lint.FAN_WORDS):
                continue
            parts = form.split("+")
            if not all(p.isdigit() for p in parts):
                continue
            seen = bays.get(name, 0)
            if sum(int(p) for p in parts) == seen:
                continue
            if FIGURE_IS_NOT_THE_BAY_COUNT.get((slug, name)) == seen:
                continue
            odd.append(f"{slug}:{name} {form} in {seen} bays")
    assert not odd, odd


# WHAT EACH EXEMPTED DEVICE MUST SAY IN ITS OWN PROSE. This started as one hard-coded
# phrase - "2 fans per module" - asserted against every entry in the table above, which
# worked while every entry was an AIS800. The EPS pair broke it, and rightly: their figure
# is not about modules at all, so demanding that they say "2 fans per module" was demanding
# they say something untrue. The test's own docstring is the argument against the old form.
# So the REQUIRED PHRASE IS PART OF THE EXEMPTION. An exemption now declares both what the
# bay count is and the words the device must carry to earn it, which keeps the two kinds of
# mismatch apart: a figure that counts rotors inside trays, and a figure with no trays.
WHAT_THE_NOTE_MUST_SAY = {
    ("edgecore/ais800-64d", "fans"): "2 fans per module",
    ("edgecore/ais800-64o", "fans"): "2 fans per module",
    ("edgecore/eps121", "fans"): "THERE ARE NO BAYS",
    ("edgecore/eps122", "fans"): "THERE ARE NO BAYS",
    ("edgecore/eps112", "fans"): "THERE ARE NO BAYS",
}


def test_the_chassis_whose_figure_is_not_their_bay_count_say_so_in_prose():
    """An exemption that only lives in a test teaches nobody. The device carries
    the explanation where a reader of the library will meet it - in the group's
    own redundancy-note - so the count and the reason travel together."""
    by_slug = dict(devices())
    assert set(WHAT_THE_NOTE_MUST_SAY) == set(FIGURE_IS_NOT_THE_BAY_COUNT), (
        "every exemption declares the words that earn it, and only exemptions do")
    for (slug, group), phrase in WHAT_THE_NOTE_MUST_SAY.items():
        d = by_slug[slug]
        note = str((((d.get("groups") or {}).get(group) or {}).get("attrs") or {}).get("redundancy-note") or "")
        assert phrase in note, (slug, group, phrase)
        assert "bay" in note.lower() and "fan" in note.lower(), (slug, group)


def test_the_unstated_ones_are_the_ones_we_could_not_source():
    """The holdouts are deliberate and named. Four Edgecore chassis carry TWO
    conflicting fan figures in the staged corpus; the rest have no fan
    statement at all in any document we hold.

    THE ASR 9903 MADE IT TWENTY-ONE AND THE ASR 9902 TWENTY-TWO, and they are a
    third kind of holdout worth telling apart from the other two. Cisco is not
    silent about either and does not contradict itself: each data sheet says the
    chassis has its fans "in redundant configuration" and lists "Fan redundancy"
    in Table 2, and the fixed-port Hardware Installation Guide gives replacement
    steps. What none of them gives is the FORM. Four trays redundant is 3+1 or
    2+2, three trays is 2+1, and the difference is the whole question - so each
    group carries the sentence and no `redundancy`, which is the ruling the
    CSR310 got for "Hot swappable redundant fan modules" applied to a vendor who
    said more and still not enough.

    THE TWO ARRIVED TOGETHER AND THE SECOND ONE IS THE TEST OF THE FIRST. Three
    trays has only one sensible reading, 2+1, and it was still not written down,
    because a ratio nobody published is not a ratio this library states. The ASR
    9901 made it twenty-three on the same ruling a day later - "Fan redundancy"
    in its data sheet's Table 2, "Cisco ASR 9901 Router has three fan trays" in
    the install guide, and no arithmetic anywhere - so all three fixed-port
    chassis Cisco shipped with this wording are in this count together."""
    unstated = sorted(slug for slug, d in devices() if run(d))
    assert "edgecore/cor580" in unstated and "edgecore/dcs510" in unstated
    assert {"cisco/asr-9901", "cisco/asr-9902", "cisco/asr-9903"} <= set(unstated)
    assert len(unstated) == 23, unstated


def test_the_comparison_layer_can_now_reach_them():
    """The point of the exercise. It resolved on nothing before this. Forty
    when the rule landed; the R740xd made it forty-one the day its fans became
    bays with a group that quotes the technical guide's N+1, the AGR110
    forty-two, its fan group quoting the datasheet's 5+1, its AGR130 sibling
    forty-three, and the ASR 9006 forty-four the day FT0 and FT1 stopped being
    cutouts - its group states 1+1 and quotes the three sentences of the
    Overview and Reference Guide that have to be read together to get there.

    THE CSR310 DID NOT MAKE IT FORTY-FIVE, and that is the rule working rather
    than failing. Its fan tray IS a bay with a redundant group, but the
    datasheet's whole sentence is "Hot swappable redundant fan modules" - no
    form, no count - so the group carries a note and no `redundancy`, and the
    comparison layer correctly cannot reach it. An unstated group is an honest
    gap; the number this test holds counts devices whose vendor said something,
    not devices that have fans.

    THE TWO PARAGRAPHS ABOVE ARRIVED FROM DIFFERENT BRANCHES ON THE SAME DAY and
    are the two halves of one point: the ASR 9006 counts because its guide gives
    a form, the CSR310 does not because its datasheet gives a phrase. The number
    is meant to go up, one sourced statement at a time. A drop is the thing to
    look at.

    FORTY-FIVE IS THE CSR440, and it is the first in this family whose digit form
    and bay count agree without argument: the datasheet says 5+1 and the rear
    face has six fan modules, so test_every_stated_fan_figure_fills_its_bays
    checks 5+1 against six bays and is satisfied. Its CSR430 sibling had to drop
    its own 4+1 because that figure counts FANS INSIDE ONE TRAY - true at the
    wrong level - and the CSR310 above never had a form to check. Six removable
    modules is the arrangement the comparison layer was built for.

    FORTY-SIX IS THE DCS201, whose datasheet says "4+1 redundant fan modules" against five
    rear bays - and whose quick start counts them the same way, "5 x fan trays", so the two
    documents agree with each other and with the metal. Its three sibling chassis carry SIX
    fans on a 48.6 pitch and are already counted here; this one is five on a 58.8 pitch,
    which is why its fan is its own part rather than the family's.

    FORTY-SEVEN IS THE DCS202, the DCS201's copper sibling, which states the same "4+1
    redundant fan modules" over the same five bays - and seats the same fan, because its
    guide prints the DCS201's supply tables character for character and its own rear
    photograph puts the handles on a 59.06 pitch against the DCS201's 58.82. Two devices,
    one rear, one figure, counted twice because two vendors' documents state it twice.

    FORTY-EIGHT IS THE DCS240, and it is the first in this family to state 5+1 against SIX
    bays - "5+1 redundant hot-swappable fan modules" in the datasheet, "6 x fan trays" in the
    quick start's rear callout, and six measured bays on a 48.50 pitch. The CSR440's 5+1 was
    the first digit form to match its bay count at all; this one matches at a different count,
    on a different shell, with a fan of its own.

    FORTY-NINE IS THE DCS511, which states the DCS240's figure over the DCS240's bays and
    SEATS THE DCS240'S FAN. Its datasheet says "Hot-swappable 5 + 1 redundant fans" and its
    quick start's rear callout says "6 x fan trays", so the digit form and the bay count agree
    again. What is new is that nothing was measured twice: the six red handles on its own rear
    photograph fit a 48.81 pitch against the DCS240's 48.50, and the same colour instrument run
    over the DCS240's photograph reads its handles 1.1 mm away on average. One rear, two
    chassis, one fan part - counted twice because two documents state it twice.

    FIFTY IS THE EXP800-16O, and it is the first in this family whose bays do not butt.
    Its datasheet says "5+1 hot-swappable redundant fans" and its quick start's rear callout
    "6 x fan trays", so the digit form and the bay count agree as they did on the last two. What
    is new is the wall: six trays 41.45 mm wide on a 48.92 mm pitch, with a 7.47 mm chassis rail
    between each pair. Every other Edgecore rear counted here butts its trays edge to edge, and
    that rail is why this is the one device in the line whose fan-bay digits can be drawn at all
    - on the CSR440 and the DCS511 they would land inside a neighbouring bay.

    FIFTY-ONE IS THE EXP100-32X, which states "5+1" twice in one document - in its feature
    list and again in its interface callouts - against six bays on its rear elevation. It SEATS
    THE EXP800'S TRAY, and that was proven rather than assumed: its own six pull bars fit a
    49.263 mm pitch against the EXP800's 48.921, and the seams either side of its fan block put
    the two supplies within 1.2 mm of where that device carries them. One rear, two chassis,
    one fan part - counted twice because two datasheets state it twice.

    FIFTY-TWO IS THE EXP400-32X, the third and last of that shell, and it adds nothing new to
    this census except a third statement of the same figure - "5+1 redundant, hot-swappable fan
    modules" over six bays. It is here for the same reason the DCS202 is: the comparison layer
    counts DEVICES that state a redundancy, not distinct rears, and three devices sharing one
    fan part is a fact about the line rather than a duplicate.

    FIFTY-THREE IS THE AIS800-32D, and it is the first rear in this census with SEVEN bays.
    Its datasheet says "7 Hot-swappable fan modules with 6+1 redundant fans" twice - in the
    feature list and in the interface callouts - and its quick start's rear callout "7 x fan
    trays"; the rear elevation, measured on two separate row bands, has seven trays 41.65 mm
    wide on a 45.005 mm pitch with a 3.36 mm rail between. The digit form and the bay count
    agree, as they have on every Edgecore rear here. What the census cannot say, and the
    device records as a gap, is which end the trays number from: the elevation is a 1.83 px/mm
    raster and a 2 mm numeral is under four pixels.

    FIFTY-FOUR IS THE AIS800-32O, the OSFP twin, and it is the DCS202/EXP400 case again: the
    same datasheet states the same "6+1" for both models, the same rear elevation is
    pixel-identical between the two guides, and one fan part serves both. Counted twice
    because two devices state it, not because there are two rears.

    FIFTY-FIVE IS THE AIS800-64D, AND IT IS THE FIRST DEVICE IN THIS CENSUS WHOSE REDUNDANCY
    FIGURE DOES NOT COUNT BAYS. Its datasheet says, twice, "4 hot-swappable fan modules (2 fans
    per module), 8 fans total with 7+1 redundancy", and its quick start's rear callout reads
    "4 x fan trays"; the rear elevation and the datasheet's own rear photograph both give FOUR
    trays, 81.6 mm wide on an 85.71 mm pitch. So the bay count is four and the "7+1" counts the
    EIGHT rotors inside them, two per tray - and the device says so in its fans group rather
    than leaving a reader to divide. Every other Edgecore rear in this census has one fan per
    tray and gets away with the two numbers being the same; this one does not, and the AIS800
    line now holds both cases: the 32-port models' "6+1" over seven single-fan trays and this
    one's "7+1" over four double-fan trays. A census that compares the digit forms alone would
    call these two the same kind of rear, which is exactly why the redundancy-note is prose.

    FIFTY-SIX IS THE AIS800-64O, the OSFP twin of the one above, and it is the FIFTY-FOUR case
    applied to the double-fan rear: the shared datasheet states the same "7+1" for both models,
    the two guides' rear elevations are the same image file - identical bounding boxes and a
    maximum difference of zero grey levels - and edgecore/fan-2u-1x1sn@1 serves both. So the
    census now holds two entries whose figure does not count bays, and they are one rear. Both
    are listed in FIGURE_IS_NOT_THE_BAY_COUNT because the exemption is keyed to the device that
    states the figure; if either rear is ever remodelled with a different tray count, that
    device fails on its own and asks again.

    FIFTY-SEVEN IS THE EDGECORE AGR560, and it is the THIRD DEVICE ON THAT SAME REAR and the
    only one of the three whose figure does count bays. Its datasheet says "Fans:
    Hot-swappable 3+1 redundant fans" over the same four trays and the same
    edgecore/fan-2u-1x1sn@1 - the FRU number `FAN-2U-1x1SN-F` is printed in all three
    datasheets - so three machines share one tray and their vendor counts it three different
    ways: 7+1 twice, meaning rotors, and 3+1 once, meaning trays. THE AGR560 NEEDS NO
    EXEMPTION, which is the whole point of listing it here: the exemption table is not a list
    of devices with four fan bays, it is a list of devices whose stated figure is about
    something other than bays, and being on the same rear as two of those does not put a
    device on it.

    FIFTY-EIGHT IS THE EDGECORE DCS520, the FOURTH and last device on that 440 x 649.2 x 87
    shell, and it needs no exemption either: "3 + 1 redundant, hot-swappable fan modules",
    printed three times in its datasheet, over four bays. So the shell now carries four
    devices, three product lines and TWO WAYS OF COUNTING THE SAME TRAY - 7+1 twice, meaning
    rotors, and 3+1 twice, meaning bays.
    AND ITS REAR IS NOT THEIR REAR, which is worth recording here because the census is
    about fans: the other three stack both supplies at the left with the four trays to their
    right, and this one puts a supply at each END with the trays between them. Same tray
    pitch to six hundredths of a millimetre, different architecture around it.

    FIFTY-NINE AND SIXTY ARE THE EDGECORE EPS121 AND EPS122, and they are the first
    entries here whose fans are not FRUs at all. Both state "2+1 fixed redundant fans" -
    the word is the vendor's - over three fans with no bay, no latch and no replacement
    procedure; the shared guide's FRU Replacement section covers the supplies only. They
    are PLACED rather than bayed and they sit in FIGURE_IS_NOT_THE_BAY_COUNT at 0.
    THAT IS WHY THE COMPARISON LAYER MATTERS HERE. A reader comparing rear serviceability
    across this library needs "2+1, and you cannot change them" to be reachable, and it is
    only reachable because the figure is recorded even though nothing swaps. A census that
    only counted removable trays would report these two as having no cooling at all.

    SIXTY-ONE IS THE EDGECORE EPS112, the third device on the 440 x 350.3 x 44 shell and
    the first of the three to arrive with its own document rather than the shared one. It
    states "2+1 fixed redundant fans" in both its guide and its datasheet, over three fans
    that nothing swaps, so it joins its two siblings in FIGURE_IS_NOT_THE_BAY_COUNT at 0.
    Three of the sixty-one entries are now fixed fans on one shell, which is a small
    population and a real one: this library's rear-serviceability question has an answer
    for an access switch that cannot be serviced at the rear at all.

    SIXTY-TWO IS THE EDGECORE EPS203, and it needs no exemption - which is worth a line
    precisely because the three entries above it do. It states "Hot-swappable 2 + 1
    redundant fan trays" in its key features and again in Interfaces callout 8, over THREE
    BAYS, so the figure and the bay count agree the way most of this census does. Its guide
    carries a Fan Tray Replacement procedure where the EPS1xx guide carries none.
    SO THE EDGECORE ACCESS LINE NOW ANSWERS THE QUESTION BOTH WAYS. The EPS1xx shell puts
    2+1 over three fans nobody can swap; the EPS20x shell puts 2+1 over three trays with a
    thumbscrew each, and one fan module - FAN-1U-1x1M - fits all three EPS20x chassis. Same
    vendor, same figure, same port count, opposite serviceability, and a reader comparing
    rears can now see that from the data rather than from the prose.

    SIXTY-THREE IS THE EDGECORE EPS201, the EPS203's shell-mate, and it states the same
    "Hot-swappable 2 + 1 redundant fan trays" over the same three bays with the same
    FAN-1U-1x1M tray in them. What it adds to this census is the AIRFLOW: it is the first
    entry here whose fan tray ships in two directions under two part numbers, -F and -B,
    and whose two orderable configurations differ in nothing a drawing can show but the
    colour of the handles. Its shell-mate ships front-to-back only. So one fan part, one
    redundancy figure, two chassis, and only one of them lets you choose which way the air
    goes.

    SIXTY-FOUR IS THE EDGECORE EPS202, which completes the EPS20x trio, and it is the one
    whose SHELL is not shared: 438 x 442 x 43.7 against its two siblings' 438 x 474 x 44,
    thirty-two millimetres shallower. It states the same "Hot-swappable 2 + 1 redundant fan
    trays" over the same three bays with the same FAN-1U-1x1M tray, front-to-back only.
    SO THE CENSUS NOW CARRIES A CASE IT DID NOT HAVE: one fan tray, one redundancy figure
    and one bay pitch across THREE chassis, two of which share a shell and one of which
    does not. What travels with the tray is the cooling; what does not travel is the box.

    SIXTY-FIVE IS THE EDGECORE COR550, a 4+1 over five bays - the same figure over the
    same bay count as the Edgecore DCS202 and six UfiSpace chassis already here. It states
    "4+1 redundant, hot-swappable fan modules" in its key features and "Fans:
    Hot-Swappable 4+1 redundant fans" in Physical and Environmental, so the figure and the
    bay count agree.
    WHAT IT ADDS IS A REDUNDANCY FIGURE WHOSE FAN COUNT IS NOT KNOWN, which is a shape this
    census has met before from the other side. edgecore/fan-2u-1x1sn@1's three chassis all
    say "4 hot-swappable fan modules (2 fans per module), 8 fans total with 7+1
    redundancy" - the vendor counting FANS where the bays count TRAYS, which is why those
    entries read 7+1 over four bays. The COR550 is the same vendor on a 2RU shell with one
    rotor visible per tray and NO per-module fan count published anywhere, so 4+1 over five
    bays is all that can be said. If it turned out to carry two fans a tray like its
    shell-neighbours, the vendor's own figure would have been 9+1 and it is not.
    AND ITS TRAY IS ITS OWN. The AGR560 and the DCS520 sit on the same 440 x 87 shell and
    take four trays about 80 mm wide; this takes five at 68.0 x 62.3 on a 68.53 pitch. So
    the shell does not carry the cooling either - which is the EPS20x lesson above with the
    terms exchanged: there, one tray crossed three boxes; here, one box shape carries three
    different trays.

    SIXTY-SIX IS THE EDGECORE DCS500, a 3+1 over four bays - the commonest figure in this
    census, carried by the AGR560 and DCS520 on this vendor's other 2RU shells and by
    two dozen UfiSpace chassis. It states "3+1 redundant, hot-swappable fan modules" and
    "Hot-swappable 3 + 1 redundant fans", and four trays sit between its two supplies.
    WHAT IT ADDS IS THE NUMBERING OF THE FANS THEMSELVES. The vendor sells the chassis in
    two series whose only stated difference is that one prints its ports, fans and
    supplies from zero and the other from one; this is the zero-based OZ, so its trays
    are fan-0..fan-3 even though both documents' rear drawings print 4..1. The redundancy
    figure does not care which, which is the point: a comparison keyed on the figure is
    safe across the two series, and one keyed on a fan's printed number is not.

    SIXTY-SEVEN IS THE EDGECORE AMX3200, a 4+1 over five bays like the COR550 two entries
    above, and one of the few whose vendor states the fans inside the trays - as the
    AIS800-64D, AIS800-64O and AGR560 datasheets do with '2 fans per module'. Its ordering
    table says 'Fan-tray modules with 5 pcs of 40.5 mm x 70.14 mm 12V fans': one fan per
    tray, five trays, four needed, so here the tray count and the fan count are the same
    number and the redundancy figure means the same thing counted either way.

    SIXTY-EIGHT IS THE MAIAEDGE PORT EXTENDER, a 3+1 over four bays - "3+1 Redundant Fans"
    on its datasheet's page 3. It is the first entry whose BAYS ARE NOT MEASURED: the rear
    is known from an oblique setup video that shows only its right half, so the four
    modules are the datasheet's count placed symmetrically about the management panel.
    The figure is sourced and the geometry is not, and the census compares the figure -
    which is exactly why it can take a device whose rear is still an estimate.

    SIXTY-NINE AND SEVENTY ARE THE NOKIA 7750 SR-1, AC AND DC: one chassis rear in two
    builds, four fan trays across the top of it, and a guide sentence (SR1 p75) that
    gives the form without a digit - "four redundant variable-speed fan trays", with the
    remaining fans cooling adequately when a single fan fails. Four trays, one allowed
    to fail, is 3+1 over four bays, and the two devices state it twice because the AC
    and DC chassis are two part numbers with two rear faces, not one device configured.

    SEVENTY-ONE IS THE NOKIA 7750 SR-12, the first entry with NOTHING SPARE: 3+0 over
    three vertical trays. The guide says "Three fan trays are required for normal
    operation" (SR12 p84), a single fan failure takes its whole tray out for replacement
    (p80), and the chassis rides through a missing tray for only two minutes at 35 C. That
    is a stated form with a zero in it, not an absence, so the census counts it. The SR-7
    beside it has one tray and states no form, and is not counted.
    """
    from portrayal import comparable as C
    n = sum(1 for _, d in devices() if C.resolve(d).get("fan-redundancy"))
    assert n == 71, n
