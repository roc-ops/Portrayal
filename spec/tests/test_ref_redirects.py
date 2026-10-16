"""A replaced part leaves a redirect (#1049): `supersedes:` on the replacement.

A saved rack names a part by ref. When a major is removed the ref no longer
resolves, and the rack quietly loses the part. The library therefore lets the
REPLACEMENT say which removed refs it stands in for, and record a signature of
what the removed part published: its slots, the ids of its parts, its faces and
its fibre paths. The signature is the proof that the replacement is a drop-in
(same part ids, port paths and names); it is recomputed from the replacement at
every build, so a later edit that breaks the drop-in is refused.

These tests hold the signature (what it covers and what it leaves out), the
build check, the lint rule (L184) and the live Fibrain pairs.
"""
import copy
import json
from pathlib import Path

import pytest
import yaml

import libdata
from portrayal import lint as L
from portrayal import redirects as R

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
LIB = [str(ROOT / "library")]

ENTRY = {
    "ns": "acme", "name": "holder", "major": "v2", "version": "2.0.0", "kind": "module", "class": "adapter-panel",
    "attrs": {"model": "H-12"}, "description": "A holder.", "size": {"w": 100, "h": 21, "d": 37},
    "fields": {"label": {"type": "text"}},
    "elements": ["body", "label"],
    "faces": {"rear": "acme/holder-rear@2"},
    "bays": {},
    "parts": [{"id": "lc01", "ref": "acme/adapter@1", "at": [1, 2]}, {"id": "lc02", "ref": "acme/adapter@1", "at": [3, 4]}],
    "cages": [
        {"id": "lc01", "interface": "lc-duplex", "kind": "connector", "media": None, "bores": ["1", "2"],
         "accepts": ["acme/cap@2", "acme/plug@2"], "default": "acme/cap@2", "at": [5.1, -1.0], "mate": [9.7, 7.0], "rotate": 0, "lift": 1.2},
        {"id": "lc02", "interface": "lc-duplex", "kind": "connector", "media": None, "bores": ["1", "2"],
         "accepts": ["acme/plug@2", "acme/cap@2"], "default": "acme/cap@2", "at": [21.2, -1.0], "mate": [25.8, 7.0], "rotate": 0, "lift": 1.2},
    ],
    "optical": {"media": "os2", "front-order": ["lc01", "lc02"], "paths": [{"from": "lc01.1", "to": "rear:b01.1"}]},
}


def changed(**edits):
    e = copy.deepcopy(ENTRY)
    for k, v in edits.items():
        e[k] = v
    return e


# --- the signature --------------------------------------------------------

def test_a_signature_is_a_sha256_string():
    s = R.signature(ENTRY)
    assert s.startswith("sha256:") and len(s) == len("sha256:") + 64


@pytest.mark.parametrize("what,entry", [
    ("a version bump", changed(version="2.1.0", major="v3")),
    ("a moved port", changed(cages=[dict(c, at=[c["at"][0] + 4.7, c["at"][1]], mate=[c["mate"][0] + 4.7, c["mate"][1]]) for c in ENTRY["cages"]])),
    ("a new size", changed(size={"w": 101, "h": 21, "d": 37})),
    ("a new description", changed(description="Another sentence.")),
    ("a different adapter ref under the same part ids", changed(parts=[dict(p, ref="acme/other@1") for p in ENTRY["parts"]])),
    ("the order of accepts", changed(cages=[dict(c, accepts=sorted(c["accepts"], reverse=True)) for c in ENTRY["cages"]])),
    ("a rear face at a new major", changed(faces={"rear": "acme/holder-rear@3"})),
])
def test_the_signature_leaves_out_what_a_drop_in_may_change(what, entry):
    assert R.signature(entry) == R.signature(ENTRY), what


@pytest.mark.parametrize("what,entry", [
    ("a renamed port", changed(cages=[dict(ENTRY["cages"][0], id="lc09"), ENTRY["cages"][1]])),
    ("a port lost", changed(cages=ENTRY["cages"][:1])),
    ("a renamed part", changed(parts=[dict(ENTRY["parts"][0], id="lcX"), ENTRY["parts"][1]])),
    ("an interface", changed(cages=[dict(c, interface="sc-duplex") for c in ENTRY["cages"]])),
    ("what a port accepts", changed(cages=[dict(c, accepts=["acme/cap@2"]) for c in ENTRY["cages"]])),
    ("a default", changed(cages=[dict(c, default=None) for c in ENTRY["cages"]])),
    ("a bore", changed(cages=[dict(c, bores=["1"]) for c in ENTRY["cages"]])),
    ("a fibre path", changed(optical={"media": "os2", "front-order": ["lc01", "lc02"], "paths": [{"from": "lc01.1", "to": "rear:b02.1"}]})),
    ("a lost face", changed(faces={})),
    ("a class", changed(**{"class": "other"})),
    ("a bay", changed(bays={"bay-1": {"accepts": ["acme/x@1"]}})),
    ("a field", changed(fields={})),
    ("an element", changed(elements=["body"])),
])
def test_the_signature_covers_what_a_saved_rack_names(what, entry):
    assert R.signature(entry) != R.signature(ENTRY), what


def test_a_part_with_nothing_to_say_still_signs():
    assert R.signature({"ns": "a", "name": "b", "major": "v1"}).startswith("sha256:")


# --- the build check ------------------------------------------------------

def published(*extra):
    old = copy.deepcopy(ENTRY)
    new = changed(version="2.0.0", major="v2", name="holder")
    new["supersedes"] = [{"ref": "acme/holder@1", "signature": R.signature(old), "from": "0123abc"}]
    return [new, *extra]


def test_a_matching_signature_is_clean():
    assert R.problems(published()) == []


def test_a_replacement_that_is_no_longer_a_drop_in_is_named():
    new = published()[0]
    new["cages"] = new["cages"][:1]
    out = R.problems([new])
    assert len(out) == 1 and "acme/holder@2" in out[0] and "acme/holder@1" in out[0] and "drop-in" in out[0], out


def test_a_removed_ref_that_is_still_published_is_not_a_redirect():
    live = changed(major="v1", version="1.0.0")
    out = R.problems(published(live))
    assert len(out) == 1 and "acme/holder@1" in out[0] and "still in the library" in out[0], out


def test_two_replacements_claiming_one_ref_are_refused():
    a, = published()
    b = copy.deepcopy(a)
    b["name"], b["major"] = "other", "v1"
    out = R.problems([a, b])
    assert len(out) == 1 and "acme/holder@1" in out[0] and "two" in out[0], out


def test_a_redirect_loop_is_refused():
    a = {"ns": "x", "name": "a", "major": "v2", "supersedes": [{"ref": "x/b@1", "signature": R.signature({"ns": "x", "name": "a", "major": "v2"}), "from": "abc1234"}]}
    b = {"ns": "x", "name": "b", "major": "v1", "supersedes": [{"ref": "x/a@2", "signature": R.signature({"ns": "x", "name": "b", "major": "v1"}), "from": "abc1234"}]}
    out = R.problems([a, b])
    assert any("loop" in m for m in out), out


def test_the_table_maps_each_removed_ref_to_its_replacement():
    assert R.table(published()) == {"acme/holder@1": "acme/holder@2"}


# --- the lint rule --------------------------------------------------------

def lint(doc, path="library/components/acme/holder/v2/contract.yaml", lib=LIB):
    with L.collecting() as found:
        L.lint_component_supersedes(path, doc, lib)
    return [e for e in found.errors if "[L184]" in e]


def good(**over):
    s = {"ref": "acme/gone@1", "signature": "sha256:" + "0" * 64, "from": "0123abc"}
    s.update(over)
    return {"name": "holder", "supersedes": [s]}


def test_a_well_formed_supersedes_is_clean():
    assert lint(good()) == []


def test_a_contract_with_no_supersedes_is_clean():
    assert lint({"name": "holder"}) == []


@pytest.mark.parametrize("what,doc,words", [
    ("a ref with no major", good(ref="acme/gone"), "ns/name@major"),
    ("a self-pointer", good(ref="acme/holder@2"), "itself"),
    ("a bad signature", good(signature="abc"), "sha256"),
    ("an upper-case signature", good(signature="sha256:" + "A" * 64), "sha256"),
    ("no commit", good(**{"from": ""}), "from"),
    ("a duplicate", {"name": "holder", "supersedes": [good()["supersedes"][0], good()["supersedes"][0]]}, "twice"),
    ("a live part", good(ref="juniper/mic-3d-20ge-sfp-v@1"), "still in the library"),
])
def test_a_malformed_supersedes_is_an_error(what, doc, words):
    out = lint(doc)
    assert out and any(words in e for e in out), (what, out)


def test_the_rule_is_catalogued():
    assert "L184" in L.RULES


# --- the live library -----------------------------------------------------

def pairs():
    out = []
    for ref, path, doc in libdata.components():
        for s in doc.get("supersedes") or []:
            out.append((f"{ref}@{path.parent.name[1:]}", s))
    return out


def test_the_forty_fibrain_refs_of_1046_are_redirected():
    got = {old: new for new, s in pairs() for old in [s["ref"]]}
    want = {}
    for name in sorted(p.name for p in (ROOT / "library/components/fibrain").iterdir()
                       if p.name.startswith(("xmi", "xmn"))):
        want[f"fibrain/{name}@1"] = f"fibrain/{name}@2"
    assert got == want and len(want) == 40, sorted(set(want) ^ set(got))


def test_no_redirect_names_a_ref_the_library_still_has():
    live = {f"{r}@{p.parent.name[1:]}" for r, p, _ in libdata.components()}
    assert [s["ref"] for _, s in pairs() if s["ref"] in live] == []


def test_every_recorded_signature_matches_the_published_replacement():
    components = json.loads((DIST / "components.json").read_text())["components"]
    assert R.problems(components) == []
    by_ref = {f"{c['ns']}/{c['name']}@{c['major'].lstrip('v')}": c for c in components}
    for new, s in pairs():
        assert by_ref[new]["supersedes"][0]["ref"] == s["ref"]
        assert R.signature(by_ref[new]) == s["signature"], new


def test_the_published_entry_carries_supersedes_on_every_row():
    components = json.loads((DIST / "components.json").read_text())["components"]
    assert all(isinstance(c.get("supersedes"), list) for c in components)
    assert sum(1 for c in components if c["supersedes"]) == 40


def test_the_redirect_table_of_the_live_library_has_forty_hops_and_no_chain():
    components = json.loads((DIST / "components.json").read_text())["components"]
    t = R.table(components)
    assert len(t) == 40 and not set(t) & set(t.values())


def test_the_schema_has_the_key():
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    assert "supersedes" in schema["properties"]
    assert yaml  # keep the import honest for the contracts read above


# --- the kit's package ----------------------------------------------------

def test_the_kit_ships_the_resolver():
    pkg = json.loads((ROOT / "kit/package.json").read_text())
    assert pkg["exports"]["./redirects"] == "./redirects.js"
    assert "node --check redirects.js" in pkg["scripts"]["test"]
    assert (ROOT / "kit/redirects.js").exists()
    assert "| `redirects.js` |" in (ROOT / "kit/README.md").read_text()


def test_the_kit_version_is_the_one_the_changelog_names():
    pkg = json.loads((ROOT / "kit/package.json").read_text())
    assert pkg["version"] == "0.50.0"
    assert "0.50.0" in (ROOT / "changelog.d/body-piece-sides.md").read_text()
    assert "0.50.0" in (ROOT / "changelog.d/two-slot-bays.md").read_text()
    assert "0.49.0" in (ROOT / "changelog.d/overlay-library.md").read_text()
    assert "0.48.0" in (ROOT / "changelog.d/xcu-couplers.md").read_text()
    assert "0.47.0" in (ROOT / "changelog.d/display-content.md").read_text()
    assert "0.46.0" in (ROOT / "changelog.d/seated-end-refused.md").read_text()
    assert "0.45.0" in (ROOT / "changelog.d/settable-lamps.md").read_text()
    assert "0.44.0" in (ROOT / "changelog.d/zero-u-module-ports.md").read_text()
    assert "0.43.0" in (ROOT / "changelog.d/relief-batched.md").read_text()
    assert "0.42.0" in (ROOT / "changelog.d/zero-u-pdu-cord-route.md").read_text()
    assert "0.41.0" in (ROOT / "changelog.d/relief-id-lookups.md").read_text()
    assert "0.40.0" in (ROOT / "changelog.d/estimated-duct-capacity.md").read_text()
    assert "0.39.0" in (ROOT / "changelog.d/spare-in-ducts-fixes.md").read_text()
    assert "0.38.0" in (ROOT / "changelog.d/zero-u-cable-ends.md").read_text()
    assert "0.37.0" in (ROOT / "changelog.d/agent-findings.md").read_text()
    assert "0.36.0" in (ROOT / "changelog.d/manager-pass-through.md").read_text()
    assert "0.35.0" in (ROOT / "changelog.d/spare-in-ducts.md").read_text()


# --- the device lock ------------------------------------------------------

def test_a_redirect_does_not_re_lock_the_devices_that_seat_the_part(tmp_path):
    """`supersedes` names removed refs; it draws nothing, so the digest a device
    lock records for a component does not move when one is added or changed."""
    from portrayal import devicelock
    (tmp_path / "skins").mkdir()
    (tmp_path / "skins" / "default.svg").write_text("<svg/>")
    base = {"name": "holder", "version": "2.0.0", "size": {"w": 1, "h": 1, "d": 1}}
    claim = {"ref": "acme/holder@1", "signature": "sha256:" + "0" * 64, "from": "0123abc"}
    a = devicelock._component_digest(tmp_path, base)
    assert devicelock._component_digest(tmp_path, {**base, "supersedes": [claim]}) == a
    assert devicelock._component_digest(tmp_path, {**base, "supersedes": [dict(claim, ref="acme/holder@0")]}) == a
    assert devicelock._component_digest(tmp_path, {**base, "size": {"w": 2, "h": 1, "d": 1}}) != a
