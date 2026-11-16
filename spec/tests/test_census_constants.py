"""The census counts of the ground stud and seat turn tests are named constants.

A pull request that adds a device moves a few of these counts. Written inside an
assertion, two such changes cannot be added together. Written as a module-level
constant, each side's change can be settled on its own line. This test reads the
two files as text only.
"""
import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
NAMED = {
    "test_ground_stud_lugs.py": ("GROUND_SCREW_COUNT", "GROUND_SCREW_LOCATIONS", "STUD_SEATS_SEEN",
                                 "STUD_PLACEMENTS", "STUD_DEVICES"),
    "test_occupant_turn.py": ("RING_DEVICES", "PAIR_DEVICES", "CROSSED_SEATS"),
}
LIMIT = 30
ANGLES = (90, 180, 270)


def _tree(name):
    return ast.parse((TESTS / name).read_text())


@pytest.mark.parametrize("name", sorted(NAMED))
def test_no_assertion_compares_a_count_to_a_bare_integer(name):
    bare = []
    for node in ast.walk(_tree(name)):
        if not isinstance(node, ast.Assert):
            continue
        for cmp in (n for n in ast.walk(node.test) if isinstance(n, ast.Compare)):
            for op, right in zip(cmp.ops, cmp.comparators):
                if (isinstance(op, ast.Eq) and isinstance(right, ast.Constant)
                        and type(right.value) is int and right.value > LIMIT
                        and right.value not in ANGLES):
                    bare.append(f"{name}:{node.lineno} compares to {right.value}")
    assert not bare, bare


@pytest.mark.parametrize("name", sorted(NAMED))
def test_each_census_constant_is_a_plain_module_level_integer(name):
    found = {}
    for node in _tree(name).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            value = node.value
            if isinstance(value, ast.Constant) and type(value.value) is int:
                found[node.targets[0].id] = value.value
    missing = [c for c in NAMED[name] if c not in found]
    assert not missing, (name, missing)
