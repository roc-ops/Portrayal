"""A cassette's LC adapters wear one colour, and it is the colour of its fibre.

`common/lc-duplex-v-adapter@4` and `common/lc-duplex-shuttered-adapter@1` draw
their housing from a `housing-finish` field (OS2 blue by default), and each cassette in another fibre sets it on every
adapter it composes - six or twelve `attrs:` lines stating one fact, beside the
`optical.media` that states it again in words. Nothing else ties them together,
so an edit that re-measures the colour and misses one line ships a mottled
plate, and a new OM4 cassette that forgets the field ships blue.

Three promises, read from the contracts so the check cannot skip:
- every adapter on one cassette carries the same finish;
- a cassette whose fibre is not OS2 sets one (the default is the OS2 blue);
- an OS2 cassette does not, because the default IS its colour.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
FS = ROOT / "library" / "components" / "fs"
ADAPTERS = ("common/lc-duplex-v-adapter@", "common/lc-duplex-shuttered-adapter@")


def _cassettes():
    for contract in sorted(FS.glob("fhd-*/v*/contract.yaml")):
        doc = yaml.safe_load(contract.read_text())
        parts = [p for p in doc.get("parts") or [] if str(p.get("ref", "")).startswith(ADAPTERS)]
        if doc.get("class") == "cassette" and parts:
            yield f"fs/{doc['name']}@{contract.parent.name[1:]}", doc, parts


def test_every_fhd_adapter_wears_its_fibres_colour():
    seen = coloured = 0
    bad = []
    for ref, doc, parts in _cassettes():
        seen += 1
        media = (doc.get("optical") or {}).get("media")
        finishes = {(p.get("attrs") or {}).get("housing-finish") for p in parts}
        if len(finishes) != 1:
            bad.append(f"{ref}: its {len(parts)} adapters wear {len(finishes)} finishes "
                       f"{sorted(map(str, finishes))}")
            continue
        finish = finishes.pop()
        coloured += finish is not None
        if media != "os2" and finish is None:
            bad.append(f"{ref}: media {media} but its adapters wear the OS2 default blue - "
                       "set `housing-finish` on each")
        if media == "os2" and finish is not None:
            bad.append(f"{ref}: OS2, whose colour is the field's default, yet sets {finish}")

    assert not bad, "FHD adapter colour does not follow the fibre:\n  " + "\n  ".join(bad)
    assert seen >= 15 and coloured >= 10, (
        f"reached {seen} FHD LC cassettes, {coloured} of them coloured - this is not "
        "measuring the family it was written for")
