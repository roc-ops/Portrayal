"""L144, L145 and L19 on a bay: the structural rules a sweep of the manifests
found broken with no model and no prose to read (#414).

L144 - members of one group that one build draws on one face hold one position
each. L145 - a port group is named for its family, not `ports`. L19 - a bay in
an `indicator` group says what it indicates, as a lamp placement does.
"""
from pathlib import Path

import yaml

from portrayal import lint

LIB = Path(__file__).resolve().parents[2] / "library"


class _NoSchema:
    def iter_errors(self, _data):
        return iter(())


def _rel_pos(doc):
    with lint.collecting() as got:
        lint.lint_device_rel_pos("device.yaml", doc)
    return [w for w in got.warnings if "[L144]" in w]


def _names(doc):
    with lint.collecting() as got:
        lint.lint_device_group_names("device.yaml", doc)
    return [w for w in got.warnings if "[L145]" in w]


def _face(*items, bays=()):
    return {"components": {"placements": list(items), "bays": list(bays)}}


def _jack(i, pos, group="grounding", **extra):
    return {"id": i, "ref": "common/esd-jack@1", "at": [0, 0],
            "group": group, "rel-pos": pos, **extra}


def test_L148_two_members_at_one_position_on_one_face():
    doc = {"views": {"rear": _face(_jack("esd-rear-jack", 0), _jack("ground-stud-0", 0),
                                   _jack("ground-stud-1", 1))}}
    found = _rel_pos(doc)
    assert len(found) == 1
    assert "rear: group 'grounding'" in found[0] and "esd-rear-jack, ground-stud-0" in found[0]


def test_L148_quiet_when_every_member_has_its_own_position():
    doc = {"views": {"rear": _face(_jack("ground-stud-0", 0), _jack("ground-stud-1", 1)),
                     "front": _face(_jack("esd-front-jack", 0, group="esd"))}}
    assert _rel_pos(doc) == []


def test_L148_quiet_for_the_same_position_on_another_face():
    # front and rear ears that each count from 1 read unambiguously with their face
    doc = {"views": {"front": _face(_jack("ear-left", 1, group="furniture")),
                     "rear": _face(_jack("rear-ear-left", 1, group="furniture"))}}
    assert _rel_pos(doc) == []


def test_L148_quiet_for_alternatives_only_in_scopes_apart():
    # one riser position, built two ways - never drawn together
    bays = [{"id": "riser-2", "group": "risers", "rel-pos": 2, "only-in": ["a"]},
            {"id": "riser-2-lp", "group": "risers", "rel-pos": 2, "only-in": ["b"]}]
    doc = {"configurations": {"a": {}, "b": {}}, "views": {"rear": _face(bays=bays)}}
    assert _rel_pos(doc) == []
    bays[1]["only-in"] = ["a", "b"]                  # now build a draws both
    assert len(_rel_pos(doc)) == 1


def test_L148_quiet_for_variant_views_of_one_face():
    doc = {"configurations": {"a": {"views": {"front": "front-a"}},
                              "b": {"views": {"front": "front-b"}}},
           "views": {"front-a": {"face": "front", **_face(_jack("panel", 1, group="panels"))},
                     "front-b": {"face": "front", **_face(_jack("panel", 1, group="panels"))}}}
    assert _rel_pos(doc) == []


def test_L148_counts_each_clash_once_across_builds():
    doc = {"configurations": {"a": {}, "b": {}},
           "views": {"front": _face(*[_jack(f"led-port-48-{n}", 48, group="port-leds")
                                      for n in (1, 2, 3, 4)],
                                    *[_jack(f"led-port-49-{n}", 49, group="port-leds")
                                      for n in (1, 2)])}}
    found = _rel_pos(doc)
    assert len(found) == 1 and "4 members position 48" in found[0] and "1 more" in found[0]


def test_L149_ports_names_no_family():
    assert len(_names({"groups": {"ports": {"term": "Port"}}})) == 1
    assert _names({"groups": {"sfp28": {}, "front-io": {}, "leds": {}}}) == []


def test_L19_a_bay_in_an_indicator_group_declares_for(tmp_path):
    doc = {"groups": {"craft": {"term": "Panel", "role": "indicator", "index-origin": 0}},
           "views": {"front": {"size": {"w": 100, "h": 50}, "components": {"bays": [
               {"id": "craft", "at": [0, 0], "size": {"w": 100, "h": 20},
                "accepts": ["juniper/mx960-craft@2"], "default": "juniper/mx960-craft@2",
                "group": "craft", "rel-pos": 0}]}}}}
    path = tmp_path / "device.yaml"

    def l19():
        path.write_text(yaml.safe_dump(doc))
        with lint.collecting() as got:
            lint.lint_device(path, _NoSchema(), [str(LIB)])
        return [w for w in got.warnings if "[L19]" in w and "craft" in w]

    assert len(l19()) == 1
    doc["views"]["front"]["components"]["bays"][0]["for"] = "chassis"
    assert l19() == []
    doc["groups"]["craft"]["role"] = "management"    # a bay nobody reads is not asked
    del doc["views"]["front"]["components"]["bays"][0]["for"]
    assert l19() == []
