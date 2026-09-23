"""Every FS FHD cassette is the same box, so every contract must say the same box.

FHD is a format before it is a product: a cassette is whatever fits a bay of an
FHD enclosure, and FS draws every one of them on the same dimension line - 4.29
x 1.38 x 4.64 in, 108.97 x 35.05 x 117.86 mm. What differs between two cassettes
is what is mounted on the plate and what runs behind it, never the envelope.

WHAT IT COST. fs/fhd-1mtp6lcd-os2-a, the first cassette modelled, read its
depth line as 4.34in and carried 110.24 mm. Its AF and universal twins were
modelled later from FS's product pages and carried 117.86 - three contracts for
one body, two depths, and nothing compared them. The wrong figure was then
borrowed whole by the splice cassette, and the SC cassette's contract, reading
its own correct 4.64in beside it, explained the difference as an SC body being
genuinely deeper. The misreading sat beside six correct siblings for as long as
the family has existed; a check that asked them to agree would have found it
on the day the second one arrived.

Read from the contracts themselves, not the build, so it cannot skip.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
FS = ROOT / "library" / "components" / "fs"


def _cassettes():
    out = []
    for contract in sorted(FS.glob("fhd-*/v*/contract.yaml")):
        doc = yaml.safe_load(contract.read_text())
        if doc.get("kind") == "module" and doc.get("class") == "cassette":
            out.append((f"fs/{doc['name']}@{contract.parent.name[1:]}", doc))
    return out


def test_every_fhd_cassette_declares_the_same_envelope():
    cassettes = _cassettes()
    assert len(cassettes) >= 10, (
        f"only {len(cassettes)} FHD cassettes were found, so this is not measuring "
        "the family it was written for - have they moved or been renamed?")

    envelopes = {}
    for ref, doc in cassettes:
        size = doc.get("size") or {}
        # TO A TENTH OF A MILLIMETRE: 4.64in is 117.856, and a contract that
        # writes it that way is the same box as one that writes 117.86. The
        # misreading this exists for was 7.62 mm; precision is not the question.
        box = tuple(None if size.get(k) is None else round(size[k], 1) for k in "whd")
        envelopes.setdefault(box, []).append((ref, size))

    assert len(envelopes) == 1, (
        "FHD cassettes disagree about the box they all are:\n  " + "\n  ".join(
            f"w {members[0][1].get('w')} x h {members[0][1].get('h')} x d "
            f"{members[0][1].get('d')}: {', '.join(ref for ref, _ in members)}"
            for members in sorted(envelopes.values(), key=len, reverse=True)))


def test_every_fhd_cassette_body_is_as_deep_as_its_size_says():
    bad = []
    for ref, doc in _cassettes():
        d = (doc.get("size") or {}).get("d")
        body = (doc.get("body") or {}).get("depth")
        if body != d:
            bad.append(f"{ref}: size.d {d} but body.depth {body}")
    assert not bad, "a cassette whose body and size disagree:\n  " + "\n  ".join(bad)


# A CASSETTE THAT DRAWS NO THUMB-KNOBS SAYS WHY HERE. Every other FHD cassette
# face carries the same pair, so a new one without them is a skin copied from
# the wrong place, not a different product.
NO_KNOBS = {
    "fs/fhd-splice-12-lc@2": "no render of this SKU exists to draw them from; "
                             "its contract records the gap",
}


def _knobs(ref, doc, contract_dir):
    import xml.etree.ElementTree as ET
    out = {}
    for skin in doc.get("skins") or []:
        root = ET.parse(contract_dir / "skins" / f"{skin}.svg").getroot()
        found = {}
        for el in root.iter():
            if el.get("id") in ("thumb-knob-left", "thumb-knob-right"):
                found[el.get("id")] = tuple(float(el.get(a)) for a in ("cx", "cy", "r"))
        out[f"{ref} skin {skin}"] = found
    return out


def test_every_fhd_cassette_draws_the_same_thumb_knobs():
    """THE KNOBS ARE ONE PART, drawn the same on every FHD cassette face.

    They were placed by eye on the first cassette and copied into eight more,
    2.8 mm inboard and 1 mm small, and nothing compared them; when they were
    measured, every copy had to be found by hand. A skin copied before a
    correction carries the old circles, and this is what notices.
    """
    skins = {}
    for contract in sorted(FS.glob("fhd-*/v*/contract.yaml")):
        doc = yaml.safe_load(contract.read_text())
        if doc.get("kind") != "module" or doc.get("class") != "cassette":
            continue
        ref = f"fs/{doc['name']}@{contract.parent.name[1:]}"
        if ref in NO_KNOBS:
            continue
        for name, found in _knobs(ref, doc, contract.parent).items():
            skins[name] = (found, doc["size"]["w"])

    assert len(skins) >= 9, (
        f"only {len(skins)} FHD cassette skins were checked, so this is not "
        "measuring the family it was written for")

    missing = [n for n, (found, _w) in skins.items() if len(found) != 2]
    assert not missing, (
        "an FHD cassette skin without both thumb-knobs (draw them, or say why "
        "in NO_KNOBS):\n  " + "\n  ".join(missing))

    # MIRRORED ABOUT THE PLATE'S CENTRE: the right knob is the left one
    # reflected, so their centres add up to the plate width.
    lopsided = [f"{n}: left cx {f['thumb-knob-left'][0]} + right cx "
                f"{f['thumb-knob-right'][0]} != w {w}"
                for n, (f, w) in skins.items()
                if abs(f["thumb-knob-left"][0] + f["thumb-knob-right"][0] - w) > 0.01]
    assert not lopsided, "thumb-knobs not mirrored:\n  " + "\n  ".join(lopsided)

    pairs = {}
    for n, (f, _w) in skins.items():
        pairs.setdefault((f["thumb-knob-left"], f["thumb-knob-right"]), []).append(n)
    assert len(pairs) == 1, (
        "FHD cassette skins disagree about the thumb-knobs (cx, cy, r):\n  "
        + "\n  ".join(f"left {k[0]} right {k[1]}: {', '.join(v)}"
                      for k, v in sorted(pairs.items(), key=lambda kv: -len(kv[1]))))


def test_a_cassette_excused_from_thumb_knobs_exists_and_draws_none():
    """An exemption outlives its reason silently unless something reads it back."""
    stale = []
    for ref in NO_KNOBS:
        name, major = ref[len("fs/"):].split("@")
        contract = FS / name / f"v{major}" / "contract.yaml"
        if not contract.exists():
            stale.append(f"{ref}: no such component")
            continue
        doc = yaml.safe_load(contract.read_text())
        drawn = [n for n, found in _knobs(ref, doc, contract.parent).items() if found]
        if drawn:
            stale.append(f"{ref}: draws thumb-knobs after all ({', '.join(drawn)})")
    assert not stale, "NO_KNOBS is out of date:\n  " + "\n  ".join(stale)
