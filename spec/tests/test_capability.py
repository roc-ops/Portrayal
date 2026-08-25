"""Capability levels are derived, and the level-3 consistency check is the point."""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import capability  # noqa: E402

PROFILES = capability.load_profiles(SPEC / "schemas")


def load(rel):
    return yaml.safe_load((LIB / "devices" / rel / "device.yaml").read_text())


def assess(dev):
    return capability.assess(dev, profiles=PROFILES)[0]


def test_no_device_declares_its_own_level():
    """Derive, never declare. An author who can write `level: 3` will, and then
    it lies the first time the model changes underneath it."""
    for man in sorted(LIB.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(man.read_text())
        assert "capability" not in d, man
        assert "level" not in d, man


def test_six_views_are_not_enough_they_must_be_one_box():
    """The AGR420 was written 480mm deep while its provenance said the top,
    bottom and sides were the AGR400 shell - and the AGR400 is 524. A human
    caught that. This is the predicate that catches it every time."""
    dev = load("edgecore/as7946-30xb")
    assert assess(dev)["level"] == 4

    dev["views"]["left"]["size"]["w"] = 524.0      # sides say one depth,
    cap = assess(dev)                              # top and chassis say another
    assert cap["level"] == 2, "an inconsistent box must not reach solid"
    blocked = {b["level"]: b["needs"] for b in cap["blocked"]}
    assert "chassis depth disagrees" in blocked[3]
    assert "left.w=524" in blocked[3] and "top.h=480" in blocked[3]


def test_level_is_the_longest_satisfied_prefix():
    """The c100g carries group and rel-pos on all 39 of its placements and has
    two views, so it is `faced` however addressable its front panel is. The
    chain is what makes one number honest; listing every unsatisfied level
    rather than only the next is what keeps it from being a grade - here it
    says the shortest real path is four views plus two thin group blocks."""
    cap = assess(load("casa/c100g"))
    assert (cap["level"], cap["name"]) == (2, "faced")
    blocked = {b["level"]: b["needs"] for b in cap["blocked"]}
    assert "top, bottom, left, right" in blocked[3]
    assert "`index-origin` on 2 groups furniture, grounding" in blocked[4]
    assert "`group` on" not in blocked[4], "every placement is already grouped"


def test_blocked_says_how_to_fix_it_in_words():
    """A capability report that does not say how to fix it is a scoreboard."""
    cap = assess(load("ufispace/s9510-28dc"))
    needs = cap["blocked"][0]["needs"]
    assert "`rel-pos`" in needs and "front" in needs


def test_a_view_needs_no_panel_block_to_count():
    """`panel` carries decor and cutouts, both optional, and the faceplate is
    drawn from the size regardless. Requiring it put the best-modelled device in
    the portfolio at level 0 while it rendered perfectly."""
    dev = load("edgecore/as7946-30xb")
    assert not any("panel" in v for v in dev["views"].values())
    assert assess(dev)["level"] == 4


def test_front_may_take_its_size_from_the_chassis_but_top_may_not():
    """render.py falls back to the chassis for a view with no size. That is the
    truth for a face that IS width x height; for a top the second number is
    depth, so the fallback would silently certify a wrong box."""
    ch = {"width": 440, "height": 44, "depth": 500}
    assert capability.effective_size("front", {}, ch) == (440.0, 44.0)
    assert capability.effective_size("top", {}, ch) is None


def test_wired_is_not_vacuously_true():
    """A device with nothing to correlate must not report that everything is
    correlated - that is the flag reporting a hole as a feature."""
    dev = load("halny/hlx-tgv")
    assert "wired" not in assess(dev)["flags"]


def test_declared_gaps_carry_what_no_rule_can_see():
    dev = load("ufispace/s9510-28dc")
    gaps = capability.declared_gaps(dev)
    assert [g["what"] for g in gaps] == ["port-led-semantics"]
    assert gaps[0]["because"] == "vendor-silent"
    assert gaps[0]["wanted"], "wanted is the field that makes it actionable"


def test_derived_gaps_are_not_hand_written():
    """A hand-kept list of machine-findable problems goes stale the first time
    someone fixes one, so the rules are asked rather than transcribed."""
    man = LIB / "devices/edgecore/as7946-74xksb/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    by_rule = {g["because"]: g for g in gaps}
    assert by_rule["L20"]["count"] > 100, "the prose-in-attrs debt is real"
    assert all(g["kind"] == "derived" for g in gaps)


def test_cannot_evaluate_is_not_the_same_answer_as_no():
    """The two most complete models in the portfolio - level 4, `modelled`, 19
    and 23 attrs off a datasheet - declare no `profile:`, so `specified` has
    nothing to judge them against. Reporting that as a bare `no` is a silent
    failure: it is indistinguishable from a device that was checked and came up
    short, and a reader who knows the attr count concludes the predicate is
    broken."""
    complete = assess(load("edgecore/as7946-30xb"))
    assert complete["level"] == 4
    assert "specified" not in complete["flags"]
    assert complete["unknown"] == ["specified"]

    checked = assess(load("edgecore/as7326-56x"))          # has a profile,
    assert "specified" not in checked["flags"]             # genuinely short a key
    assert checked["unknown"] == []


def test_an_unevaluable_flag_files_its_gap_against_the_missing_thing():
    """`specified: no` on a device with 23 datasheet attrs reads as a broken
    predicate. `profile-undeclared` reads as one line of YAML somebody has to
    decide on, which is what it is - and which profile a device is, is a
    decision, not something to guess to make a number go up."""
    man = LIB / "devices/edgecore/as7946-74xksb/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    what = {g["what"] for g in gaps}
    assert "profile-undeclared" in what
    assert "specified" not in what, "the gap names the cause, not the symptom"
    gap = next(g for g in gaps if g["what"] == "profile-undeclared")
    assert "profiles.yaml" in gap["wanted"] and "`specified`" in gap["wanted"]


def test_both_kinds_of_gap_say_why_in_the_same_field():
    """A derived gap carried `rule` and a declared one `reason`, so a renderer
    could not tell by position which it was holding and put both in one badge.
    One field, and `kind` says how to read it."""
    man = LIB / "devices/ufispace/s9510-28dc/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = (capability.declared_gaps(dev)
            + capability.derived_gaps(man, dev, [str(LIB)], cap, flags))
    assert all("because" in g for g in gaps)
    assert not any("rule" in g or "reason" in g for g in gaps)
    kinds = {g["because"]: g["kind"] for g in gaps}
    assert kinds["vendor-silent"] == "declared"
    assert kinds["L21"] == "derived"


def test_the_chain_is_stated_once():
    """`capability.blocked` carries every unsatisfied level with the sentence
    that says how to fix it. A gap record repeating it verbatim is one statement
    printed twice, and left consumers de-duplicating by string equality."""
    man = LIB / "devices/casa/c100g/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    assert [b["level"] for b in cap["blocked"]] == [3, 4]
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    names = {n for _, n in capability.LEVELS}
    assert not (names & {g["what"] for g in gaps}), "the chain is not a gap"
    needs = {b["needs"] for b in cap["blocked"]}
    assert not (needs & {g["wanted"] for g in gaps})


def test_a_gap_that_counts_nothing_omits_count():
    """`count: 0` reads as "nothing found" rather than "nothing to count"."""
    man = LIB / "devices/edgecore/as7946-30xb/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    flag_gap = next(g for g in gaps if g["what"] == "profile-undeclared")
    assert "count" not in flag_gap
    rule_gap = next(g for g in gaps if g["because"] == "L21")
    assert rule_gap["count"] > 0


def test_search_finds_what_a_device_is_not_how_it_was_phrased():
    """The filter matched manufacturer, model, series, family and description,
    so it found devices by wording. `search` flattens what a device IS - attrs,
    group attrs, component refs - which otherwise lives in configs.json and
    would cost one fetch per device to index in the browser."""
    import subprocess
    import sys
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable, SPEC / "tools/portrayal/devices_index.py",
                            "--library", LIB, "--out", tmp],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        idx = {d["name"]: d["search"]
               for d in json.load(open(f"{tmp}/devices.json"))["devices"]}

    def find(q):
        return {n for n, blob in idx.items() if q in blob}

    # the ASIC nobody writes in a summary
    assert "as7946-74xksb" in find("qumran")
    # a form factor, from the component ref rather than any sentence
    assert "as7946-30xb" in find("qsfp-dd")
    # 400G is declared ONLY in groups.qsfpdd-400g.attrs.speed on the AGR400 -
    # device attrs say "2.4 Tb/s" and never mention it
    assert find("400g") == {"as7946-30xb", "s9510-28dc"}
    # and it must not find the AGR420, whose QSFP-DD ports are declared 100g
    assert "as7946-74xksb" not in find("400g")
    # transcribed vendor prose is deliberately NOT indexed: `states` holds
    # "Blue = all lanes linked, Off = not all lanes linked", and folding that in
    # makes half the portfolio match "off" and "link"
    assert "lanes" not in idx["as7946-74xksb"]


def test_a_gap_names_the_flag_it_blocks_in_a_field():
    """The About panel renders a `?specified` chip and wants to explain it. The
    gap is correctly named for the cause - `profile-undeclared` - so a name
    match finds nothing, and matching the flag in backticks inside `wanted` is
    prose parsing that breaks silently the first time someone rewords it."""
    man = LIB / "devices/edgecore/as7946-30xb/device.yaml"
    dev = yaml.safe_load(man.read_text())
    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    assert all("blocks" in g for g in gaps)

    for flag in cap["unknown"] + [f for f in capability.FLAGS
                                  if f not in cap["flags"]]:
        assert [g for g in gaps if flag in g["blocks"]], \
            f"nothing explains why {flag} is not earned"

    cause = next(g for g in gaps if g["what"] == "profile-undeclared")
    assert cause["blocks"] == ["specified"]
    # a debt no capability is waiting on says so, rather than inventing one
    assert next(g for g in gaps if g["because"] == "L21")["blocks"] == []


def test_a_declared_gap_may_block_nothing():
    """Empty is a fine answer. The S9510's lamps render and nothing downstream
    waits on their vocabulary; a join that is sometimes fabricated is worse than
    one that is sometimes empty."""
    gaps = capability.declared_gaps(load("ufispace/s9510-28dc"))
    assert gaps[0]["blocks"] == []
