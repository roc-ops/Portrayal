"""The RJ45 family: two bare jacks, two lamped ones (docs/rj45-family-design.md).

Every figure here is from TE customer drawing 1734264 rev A2 unless a test says
otherwise. The drawings are under working/intake/standards/rj45/ and are not
committed; the numbers are.
"""
import pathlib
import re
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))
import lint  # noqa: E402

STANDARDS = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

BODY = (11.91, 6.83)
SHOULDER = (6.30, 1.69)
SLOT_W = 4.06


def test_the_rj45_registry_entry_is_the_housing_from_te_1734264():
    r = STANDARDS["rj45"]
    assert (r["w"], r["h"], r["depth"]) == (15.8, 13.2, 18.6)
    assert r["confidence"] == "drawing"
    assert r["depth-confidence"] == "drawing"
    assert "1734264" in r["registry"]
    assert r["cavity"] == {"w": 11.91, "h": 11.2}


def test_the_registry_carries_the_three_tiers():
    for key in ("rj45", "rj45-ganged"):
        tiers = STANDARDS[key]["tiers"]
        assert [t["name"] for t in tiers] == ["body", "shoulder", "slot"]
        assert (tiers[0]["w"], tiers[0]["h"]) == BODY
        assert (tiers[1]["w"], tiers[1]["h"]) == SHOULDER
        assert tiers[2]["w"] == SLOT_W and "h" not in tiers[2], "the slot runs to the edge; no height is sourced"


def test_the_ganged_cell_keeps_its_measured_face_and_gains_the_tiers():
    g = STANDARDS["rj45-ganged"]
    assert (g["w"], g["h"]) == (12.7, 11.0)
    assert g["confidence"] == "measured"
    assert g["cavity"] == {"w": 11.91, "h": 10.5}
    assert g["depth"] == 18.6
    assert g["depth-confidence"] == "drawing"


def contract(ref):
    nsname, major = ref.rsplit("@", 1)
    return yaml.safe_load((LIB / "components" / nsname / f"v{major}" / "contract.yaml").read_text())


def skin(ref, name="default"):
    nsname, major = ref.rsplit("@", 1)
    return (LIB / "components" / nsname / f"v{major}" / "skins" / f"{name}.svg").read_text()


def cavity_path(ref):
    m = re.search(r'id="cavity"[^>]*\bd="([^"]+)"', skin(ref), re.S)
    assert m, "no cavity path"
    return m.group(1)


def tier_widths(d):
    """The horizontal runs of an evenodd cavity path, largest first. A three-tier
    opening drawn as one outline has runs of the body, shoulder and slot widths."""
    runs = {abs(float(x)) for x in re.findall(r"h\s*(-?[\d.]+)", d)}
    return sorted(runs, reverse=True)


def test_std_rj45_v2_is_the_housing():
    c = contract("std/rj45@2")
    assert c["version"].startswith("2.")
    assert c["size"] == {"w": 15.8, "h": 13.2, "d": 18.6}
    assert c["conforms"] == "rj45" and c["interface"] == "rj45"
    assert c["elements"]["opening"]["class"] == "cutout"
    assert c["relief"]["cavity"] == "cavity"
    assert c["relief"]["size"] == {"w": 11.91, "h": 11.2}
    assert c["connection-points"]["mate"] == {"at": [7.9, 6.6], "direction": "front"}
    assert "1734264" in yaml.safe_dump(c["provenance"])


def test_std_rj45_v2_cavity_has_three_tiers():
    """Body 11.91; shoulder 6.30 drawn as two 2.805 steps in from the body;
    slot 4.06 reached by two 1.12 steps in from the shoulder (TE 1734264)."""
    widths = tier_widths(cavity_path("std/rj45@2"))
    assert 11.91 in widths and 4.06 in widths, widths
    assert 2.805 in widths and 1.12 in widths, widths
    assert round(11.91 - 2 * 2.805, 2) == 6.3
    assert round(6.3 - 2 * 1.12, 2) == 4.06


def test_std_rj45_v2_lints_clean(tmp_path):
    p = LIB / "components/std/rj45/v2/contract.yaml"
    import jsonschema, json
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    lint.ERRORS.clear(); lint.WARNINGS.clear()
    if not lint.STANDARDS:
        lint.STANDARDS.update(STANDARDS)
    data = lint.lint_component(p, jsonschema.Draft202012Validator(schema))
    lint._skin_checks(p, data)        # L3 (every element id in the skin) and L4 (viewBox = size)
    assert not [e for e in lint.ERRORS if "[L9]" in e or "[L1]" in e or "[L3]" in e or "[L4]" in e], lint.ERRORS


def test_std_rj45_ganged_v2_is_the_cell():
    c = contract("std/rj45-ganged@2")
    assert c["size"] == {"w": 12.7, "h": 11.0, "d": 18.6}
    assert c["conforms"] == "rj45-ganged" and c["interface"] == "rj45"
    assert c["relief"]["size"] == {"w": 11.91, "h": 10.5}
    assert c["connection-points"]["mate"] == {"at": [6.35, 5.1], "direction": "front"}
    widths = tier_widths(cavity_path("std/rj45-ganged@2"))
    assert 11.91 in widths and 4.06 in widths and 2.805 in widths and 1.12 in widths, widths


def test_the_v1_jacks_no_longer_claim_the_standard():
    """They keep drawing until the sweeps retire them, but they were the 16 x 14
    aperture and must not assert conformance to a housing they are not."""
    assert "conforms" not in contract("std/rj45@1")
    assert "conforms" not in contract("std/rj45-ganged@1")
