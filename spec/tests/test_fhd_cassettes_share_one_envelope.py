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
