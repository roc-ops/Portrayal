"""The FHD adapter panels keep the promises the FHD cassettes are held to.

The cassette guards (test_fhd_adapter_finish_follows_media,
test_fhd_adapter_rows_are_centred, test_fhd_cassettes_share_one_envelope) select
`class: cassette`, and the panels are `class: adapter-panel` because their depth
is not the cassette envelope's. Without this file none of the three promises
below would be checked on a panel at all.

- every adapter on one panel wears one finish, and a panel whose fibre is not
  OS2 sets one (the adapters' default is the OS2 blue);
- the connector block is centred on the 108.97 plate, as FS draws every panel
  (fhd-fiber-adapter-panels-datasheet.pdf pp5-9);
- every panel skin draws the same two thumb-knobs, mirrored about the plate.

Read from the contracts and skins themselves, so it cannot skip.
"""
import pathlib
import xml.etree.ElementTree as ET

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"


def _load(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / ns / name / f"v{major}" / "contract.yaml").read_text())


def _panels():
    out = []
    # the blank (fhd-fapb) is `class: blank`, and its plate and knobs are a
    # panel's all the same
    for contract in sorted((LIB / "fs").glob("fhd-fap*/v*/contract.yaml")):
        doc = yaml.safe_load(contract.read_text())
        if doc.get("kind") == "module" and doc.get("class") in ("adapter-panel", "blank"):
            out.append((f"fs/{doc['name']}@{contract.parent.name[1:]}", doc, contract.parent))
    assert len(out) >= 15, (
        f"only {len(out)} FHD adapter panels found - have they moved or been renamed?")
    return out


def test_every_panel_wears_one_finish_and_non_os2_sets_it():
    bad, coloured = [], 0
    for ref, doc, _ in _panels():
        parts = [p for p in doc.get("parts") or [] if "adapter" in p["ref"]]
        if not parts:
            continue
        finishes = {(p.get("attrs") or {}).get("housing-finish") for p in parts}
        if len(finishes) != 1:
            bad.append(f"{ref}: {len(parts)} adapters wear {len(finishes)} finishes")
            continue
        media = (doc.get("optical") or {}).get("media")
        if media and media != "os2" and finishes == {None}:
            bad.append(f"{ref}: {media} panel wears the OS2 default blue")
        coloured += finishes != {None}
    assert coloured >= 5, f"only {coloured} panels set a finish - is the field still read?"
    assert not bad, "\n".join(bad)


def test_every_panel_centres_its_connector_block():
    """HALF A MILLIMETRE, as the cassette check allows: FS's drawings put every
    block on the plate's centre line, and the 36F panel's pairs sit 0.125 off
    their drawn centres because the shared adapter is wider than drawn."""
    bad, seen = [], 0
    for ref, doc, _ in _panels():
        parts = doc.get("parts") or []
        if not parts:
            continue
        seen += 1
        centres = []
        for p in parts:
            size = _load(p["ref"])["size"]
            centres.append(p["at"][0] + size["w"] / 2)   # rotation keeps the centre
        mid = (min(centres) + max(centres)) / 2
        if abs(mid - doc["size"]["w"] / 2) > 0.5:
            bad.append(f"{ref}: block centred at {mid:.2f}, plate at {doc['size']['w'] / 2:.3f}")
    assert seen >= 14, seen
    assert not bad, "\n".join(bad)


def test_every_panel_draws_the_same_mirrored_thumb_knobs():
    knobs, bad = {}, []
    for ref, doc, d in _panels():
        root = ET.parse(d / "skins" / "default.svg").getroot()
        found = {}
        for el in root.iter():
            if el.get("id") in ("thumb-knob-left", "thumb-knob-right"):
                found[el.get("id")] = tuple(float(el.get(a)) for a in ("cx", "cy", "r"))
        if len(found) != 2:
            bad.append(f"{ref}: {sorted(found)}")
            continue
        l, r = found["thumb-knob-left"], found["thumb-knob-right"]
        if abs(l[0] + r[0] - doc["size"]["w"]) > 0.01 or l[1:] != r[1:]:
            bad.append(f"{ref}: knobs not mirrored {l} {r}")
        knobs.setdefault((l, r), []).append(ref)
    assert not bad, "\n".join(bad)
    assert len(knobs) == 1, {k: v for k, v in knobs.items()}


# THE FIRST MPO-FRONTED MODULES. A front MPO adapter is ONE DCIM port carrying
# a position per fibre - twelve one-fibre "mpo" ports named 1..12 would be a
# trunk nobody can cable (the #616 merge-queue review). Pinned per panel: the
# port count, the positions on each, and a fibre-map row for every position of
# every front port, landing on a port that exists.
MPO_FRONTS = {"fs/fhd-fap12mtp-a@1": (12, 12), "fs/fhd-fap12mtp-b@1": (12, 12),
              "fs/fhd-fap8mtp-b@1": (8, 12), "fs/fhd-fap12mtp16-a@1": (12, 16)}


def test_an_mpo_front_is_one_port_per_adapter():
    from portrayal import optical_ports as P
    for ref, (count, positions) in MPO_FRONTS.items():
        doc = _load(ref)
        got = P.ports(doc, _load)
        assert [p["type"] for p in got["front"]] == ["mpo"] * count, ref
        assert [p["positions"] for p in got["front"]] == [positions] * count, ref
        names = {p["name"] for p in got["front"]}
        rows = P.fibre_map(doc, _load, ref)["rows"]
        assert len(rows) == count * positions, (ref, len(rows))
        seen = {(r["front"], r["front_position"]) for r in rows}
        assert seen == {(n, i) for n in names for i in range(1, positions + 1)}, ref
