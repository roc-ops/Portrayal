"""FS centres the adapter row on every FHD cassette plate, so ours must be too.

Measured from the plate's true edges, FS's rows are symmetric on every face-on
cassette render staged: the first housing starts 17.07-17.36 mm from the left
edge and the last ends 17.14-17.38 mm from the right, on the 12-fibre, 24-fibre
and SC plates alike (57016.main, 57017.B, 182642.g1, 57341.B, 182644.g1,
57058.main).

WHAT IT COST. `panel_measure.plate()` took the plate's left edge from the first
row of its dark band, which on these renders lies on the rounded top corner,
1.25-1.53 mm inboard of the real edge. Every adapter measured with it came out
that much too far left - rows at 15.8 / 19.2, a 3.4 mm asymmetry FS never drew -
and the check that "proved" the method compared it with a skin the same tool had
produced, so the two agreed to the hundredth. Asking the row to be centred needs
no image and no tool, and it fails on the old contracts.

HALF A MILLIMETRE, because the rows are measured to about one pixel (0.17 mm on
a 5.8 px/mm render) at each end, and a housing's detected width runs up to a
pixel over its 9.28. The defect this exists for was 3.4 mm.

Read from the contracts themselves, not the build, so it cannot skip.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"


def _contract(ref):
    name, major = ref.split("@")
    p = LIB / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def _rows():
    out = []
    for path in sorted((LIB / "fs").glob("fhd-*/v*/contract.yaml")):
        doc = yaml.safe_load(path.read_text())
        if doc.get("kind") != "module" or doc.get("class") != "cassette":
            continue
        spans = []
        for part in doc.get("parts") or []:
            if "adapter" not in part["ref"]:
                continue
            w = ((_contract(part["ref"]) or {}).get("size") or {}).get("w")
            assert w, f"{part['ref']} has no size.w to measure a margin with"
            spans.append((float(part["at"][0]), float(part["at"][0]) + float(w)))
        if spans:
            ref = f"fs/{doc['name']}@{path.parent.name[1:]}"
            out.append((ref, doc["size"]["w"], spans))
    return out


def test_every_fhd_cassette_centres_its_adapter_row():
    rows = _rows()
    assert len(rows) >= 10, (
        f"only {len(rows)} FHD cassettes with adapters were found, so this is not "
        "measuring the family it was written for - have they moved or been renamed?")
    bad = []
    for ref, w, spans in rows:
        left = min(a for a, _b in spans)
        right = w - max(b for _a, b in spans)
        if abs(left - right) > 0.5:
            bad.append(f"{ref}: {left:.2f} mm left of the row, {right:.2f} right")
    assert not bad, (
        "FS centres the adapter row on the plate (17.1-17.4 mm each side on every "
        "face-on render); these do not:\n  " + "\n  ".join(bad))
