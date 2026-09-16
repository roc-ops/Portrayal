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


def _render():
    from portrayal import render
    return render


def test_a_segment_state_names_the_segments_it_leaves_off():
    """A SEVEN-SEGMENT DIGIT CHANGES SHAPE, NOT COLOUR, so its states drive
    `opacity` per segment rather than a colour variable - and each state has to
    be a COMPLETE statement of the face.

    The bug this locks: a rule that only turns segments ON leaves whatever the
    previous state lit still lit, so selecting `1` after `8` still reads `8`.
    Every state therefore names the segments it lights and, separately, every
    other segment in the component's vocabulary as off.
    """
    r = _render()
    style = r.state_style({"name": "1", "lights": ["b", "c"]},
                          {"a", "b", "c", "d", "e", "f", "g"})
    assert style is not None, "a state that lights segments needs CSS"
    css = r.state_rule("SEL", "SEL", *style)
    on = [s for s in css.split("\n") if "opacity: 1" in s]
    off = [s for s in css.split("\n") if "opacity: 0" in s]
    assert len(on) == 1 and len(off) == 1, css
    for seg in ("b", "c"):
        assert f"[data-seg='{seg}']" in on[0], (seg, on[0])
    for seg in ("a", "d", "e", "f", "g"):
        assert f"[data-seg='{seg}']" in off[0], (seg, off[0])
    assert "--led-color" not in css, "a digit is not a coloured lamp"


def test_a_colour_state_is_unchanged_by_the_segment_support():
    """The half that keeps the old shape honest: an ordinary lamp state carries
    no `lights`, emits no opacity rule, and still sets its colour."""
    r = _render()
    css = r.state_rule("SEL", "SEL", *r.state_style({"name": "ok",
                                                     "color": "#22c55e"}))
    assert "--led-color: #22c55e;" in css
    assert "opacity" not in css and "data-seg" not in css


def test_every_animation_names_a_keyframes_that_exists():
    """An animation is a promise that a @keyframes of that name is defined.

    The bug this locks: the sequence keyframes name was threaded through
    render.py's call site and NOT through components_index.py's, so every
    component skin carrying a sequence emitted

        @keyframes None { ... }
        .state-predicted-failure { animation: None 3s steps(1, end) infinite; }

    twice over, with the second definition of `None` silently replacing the
    first. `None` is a valid CSS identifier, so the stylesheet parsed, the class
    landed, and both lamps ran whichever cycle happened to be defined last.

    The general shape is the one at the top of this file - two generators for
    one output drift - and it recurred in the SAME PAIR OF FILES, which is why
    the name is now built by a single function both import. This test does not
    care which function that is: it asserts the output is coherent.
    """
    missing = []
    for f in svgs():
        t = f.read_text()
        defined = set(re.findall(r"@keyframes\s+([^\s{]+)", t))
        for name in re.findall(r"animation:\s*([^\s;]+)", t):
            if name not in defined:
                missing.append(f"{f.relative_to(DIST)}: animation {name!r} has "
                               f"no @keyframes (defined: "
                               f"{', '.join(sorted(defined)) or 'none'})")
    assert not missing, "\n  ".join([""] + missing[:12])


def test_no_two_states_share_one_keyframes_name():
    """A sequence's cycle is per state, so its name must be too - two states
    sharing one means the second definition wins and the first lamp animates
    somebody else's pattern. Defining a name twice in one stylesheet is the
    signature, and it is what `None` did."""
    dupes = []
    for f in svgs():
        seen = {}
        for name in re.findall(r"@keyframes\s+([^\s{]+)", f.read_text()):
            seen[name] = seen.get(name, 0) + 1
        for name, n in seen.items():
            if n > 1:
                dupes.append(f"{f.relative_to(DIST)}: @keyframes {name!r} "
                             f"defined {n} times")
    assert not dupes, "\n  ".join([""] + dupes[:12])
