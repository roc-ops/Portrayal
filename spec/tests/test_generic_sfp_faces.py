"""The SFP faces that are not LC duplex: one LC (bidi). Same
envelope, same latch, a different face - and the face is in the name
(docs/pluggables-design.md decision 4).

generic/sfp-sc is GATED (no free document dimensions the SC opening - see the
ruling in spec A section 4). Only generic/sfp-lc-simplex is built here."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

# STANDARDS IS EMPTY ON A PLAIN IMPORT: lint.py fills it inside main(), so a
# rule called directly finds no entry for any `conforms` key and L9 reports an
# unknown key - or, worse, passes vacuously. Load it once, the way main does
# (the pattern spec/tests/test_pitch_lint.py established).
lint.STANDARDS.update(
    lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


# the live major of each generic read here - sfp-lc-simplex went to @2 when its
# bore moved to the duplex's RX position (2026-09-21)
MAJOR = {"sfp-lc": 1, "sfp-lc-simplex": 2}


def contract_path(name):
    return LIB / f"components/generic/{name}/v{MAJOR[name]}/contract.yaml"


def contract(name):
    return yaml.safe_load(contract_path(name).read_text())


def test_bidi_has_one_lc_bore_and_one_optical_point():
    d = contract("sfp-lc-simplex")
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert [p["ref"] for p in d["parts"]] == ["std/lc-bore@3"]
    assert "optical" in d["connection-points"]
    assert "optical-tx" not in d["connection-points"]


def test_both_share_the_sfp_envelope_and_protrude():
    lc = contract("sfp-lc")
    for name in ("sfp-lc-simplex",):
        d = contract(name)
        assert d["size"] == lc["size"], name
        body = next(f for f in d["relief"]["features"] if f["node"] == "body")
        assert body["out"] == next(f for f in lc["relief"]["features"] if f["node"] == "body")["out"]


def test_both_lint_clean():
    for name in ("sfp-lc-simplex",):
        p = contract_path(name)
        assert rule_errors(p, "L9", "L11", "L99") == [], name


# --- the simplex bore sits where the duplex's RX bore does ------------------
#
# Corrected in @2 on the maintainer's observation of real simplex parts,
# 2026-09-21 (no document or photograph in the corpus shows it - see
# provenance.bores). Everything here is read off the two contracts and their
# compiles, so the duplex part stays the one source for where RX is.

def _compiled(ref):
    from portrayal import render
    lib = render.Library([str(LIB)])
    g, _ = render.instance_group(lib, ref, "t", [0, 0], None, None, None, None,
                                 skin_name="default", palette={}, resolved={})
    return {n.get("id"): n for n in g.iter() if n.get("id")}


def test_the_simplex_bore_is_the_duplex_rx_bore():
    duplex, simplex = contract("sfp-lc"), contract("sfp-lc-simplex")
    rx = next(p for p in duplex["parts"] if p["id"] == "rx")
    (bore,) = simplex["parts"]
    assert bore["ref"] == rx["ref"]
    assert bore["at"] == rx["at"], (
        f"the simplex bore is at {bore['at']}; the duplex RX bore is at {rx['at']}")
    assert bore["rotate"] == rx["rotate"] and bore["lift"] == rx["lift"]
    # its optical point is the duplex's optical-rx, and the module's own mate
    # into its cage did not move with it
    assert (simplex["connection-points"]["optical"]["at"]
            == duplex["connection-points"]["optical-rx"]["at"])
    assert (simplex["connection-points"]["mate"]
            == duplex["connection-points"]["mate"])


def test_the_simplex_hole_is_the_duplex_rx_hole():
    """The compiled face's evenodd path: its second subpath (the one hole) is
    exactly the duplex face's third (the RX hole, after the outline and TX)."""
    import re

    def holes(ref):
        d = _compiled(ref)["t--body"].get("d")
        return [" ".join(s.split()) for s in re.findall(r"M[^M]*", d)]

    duplex = holes("generic/sfp-lc@1")
    simplex = holes("generic/sfp-lc-simplex@2")
    assert len(duplex) == 3 and len(simplex) == 2, (len(duplex), len(simplex))
    assert simplex[0] == duplex[0], "the module outline changed"
    assert simplex[1] == duplex[2], (
        f"the simplex hole {simplex[1]!r} is not the duplex RX hole {duplex[2]!r}")
    assert simplex[1] != duplex[1], "the hole is the TX one"
