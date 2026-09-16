"""FHD-1MTP6LCDOS2A, and the adapter it is built from.

Measured off FS's own face-on render of SKU 57016, scaled on the 108.97 mm FHD
faceplate and validated against the 35.05 mm height to 1.02%. What makes these
assertions worth making is that they are a measurement and not a guess.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"

from portrayal import optical as O


def contract(rel):
    p = LIB / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_stacked_lc_adapter_presents_two_fibres():
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c is not None, "common/lc-duplex-v-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 2


def test_the_stacked_lc_adapter_is_the_measured_width():
    """9.28 across all six adapters on 57016, spread 0.00."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["w"] == 9.28


def test_the_stacked_adapter_is_the_measured_height():
    """13.75 across all six, spread 0.00 - top edge 10.66, bottom 24.41."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["h"] == 13.75


def test_the_stacked_adapter_says_which_of_its_dimensions_were_measured():
    c = contract("common/lc-duplex-v-adapter/v1")
    sc = c.get("size-confidence") or {}
    assert sc.get("w") == "photo-measured", \
        "the width IS measured - six bodies, spread 0.00 - and must say so"
    assert sc.get("h") == "photo-measured", \
        "so is the height - same six bodies, same spread"
    assert "d" not in sc and "d" not in c["size"], \
        "no depth is recorded: a face-on render cannot give one and neither " \
        "sibling adapter carries one to borrow, so stating it would invent it"


def test_two_stacked_bores_actually_fit_in_the_body():
    """A 6.3-tall bore twice over needs 12.6, and the body is 13.75.

    An earlier draft of this plan sized the body at 12.0, borrowed from the SC
    shell - which would have put 12.6 mm of bore into 12.0 mm of adapter and
    drawn two apertures overlapping. Measuring the height instead of borrowing
    it is what caught that, so this is the assertion that keeps it caught.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    ys = sorted(float(p["at"][1]) for p in bores)
    assert ys[1] >= ys[0] + 6.3, f"the bores overlap: {ys}"
    assert ys[1] + 6.3 <= c["size"]["h"], \
        f"the lower bore hangs out of the body: {ys[1]} + 6.3 > {c['size']['h']}"


def test_its_two_ports_are_stacked_not_side_by_side():
    """THE REASON THIS COMPONENT EXISTS.

    `common/lc-duplex-adapter@3` puts its bores side by side. A 6x crop of
    57016.main.jpg shows one dust cap over two ports one ABOVE the other, and
    the faceplate numbers agree - evens along the top, odds along the bottom.
    If a later edit lays these out abreast, this is what says so.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    assert len(bores) == 2, [p.get("ref") for p in c.get("parts") or []]
    xs = {round(float(p["at"][0]), 3) for p in bores}
    ys = {round(float(p["at"][1]), 3) for p in bores}
    assert len(xs) == 1, f"the two bores are at different x - abreast, not stacked: {xs}"
    assert len(ys) == 2, f"the two bores share a y - abreast, not stacked: {ys}"


def test_the_fs_cassette_pitch_is_in_the_registry_as_measured():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["fhd-lc-cassette"]
    assert s["pitch"] == 12.92
    assert s["pitch-confidence"] == "measured"
    assert "57016" in s["registry"], \
        "the registry entry must name the render the pitch came from"


CASSETTE = "fs/fhd-1mtp6lcd-os2-a/v1"
CENTRES = [20.45, 33.34, 46.23, 59.30, 72.19, 85.08]


def test_the_cassette_is_an_fhd_module():
    c = contract(CASSETTE)
    assert c is not None, "fs/fhd-1mtp6lcd-os2-a@1 not built"
    assert c["size"]["w"] == 108.97 and c["size"]["h"] == 35.05


def test_the_cassette_carries_six_stacked_lc_adapters():
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    assert len(lcs) == 6, [p["ref"] for p in c["parts"]]


def test_the_adapters_sit_on_their_measured_centres():
    """Not a pitch multiplied out - the six centres as measured, each to 0.01.

    lc4 sits 13.07 from lc3 where every other gap is 12.89. That asymmetry is in
    the render, and rounding it away to a tidy 12.92 everywhere would turn a
    measurement into a model of one.
    """
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    got = sorted(round(float(p["at"][0]) + 4.64, 2) for p in lcs)
    assert got == CENTRES


def test_the_adapter_row_is_measured_as_centred_not_drawn_as_centred():
    """10.66 is the measured top edge of all six, not a number chosen to centre.

    That it ALSO centres - 10.66 + 13.75/2 = 17.53 against 35.05/2 = 17.525 - is
    the corroboration, not the source. If a later edit rounds `at.y` to make the
    arithmetic tidier, it has replaced a measurement with a model of one.
    """
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    assert {round(float(p["at"][1]), 2) for p in lcs} == {10.66}


def test_the_cassette_names_the_render_it_was_measured_from():
    c = contract(CASSETTE)
    blob = yaml.safe_dump(c.get("provenance") or {})
    assert "57016" in blob, "provenance must name the SKU it was measured from"
    assert "1.02" in blob, "and the scale check that makes it a measurement"


def test_the_cassette_has_a_rear_face():
    c = contract(CASSETTE)
    assert ((c.get("faces") or {}).get("rear") or {}).get("ref") == \
        "fs/fhd-1mtp6lcd-rear@1"


def test_the_rear_face_carries_one_mtp():
    c = contract("fs/fhd-1mtp6lcd-rear/v1")
    assert c is not None, "fs/fhd-1mtp6lcd-rear@1 not built"
    mtps = [p for p in c["parts"] if p["ref"] == "common/mpo-adapter@1"]
    assert len(mtps) == 1, [p["ref"] for p in c["parts"]]


def test_the_rear_face_admits_it_was_never_measured():
    """The one render of this face is a three-quarter; the tool refuses it.

    An estimate that does not say it is one is the failure this whole library is
    built to avoid, and a rear face is where it would be easiest to hide.
    """
    c = contract("fs/fhd-1mtp6lcd-rear/v1")
    sc = c.get("size-confidence") or {}
    assert sc.get("w") == "estimated" and sc.get("h") == "estimated"
    assert "3.77" in (c.get("size-notes") or ""), \
        "say how far off the render actually is, not just that it is off"


def test_all_twelve_fibres_are_routed():
    """Twelve MTP positions, twelve LC ports, and no position left dark."""
    c = contract(CASSETTE)
    paths = (c.get("optical") or {}).get("paths") or []
    assert len(paths) == 12, f"{len(paths)} paths for a 12-fibre cassette"
    rear = {e for p in paths for e, _ in O.endpoints(p) if e.startswith("rear:")}
    assert rear == {f"rear:mtp.{n}" for n in range(1, 13)}
    front = {e for p in paths for e, _ in O.endpoints(p)
             if not e.startswith("rear:")}
    assert front == {f"lc{a}.{b}" for a in range(1, 7) for b in (1, 2)}


def test_the_cassette_says_where_its_polarity_map_came_from():
    """Sourced or assumed, it must say which. Naming the type is not sourcing it."""
    c = contract(CASSETTE)
    note = ((c.get("provenance") or {}).get("optical") or "")
    assert note, "no provenance for the fibre mapping at all"
    assert ("fig-" in note) or ("ASSUMPTION" in note.upper()), \
        "either name the figure it was read from, or say plainly it is assumed"


def test_the_cassette_pitch_standard_is_actually_conformed_to():
    """A registry entry nothing references is a fact nothing checks.

    `fhd-lc-cassette` was added to settle the open question at
    docs/optical-paths-design.md:287, but L81 reads `conforms` off the COMPOSED
    part - so until the adapter names it, the entry is inert and the rule that
    exists to compare the two never runs.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c.get("conforms") == "fhd-lc-cassette", \
        "the adapter must name the standard whose pitch describes how it is spaced"


def test_conforming_to_a_pitch_only_standard_does_not_crash_lint(tmp_path):
    """Seven registry entries carry no `w`/`h`, and `std["w"]` indexed them.

    A panel adapter's OPENING is standardised where its bezel is not, so a
    pitch-only or cavity-only entry is a legitimate shape here - and conforming
    to one used to end the run in `KeyError: 'w'` rather than a message. That is
    the third time a missing registry key has taken lint down, so this drives
    the real binary rather than the function.
    """
    import subprocess
    d = tmp_path / "components" / "t" / "conformer" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: conformer\nversion: 1.0.0\n"
        "class: port\nsize: {w: 9.28, h: 13.75}\n"
        "conforms: fhd-lc-cassette\n")
    r = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/lint.py"),
         "--schemas", str(ROOT / "spec/schemas"), "--library", str(tmp_path)],
        capture_output=True, text=True)
    assert "Traceback" not in r.stderr, r.stderr
    assert "[L9]" not in r.stdout, \
        f"a standard with no envelope has no size to disagree with: {r.stdout}"


def test_the_registry_pitches_are_what_its_own_centres_give():
    """A transcription slip inside one sentence, which is how 13.06 got in.

    The entry lists the six centres and then the five gaps between them. The
    second is arithmetic on the first, so it can be checked rather than
    trusted - and it disagreed by 0.01 for as long as both were written down.
    """
    import re
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    text = std["standards"]["fhd-lc-cassette"]["registry"]
    m = re.search(r"centres ([\d.\s]+?), pitches ([\d.\s]+?), mean", text)
    assert m, f"cannot find the centres/pitches pair in: {text[:200]}"
    centres = [float(v) for v in m.group(1).split()]
    stated = [float(v) for v in m.group(2).split()]
    derived = [round(centres[i] - centres[i - 1], 2) for i in range(1, len(centres))]
    assert stated == derived, \
        f"registry states pitches {stated} but its own centres give {derived}"


def test_the_registry_centres_are_the_contracts_centres():
    """The two files must be describing one measurement, not two."""
    c = contract(CASSETTE)
    import re
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    text = std["standards"]["fhd-lc-cassette"]["registry"]
    centres = [float(v) for v in
               re.search(r"centres ([\d.\s]+?), pitches", text).group(1).split()]
    w = contract("common/lc-duplex-v-adapter/v1")["size"]["w"]
    placed = [round(float(p["at"][0]) + w / 2, 2) for p in c["parts"]]
    assert centres == placed, \
        f"registry centres {centres} are not where the contract places them: {placed}"


def test_the_rear_mtp_is_where_its_provenance_says_it_is():
    """The provenance says centred; centred is what the placement must be.

    It used to say the adapter sits slightly below the vertical centre while
    placing it exactly on both axes - and since every number on that face is an
    estimate awaiting a face-on photograph, the provenance is the only record
    of what was intended.
    """
    rear = contract("fs/fhd-1mtp6lcd-rear/v1")
    mtp = next(p for p in rear["parts"] if p["id"] == "mtp")
    adapter = contract("common/mpo-adapter/v1")
    cx = float(mtp["at"][0]) + adapter["size"]["w"] / 2
    cy = float(mtp["at"][1]) + adapter["size"]["h"] / 2
    assert (round(cx, 3), round(cy, 3)) == (round(rear["size"]["w"] / 2, 3),
                                            round(rear["size"]["h"] / 2, 3)), \
        f"provenance says centred, placement puts it at ({cx}, {cy})"
    assert "CENTRED" in rear["provenance"]["parts"]
