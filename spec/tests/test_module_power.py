"""L27, L28, L29 - a module's watts, which way they point, and what a chassis
can account for.

Every component and every device here is planted in a `tmp_path` library. The
obvious way to test L27 is to point it at the AGR PSUs, which really do state no
output wattage because Edgecore never published one, and the obvious way to test
L29 is to point it at the C100G, which really cannot total any of its five
cards. Four tests in this repo have already had to be repointed because they
asserted somebody's real debt was still outstanding, and each time the person
who paid the debt broke the suite. A test that owns its own defect keeps working
whichever way the library goes.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402


def plant(root, ref, cls="line-card", **contract):
    """Write one contract into a tmp library at `ns/name/vN/contract.yaml`."""
    nsname, major = ref.rsplit("@", 1)
    p = root / "components" / nsname / f"v{major}" / "contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": 1, "kind": "component", "name": nsname.split("/")[-1],
            "version": f"{major}.0.0", "class": cls,
            "size": {"w": 40.0, "h": 20.0}}
    data.update(contract)
    p.write_text(yaml.safe_dump(data))
    return p


def plant_device(root, name, bays, configurations=None):
    """A one-view chassis whose bays accept the refs given."""
    p = root / "devices" / "acme" / name / "device.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": name,
        "views": {"front": {"size": {"w": 440.0, "h": 44.0}, "components": {
            "bays": [dict(b, at=[0.0, 0.0], size={"w": 40.0, "h": 20.0})
                     for b in bays]}}},
        "configurations": configurations or {}}))
    return p


def plant_paired_device(root, name, front, rear):
    """A front/rear chassis: `front` and `rear` are lists of accepted refs.

    Two views, because a paired I/O module lives on the OPPOSITE face from the
    card it serves - that is what makes it a pairing, and a one-view fixture
    cannot express the thing L30 looks for.
    """
    p = root / "devices" / "acme" / name / "device.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)

    def view(refs, tag):
        return {"size": {"w": 440.0, "h": 44.0}, "components": {"bays": [
            {"id": f"{tag}-{i}", "at": [0.0, 0.0],
             "size": {"w": 40.0, "h": 20.0}, "accepts": [r]}
            for i, r in enumerate(refs)]}}

    p.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": name,
        "views": {"front": view(front, "front"), "rear": view(rear, "rear")}}))
    return p


def double_count(path, root):
    lint.WARNINGS.clear()
    lint.lint_device_double_count(path, yaml.safe_load(path.read_text()),
                                  [str(root)])
    return [w for w in lint.WARNINGS if "[L30]" in w]


def found(path, root, code):
    """Warnings and errors of one code raised by one manifest, and nothing else."""
    lint.WARNINGS.clear()
    lint.ERRORS.clear()
    data = yaml.safe_load(path.read_text())
    if data.get("kind") == "device":
        lint.lint_device_module_power(path, data, [str(root)])
    else:
        lint.lint_component_power(path, data)
    return [m for m in lint.WARNINGS + lint.ERRORS if f"[{code}]" in m]


# ---------------------------------------------------------------- L27


def test_a_power_bearing_module_with_no_figure_is_named(tmp_path):
    """The defect the rule exists for. `edgecore/agr-psu-ac` is this shape and
    is unfixable today - Edgecore's datasheet gives input current only."""
    p = plant(tmp_path, "acme/psu@1", cls="psu")
    assert len(found(p, tmp_path, "L27")) == 1


def test_the_message_names_the_key_for_that_class_not_a_generic_one(tmp_path):
    """The whole design turns on draw and supply never sharing a key, so the
    warning that makes an author add one has to say which side they are on. A
    message reading 'add a power figure' invites exactly the mistake."""
    psu = plant(tmp_path, "acme/psu@1", cls="psu")
    card = plant(tmp_path, "acme/card@1", cls="line-card")
    assert "power-output-w" in found(psu, tmp_path, "L27")[0]
    assert "PROVIDE" in found(psu, tmp_path, "L27")[0]
    assert "power-draw-max-w" in found(card, tmp_path, "L27")[0]
    assert "IMPOSES" in found(card, tmp_path, "L27")[0]


def test_the_message_forbids_estimating_the_number(tmp_path):
    """An unsourced watt figure is the same number minus the warning, and the
    rule has to say so where the author reads it - otherwise the cheapest way
    to clear a warning is to invent the fact it is reporting."""
    p = plant(tmp_path, "acme/card@1")
    assert "Do not estimate" in found(p, tmp_path, "L27")[0]


def test_any_one_draw_figure_satisfies_the_rule(tmp_path):
    """A vendor that publishes only a typical has still said something, and a
    rule that insists on `max` would make the author choose between silence and
    filing the typical under the wrong name."""
    for key in ("power-draw-max-w", "power-draw-typical-w", "power-draw-min-w"):
        p = plant(tmp_path, "acme/card@1", attrs={key: 310.0})
        assert found(p, tmp_path, "L27") == [], key


def test_supply_does_not_satisfy_draw_or_the_reverse(tmp_path):
    """The one thing that must not happen: a card cleared by declaring output,
    which is what a single `watts` key allowed."""
    card = plant(tmp_path, "acme/card@1", attrs={"power-output-w": 650.0})
    psu = plant(tmp_path, "acme/psu@1", cls="psu",
                attrs={"power-draw-max-w": 650.0})
    assert len(found(card, tmp_path, "L27")) == 1
    assert len(found(psu, tmp_path, "L27")) == 1


def test_classes_that_neither_draw_nor_supply_are_not_asked(tmp_path):
    """A C14 inlet is passive and a sticker draws nothing. A rule that ran over
    every class would report 97 components and mean nothing."""
    for cls in ("inlet", "sticker", "port", "mechanical", "led"):
        p = plant(tmp_path, "acme/thing@1", cls=cls)
        assert found(p, tmp_path, "L27") == [], cls


# ---------------------------------------------------------------- L28


def test_watts_is_refused_because_it_does_not_say_which_direction(tmp_path):
    """`attrs: {watts: '650'}` shipped on ten PSU contracts. The string is the
    smaller half of what is wrong with it."""
    p = plant(tmp_path, "acme/psu@1", cls="psu", attrs={"watts": "650"})
    msgs = found(p, tmp_path, "L28")
    assert len(msgs) == 1
    assert "draws this or provides it" in msgs[0]
    assert "power-output-w" in msgs[0], "it must say what to write instead"


def test_the_device_spelling_is_reserved_and_refused_on_a_component(tmp_path):
    """This is the load-bearing one. A downstream author writing the obvious
    `sum(attrs['power-max-w'])` over a chassis's occupants must get zero results
    rather than a plausible total: make the wrong query fail to resolve, do not
    make it resolve wrongly."""
    for key in ("power-max-w", "power-typical-w", "power-min-w",
                "power-max-ac-w", "power-max-dc-w"):
        p = plant(tmp_path, "acme/card@1", attrs={key: 850.0})
        msgs = found(p, tmp_path, "L28")
        assert len(msgs) == 1, key
        assert "belongs to the whole device" in msgs[0]


def test_the_ban_is_an_error_and_not_a_warning(tmp_path):
    """A warning-level ban is not a ban. It can be an error where L26 and L27
    cannot because it depends on no document nobody has - renaming a key needs
    no new information."""
    lint.WARNINGS.clear()
    lint.ERRORS.clear()
    p = plant(tmp_path, "acme/psu@1", cls="psu", attrs={"watts": 650})
    lint.lint_component_power(p, yaml.safe_load(p.read_text()))
    assert [m for m in lint.ERRORS if "[L28]" in m]
    assert not [m for m in lint.WARNINGS if "[L28]" in m]
    # And L27 stands beside it, because a banned key is not a figure: the module
    # still states nothing this library can add up. The two clear together.
    assert len([m for m in lint.WARNINGS if "[L27]" in m]) == 1


def test_a_draw_that_contradicts_itself_is_an_error(tmp_path):
    """Typical above max is a transcription slip in this repo, not a fact about
    the world, so the person reading the message can always fix it."""
    p = plant(tmp_path, "acme/card@1", attrs={"power-draw-typical-w": 900.0,
                                              "power-draw-max-w": 850.0})
    msgs = found(p, tmp_path, "L28")
    assert len(msgs) == 1
    assert "typical cannot exceed max" in msgs[0]


def test_all_three_orderings_are_checked_not_only_neighbours(tmp_path):
    """min > max with no typical between them is still a contradiction, and a
    pairwise check on neighbours alone would let it through."""
    p = plant(tmp_path, "acme/card@1", attrs={"power-draw-min-w": 900.0,
                                              "power-draw-max-w": 850.0})
    assert len(found(p, tmp_path, "L28")) == 1


def test_figures_in_order_raise_nothing(tmp_path):
    p = plant(tmp_path, "acme/card@1", attrs={"power-draw-min-w": 149.8,
                                              "power-draw-typical-w": 296.7,
                                              "power-draw-max-w": 350.0})
    assert found(p, tmp_path, "L28") == []
    assert found(p, tmp_path, "L27") == []


def test_equal_figures_are_not_a_contradiction(tmp_path):
    """A card whose typical IS its max is a real datasheet - Cisco's per-card
    table gives one number per ambient and no typical at all."""
    p = plant(tmp_path, "acme/card@1", attrs={"power-draw-typical-w": 310.0,
                                              "power-draw-max-w": 310.0})
    assert found(p, tmp_path, "L28") == []


# ---------------------------------------------------------------- L29


def test_a_chassis_counts_the_modules_it_cannot_account_for(tmp_path):
    """The failure this exists for is a sum that is quotable when it is not: a
    chassis whose cards have no figures totals to a small, confident, wrong
    number with nothing saying which bays were skipped."""
    plant(tmp_path, "acme/card-a@1")
    plant(tmp_path, "acme/card-b@1", attrs={"power-draw-max-w": 850.0})
    dev = plant_device(tmp_path, "chassis", [
        {"id": "slot-0", "accepts": ["acme/card-a@1", "acme/card-b@1"]}])
    msgs = found(dev, tmp_path, "L29")
    assert len(msgs) == 1
    assert "acme/card-a@1" in msgs[0]
    assert "1 of 2 module(s)" in msgs[0]


def test_the_total_is_called_a_floor_while_anything_is_missing(tmp_path):
    """A number that excludes an unknown number of terms is a lower bound. The
    word is the point: 'total' invites a reader to compare it to a PSU rating."""
    plant(tmp_path, "acme/card@1")
    dev = plant_device(tmp_path, "chassis",
                       [{"id": "slot-0", "accepts": ["acme/card@1"]}])
    assert "floor and not a total" in found(dev, tmp_path, "L29")[0]


def test_one_warning_per_module_so_the_register_records_the_size(tmp_path):
    """`capability.RULE_GAPS` turns a rule's warning count into the gap's size,
    and a chassis that cannot account for five cards is a bigger hole than one
    that cannot account for one. A single warning per device flattens both to 1."""
    for n in "abc":
        plant(tmp_path, f"acme/card-{n}@1")
    dev = plant_device(tmp_path, "chassis", [
        {"id": f"slot-{i}", "accepts": [f"acme/card-{n}@1"]}
        for i, n in enumerate("abc")])
    assert len(found(dev, tmp_path, "L29")) == 3


def test_a_fully_sourced_chassis_raises_nothing(tmp_path):
    plant(tmp_path, "acme/card@1", attrs={"power-draw-max-w": 850.0})
    plant(tmp_path, "acme/fan@1", cls="fan", attrs={"power-draw-max-w": 1800.0})
    dev = plant_device(tmp_path, "chassis", [
        {"id": "slot-0", "accepts": ["acme/card@1"]},
        {"id": "fan-0", "accepts": ["acme/fan@1"]}])
    assert found(dev, tmp_path, "L29") == []


def test_the_population_is_what_a_bay_accepts_not_only_what_is_installed(tmp_path):
    """A bay's occupant is a configuration choice and the chassis has to be
    totalled for each of them, so a card accepted anywhere and unsourced blocks
    some real configuration's total even if no default installs it."""
    plant(tmp_path, "acme/card-a@1", attrs={"power-draw-max-w": 310.0})
    plant(tmp_path, "acme/card-b@1")
    dev = plant_device(tmp_path, "chassis", [
        {"id": "slot-0", "accepts": ["acme/card-a@1", "acme/card-b@1"],
         "default": "acme/card-a@1"}])
    assert "acme/card-b@1" in found(dev, tmp_path, "L29")[0]


def test_a_configuration_can_introduce_a_module_no_bay_lists(tmp_path):
    """`configurations.<name>.bays` maps a bay to a ref directly, so reading
    `accepts` alone would miss whatever a variant installs."""
    plant(tmp_path, "acme/card-a@1", attrs={"power-draw-max-w": 310.0})
    plant(tmp_path, "acme/card-b@1")
    dev = plant_device(
        tmp_path, "chassis",
        [{"id": "slot-0", "accepts": ["acme/card-a@1"]}],
        configurations={"dense": {"bays": {"slot-0": "acme/card-b@1"}}})
    assert "acme/card-b@1" in found(dev, tmp_path, "L29")[0]


def test_psu_bays_are_not_counted_in_the_draw_shortfall(tmp_path):
    """A PSU's figure is `power-output-w` and belongs to the supply side, which
    is a different sum with a different meaning. Counting a PSU as an
    unaccounted-for DRAW would be the category error the design exists to stop,
    committed by the rule that reports it."""
    plant(tmp_path, "acme/psu@1", cls="psu")
    dev = plant_device(tmp_path, "chassis",
                       [{"id": "psu-0", "accepts": ["acme/psu@1"]}])
    assert found(dev, tmp_path, "L29") == []


def test_transceivers_are_in_the_population(tmp_path):
    """32 cages of 400G ZR at ~20 W is 640 W against a line card's own 920 W.
    Excluding occupants makes the total wrong by more than it computes."""
    plant(tmp_path, "acme/zr@1", cls="transceiver")
    dev = plant_device(tmp_path, "chassis",
                       [{"id": "cage-0", "accepts": ["acme/zr@1"]}])
    assert len(found(dev, tmp_path, "L29")) == 1


def test_a_chassis_with_no_bays_at_all_raises_nothing(tmp_path):
    """A fixed box has nothing to total and must not be reported as having an
    incomplete total - that is a flag reporting an absence as a defect."""
    dev = plant_device(tmp_path, "chassis", [])
    assert found(dev, tmp_path, "L29") == []


# ---------------------------------------------------------------- power-envelope


def _envelope(value):
    """A minimal device carrying one `power-envelope`, against the schema."""
    import json

    from jsonschema import Draft202012Validator
    schema = json.loads((SPEC / "schemas/device.schema.json").read_text())
    dev = {"format": 1, "kind": "device", "name": "chassis", "version": "0.1.0",
           "attrs": {"power": {"power-max-w": "4000", "power-envelope": value}},
           "views": {"front": {"size": {"w": 440.0, "h": 44.0}}}}
    # Only this key's errors: a deliberately minimal device is missing other
    # required fields, and those are not what is under test here.
    return [e.message for e in Draft202012Validator(schema).iter_errors(dev)
            if "power-envelope" in list(e.path) or "power-envelope" in e.message]


def test_the_envelope_vocabulary_is_closed():
    """It decides whether a module total may be reconciled against the vendor's
    figure at all, and an uncontrolled value that licenses a reconciliation
    drifts into `fully-loaded`, `full` and `yes`. Casa's own wording is "fully
    loaded" - the token is deliberately not a quote of it."""
    for ok in ("bare", "as-tested", "fully-configured", "unstated"):
        assert _envelope(ok) == [], ok
    for drift in ("fully-loaded", "full", "yes", "Fully-Configured"):
        assert _envelope(drift), drift


def test_unstated_is_a_value_and_not_the_absence_of_one():
    """`unstated` means somebody read the datasheet and it is silent, which is a
    finding. An absent key means nobody looked. Collapsing the two would lose
    the distinction `lifecycle.eol: none-announced` exists to draw."""
    assert _envelope("unstated") == []
    import json

    from jsonschema import Draft202012Validator
    schema = json.loads((SPEC / "schemas/device.schema.json").read_text())
    dev = {"format": 1, "kind": "device", "name": "chassis", "version": "0.1.0",
           "attrs": {"power": {"power-max-w": "4000"}},
           "views": {"front": {"size": {"w": 440.0, "h": 44.0}}}}
    assert [e.message for e in Draft202012Validator(schema).iter_errors(dev)
            if "power-envelope" in list(e.path) or "power-envelope" in e.message] == []


def _gap_reason(value):
    """A minimal device carrying one declared gap, against the schema."""
    import json

    from jsonschema import Draft202012Validator
    schema = json.loads((SPEC / "schemas/device.schema.json").read_text())
    dev = {"format": 1, "kind": "device", "name": "chassis", "version": "0.1.0",
           "views": {"front": {"size": {"w": 440.0, "h": 44.0}}},
           "gaps": [{"what": "fan-power-sources", "reason": value,
                     "wanted": "a measurement from a running chassis"}]}
    return [e.message for e in Draft202012Validator(schema).iter_errors(dev)
            if "reason" in list(e.path) or "is not one of" in e.message]


def test_two_sources_disagreeing_has_its_own_reason():
    """`vendor-silent` means no document describes it. Two documents describing
    it differently is the opposite, and filing it as vendor-silent would be a
    false statement about the sources. The C100G guide gives its fan assemblies
    100 W each in prose and 330 W for the three of them in Table A-2; the AGR400
    datasheet says 527 W max where its own QSG says 638 W. Four such cases
    across three vendors is why this is a token and not a provenance sentence."""
    assert _gap_reason("sources-disagree") == []


def test_the_reason_vocabulary_is_still_closed():
    """It decides who can close the gap, so it cannot become free text - a
    reason nobody can act on is a note, and notes were what the register
    replaced."""
    for drift in ("sources-conflict", "disputed", "conflict", "unknown"):
        assert _gap_reason(drift), drift


def test_the_register_carries_the_rule(tmp_path):
    """L29 is in RULE_GAPS, which is the only reason any of this reaches
    `gaps.json`: `derived_gaps` runs the DEVICE rules, so a component-scoped
    warning never gets there - L26 does not."""
    import capability
    assert "L29" in capability.RULE_GAPS
    what, wanted = capability.RULE_GAPS["L29"]
    assert what == "module-power"
    assert "power-draw-max-w" in wanted


# ---------------------------------------------------------------- L30


def test_a_pairing_counted_from_both_ends_is_reported(tmp_path):
    """The defect: a front card whose figure already contains its rear partner,
    beside a rear partner that states its own. `sum()` over populated bays then
    counts the pairing twice - a plausible over-count, not an error."""
    plant(tmp_path, "acme/dqm@1", attrs={"power-draw-max-w": 320.0,
                                         "power-draw-scope": "module-with-paired-io"})
    plant(tmp_path, "acme/rf-io@1", attrs={"power-draw-max-w": 30.0})
    dev = plant_paired_device(tmp_path, "chassis", ["acme/dqm@1"], ["acme/rf-io@1"])
    ws = double_count(dev, tmp_path)
    assert len(ws) == 1
    assert "acme/rf-io@1" in ws[0] and "acme/dqm@1" in ws[0]
    assert "counts the pairing twice" in ws[0]


def test_the_message_offers_both_repairs_not_one(tmp_path):
    """Either the front scope is wrong or the rear figure is for something the
    front does not cover. The rule cannot tell which, so it must not accuse
    one side - that is the recalibration L14 and L21 both needed."""
    plant(tmp_path, "acme/dqm@1", attrs={"power-draw-max-w": 320.0,
                                         "power-draw-scope": "module-with-paired-io"})
    plant(tmp_path, "acme/rf-io@1", attrs={"power-draw-max-w": 30.0})
    dev = plant_paired_device(tmp_path, "chassis", ["acme/dqm@1"], ["acme/rf-io@1"])
    msg = double_count(dev, tmp_path)[0]
    assert "scope is wrong" in msg and "does not cover" in msg


def test_a_scoped_card_with_no_rear_figure_is_silent(tmp_path):
    """The library today: every DQM and BDM is scoped to the pair and no rear
    I/O module has a figure yet. Nothing is being double-counted, so nothing is
    reported - the rule fires the moment casa-rear-io lands one."""
    plant(tmp_path, "acme/dqm@1", attrs={"power-draw-max-w": 320.0,
                                         "power-draw-scope": "module-with-paired-io"})
    plant(tmp_path, "acme/rf-io@1")
    dev = plant_paired_device(tmp_path, "chassis", ["acme/dqm@1"], ["acme/rf-io@1"])
    assert double_count(dev, tmp_path) == []


def test_two_bare_cards_are_not_a_double_count(tmp_path):
    """Absent scope means `module`, so a front and a rear card that each state
    their own draw are two independent terms and summing both is correct. This
    is every other chassis in the library and the rule must stay off it."""
    plant(tmp_path, "acme/front@1", attrs={"power-draw-max-w": 320.0})
    plant(tmp_path, "acme/rear@1", attrs={"power-draw-max-w": 30.0})
    dev = plant_paired_device(tmp_path, "chassis", ["acme/front@1"], ["acme/rear@1"])
    assert double_count(dev, tmp_path) == []


def test_a_rear_fan_or_psu_cannot_trip_it(tmp_path):
    """The C100G's rear face carries the fans and the PEMs beside the I/O cards,
    and `casa/fan` states 100 W. A card's figure was never going to include a
    fan, so restricting both sides to `line-card` is what keeps this rule from
    crying wolf on the one device it was written for."""
    plant(tmp_path, "acme/dqm@1", attrs={"power-draw-max-w": 320.0,
                                         "power-draw-scope": "module-with-paired-io"})
    plant(tmp_path, "acme/fan@1", cls="fan", attrs={"power-draw-max-w": 100.0})
    plant(tmp_path, "acme/psu@1", cls="psu", attrs={"power-output-w": 650.0})
    dev = plant_paired_device(tmp_path, "chassis", ["acme/dqm@1"],
                              ["acme/fan@1", "acme/psu@1"])
    assert double_count(dev, tmp_path) == []


def test_a_partner_on_the_same_face_is_not_a_pairing(tmp_path):
    """A pairing spans two faces by definition - the rear module is what the
    front card's figure absorbed. Two scoped cards sharing one face say nothing
    about each other."""
    plant(tmp_path, "acme/dqm@1", attrs={"power-draw-max-w": 320.0,
                                         "power-draw-scope": "module-with-paired-io"})
    plant(tmp_path, "acme/other@1", attrs={"power-draw-max-w": 250.0})
    dev = plant_paired_device(tmp_path, "chassis",
                              ["acme/dqm@1", "acme/other@1"], [])
    assert double_count(dev, tmp_path) == []


def test_the_scope_vocabulary_is_closed_and_defaults_to_module(tmp_path):
    """Absent means `module`, which is what makes this key free to add: every
    figure written before it existed keeps meaning exactly what it meant."""
    import json

    from jsonschema import Draft202012Validator
    schema = json.loads((SPEC / "schemas/component.schema.json").read_text())
    v = Draft202012Validator(schema)

    def errs(attrs):
        c = {"format": 1, "kind": "component", "name": "card", "version": "1.0.0",
             "class": "line-card", "size": {"w": 40.0, "h": 20.0}, "attrs": attrs}
        return [e.message for e in v.iter_errors(c)]

    assert errs({"power-draw-max-w": 320.0}) == []
    assert errs({"power-draw-scope": "module"}) == []
    assert errs({"power-draw-scope": "module-with-paired-io"}) == []
    for drift in ("with-io", "pair", "module+io", "Module"):
        assert errs({"power-draw-scope": drift}), drift
