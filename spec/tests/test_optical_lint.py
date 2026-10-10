"""The optical rules fire on their defect and stay quiet on the real thing.

Each rule gets both halves. A rule that only ever fires is as useless as one
that never does, and the quiet half is the one that breaks silently when a
predicate is tightened - which is how a fixture that could not tell `!seen` from
`!seen && named` shipped in this repo before.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import lint as L

LIB = [str(ROOT / "library")]


def run(rule, doc, code=None, path="t/contract.yaml"):
    """Call ONE rule and return ONLY its errors.

    Every optical rule takes `(path, data, lib_roots)` - the ones that do not
    need the roots accept and ignore them - so one call shape serves all three.

    Filtering on a substring like "L8" would also catch L80 while testing L81,
    and would quietly pass if a rule started raising under the wrong code, so
    `code` narrows to one rule when a test cares which fired.
    """
    with L.collecting() as _found:
        rule(path, doc, LIB)
    return [e for e in _found.errors
            if code is None or f"[{code}]" in e]


def module(paths, parts=None, unused=None):
    """A module composing two LC duplex adapters, which hold 2 positions each."""
    doc = {"kind": "module", "size": {"w": 55.4, "h": 19.5},
           "parts": parts if parts is not None else [
               {"ref": "common/lc-duplex-adapter@6", "id": "common"},
               {"ref": "common/lc-duplex-adapter@6", "id": "split"}],
           "optical": {"media": "os2", "paths": paths}}
    if unused:
        doc["optical"]["unused"] = unused
    return doc


def test_a_position_past_the_connectors_capacity_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.3", "to": "split.1"}]))
    assert len(hits) == 1, hits
    assert "common.3" in hits[0] and "2" in hits[0]


def test_an_endpoint_naming_no_composed_part_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "mtp-1.1", "to": "split.1"}]))
    assert len(hits) == 1 and "mtp-1" in hits[0], hits


def test_a_path_within_capacity_is_silent():
    assert run(L.lint_component_optical_endpoints,
               module([{"from": "common.1", "to": "split.2"}])) == []


def test_a_split_destination_is_checked_like_any_other_endpoint():
    """The ratio form must not be a hole the checker walks past."""
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.9", "ratio": 50}]}]))
    assert len(hits) == 1 and "split.9" in hits[0], hits


def test_a_malformed_endpoint_gets_its_own_message_not_the_unknown_part_one():
    """Pins the `except ValueError` branch, which the other tests never reach.

    `lint_component()` reports only the FIRST schema error and still returns
    the data, so a contract that fails schema validation somewhere else still
    flows into this rule carrying an endpoint string `optical.ENDPOINT` would
    have rejected. Without a test that exercises `split_endpoint` raising,
    that branch and its distinct "is not an optical endpoint" message could be
    deleted and this suite would stay green - the other tests only ever reach
    the "names {part!r}" and "asks for position" messages, both of which
    require `split_endpoint` to have already succeeded.
    """
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "bad", "to": "split.1"}]))
    assert len(hits) == 1, hits
    assert "is not an optical endpoint" in hits[0], hits


def test_two_paths_landing_on_one_position_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.1"}]))
    assert len(hits) == 1 and "split.1" in hits[0], hits


def test_one_source_feeding_two_destinations_is_NOT_a_conflict():
    """That is a split, which is the whole point of the graph form - as long as
    it is written as ONE path with a ratio list, which is the form the ratio
    check can actually see."""
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.2", "ratio": 50}]}])) == []


def test_the_same_source_in_two_plain_paths_is_caught():
    """A split written the long way hides its ratios from the check above.

    `{from: common.1, to: split.1}` and `{from: common.1, to: split.2}` each
    yield zero ratios via `endpoints()`, so the sum-to-100 check never runs -
    a 70/30 tap written this way carries no ratios anywhere the linter can see.
    A source is allowed to be a `from` in at most one path; a genuine split
    must use the ratio list, which is the one form L79 can verify.
    """
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.1", "to": "split.2"}]))
    assert len(hits) == 1 and "common.1" in hits[0], hits


def test_ratios_that_do_not_sum_to_100_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 70},
                               {"at": "split.2", "ratio": 40}]}]))
    assert len(hits) == 1 and "110" in hits[0], hits


def test_a_97_3_split_sums_and_is_silent():
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}])) == []


def test_a_position_no_path_reaches_and_no_entry_declares_is_caught():
    """ppm-ocu-97-3's dead bore, which is currently a sentence in provenance."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}]))
    assert len(hits) == 1 and "common.2" in hits[0], hits


def test_declaring_it_unused_silences_it():
    assert run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}],
                      unused={"common.2": "three-port coupler in a four-bore "
                                          "faceplate"})) == []


def test_declaring_a_position_unused_that_a_path_DOES_reach_is_caught():
    """The rule has to bite both ways or `unused` becomes a way to silence it."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.2"}],
                      unused={"common.2": "this claim contradicts path 1 above"}))
    assert len(hits) == 1 and "common.2" in hits[0], hits


def test_an_unused_key_naming_no_real_position_is_caught():
    """`unused: {ghost.7: "..."}` or `common.9` on a two-bore adapter validates
    against the schema - `propertyNames` only checks the string shape - and
    the per-position loop above only ever walks real positions, so a bogus key
    was previously checked by nothing at all. An uncheckable claim is a defect
    here the same as a missing one.
    """
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.2"}],
                      unused={"ghost.7": "does not exist"}))
    assert len(hits) == 1 and "ghost.7" in hits[0], hits


def test_a_component_with_no_paths_at_all_is_not_checked_by_L80():
    """This is the rule's deliberate blind spot, not a bug.

    L80 only asks its question of a part that has opted in by declaring
    `optical.paths`. A component that composes connectors (here, two LC
    duplex adapters worth four positions) but declares zero paths returns
    before the coverage walk ever runs - every position of every composed
    connector escapes "reached or declared unused" unchecked. Running the
    rule on every component that merely composes a connector would error on
    every part in the library with an LC adapter and no optical model, which
    today is all of them, so it stays a guard rather than a check. Nothing
    else in this file catches this gap either.
    """
    assert run(L.lint_component_optical_coverage, module([])) == []


# --- the trunk: L78's trunk half, L79's band exception, L129, L130, L131 ------

def three(paths, trunk=None):
    """An add/drop filter's face: OSC, EDFA and Line duplex adapters."""
    doc = module(paths, parts=[{"ref": "common/lc-duplex-adapter@6", "id": i}
                               for i in ("osc", "edfa", "line")])
    if trunk is not None:
        doc["optical"]["trunk"] = trunk
    return doc


BAND = {"centre-nm": 1511, "width-nm": 13}


def test_banded_paths_off_one_source_are_an_add_drop_filter_not_a_hidden_split():
    doc = three([{"from": "line.2", "to": "osc.1", "band": BAND},
                 {"from": "line.2", "to": "edfa.1"}])
    assert run(L.lint_component_optical_conflicts, doc, "L79") == []


def test_two_unbanded_paths_off_one_source_are_still_a_hidden_split():
    doc = three([{"from": "line.2", "to": "osc.1"},
                 {"from": "line.2", "to": "edfa.1"}])
    assert len(run(L.lint_component_optical_conflicts, doc, "L79")) == 1


def test_two_paths_on_one_band_off_one_source_are_still_a_hidden_split():
    """A band names a wavelength; two legs on the same one divide its power,
    which is the ratio this rule exists to see."""
    doc = three([{"from": "line.2", "to": "osc.1", "band": BAND},
                 {"from": "line.2", "to": "edfa.1", "band": dict(BAND)}])
    assert len(run(L.lint_component_optical_conflicts, doc, "L79")) == 1


def test_two_different_bands_off_one_source_are_an_add_drop_filter():
    doc = three([{"from": "line.2", "to": "osc.1", "band": BAND},
                 {"from": "line.2", "to": "edfa.1", "band": {"centre-nm": 1635, "width-nm": 70}}])
    assert run(L.lint_component_optical_conflicts, doc, "L79") == []


def test_a_path_with_no_trunk_is_l131():
    doc = module([{"from": "common.1", "to": "split.1"}])
    hits = run(L.lint_component_optical_trunk, doc, "L131")
    assert len(hits) == 1 and "no trunk" in hits[0], hits


def test_a_stated_trunk_satisfies_l131_and_l130():
    doc = module([{"from": "common.1", "to": "split.1"}],
                 unused={"common.2": "x" * 30, "split.2": "x" * 30})
    doc["optical"]["trunk"] = ["common"]
    assert run(L.lint_component_optical_trunk, doc) == []


def test_a_front_to_front_leg_on_a_projected_module_is_l130():
    doc = three([{"from": "line.2", "to": "osc.1"}, {"from": "osc.2", "to": "edfa.1"}],
                trunk=["line"])
    hits = run(L.lint_component_optical_trunk, doc, "L130")
    assert len(hits) == 1 and "osc.2 -> edfa.1" in hits[0], hits


def test_a_trunk_to_trunk_leg_is_l130():
    doc = three([{"from": "line.2", "to": "line.1"}], trunk=["line"])
    assert len(run(L.lint_component_optical_trunk, doc, "L130")) == 1


def test_a_trunk_beside_a_fibre_rear_face_is_l129():
    """The real cassette has a rear MTP; a trunk there is a second answer."""
    import yaml
    f = ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v4/contract.yaml"
    doc = yaml.safe_load(f.read_text())
    assert run(L.lint_component_optical_trunk, doc) == []
    doc["optical"]["trunk"] = ["lc1"]
    hits = run(L.lint_component_optical_trunk, doc, "L129")
    assert len(hits) == 1 and "rear face" in hits[0], hits


def test_a_trunk_position_declared_unused_is_l129_but_a_bare_part_may_hold_one():
    doc = module([{"from": "common.1", "to": "split.1"}],
                 unused={"common.2": "x" * 30, "split.2": "x" * 30})
    doc["optical"]["trunk"] = ["common.2"]
    hits = run(L.lint_component_optical_trunk, doc, "L129")
    assert len(hits) == 1 and "common.2" in hits[0], hits
    doc["optical"]["trunk"] = ["common"]
    assert run(L.lint_component_optical_trunk, doc, "L129") == []


def test_one_position_of_a_front_mpo_as_the_trunk_is_l129():
    """#857: the export shrinks an MPO front port to the positions the trunk
    leaves, and the fibre map keeps the leg's original front_position, so
    `trunk: [mpo.1]` wrote an 11-position port with a leg at position 12."""
    doc = module([{"from": f"mpo.{i}", "to": "mpo.1"} for i in range(2, 13)],
                 parts=[{"ref": "common/mpo-adapter@2", "id": "mpo"}])
    doc["optical"]["trunk"] = ["mpo.1"]
    hits = run(L.lint_component_optical_trunk, doc, "L129")
    assert len(hits) == 1 and "mpo.1" in hits[0] and "front connector" in hits[0], hits
    # the whole connector is a trunk the export can write
    doc["optical"]["trunk"] = ["mpo"]
    assert run(L.lint_component_optical_trunk, doc, "L129") == []
    # and one position of a duplex adapter - the PPMs' shape - is still fine
    duplex = module([{"from": "common.1", "to": "split.1"}])
    duplex["optical"]["trunk"] = ["common.1"]
    assert run(L.lint_component_optical_trunk, duplex, "L129") == []


def test_a_trunk_naming_no_connector_or_no_position_is_l78():
    doc = module([{"from": "common.1", "to": "split.1"}])
    doc["optical"]["trunk"] = ["ghost", "common.3"]
    hits = run(L.lint_component_optical_endpoints, doc, "L78")
    assert len(hits) == 2, hits
    assert any("ghost" in h for h in hits) and any("common.3" in h for h in hits)


def test_every_path_bearing_ppm_states_its_trunk_and_lints_clean():
    """The eight retrofitted PPMs, quiet on every trunk rule."""
    import yaml
    names = ["ppm-ad1-1510", "ppm-ad1-1625", "ppm-ocu-50-50", "ppm-ocu-97-3",
             "ppm-dcm-10", "ppm-dcm-20", "ppm-dcm-40", "ppm-dcm-80"]
    for n in names:
        f = ROOT / f"library/components/smartoptics/{n}/v2/contract.yaml"
        doc = yaml.safe_load(f.read_text())
        assert doc["optical"].get("trunk"), n
        for rule in (L.lint_component_optical_trunk, L.lint_component_optical_endpoints,
                     L.lint_component_optical_conflicts, L.lint_component_optical_coverage,
                     L.lint_component_optical_combine):
            assert run(rule, doc) == [], (n, rule.__name__)


# --- combine: L171, and what L78, L79, L80 and L130 make of one ---------------

def add_drop(combine, to="line.1", **extra):
    """The add side of a filter on `three`'s face, trunk on Line."""
    path = {"combine": combine, "to": to}
    path.update(extra)
    return three([{"from": "line.2", "to": "osc.1", "band": BAND},
                  {"from": "line.2", "to": "edfa.1"},
                  path], trunk=["line"])


GOOD = [{"at": "osc.2", "band": BAND}, {"at": "edfa.2"}]

OPTICAL_RULES = ("lint_component_optical_endpoints", "lint_component_optical_conflicts",
                 "lint_component_optical_coverage", "lint_component_optical_trunk",
                 "lint_component_optical_combine")


def test_a_wavelength_combine_is_quiet_on_every_optical_rule():
    """The real shape: two inputs onto Line Tx, one banded, one carrying the
    rest. Every position of the three adapters is reached, so L80 is in it."""
    doc = add_drop(GOOD)
    for name in OPTICAL_RULES:
        assert run(getattr(L, name), doc) == [], name


def test_a_power_combine_with_ratios_summing_to_100_is_quiet():
    doc = add_drop([{"at": "osc.2", "ratio": 50}, {"at": "edfa.2", "ratio": 50}])
    assert run(L.lint_component_optical_combine, doc) == []
    assert run(L.lint_component_optical_conflicts, doc) == []


def test_two_plain_paths_into_one_position_are_still_a_collision():
    """The undeclared spelling of the same glass. `combine` is an escape hatch
    only for the path that states it."""
    doc = three([{"from": "osc.2", "to": "line.1"},
                 {"from": "edfa.2", "to": "line.1"}], trunk=["line"])
    hits = run(L.lint_component_optical_conflicts, doc, "L79")
    assert len(hits) == 1 and "line.1" in hits[0] and "combine" in hits[0], hits


def test_a_second_path_into_a_combines_destination_is_a_collision():
    doc = add_drop(GOOD)
    doc["optical"]["paths"].append({"from": "osc.1", "to": "line.1"})
    hits = run(L.lint_component_optical_conflicts, doc, "L79")
    assert any("line.1 is the destination of two paths" in h for h in hits), hits


def test_a_combine_source_that_starts_another_path_is_caught():
    doc = add_drop(GOOD)
    doc["optical"]["paths"].append({"from": "osc.2", "to": "edfa.1"})
    hits = run(L.lint_component_optical_conflicts, doc, "L79")
    assert any("osc.2 is the source of two paths" in h for h in hits), hits


def test_a_combine_source_past_the_connectors_capacity_is_l78():
    """The combine list must not be a hole the endpoint check walks past."""
    doc = add_drop([{"at": "osc.9", "band": BAND}, {"at": "edfa.2"}])
    hits = run(L.lint_component_optical_endpoints, doc, "L78")
    assert len(hits) == 1 and "osc.9" in hits[0], hits


def test_a_position_only_a_combine_reaches_is_not_unreached():
    """L80 reads a combine's sources as reached - drop the combine and the
    three positions it wires are reported."""
    doc = add_drop(GOOD)
    assert run(L.lint_component_optical_coverage, doc, "L80") == []
    doc["optical"]["paths"].pop()
    hits = run(L.lint_component_optical_coverage, doc, "L80")
    assert {h.split("] ")[1].split(" ")[0] for h in hits} == {"osc.2", "edfa.2", "line.1"}, hits


def test_a_combine_leg_that_stays_on_the_front_is_l130():
    """A role that contradicts the path set: the destination is a branch, so
    no leg crosses to the trunk and none has a row in the fibre map."""
    doc = add_drop([{"at": "osc.2", "band": BAND}, {"at": "line.1"}], to="edfa.2")
    hits = run(L.lint_component_optical_trunk, doc, "L130")
    assert len(hits) == 1 and "osc.2 -> edfa.2" in hits[0], hits


def test_a_combine_with_no_trunk_is_l131():
    doc = add_drop(GOOD)
    del doc["optical"]["trunk"]
    assert len(run(L.lint_component_optical_trunk, doc, "L131")) == 1


def test_two_unbanded_combine_sources_do_not_say_how_they_join():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2"}, {"at": "edfa.2"}]), "L171")
    assert len(hits) == 1 and "neither" in hits[0], hits


def test_two_combine_sources_on_one_band_are_caught():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2", "band": BAND},
                         {"at": "edfa.2", "band": dict(BAND)}]), "L171")
    assert len(hits) == 1 and "same" in hits[0], hits


def test_combine_ratios_must_sum_to_100():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2", "ratio": 70}, {"at": "edfa.2", "ratio": 40}]),
               "L171")
    assert len(hits) == 1 and "110" in hits[0], hits


def test_a_power_combine_states_every_share():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2", "ratio": 50}, {"at": "edfa.2"}]), "L171")
    assert len(hits) == 1 and "1 of its 2" in hits[0], hits


def test_a_combine_does_not_mix_ratio_and_band():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2", "band": BAND},
                         {"at": "edfa.2", "ratio": 100}]), "L171")
    assert len(hits) == 1 and "mixes" in hits[0], hits


def test_a_combine_has_one_destination():
    doc = add_drop(GOOD, to=[{"at": "line.1", "ratio": 50}, {"at": "line.2", "ratio": 50}])
    doc["optical"]["paths"] = doc["optical"]["paths"][2:]
    hits = run(L.lint_component_optical_combine, doc, "L171")
    assert len(hits) == 1 and "one destination" in hits[0], hits
    # and no other optical rule falls over on the shape
    for name in OPTICAL_RULES:
        run(getattr(L, name), doc)


def test_a_combine_carries_no_path_level_band():
    hits = run(L.lint_component_optical_combine, add_drop(GOOD, band=BAND), "L171")
    assert len(hits) == 1 and "path-level" in hits[0], hits


def test_a_combine_names_a_source_once():
    hits = run(L.lint_component_optical_combine,
               add_drop([{"at": "osc.2", "band": BAND}, {"at": "osc.2"}]), "L171")
    assert len(hits) == 1 and "twice" in hits[0], hits


def test_from_beside_combine_is_caught():
    doc = add_drop(GOOD)
    doc["optical"]["paths"][2]["from"] = "osc.1"
    hits = run(L.lint_component_optical_combine, doc, "L171")
    assert len(hits) == 1 and "both" in hits[0], hits


def test_the_schema_takes_a_combine_and_refuses_the_malformed_ones():
    import json
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    paths = dict(schema["properties"]["optical"]["properties"]["paths"])
    paths["$defs"] = schema["$defs"]
    v = Draft202012Validator(paths)
    ok = lambda p: not list(v.iter_errors([p]))
    assert ok({"combine": GOOD, "to": "line.1"})
    assert ok({"from": "line.2", "to": "osc.1", "band": BAND})          # unchanged
    assert ok({"from": "a.1", "to": [{"at": "b.1", "ratio": 50}, {"at": "b.2", "ratio": 50}]})
    assert not ok({"combine": GOOD, "from": "osc.1", "to": "line.1"})   # both
    assert not ok({"to": "line.1"})                                     # neither
    assert not ok({"combine": [{"at": "osc.2"}], "to": "line.1"})       # one source
    assert not ok({"combine": ["osc.2", "edfa.2"], "to": "line.1"})     # bare strings
    assert not ok({"combine": [{"at": "osc.2", "share": 1}, {"at": "edfa.2"}], "to": "line.1"})


def test_both_add_drop_filters_state_their_add_direction_as_a_combine():
    """The two parts that used to write a combine from the wrong end. Read
    from the parsed contract, so a folded string cannot hide it."""
    import yaml
    for n, branches in (("ppm-ad1-1510", {"osc.2", "edfa.2"}),
                        ("ppm-ad1-1625", {"otdr.2", "ext.2"})):
        doc = yaml.safe_load((ROOT / f"library/components/smartoptics/{n}/v2/"
                              "contract.yaml").read_text())
        combines = [p for p in doc["optical"]["paths"] if "combine" in p]
        assert len(combines) == 1, n
        assert combines[0]["to"] == "line.1", n
        assert {s["at"] for s in combines[0]["combine"]} == branches, n
        assert sum(1 for s in combines[0]["combine"] if s.get("band")) == 1, n
        assert run(L.lint_component_optical_combine, doc) == [], n


def _drop_reusing_a_combine_source(combine_first):
    """Banded drop legs off `line.2`, and a combine that also names `line.2`
    as a source. L79's band exception would pass the drop legs on their own."""
    drop = [{"from": "line.2", "to": "osc.1", "band": BAND},
            {"from": "line.2", "to": "edfa.1"}]
    join = [{"combine": [{"at": "line.2", "band": {"centre-nm": 1625}}, {"at": "osc.2"}],
             "to": "edfa.2"}]
    return three(join + drop if combine_first else drop + join, trunk=["line"])


def test_banded_legs_do_not_excuse_reusing_a_combine_source_written_after_them():
    hits = run(L.lint_component_optical_conflicts,
               _drop_reusing_a_combine_source(combine_first=False), "L79")
    assert hits and all("line.2 is the source of two paths" in h for h in hits), hits


def test_banded_legs_do_not_excuse_reusing_a_combine_source_written_before_them():
    """The same glass with the combine first. The finding must not depend on
    the order the paths are written in."""
    hits = run(L.lint_component_optical_conflicts,
               _drop_reusing_a_combine_source(combine_first=True), "L79")
    assert hits and all("line.2 is the source of two paths" in h for h in hits), hits


def test_l171_is_reachable_from_a_real_lint_run(tmp_path):
    """The rule fires from the command line, not only when a test calls it:
    a rule left out of the per-component loop is dead code with green tests."""
    import subprocess
    d = tmp_path / "components" / "t" / "joiner" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: module\nname: joiner\nversion: 1.0.0\n"
        "class: filter\nsize: {w: 40, h: 20}\n"
        "optical:\n  media: os2\n  trunk: [b]\n  paths:\n"
        "    - combine: [{at: a.1}, {at: a.2}]\n      to: b.1\n")
    out = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/lint.py"),
         "--schemas", str(ROOT / "spec/schemas"), "--library", str(tmp_path)],
        capture_output=True, text=True).stdout
    assert "[L171]" in out and "neither" in out, out
