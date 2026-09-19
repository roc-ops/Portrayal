"""A component rewritten in place must move the lock of every device that seats it.

`_composed()` resolved each ref to the component's DECLARED VERSION STRING, so the
guard closed on the author remembering to bump. Edit a component in place and
nothing reported it: the component has no lock of its own, the device hashed a
version that had not changed, and no lint rule asked for a bump.

Found on roc-ops/Portrayal#405, from a real case - three components' `relief`
blocks and one skin were rewritten across six bays in two devices, all three
stayed at 1.0.0, and `devicelock --update` re-locked neither device.

The fingerprint now carries a digest of the component's own files beside its
version, so `composed-refs` reads `edgecore/fan-2u-1x1sn@1 1.0.0+a1b2c3d4 ->
1.0.0+9f8e7d6c` - which says in one line that the contents moved and the version
did not.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal import devicelock as dl   # noqa: E402


CONTRACT = """\
format: 1
kind: module
name: widget
version: 1.0.0
class: psu
size: {w: 10.0, h: 10.0}
states: [absent]
skins: [default]
"""

SKIN = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">' \
       '<rect id="body" x="0" y="0" width="10" height="10" fill="#aaa"/></svg>'

DEVICE = {
    "format": 1, "kind": "device", "name": "thing", "version": "1.0.0",
    "manufacturer": "Acme", "model": "Thing",
    "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0, "ru": 1},
    "views": {"rear": {"size": {"w": 100.0, "h": 44.0}, "components": {"bays": [
        {"id": "psu-1", "at": [0, 0], "size": {"w": 10.0, "h": 10.0},
         "group": "psus", "rel-pos": 1,
         "accepts": ["acme/widget@1"], "default": "acme/widget@1"}]}}},
    "groups": {"psus": {"term": "PSU", "role": "service", "index-origin": 1}},
}


def _library(tmp_path) -> pathlib.Path:
    lib = tmp_path / "library"
    v1 = lib / "components" / "acme" / "widget" / "v1"
    (v1 / "skins").mkdir(parents=True)
    (v1 / "contract.yaml").write_text(CONTRACT)
    (v1 / "skins" / "default.svg").write_text(SKIN)
    return lib


def _composed_for(lib) -> dict:
    return dl.entry(DEVICE, dl.component_versions(lib))["composed"]


def test_a_rewritten_skin_moves_the_seating_device_s_fingerprint(tmp_path):
    """The case from #405, at its smallest: the component's drawing changes and
    its version does not."""
    lib = _library(tmp_path)
    before = _composed_for(lib)

    skin = lib / "components" / "acme" / "widget" / "v1" / "skins" / "default.svg"
    skin.write_text(SKIN.replace('fill="#aaa"', 'fill="#c0453f"'))

    assert _composed_for(lib) != before


def test_a_rewritten_contract_moves_it_too(tmp_path):
    """Relief lives in the contract, not the skin, and that is what #405 was
    actually about - three `relief` blocks rewritten with every skin but one
    untouched."""
    lib = _library(tmp_path)
    before = _composed_for(lib)

    ct = lib / "components" / "acme" / "widget" / "v1" / "contract.yaml"
    ct.write_text(CONTRACT + "relief:\n  wall: '#3a3e43'\n"
                             "  features:\n    - {node: body, out: 2.0}\n")

    assert _composed_for(lib) != before


def test_a_comment_or_reindentation_does_not_move_it(tmp_path):
    """The file's own rule: "a fingerprint that fires on re-indentation would be
    re-locked" for nothing. The contract is hashed as PARSED yaml, so prose in a
    comment - which is most of what this library edits - is free."""
    lib = _library(tmp_path)
    before = _composed_for(lib)

    ct = lib / "components" / "acme" / "widget" / "v1" / "contract.yaml"
    ct.write_text("# a comment that says why, and changes nothing\n"
                  + CONTRACT.replace("size: {w: 10.0, h: 10.0}",
                                     "size:\n  w: 10.0\n  h: 10.0"))

    assert _composed_for(lib) == before


def test_the_version_is_still_readable_beside_the_digest(tmp_path):
    """`composed-refs` is committed per device so a reviewer sees the fingerprint
    beside the thing it fingerprints. A bare hash would lose the version, which is
    the half of it a human reads."""
    lib = _library(tmp_path)
    refs = dl.entry(DEVICE, dl.component_versions(lib))["composed-refs"]
    assert refs["acme/widget@1"].startswith("1.0.0+"), refs
