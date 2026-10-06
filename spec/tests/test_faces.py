"""`faces:` - a part naming its own drawings seen from other directions.

The legacy spelling is a top-level `plan: {ref}`. The new one is
`faces: {plan: {ref}, rear: {ref}}`. Both must mean the same thing for `plan`,
and the library must never carry both on one contract, because then a reader has
to guess which the author meant.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal import faces as F
from portrayal import lint as L

LIB = [str(ROOT / "library")]


def test_the_directions_constant_matches_the_schema():
    """The schema is the authority; this constant is how the tools read it.

    They drift the moment somebody adds a face to one and not the other - and
    the drift is silent, because a direction the schema allows but the tools do
    not iterate simply never appears in the built index.
    """
    import json
    s = json.loads(
        (ROOT / "spec/schemas/component.schema.json").read_text())
    assert tuple(s["properties"]["faces"]["properties"]) == F.DIRECTIONS


def run82(doc, path="t/contract.yaml"):
    with L.collecting() as _found:
        L.lint_component_faces_once(path, doc)
    return [e for e in _found.errors if "[L82]" in e]


def test_the_legacy_spelling_still_answers():
    assert F.face_ref({"plan": {"ref": "dell/riser-card-14g@1"}}, "plan") == \
        "dell/riser-card-14g@1"


def test_the_new_spelling_answers_the_same_way():
    assert F.face_ref({"faces": {"plan": {"ref": "dell/riser-card-14g@1"}}},
                      "plan") == "dell/riser-card-14g@1"


def test_a_rear_face_has_no_legacy_spelling_to_fall_back_to():
    """`rear` is new, so it reads `faces` only - there is no top-level `rear:`."""
    assert F.face_ref({"faces": {"rear": {"ref": "fs/x-rear@1"}}}, "rear") == \
        "fs/x-rear@1"
    assert F.face_ref({"rear": {"ref": "fs/x-rear@1"}}, "rear") is None


def test_a_part_with_no_faces_at_all_answers_none():
    assert F.face_ref({}, "plan") is None
    assert F.face_ref({}, "rear") is None


def test_saying_it_both_ways_is_an_error():
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/c@1"}}})
    assert len(got) == 1, got
    assert "faces.plan" in got[0]


def test_saying_it_both_ways_is_an_error_even_when_they_agree():
    """Agreeing today is not the point - one of them gets edited tomorrow."""
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/b@1"}}})
    assert len(got) == 1, got


def test_one_spelling_or_the_other_is_quiet():
    assert run82({"plan": {"ref": "a/b@1"}}) == []
    assert run82({"faces": {"plan": {"ref": "a/b@1"}}}) == []
    assert run82({"faces": {"rear": {"ref": "a/b@1"}}}) == []
    assert run82({}) == []


def test_render_reads_a_plan_through_the_accessor():
    """render.py must not spell out `.get("plan")` for a COMPONENT any more.

    The bay-side `plan:` - where a projection LANDS - is a different key and
    keeps its literal reads; this only checks the two component-side ones.
    """
    src = (ROOT / "spec/tools/portrayal/render.py").read_text()
    assert 'oc or {}).get("plan")' not in src, \
        "render.py:~1199 still reads a component's plan directly"
    assert 'sc or {}).get("plan")' not in src, \
        "render.py:~1218 still reads a component's plan directly"
    assert "face_ref(" in src, "render.py does not use the accessor at all"


def test_lint_reads_a_plan_through_the_accessor():
    src = (ROOT / "spec/tools/portrayal/lint.py").read_text()
    assert 'c.get("plan") or {}).get("ref")' not in src, \
        "lint.py:~5844 still reads a component's plan directly"


def test_the_accessor_answers_for_every_part_that_names_a_plan():
    """Fourteen parts name a plan drawing; the accessor must find all of them.
    The fourteenth is ufispace/n3100-4c@1, the first real PCIe card, whose
    plan is ufispace/n3100-4c-plan@1. Fifty since the 36 NVIDIA ConnectX card
    modules, each naming the generic card plan of its bracket height. Sixty-two
    since the R660's top view: its four 60 mm supplies, the BOSS-N1 module, the
    six OCP NIC 3.0 cards and the shared 2.5 inch carrier now name their plans.
    Sixty-nine since the R660's risers: 2A, 2P, 2R and 3A, 3P, 3Q, 3R, the
    variants Dell's service model shows from above (2Q, 1P and 4P name none).
    Seventy-one since its LOM card and rear I/O board became modules.
    Seventy-two since riser 3S, drawn from above as riser 3P (2S names none).
    Seventy-three since the liquid-cooling rear I/O board, which names the
    standard board's plan.
    Seventy-four since riser 2S, drawn from above off two sibling manuals.
    Seventy-seven since risers 2Q, 1P and 4P name estimated plans, outlines by
    eye from the ISM's isometric figures.
    Seventy-nine since the HPE DL160 Gen10's two Flex Slot supplies
    (psu-865408-b21, psu-865414-b21) named hpe/psu-flex-slot-plan@1.
    Eighty-five since the Supermicro SYS-111E servers: their four supplies
    (psu-pws-861a-1r, psu-pws-601s-1r, psu-pws-804p-1r, psu-pws-862s-1r) each
    named the can they run into the chassis as, and the two WIO risers they
    share each named its bracket seen from above.

    Reads the real library rather than a fixture. Spelling-agnostic on purpose -
    it passes before Task 5's migration and after it, because what it watches is
    that no part LOSES its plan drawing, not which way the part spells it.
    """
    lib = ROOT / "library/components"
    named = [p for p in lib.glob("*/*/v*/contract.yaml")
             if F.face_ref(yaml.safe_load(p.read_text()) or {}, "plan")]
    # 86 since the Fibrain XCU10's drawer, seen from above under the shell top.
    assert len(named) == 86, \
        f"expected 86 parts naming a plan drawing, found {len(named)}"


def run83(doc, path="t/contract.yaml", name="t/thing@1", lib=LIB):
    with L.collecting() as _found:
        L.lint_component_faces_resolve(path, doc, lib, name)
    return [e for e in _found.errors if "[L83]" in e]


@pytest.mark.parametrize("direction", ["plan", "rear"])
def test_a_face_must_name_a_component_that_exists(direction):
    got = run83({"faces": {direction: {"ref": "fs/not-a-real-part@1"}}})
    assert len(got) == 1, got
    assert "not in the library" in got[0]


def test_a_plan_face_written_the_legacy_way_must_also_name_a_real_component():
    """L83 reads through `face_ref`, so the legacy `plan:` spelling gets the
    same check as `faces.plan` - the whole point of routing both through one
    accessor instead of leaving `plan:` a blind spot."""
    got = run83({"plan": {"ref": "fs/not-a-real-part@1"}})
    assert len(got) == 1, got
    assert "not in the library" in got[0]


@pytest.mark.parametrize("direction", ["plan", "rear"])
def test_a_part_may_not_be_its_own_face(direction):
    got = run83({"faces": {direction: {"ref": "common/mpo-adapter@2"}}},
                name="common/mpo-adapter@2")
    assert len(got) == 1, got
    assert f"its own {direction}" in got[0]


@pytest.mark.parametrize("direction", ["plan", "rear"])
def test_a_face_may_not_itself_have_a_face_of_the_same_direction(direction, tmp_path):
    """A part has one back and one top. `a`'s face being `b` whose face of the
    same direction is `c` means nothing.

    Builds its own two-component library rather than leaning on the real one
    staying arranged as it is - and the real library has no chain to point at,
    which is exactly why this rule exists before one appears.
    """
    d = tmp_path / "components" / "t" / "middle" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: middle\nversion: 1.0.0\n"
        "class: port\nsize: {w: 1, h: 1}\n"
        f"faces: {{{direction}: {{ref: t/deepest@1}}}}\n")
    e = tmp_path / "components" / "t" / "deepest" / "v1"
    e.mkdir(parents=True)
    (e / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: deepest\nversion: 1.0.0\n"
        "class: port\nsize: {w: 1, h: 1}\n")

    got = run83({"faces": {direction: {"ref": "t/middle@1"}}},
                name="t/outer@1", lib=[str(tmp_path)])
    assert len(got) == 1, got
    assert f"{direction} of its own" in got[0]


@pytest.mark.parametrize("direction", ["plan", "rear"])
def test_a_real_face_reference_is_quiet(direction):
    got = run83({"faces": {direction: {"ref": "common/mpo-adapter@2"}}})
    assert got == [], got


def test_no_faces_at_all_is_quiet():
    assert run83({}) == []


def test_the_index_carries_a_parts_other_faces():
    """The viewer offers a rear or plan drawing only if the built index says
    there is one - a source-text `"face_ref(" in src` check passes against a
    refactor that computes the value and drops the assignment, leaving every
    published entry silently without its faces while the test stays green.

    Skips when dist is absent, the way the emptiness check below already does.
    """
    import json
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    entries = json.loads(f.read_text())["components"]
    by_name = {e["name"]: e for e in entries if e["ns"] == "common"}
    for name, want in (("pcie-card-fh", "common/pcie-card-plan@1"),
                       ("pcie-card-lp", "common/pcie-card-plan-lp@1")):
        assert name in by_name, f"common/{name} missing from the built index"
        assert by_name[name].get("faces", {}).get("plan") == want, \
            f"common/{name}'s built entry does not carry faces.plan == {want!r}"
    # 18, not 17: fs/fhd-1mtp24-lc-os2-a@4 is the fifth contract to declare
    # `faces.rear` - after fs/fhd-1mtp6lcd-os2-a@4, fs/fhd-splice-12-lc@3,
    # fs/fhd-2mtp12-lc-os2-a@4 and fs/fhd-1mtp12-sc-os2-a@3, the first
    # cassette plan's whole reason for widening this file past `plan` -
    # joining the 13 that carry the `plan:`/`faces.plan` sugar instead. A
    # future rear or plan face bumps this again.
    # 23, not 18: the FHD polarity twins - fhd-1mtp6lcd-os2-af, -os2-u,
    # fhd-2mtp12-lc-os2-af, -os2-u and fhd-1mtp24-lc-os2-af - each declare
    # `faces.rear`, their Type A twins' bodies in Type AF or universal wiring.
    # 33, not 23: the ten FHD media twins - OM4 fhd-1mtp6lcd-om4-a, -om4-u,
    # fhd-2mtp12-lc-om4-a, -om4-u, fhd-1mtp24-lc-om4-a; OM5 fhd-1mtp6lcd-om5-a,
    # fhd-2mtp12-lc-om5-a, fhd-1mtp24-lc-om5-a; OM3 fhd-2mtp12-lc-om3-a,
    # fhd-1mtp24-lc-om3-a - each declare their OS2 twin's `faces.rear`.
    # 35, not 33: the 36-fibre pair, fhd-3mtp18-lc-os2-a and -om4-a, declare
    # fs/fhd-3mtp18-lc-rear@1.
    # 48, not 35: the thirteen FHD fibre adapter panels (fhd-fap12lcd-os2 and
    # its APC, OM4 and OM5 twins; fhd-fap18lcd-os2, -om4; fhd-fap6scd-apc-os2,
    # -os2, -om4; fhd-fap12mtp-a, -b, fhd-fap8mtp-b, fhd-fap12mtp16-a) each
    # declare a rear face - the adapters seen from behind. The modular panel
    # and the blank have none.
    # 49, not 48: ufispace/n3100-4c@1, a PCIe card, declares its plan face
    # ufispace/n3100-4c-plan@1 - the card seen from above in a riser slot.
    # 85, not 49: the 36 nvidia/ ConnectX card modules each declare the generic
    # card plan of their bracket height, common/pcie-card-plan@1 or -lp@1.
    # 97 since the R660's top view added twelve: four supplies, the BOSS-N1
    # module, six OCP cards and the shared 2.5 inch carrier.
    # 104 since its seven risers seen from above (2A, 2P, 2R, 3A, 3P, 3Q, 3R);
    # 106 since its LOM card and rear I/O board; 107 since riser 3S; 108 since
    # the liquid-cooling rear I/O board.
    # 109 since riser 2S; 112 since risers 2Q, 1P and 4P;
    # 114 since the HPE DL160 Gen10's two Flex Slot supplies;
    # 120 since the four Supermicro SYS-111E supplies and their two risers;
    # 125 since the Fibrain XCU10's drawer and the four SC adapter holders,
    # each of which declares its rear face.
    with_faces = [e for e in entries if e.get("faces")]
    assert len(with_faces) == 125, \
        f"expected exactly 125 of {len(entries)} entries to carry a faces " \
        f"key, found {len(with_faces)}"


def test_the_index_entry_omits_faces_when_there_are_none():
    """An empty dict on 700-odd entries is bytes on every page load.

    Reads the BUILT index, not the source that writes it - a source-text
    assertion passes against code that was rearranged and still emits `{}`.
    Skips when dist is absent so a bare checkout does not fail on it.
    """
    import json
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    entries = json.loads(f.read_text())["components"]
    empty = [e["name"] for e in entries if e.get("faces") == {}]
    assert not empty, f"these carry an empty faces object: {empty}"


def test_the_self_reference_check_is_reachable_from_a_real_lint_run(tmp_path):
    """L83's self-reference branch must fire from the CLI, not only from a unit test.

    It first shipped with `name=None` at the registration site, because the
    per-component loop was read as having nothing to build the component's own
    ref from. It has `f`: the contract path carries the namespace and the major.
    A rule branch that only its unit test can reach is dead code with a green
    test beside it, so this drives the actual binary over a throwaway library.
    """
    import subprocess
    d = tmp_path / "components" / "t" / "selfrear" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: selfrear\nversion: 1.0.0\n"
        "class: port\nsize: {w: 10, h: 10}\n"
        "faces:\n  rear: {ref: t/selfrear@1}\n")
    out = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/lint.py"),
         "--schemas", str(ROOT / "spec/schemas"), "--library", str(tmp_path)],
        capture_output=True, text=True).stdout
    assert "[L83]" in out and "its own rear" in out, out


CARDS = ["common/pcie-card-fh/v2", "common/pcie-card-lp/v1"]


@pytest.mark.parametrize("rel", CARDS)
def test_the_migrated_cards_use_the_new_spelling(rel):
    c = yaml.safe_load(
        (ROOT / "library/components" / rel / "contract.yaml").read_text())
    assert "plan" not in c, f"{rel} still carries the legacy top-level `plan:`"
    assert ((c.get("faces") or {}).get("plan") or {}).get("ref"), \
        f"{rel} lost its plan drawing in the migration"


# The eleven card risers that carry a plan drawing, BY NAME. `dell/` holds 25
# riser directories; the other fourteen are plates, shrouds, cage mounts and
# clips with no plan face at all, so a count over the glob would also be
# counting those. Naming them means a NEW riser card does not fail this test,
# and migrating one of these eleven does - which is the distinction the test is
# for.
LEGACY_RISERS = [
    "riser-1a-14g", "riser-1b-14g", "riser-1d-14g",
    "riser-2a-14g", "riser-2b-14g", "riser-2c-14g", "riser-2d-14g",
    "riser-2e-14g", "riser-2f-14g", "riser-3a-14g", "riser-3b-14g",
]


@pytest.mark.parametrize("riser", LEGACY_RISERS)
def test_the_risers_still_use_the_legacy_spelling(riser):
    """THE SUGAR IS LOAD-BEARING and this is what watches it.

    Eleven risers and one device depend on `plan:` continuing to mean
    `faces.plan`. If a later sweep migrates them, the fallback in
    `faces.face_ref` stops being exercised by anything real, and the thirteen
    components relying on it would be one refactor from breaking with nothing
    to say so. This fails loudly instead, naming the riser that moved.
    """
    # whichever major the riser is at: it is the spelling under test, not the path
    (path,) = (ROOT / "library/components/dell" / riser).glob("v*/contract.yaml")
    c = yaml.safe_load(path.read_text()) or {}
    assert (c.get("plan") or {}).get("ref"), \
        f"{riser} no longer carries the legacy `plan:` - if that was deliberate, " \
        "check something still exercises face_ref's fallback before removing it here"


def test_every_contract_in_the_library_passes_l82():
    """Nobody, anywhere, says it both ways."""
    bad = []
    for p in (ROOT / "library/components").glob("*/*/v*/contract.yaml"):
        c = yaml.safe_load(p.read_text()) or {}
        if (c.get("plan") or {}).get("ref") and \
                ((c.get("faces") or {}).get("plan") or {}).get("ref"):
            bad.append(str(p.relative_to(ROOT)))
    assert not bad, bad


def test_an_empty_faces_block_fails_schema_validation():
    """`faces:` with nothing under it passes L82, L83, and the index build -
    none of them have anything to object to, and the part is silently omitted
    from every viewer. The schema is the only layer left that can catch it,
    so `minProperties` on `faces` has to be the backstop.
    """
    import json
    import jsonschema
    schema = json.loads(
        (ROOT / "spec/schemas/component.schema.json").read_text())
    doc = {"format": 1, "kind": "component", "name": "t", "version": "1.0.0",
          "class": "port", "size": {"w": 1, "h": 1}, "faces": {}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema)
