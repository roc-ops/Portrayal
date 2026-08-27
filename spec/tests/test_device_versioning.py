"""Device versioning: a device cannot change without saying so.

The rules under test are about DISCIPLINE rather than geometry, so the fixtures
are the smallest devices that can express a change of each kind.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "portrayal"))

import devicelock as dl  # noqa: E402


def dev(version="1.0.0", at=(0, 0), extra_bay=None, gaps=None, note="a"):
    bays = [{"id": "slot-0", "at": list(at), "size": {"w": 10, "h": 10},
             "group": "slots", "accepts": ["x/y@1"]}]
    if extra_bay:
        bays.append({"id": extra_bay, "at": [50, 0], "size": {"w": 10, "h": 10},
                     "group": "slots", "accepts": ["x/y@1"]})
    return {
        "kind": "device", "name": "d", "version": version,
        "chassis": {"width": 100, "height": 40, "depth": 30},
        "groups": {"slots": {"term": "Slot", "index-origin": 0}},
        "provenance": {"size": note},
        "gaps": gaps if gaps is not None else [],
        "views": {"front": {"size": {"w": 100, "h": 40},
                            "components": {"bays": bays}}},
    }


# ---- what kind of change is this? -------------------------------------------

def test_an_unchanged_device_needs_no_bump():
    a = dl.entry(dev())
    assert dl.required_bump(a, dl.entry(dev())) is None


def test_a_reworded_provenance_is_a_patch():
    a = dl.entry(dev(note="a"))
    assert dl.required_bump(a, dl.entry(dev(note="b"))) == "patch"


def test_a_moved_slot_is_major_even_though_nothing_was_removed():
    """The ids are identical; a coordinate someone cached is not."""
    a = dl.entry(dev(at=(0, 0)))
    assert dl.required_bump(a, dl.entry(dev(at=(1, 0)))) == "major"


def test_an_added_bay_is_minor():
    a = dl.entry(dev())
    assert dl.required_bump(a, dl.entry(dev(extra_bay="slot-1"))) == "minor"


def test_a_removed_bay_is_major():
    a = dl.entry(dev(extra_bay="slot-1"))
    assert dl.required_bump(a, dl.entry(dev())) == "major"


def test_key_order_and_integral_floats_are_not_changes():
    """Two files that differ only in how they are spelled are one device.
    A fingerprint that fires on re-indentation gets re-locked without being
    read, which is how a check stops being read at all."""
    a = dev()
    b = dev()
    b["views"]["front"]["components"]["bays"][0]["at"] = [0.0, 0.0]
    b["chassis"] = {"depth": 30, "width": 100, "height": 40}
    assert dl.entry(a)["shape"] == dl.entry(b)["shape"]


# ---- was the bump the author took big enough? -------------------------------

def test_a_patch_does_not_cover_a_moved_slot():
    assert not dl.sufficient(dl.bump_taken("1.0.0", "1.0.1"), "major")


def test_a_major_covers_anything():
    for need in ("patch", "minor", "major"):
        assert dl.sufficient(dl.bump_taken("1.0.0", "2.0.0"), need)


def test_no_bump_at_all_covers_nothing():
    assert not dl.sufficient(None, "patch")


def test_a_version_only_counts_up():
    assert dl.bump_taken("2.0.0", "1.9.9") == "backwards"
    assert not dl.sufficient("backwards", "patch")


# ---- the gaps re-affirmation ------------------------------------------------

GAP = [{"what": "port-led-semantics", "reason": "vendor-silent",
        "wanted": "a table", "scope": ["slots"]}]


def test_a_shape_change_asks_for_the_gaps_to_be_re_read(tmp_path):
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=GAP))
    kinds = {k for _, k, _ in dl.check(lib)}
    assert "gaps-unreviewed" in kinds, "a moved slot left 1 gap unexamined and nothing said so"


def test_a_surface_change_does_not(tmp_path):
    """Firing on every provenance edit would make it noise."""
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="1.0.1", note="b", gaps=GAP))
    assert not [f for f in dl.check(lib) if f[1] == "gaps-unreviewed"]


def test_a_device_with_no_gaps_is_not_nagged(tmp_path):
    lib = _library(tmp_path, dev(gaps=[]))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=[]))
    assert not [f for f in dl.check(lib) if f[1] == "gaps-unreviewed"]


def test_re_locking_clears_the_prompt(tmp_path):
    """Re-locking is the 'I have read them' step, so it has to actually clear."""
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=GAP))
    assert dl.check(lib)
    dl.update(lib)
    assert dl.check(lib) == []


# ---- gap scopes -------------------------------------------------------------

def test_a_gap_scoped_to_a_real_group_is_silent():
    assert dl.stale_gap_scopes(dev(gaps=GAP)) == []


def test_a_gap_scoped_to_nothing_is_reported():
    bad = [{"what": "w", "reason": "vendor-silent", "wanted": "x",
            "scope": ["no-such-thing"]}]
    assert dl.stale_gap_scopes(dev(gaps=bad)) == [("w", "no-such-thing")]


def test_a_gap_may_scope_an_id_a_view_or_a_nested_attr():
    d = dev(gaps=[{"what": "w", "reason": "vendor-silent", "wanted": "x",
                   "scope": ["slot-0", "front", "power-max-w"]}])
    d["attrs"] = {"power": {"power-max-w": "527 W"}}
    assert dl.stale_gap_scopes(d) == [], "a nested attribute key is a legitimate scope"


# ---- helpers ----------------------------------------------------------------

def _library(tmp_path, doc):
    lib = tmp_path / "library"
    (lib / "devices" / "v" / "d").mkdir(parents=True)
    _write(lib, doc)
    return lib


def _write(lib, doc):
    import yaml
    (lib / "devices" / "v" / "d" / "device.yaml").write_text(yaml.safe_dump(doc))
