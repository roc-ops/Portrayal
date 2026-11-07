"""The 3D scene hides a pulled part on its own view only (#1002).

`fs/dinrail2u`'s `left` and `right` views each place `screw-upper` and
`screw-lower`, and each side bracket is `under` both. The scene was handed bare
ids, so pulling the right bracket's screws hid the left's too. The scene now
takes the view of each path beside it; relief.js is what hides, in a face's text
and in its meshes, and is held here under node on a fixture of that shape. What
is left to a browser is that viewer3d.js passes the view it is given - the
preview shows it.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "js/relief-pulled-views.mjs"
SCREWS = ["screw-lower", "screw-upper"]


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent), timeout=120)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_part_pulled_on_the_right_leaves_the_right_face_only(out):
    assert out["texturesRight"] == SCREWS
    assert out["texturesLeft"] == [], "the left face's screws went with the right's"


def test_the_relief_of_a_part_pulled_on_the_right_is_hidden_on_the_right_only(out):
    assert out["meshesRight"] == ["side-right:shown", "screw-upper:hidden", "screw-lower:hidden"]
    assert out["meshesLeft"] == ["side-left:shown", "screw-upper:shown", "screw-lower:shown"]


def test_a_view_is_kept_beside_its_path(out):
    assert out["pulledAnywhere"] == SCREWS
    assert out["pulledOnRight"] == SCREWS
    assert out["pulledOnLeft"] == []
    assert out["oneViewForAll"] == [True, False]


def test_a_pull_with_no_view_is_every_faces_as_it_was(out):
    assert out["noViewLeft"] == SCREWS and out["noViewRight"] == SCREWS
    assert out["noViewMeshes"] == [["side-left:shown", "screw-upper:hidden", "screw-lower:hidden"],
                                   ["side-right:shown", "screw-upper:hidden", "screw-lower:hidden"]]


def test_a_text_asked_without_its_view_hides_only_what_is_off_everywhere(out):
    assert out["textWithoutAView"] == []


def test_the_projection_of_a_seated_part_goes_with_it_on_any_face(out):
    assert out["projectionFollows"] == ["bay-1/module"]


def test_putting_the_parts_back_shows_them_everywhere(out):
    assert out["putBack"] == []
    assert out["meshesBack"] is True
