"""A fan says it can show `ok`/`fail` only where the hardware has somewhere to show it.

roc-ops/Portrayal#212. Ten fan contracts declared `states: [ok, fail, absent]`
and drew no lamp, so every device that seated one carried L47 from the component
- including `docs/device-template.yaml`, the file a new contributor copies,
which had to allow the warning through to claim it lints silent.

THE ANSWER WAS NOT THE SAME FOR ALL TEN, and the guides say which is which:

  - MX204: "The MX204 fan module does not have any LED-the fan status LEDs are
    located on the MX204 chassis."
  - MX240 and MX480: "The fan LEDs are located on the top left of the craft
    interface."
  - MX304: "The LED for the fan module is located next to each fan module on the
    chassis."
  - MX10003: "Each fan module contains one bicolor LED."

Four say the indicator is somewhere else; one says it is on the module. So eight
contracts dropped the states and two kept them, and the difference is a document
rather than a preference. That is the question L47's own message asks - "either
the drawing is missing the indicator, or the part has none" - and this file
pins the answers so a later sweep does not flatten them back together.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint  # noqa: E402

LAMP = {"ok", "fail", "fault"}


def contracts(cls):
    out = {}
    for c in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(c.read_text()) or {}
        if d.get("class") == cls:
            out[f"{c.parts[-4]}/{c.parts[-3]}@{c.parts[-2][1:]}"] = (c, d)
    return out


@pytest.fixture(scope="module")
def fans():
    return contracts("fan")


def test_there_are_fans_to_check(fans):
    """NON-VACUITY: every assertion below passes over an empty mapping."""
    assert len(fans) >= 20, f"only {len(fans)} fan contracts found - the walk is broken"


def test_a_fan_claiming_a_lamp_state_has_something_to_show_it_or_says_why(fans):
    """The rule, over the corpus. A fan may declare `ok`/`fail` when it draws a
    lamp, or when its provenance records the indicator it has and cannot draw
    yet - and not otherwise."""
    bad = []
    for ref, (path, d) in fans.items():
        st = d.get("states")
        claimed = LAMP & set(st if isinstance(st, list) else (st or {}))
        if not claimed:
            continue
        if lint._lights_up(path, d, [str(LIB)], set()):
            continue
        prov = d.get("provenance") or {}
        if any(k in prov for k in ("states", "indicators", "led-states")):
            continue
        bad.append(f"{ref} claims {sorted(claimed)} with no lamp and no provenance for it")
    assert not bad, "\n".join(bad)


def test_the_two_fans_that_keep_their_states_name_the_document(fans):
    """The other direction: a kept claim has to be backed, or the test above
    passes by everyone simply writing a provenance key. These two say where the
    indicator is and that it is on the module."""
    for ref, key, must in (
            ("juniper/mx10003-fan@1", "states", "contains one bicolor LED"),
            ("smartoptics/dcp-2-fan@1", "indicators", "glow green")):
        path, d = fans[ref]
        assert LAMP & set(d.get("states") or []), f"{ref} should still claim a lamp state"
        text = " ".join(str((d.get("provenance") or {}).get(key, "")).split())
        assert must in text, f"{ref} provenance.{key} should quote the source: {text[:120]}"


def test_the_fans_whose_indicator_lives_elsewhere_dropped_the_claim(fans):
    """Named one by one rather than swept, because each is a separate sentence in
    a separate guide and a regression on any of them is a separate mistake."""
    for ref in ("juniper/mx204-fan@1", "juniper/mx240-fan-tray@1",
                "juniper/mx480-fan-tray@1", "juniper/mx304-fan@1",
                "common/fan-module@1", "common/fan-module-41@1",
                "common/fan-module-46@1", "juniper/mx80-fan-tray@1"):
        _, d = fans[ref]
        assert not (LAMP & set(d.get("states") or [])), \
            f"{ref} declares a lamp state again: {d.get('states')}"
        assert "states" in (d.get("provenance") or {}), \
            f"{ref} dropped the state without recording why"


def test_absent_is_left_alone(fans):
    """`absent` is a presence fact rather than a lamp, L47 does not ask about it,
    and removing it was not this issue's business. Guarding that keeps the fix
    from having quietly been a bigger one."""
    for ref in ("common/fan-module@1", "juniper/mx204-fan@1"):
        _, d = fans[ref]
        assert d.get("states") == ["absent"], (ref, d.get("states"))


def test_a_generic_fan_states_no_wattage_and_that_is_settled(fans):
    """The L29 half of #212. A drawing standing for many real fans cannot carry
    one wattage, which is the schema's own third reason for `not-applicable`."""
    for ref in ("common/fan-module@1", "common/fan-module-41@1", "common/fan-module-46@1"):
        _, d = fans[ref]
        assert (d.get("attrs") or {}).get("power-absent") == "not-applicable", ref
