"""The four Cisco 400G Combo line cards mark each SFP cage SFP+ or SFP28.

Cisco's Ethernet Line Card Installation Guide, section "400G Combo Multi-Rate Line
Card", splits the 40 SFP cages by port number: ports 0-5, 10-15, 20-25 and 30-35 take
10GE SFP+ modules, ports 6-9, 16-19, 26-29 and 36-39 take 10GE/25GE SFP28 modules, and
ports 40-43 take QSFP+ or QSFP28. The cages are placed with ids p0 to p43 in the guide's
numbers, so each SFP placement carries its `media` by id.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "library/components/cisco"
DIST = ROOT / "library/dist/components"

CARDS = ["a9k-4hg-flex-se", "a9k-4hg-flex-tr", "a99-4hg-flex-se", "a99-4hg-flex-tr"]

SFP_PLUS = [i for lo in (0, 10, 20, 30) for i in range(lo, lo + 6)]
SFP28 = [i for lo in (6, 16, 26, 36) for i in range(lo, lo + 4)]
QSFP = [40, 41, 42, 43]


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v2/contract.yaml").read_text())


def media_by_id(name):
    return {p["id"]: (p.get("attrs") or {}).get("media") for p in contract(name)["parts"]}


@pytest.mark.parametrize("name", CARDS)
def test_each_sfp_cage_carries_the_media_the_guide_gives_its_port(name):
    got = media_by_id(name)
    assert len(got) == 44
    assert {f"p{i}": "sfp-plus" for i in SFP_PLUS} == {k: v for k, v in got.items() if v == "sfp-plus"}
    assert {f"p{i}": "sfp28" for i in SFP28} == {k: v for k, v in got.items() if v == "sfp28"}
    assert len(SFP_PLUS) == 24 and len(SFP28) == 16


@pytest.mark.parametrize("name", CARDS)
def test_the_qsfp_four_are_left_as_they_were(name):
    got = {p["id"]: p for p in contract(name)["parts"]}
    for i in QSFP:
        assert got[f"p{i}"]["ref"] == "std/qsfp-ganged@1"
        assert "media" not in (got[f"p{i}"].get("attrs") or {})


@pytest.mark.parametrize("name", CARDS)
def test_the_media_counts_equal_the_cards_own_port_counts(name):
    c = contract(name)
    counts = {}
    for m in media_by_id(name).values():
        counts[m] = counts.get(m, 0) + 1
    assert counts.get("sfp-plus") == c["attrs"]["sfp-plus"] == 24
    assert counts.get("sfp28") == c["attrs"]["sfp28"] == 16
    assert c["attrs"]["qsfp28"] == 4


@pytest.mark.parametrize("name", CARDS)
def test_a_provenance_entry_cites_the_guides_section(name):
    prov = contract(name)["provenance"]
    assert "media" in prov
    text = " ".join(str(prov["media"]).split())
    assert "400G Combo Multi-Rate Line Card" in text
    assert "page 52" in text


@pytest.mark.parametrize("name", CARDS)
def test_the_built_skin_marks_the_cages_by_the_same_ids(name):
    skin = DIST / f"cisco--{name}--v2--default.svg"
    assert skin.exists(), "run a build first: this reads library/dist"
    svg = skin.read_text()
    found = {}
    for tag in re.findall(r"<[^>]*\bdata-media=[^>]*>", svg):
        ident = re.search(r'\bid="([^"]+)"', tag)
        media = re.search(r'\bdata-media="([^"]+)"', tag)
        if ident:
            found[ident.group(1)] = media.group(1)
    want = {f"p{i}": "sfp-plus" for i in SFP_PLUS}
    want.update({f"p{i}": "sfp28" for i in SFP28})
    got = {k.split("--")[-1] if "--" in k else k: v for k, v in found.items()}
    for pid, media in want.items():
        matches = [v for k, v in found.items() if k == pid or k.endswith(f"-{pid}")]
        assert matches == [media], f"{name} {pid}: skin says {matches}, want {media}"
    assert got is not None
