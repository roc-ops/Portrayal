"""A mark says what it annotates, or says it annotates the whole unit.

L14 has always been half a rule: it checks a `for:` that IS stated and is silent
on one that is not, so a legend with no owner was never wrong about anything.
459 of 989 marks had drifted into that silence. L42 is the other half.

Owning a mark is not tidiness. Without it L14 cannot check that the legend sits
near what it names, L21 cannot know which module paints over it, the tree cannot
nest it under its owner, and no consumer can answer "what is printed next to
port 12".
"""
import sys
from pathlib import Path

import yaml

import libdata

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402
from manifest import view_parts  # noqa: E402


class _NoSchema:
    def iter_errors(self, _data):
        return iter(())


def l42(dev):
    """L42 is its own function, so call it directly rather than the whole pass."""
    saved_w, saved_e = lint.WARNINGS[:], lint.ERRORS[:]
    lint.WARNINGS.clear()
    lint.ERRORS.clear()
    try:
        lint.lint_device_silkscreen_owner(Path("fixture.yaml"), dev)
        return [w for w in lint.WARNINGS if "[L42]" in w], \
               [e for e in lint.ERRORS if "[L42]" in e]
    finally:
        lint.WARNINGS[:] = saved_w
        lint.ERRORS[:] = saved_e


def device(maturity, marks):
    return {"name": "fx", "maturity": maturity,
            "views": {"front": {"size": {"w": 100.0, "h": 50.0},
                                "silkscreen": marks}}}


BARE = [{"at": [5.0, 5.0], "text": "PSU 1"}]
OWNED = [{"at": [5.0, 5.0], "text": "PSU 1", "for": "psu-1"}]
CHASSIS = [{"at": [5.0, 5.0], "text": "C40G", "for": "chassis"}]


def test_a_draft_is_not_nagged():
    """459 marks cannot become findings on the day the rule lands."""
    w, e = l42(device("draft", BARE))
    assert not w and not e


def test_modelled_warns_and_verified_errors():
    w, e = l42(device("modelled", BARE))
    assert len(w) == 1 and not e
    w, e = l42(device("verified", BARE))
    assert len(e) == 1 and not w


def test_an_owned_mark_is_silent():
    for m in (OWNED, CHASSIS):
        w, e = l42(device("modelled", m))
        assert not w and not e, m


def test_chassis_is_an_answer_and_not_an_escape_hatch():
    """L14 used to reject `for: chassis` on silkscreen outright - "printed ink
    annotates a part, not the whole unit" - while the library held some twenty
    marks that were exactly that. Requiring an owner is only fair once
    chassis-level printing can declare itself."""
    src = (SPEC / "tools/portrayal/lint.py").read_text()
    assert "Printed ink annotates a part" not in src
    marks = 0
    for _slug, p, d in libdata.library():
        for v in (d.get("views") or {}).values():
            marks += sum(1 for m in view_parts(v)["silkscreen"]
                         if m.get("for") == "chassis")
    assert marks >= 8, f"only {marks} marks claim the chassis"


def test_l14_does_not_spin_a_rotated_bay():
    """A bay's `size` is already its on-panel footprint; `rotate` spins the
    OCCUPANT. L14 transposed it, so a slot number printed beside the C40G's
    rear-0 - a horizontal slot at x 39.35 - was measured against a vertical one
    at x 196.865 and reported 157 mm away. Live until a legend first named a
    rotated bay, which nothing had ever done.
    """
    d = yaml.safe_load((LIB / "devices/casa/c40g/device.yaml").read_text())
    vp = view_parts(d["views"]["rear"])
    bay = next(b for b in vp["bays"] if b["id"] == "rear-0")
    assert bay.get("rotate") == 90, "fixture needs a rotated bay"
    mark = next(m for m in vp["silkscreen"] if m.get("for") == "rear-0")
    # the legend column sits left of the slot it names, on the slot's own row
    assert mark["at"][0] < bay["at"][0]
    assert bay["at"][1] <= mark["at"][1] <= bay["at"][1] + bay["size"]["h"] + 25


def _ownership(modelled_only):
    tot = own = 0
    for _slug, p, d in libdata.library():
        if modelled_only and (d.get("maturity") or "draft") == "draft":
            continue
        for v in (d.get("views") or {}).values():
            for m in view_parts(v)["silkscreen"]:
                tot += 1
                own += 1 if m.get("for") else 0
    return own, tot


def test_the_modelled_devices_are_nearly_all_owned():
    """The few that are not each name something the model does not hold yet -
    an unmodelled filter, an ESD jack that is a bare cutout, a fan tray. L42 is
    pointing at modelling debt, which is what it is for; it is not noise to be
    silenced with a false owner.
    """
    own, tot = _ownership(True)
    assert tot - own <= 8, f"{tot - own} unowned marks on modelled devices"
    assert own / tot > 0.95


def test_the_whole_library_stays_owned():
    """The draft devices were backfilled too, and L42 does not gate them - so
    nothing but this test stops them drifting back. 989 marks, 53 percent owned
    when the sweep started."""
    own, tot = _ownership(False)
    assert own / tot > 0.97, f"only {own}/{tot} marks name anything"


def test_a_wordmark_names_the_whole_unit_and_not_whatever_is_beside_it():
    """The backfill leaned on proximity for direction and number labels, and
    proximity is exactly wrong for printing that belongs to no part: it bound
    `smartoptics` to an ethernet jack and `DCP-R-34D-CS` to a port, because
    those happened to be nearest. A wordmark names the chassis or nothing.
    """
    for _slug, p, d in libdata.library():
        flat = lambda s: str(s).lower().replace(" ", "").replace("-", "")
        names = {flat(d.get("model")), flat(d.get("manufacturer"))}
        for v in (d.get("views") or {}).values():
            for m in view_parts(v)["silkscreen"]:
                if flat(m.get("text") or "\x00") in names:
                    assert m.get("for") in (None, "chassis"), \
                        f"{d['name']}: {m.get('text')!r} names {m.get('for')!r}"
