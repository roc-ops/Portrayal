"""`attrs` is sectioned, and the sections have to be load-bearing to be worth it.

The bag was 74 distinct spellings across 13 devices with four names for the
maximum power draw, and `profiles.yaml` had grown an alias list per fact to cope
with it. Sectioning is only an improvement if the predicate it enables is a
better predicate and if the tail it creates stays visible - so those are what
these test, not the shape of the YAML.
"""
import functools
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import attrsections  # noqa: E402
import capability  # noqa: E402
import lint  # noqa: E402

PROFILES = capability.load_profiles(SPEC / "schemas")
MANIFESTS = sorted(LIB.glob("devices/*/*/device.yaml"))


@functools.lru_cache(maxsize=None)
def load(rel):
    return yaml.safe_load((LIB / "devices" / rel / "device.yaml").read_text())


def rules(path, data):
    """Run just the attrs rules over one manifest and hand back what they said."""
    saved_e, saved_w = lint.ERRORS[:], lint.WARNINGS[:]
    lint.ERRORS.clear()
    lint.WARNINGS.clear()
    try:
        lint.lint_device_attrs(path, data)
        return lint.ERRORS[:], lint.WARNINGS[:]
    finally:
        lint.ERRORS[:] = saved_e
        lint.WARNINGS[:] = saved_w


def test_every_attr_is_in_a_section():
    """`additionalProperties: false` on the schema says this too, but it says it
    as a validation error at the bottom of a build. A key sitting loose at the
    top of `attrs` is the old bag coming back, and it should be named."""
    for man in MANIFESTS:
        d = yaml.safe_load(man.read_text())
        assert not attrsections.unsectioned(d.get("attrs")), man


def test_one_key_belongs_to_one_section():
    """`attrs` flattens onto the SVG root as `data-<key>` and an attribute list
    has no nesting to disambiguate two claims on one name, so the second would
    silently overwrite the first. Silently is the problem: the drawing still
    compiles, still validates, and only a diff of two builds shows the loss."""
    for man in MANIFESTS:
        d = yaml.safe_load(man.read_text())
        assert not attrsections.collisions(d.get("attrs")), man

    clash = {"attrs": {"power": {"fans": "2+1"}, "thermal": {"fans": "5+1"}}}
    errs, _ = rules(Path("x"), clash)
    assert len(errs) == 1 and "L25" in errs[0] and "'fans'" in errs[0]


def test_temperature_is_environmental_because_thermal_is_the_machinery():
    """`thermal` holds fans, cooling-path, fan-trays, air-filter-location. An
    operating range belongs with humidity and altitude, which is `environmental`.

    The library had it both ways - all eight ASR 9000s under `environmental`,
    four other devices under `thermal` - and the requirement named the smaller
    half, so every ASR would have failed a thermal requirement while stating its
    range on the line above. Locked here so the move is not quietly reverted."""
    where = set()
    for man in MANIFESTS:
        attrs = (yaml.safe_load(man.read_text()) or {}).get("attrs") or {}
        for section, body in attrs.items():
            if isinstance(body, dict) and any("temp" in k for k in body):
                where.add(section)
    assert where <= {"environmental"}, where
    for name in ("networking", "optical"):
        req = [r for r in PROFILES[name]["requires"] if "operating-temp" in str(r)]
        assert [r["section"] for r in req] == ["environmental"]


def test_a_section_is_not_satisfied_by_the_machinery_inside_it():
    """The AS7726-32X is why the temperature requirement names its keys.

    Its thermal section holds `fans: 5+1 redundant, hot-swappable` and no
    operating range at all. "Has thermal data" is true of it and "states the
    temperature it runs at" is not, and the first reported it as fully specified
    - a weaker predicate than the one being replaced, which is the one outcome
    this whole exercise could not accept."""
    dev = load("edgecore/as7726-32x")
    assert dev["attrs"]["thermal"] == {"fans": "5+1 redundant, hot-swappable"}
    ok, needs, _ = capability._specified(dev, PROFILES)
    assert ok is False
    assert "operating-temp" in needs


def test_the_requirement_names_a_section_and_not_four_spellings():
    """The point of the exercise. `profiles.yaml` used to alias `power-max`,
    `power-ac-max-w`, `power-max-ac-w` and `power-max-dc-w` onto one fact, which
    made `specified` mean "has a key spelled one of four ways"."""
    reqs = PROFILES["networking"]["requires"]
    assert [r["section"] for r in reqs] == ["performance", "platform", "power",
                                            "environmental"]
    # bare section requirements exist and are the common case
    assert reqs[0] == {"section": "performance"}
    # and where a key still has to be named there is exactly one spelling of it
    assert reqs[1]["keys"] == ["cpu", "memory"]


def test_the_tail_is_counted_so_it_cannot_go_quiet(tmp_path):
    """`other` is a section, not an escape hatch, and the difference is that
    somebody counts it. 17 of the 22 keys that fit no section appeared on
    exactly one device, so the tail is real - what must not happen is it going
    quiet and becoming where anything difficult gets put."""
    # The fixture is BUILT, not borrowed. This test is about the COUNTING - that
    # `other` is reported rather than silently absorbing anything awkward - and
    # not about which manifest happens to carry an unclassified key today. Pinned
    # to the live c40g, it failed the moment that device's one tail key was
    # correctly removed, i.e. because a model got better. It has to be a real
    # file on disk because the rules are re-run from the path, not from the dict.
    dev = yaml.safe_load((LIB / "devices/casa/c40g/device.yaml").read_text())
    dev.setdefault("attrs", {})["other"] = {
        "redundancy": "3+1 with BDM (slot 1 protects, slot 4 active)"}
    man = tmp_path / "device.yaml"
    man.write_text(yaml.safe_dump(dev, sort_keys=False))
    dev = yaml.safe_load(man.read_text())
    assert list(dev["attrs"]["other"]) == ["redundancy"]

    _, warns = rules(man, dev)
    assert len(warns) == 1 and "L24" in warns[0] and "redundancy" in warns[0]

    cap, flags = capability.assess(dev, profiles=PROFILES)
    gaps = capability.derived_gaps(man, dev, [str(LIB)], cap, flags)
    tail = next(g for g in gaps if g["what"] == "attrs-unclassified")
    assert tail["count"] == 1 and tail["because"] == "L24"


def test_a_fact_the_structure_already_states_is_not_an_attr():
    """`rack: '13 RU'` sat beside `chassis.ru: 13`, and `form-factor: '1RU'`
    beside `chassis.ru: 1`, on four devices. Two sources for one fact, and the
    prose one is the one no tool can use. The structure already says it."""
    for man in MANIFESTS:
        d = yaml.safe_load(man.read_text())
        flat = attrsections.flatten(d.get("attrs"))
        assert not ({"rack", "form-factor", "ports", "slots", "role"} & set(flat)), man
        ru = (d.get("chassis") or {}).get("ru")
        if ru is not None:
            assert not any(f"{ru} RU" in str(v) or f"{ru}RU" in str(v)
                           for v in flat.values()), man


def test_the_section_is_a_classification_and_not_part_of_the_key():
    """Keys are globally unique and keep their own prefix, because every one of
    them leaves the manifest as `data-<key>` on an SVG root and is read there
    without its container. It is also what makes re-filing a key between
    sections free: no drawing and no export changes."""
    for man in MANIFESTS:
        d = yaml.safe_load(man.read_text())
        attrs = d.get("attrs") or {}
        flat = attrsections.flatten(attrs)
        assert len(flat) == sum(len(v) for v in attrs.values()), man
        assert not (set(flat) & set(attrsections.SECTIONS)), man


def test_wording_that_is_a_claim_about_a_product_survives_the_move():
    """"NEBS Level 3 (pre-test; certificate by request)" is a materially
    different claim from "NEBS Level 3". Shortening it while filing it under a
    section called `compliance` would turn a hedge into a certification."""
    dev = load("edgecore/as7946-74xksb")
    assert dev["attrs"]["compliance"]["nebs"] == \
        "NEBS Level 3 (pre-test; certificate by request)"


def test_eol_has_three_states_and_the_third_is_the_point():
    """Absent means nobody looked. `none-announced` means somebody searched and
    the vendor has announced nothing - a real finding, and one that has to stay
    distinguishable from nobody looking, or the register cannot tell an unknown
    from a known-empty."""
    assert "unchecked" not in attrsections.EOL_STATES
    schema = yaml.safe_load((SPEC / "schemas/device.schema.json").read_text())
    eol = schema["properties"]["attrs"]["properties"]["lifecycle"]["properties"]["eol"]
    assert eol["enum"] == list(attrsections.EOL_STATES)
