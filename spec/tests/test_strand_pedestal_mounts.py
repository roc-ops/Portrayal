"""Two more ways a box is installed: on a strand, and on a pedestal.

An aerial-plant node clamps to the support strand of a cable run or sits on a
pedestal, and `chassis.mount` had a value for neither, so such a box could only
say `wall`. This module holds what is now true of the library: the schema takes
`strand` and `pedestal` and keeps `wall`, each says in a sentence what it is,
the lint rule's text and its warning name them, a DCIM export says the box is
not rack-mounted, and a box that states one occupies no rack unit. No device in
this change states either value.
"""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

from portrayal import dcim_export as dx  # noqa: E402
from portrayal import lint               # noqa: E402

NEW = ("strand", "pedestal")


def _mount():
    return SCHEMA["properties"]["chassis"]["properties"]["mount"]


def test_the_schema_names_a_strand_and_a_pedestal_mount_and_keeps_wall():
    enum = _mount()["enum"]
    assert all(m in enum for m in NEW)
    assert "wall" in enum and "ceiling" in enum


def test_each_new_value_says_what_it_is():
    text = _mount()["description"]
    assert ("`strand` is one that clamps to the support strand or cable of an aerial plant"
            in text)
    assert "`pedestal` is one that mounts on a pedestal or rod" in text


@pytest.mark.parametrize("mount,prose", [
    ("strand", "Strand-mounted; not rack-mounted."),
    ("pedestal", "Pedestal-mounted; not rack-mounted."),
])
def test_the_export_says_how_the_box_is_mounted(mount, prose):
    assert dx.MOUNT_PROSE[mount] == prose
    assert prose in dx.comments_for({"chassis": {"mount": mount}}, "base", {})


@pytest.mark.parametrize("mount", NEW)
def test_a_box_on_a_strand_or_pedestal_exports_no_rack_units(mount):
    assert dx.u_height({"mount": mount}) == 0.0
    assert dx.is_full_depth({"mount": mount}) is False


def _l125(chassis):
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", {"chassis": chassis})
    return [m for m in found.errors + found.warnings if "[L125]" in m]


@pytest.mark.parametrize("mount", NEW)
def test_L125_a_box_on_a_strand_or_pedestal_states_no_rack_units(mount):
    assert not _l125({"mount": mount})
    assert _l125({"mount": mount, "ru": 1})
    assert _l125({"mount": mount, "full-depth": False})
    assert _l125({"mount": mount, "kits": []})


def test_L125_names_the_new_mounts_in_its_text_and_its_warning():
    text = lint.RULES["L125"][1]
    assert all(f"`{m}`" in text for m in NEW)
    warning = " ".join(_l125({"width": 440}))
    assert all(f"`{m}`" in warning for m in NEW)
