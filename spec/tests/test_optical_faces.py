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
