"""Every state rule a viewer can reach must be valid CSS.

The bug this locks: components_index.py built its own component-scoped state
rule by hand instead of calling render.state_rule, and named the palette value
`color` when state_style() returns a (color, alt, mode) TUPLE. So every
standalone component skin carried

    g[data-ref^='cisco/a9k-rsp880-se@'] .state-amber
        { --led-color: ('#f5a623', None, 'solid'); }

which is not a colour. The class landed, the selector matched, and the lamp did
not change - in the ONE place a user can actually click a module lamp, because
demo2 fetches these files when it swaps a card into a bay. The device drawings
were correct throughout, so nothing in the built device SVGs could reveal it.

The general shape, and why this is a test rather than a lint rule: TWO
GENERATORS FOR ONE OUTPUT DRIFT, and the copy that drifts is the one with no
consumer watching it. Assert the output is well formed wherever it is produced,
not that the two call sites look alike.
"""
import re
import pathlib

import pytest

DIST = pathlib.Path(__file__).resolve().parents[2] / "library" / "dist"
# a CSS value that is a colour, a var(), or a keyword - never a Python repr
BAD = re.compile(r"--led-color(?:-alt)?:\s*[('\[]")


def svgs():
    if not DIST.exists():
        pytest.skip("library/dist not built")
    return sorted(DIST.rglob("*.svg"))


def test_no_python_repr_leaks_into_css():
    bad = []
    for f in svgs():
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if BAD.search(line):
                bad.append(f"{f.relative_to(DIST)}:{n}: {line.strip()[:90]}")
    assert not bad, (
        f"{len(bad)} state rule(s) carry a non-colour value; "
        "a tuple or list repr has reached the stylesheet:\n  "
        + "\n  ".join(bad[:12]))


def test_component_skins_declare_state_rules_for_their_own_states():
    """A lamp that declares states needs rules, or clicking it does nothing."""
    comp = DIST / "components"
    if not comp.exists():
        pytest.skip("no components built")
    silent = []
    for f in sorted(comp.glob("*.svg")):
        t = f.read_text()
        declared = set()
        for m in re.finditer(r'data-states="([^"]*)"', t):
            declared.update(m.group(1).split())
        if not declared:
            continue
        styled = set(re.findall(r"\.state-([a-z0-9-]+)", t))
        # `off` is the absence of a state and is never styled
        missing = declared - styled - {"off"}
        if missing:
            silent.append(f"{f.name}: {sorted(missing)}")
    assert not silent, (
        f"{len(silent)} component skin(s) declare a state with no rule to "
        "render it:\n  " + "\n  ".join(silent[:12]))
