"""An optical path that reaches a part on another face of the same module.

A cassette's fibres run from six front LC adapters to one rear MTP. The MTP is a
part of the REAR FACE component, not of the cassette's own `parts:` - so an
endpoint has to be able to say which face it means. `rear:mtp.1` does;
unprefixed still means this face, which is why the nine PPMs and everything else
already written need no change.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def test_an_unqualified_endpoint_has_no_face():
    assert O.split_endpoint("lc1.2") == (None, "lc1", 2)


def test_a_qualified_endpoint_carries_its_face():
    assert O.split_endpoint("rear:mtp.12") == ("rear", "mtp", 12)


def test_a_part_key_is_how_capacities_spells_it():
    assert O.part_key(None, "lc1") == "lc1"
    assert O.part_key("rear", "mtp") == "rear:mtp"


def test_an_endpoint_round_trips_through_its_key():
    face, part, pos = O.split_endpoint("rear:mtp.7")
    assert O.part_key(face, part) == "rear:mtp"


@pytest.mark.parametrize("bad", [
    "mtp", "mtp.0", "rear:mtp", ":mtp.1", "rear:.1", "REAR:mtp.1",
    "rear:mtp.1.2", "a:b:c.1", "", None,
])
def test_what_is_not_an_endpoint(bad):
    with pytest.raises(ValueError):
        O.split_endpoint(bad)


def test_capacities_reaches_a_part_on_another_face():
    """The whole point: a cassette's rear MTP must be findable from the front."""
    front = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
             "faces": {"rear": {"ref": "fs/x-rear@1"}}}
    rear = {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}]}
    known = {
        "common/lc-duplex-v-adapter@1": {"optical": {"positions": 2}},
        "common/mpo-adapter@1": {"optical": {"positions": 12}},
        "fs/x-rear@1": rear,
    }
    caps = O.capacities(front, known.get)
    assert caps == {"lc1": 2, "rear:mtp": 12}


def test_a_face_that_names_nothing_resolvable_contributes_nothing():
    """A broken `faces.rear` is L83's error to report, not a crash here.

    `optical.py` answers questions and never validates - that split is what lets
    the exporter reuse it without inheriting lint's opinions - so a face whose
    component will not load simply adds no capacities.
    """
    front = {"parts": [], "faces": {"rear": {"ref": "fs/nope@1"}}}
    assert O.capacities(front, lambda ref: None) == {}


import yaml  # noqa: E402

import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run84(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_optical_faces(path, doc)
    return [e for e in L.ERRORS if "[L84]" in e]


def test_a_path_into_a_face_the_part_does_not_have():
    got = run84({"optical": {"paths": [{"from": "lc1.1", "to": "rear:mtp.1"}]}})
    assert len(got) == 1, got
    assert "rear" in got[0] and "declares no" in got[0]


def test_a_path_into_a_face_the_part_does_have_is_quiet():
    assert run84({
        "faces": {"rear": {"ref": "fs/x-rear@1"}},
        "optical": {"paths": [{"from": "lc1.1", "to": "rear:mtp.1"}]},
    }) == []


def test_unqualified_endpoints_are_not_this_rules_business():
    assert run84({"optical": {"paths": [{"from": "a.1", "to": "b.2"}]}}) == []


def test_a_split_reports_every_bad_leg():
    got = run84({"optical": {"paths": [{
        "from": "c.1",
        "to": [{"at": "rear:x.1", "ratio": 50},
               {"at": "top:y.1", "ratio": 50}]}]}})
    assert len(got) == 2, got


def test_the_real_cassette_passes_this_rule():
    """The one contract in the library that uses a qualified endpoint."""
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml"
         ).read_text())
    assert run84(c) == []


def test_a_legacy_plan_spelling_still_counts_as_a_declared_face():
    """The eleven risers name their plan drawing the old way.

    Reading `faces:` directly would report `plan:pcb.1` on one of them as a face
    the part does not have. `face_ref` answers for both spellings, which is the
    whole reason it exists.
    """
    assert run84({
        "plan": {"ref": "dell/riser-card-14g@1"},
        "optical": {"paths": [{"from": "a.1", "to": "plan:pcb.1"}]},
    }) == []
