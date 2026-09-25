"""The intake figure filter, which could not be tested until now (#41).

`extract.py` imported docling at module scope while `convert` was its only
consumer, so on exactly the machines that run this suite `import extract`
raised and none of the filter logic could be exercised.

That matters more here than for most tooling. The banner filter carries the
most expensive history in the repository, recorded in its own comments:
matching on width and aspect cost the ASR 9900 RP elevation and the SIP-700
with its numbered callouts; pooling hashes across vendors rather than per
publisher cost the ASR 9001 DC power tray. Those are regressions a test catches
and a comment does not - so each one below is named for what it protects.
"""
import builtins
import importlib
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal_intake import extract  # noqa: E402


# ---- the fix itself ---------------------------------------------------------

def test_the_module_imports_with_docling_unavailable():
    """The point of #41. Blocked rather than assumed, because docling happens to
    be installed on this machine and a passing import would prove nothing."""
    real = builtins.__import__

    def blocked(name, *a, **k):
        if name.split(".")[0] == "docling":
            raise ImportError("docling is not installed")
        return real(name, *a, **k)

    saved = {k: v for k, v in sys.modules.items() if k.split(".")[0] == "docling"}
    for k in saved:
        del sys.modules[k]
    sys.modules.pop("portrayal_intake.extract", None)
    builtins.__import__ = blocked
    try:
        mod = importlib.import_module("portrayal_intake.extract")
        assert callable(mod.classify), "imported, but the filter is not there"
        with pytest.raises(ImportError):
            mod.convert(pathlib.Path("x.pdf"), pathlib.Path("."), 3.0)
    finally:
        builtins.__import__ = real
        sys.modules.update(saved)
        sys.modules.pop("portrayal_intake.extract", None)
        importlib.import_module("portrayal_intake.extract")


# ---- hashing ----------------------------------------------------------------

def test_hamming_counts_differing_bits():
    assert extract.hamming("0000", "0000") == 0
    assert extract.hamming("0000", "0001") == 1
    assert extract.hamming("0000", "ffff") == 16


def test_ahash_is_stable_and_ignores_a_few_pixels():
    """An average hash over an 8x8 thumbnail has to survive the crop wobble
    between chapters, which is the whole reason it was chosen over dimensions."""
    Image = pytest.importorskip("PIL.Image")
    a = Image.new("RGB", (400, 100), "white")
    for x in range(0, 200):
        for y in range(0, 100):
            a.putpixel((x, y), (0, 0, 0))
    b = a.copy()
    b.putpixel((399, 99), (128, 128, 128))          # one pixel of wobble
    assert extract.ahash(a) == extract.ahash(b)
    c = Image.new("RGB", (400, 100), "black")
    assert extract.ahash(a) != extract.ahash(c)


# ---- the filter -------------------------------------------------------------

def pic(w, h, caption="", ahash="0000000000000000", **kw):
    return dict(w=w, h=h, caption=caption, ahash=ahash, **kw)


def test_an_icon_is_dropped():
    kept, rejected = extract.classify([pic(60, 60)])
    assert not kept and rejected[0]["drop_reason"] == "icon"


def test_a_small_picture_with_a_caption_is_kept():
    """`not cap` guards the icon rule. A captioned figure is a figure whatever
    its size - the caption is the publisher saying so."""
    kept, _ = extract.classify([pic(60, 60, caption="Figure 3: latch detail")])
    assert len(kept) == 1


def test_the_icon_threshold_is_tunable_per_publisher():
    """200px is a Juniper/Cisco number and some publishers draw smaller.

    FS.com renders its FHD cassettes at about 190x140, which is under 200 on both
    axes and uncaptioned, so the default rule took 64 of the 82 pictures in their
    modular cabling portfolio - and the largest of them were the cassette faces,
    the only images of that part anywhere in that corpus. From the kept pile
    "the vendor published no pictures of it" and "the filter ate them" look
    identical, which is why the rejects stay on disk and why this knob exists.
    """
    fs_cassette = pic(189, 140)
    kept, rejected = extract.classify([fs_cassette])
    assert not kept and rejected[0]["drop_reason"] == "icon", (
        "the default no longer drops it, so this test is no longer about "
        "anything - check whether ICON_PX moved")

    kept, rejected = extract.classify([fs_cassette], icon_px=120)
    assert len(kept) == 1 and not rejected

    # and the knob does not simply disable the rule: a real icon still goes
    kept, rejected = extract.classify([pic(60, 60)], icon_px=120)
    assert not kept and rejected[0]["drop_reason"] == "icon"


def test_a_repeated_wide_uncaptioned_picture_is_dropped_as_a_banner():
    pics = [pic(900, 200, ahash="ffffffffffffffff") for _ in range(extract.BANNER_CLUSTER)]
    kept, rejected = extract.classify(pics)
    assert not kept
    assert {r["drop_reason"] for r in rejected} == {"banner"}


def test_the_same_picture_below_the_cluster_threshold_is_KEPT():
    """THE ASR 9900 RP ELEVATION. A wide uncaptioned drawing that repeats a few
    times is a real figure - a run of power cordsets, one per country - and the
    cluster threshold is the only thing separating it from furniture."""
    pics = [pic(900, 200, ahash="ffffffffffffffff")
            for _ in range(extract.BANNER_CLUSTER - 1)]
    kept, rejected = extract.classify(pics)
    assert len(kept) == len(pics), "a small cluster of real drawings was dropped"
    assert not rejected


def test_a_wide_picture_with_a_caption_is_never_a_banner():
    """A banner is furniture and furniture is uncaptioned. Dimensions alone
    cannot tell a chapter header from a line-card faceplate, which is what
    matching on width and aspect got wrong."""
    pics = [pic(900, 200, caption="Figure 12: chassis front", ahash="ffffffffffffffff")
            for _ in range(extract.BANNER_CLUSTER * 2)]
    kept, _ = extract.classify(pics)
    assert len(kept) == len(pics)


def test_banner_rule_off_keeps_every_wide_figure():
    """THE CASA CASE. On the C100G guide every wide figure shares a width, so
    the rule dropped fig-0038 - the fan tray face with its HS button and three
    status LEDs. Casa prints no repeated header at all, so for Casa the rule can
    only subtract."""
    pics = [pic(900, 200, ahash="ffffffffffffffff") for _ in range(extract.BANNER_CLUSTER)]
    kept, rejected = extract.classify(pics, banner_rule=False)
    assert len(kept) == len(pics) and not rejected


def test_an_external_pool_is_what_makes_the_rule_corpus_wide():
    """THE POINT OF THE POOL. One document under-detects; the rule needs the
    publisher's whole corpus. A single picture here is a banner only because the
    pool says the same image appears everywhere else."""
    pool = ["ffffffffffffffff"] * extract.BANNER_CLUSTER
    kept, rejected = extract.classify([pic(900, 200, ahash="ffffffffffffffff")], pool=pool)
    assert not kept and rejected[0]["drop_reason"] == "banner"


def test_a_near_miss_hash_still_clusters():
    """The threshold is Hamming 3, so a few flipped bits still count as the same
    picture - that is the crop wobble the hash exists to absorb."""
    near = f"{(int('f' * 16, 16) ^ 0b111):016x}"      # three bits away
    assert extract.hamming(near, "f" * 16) == 3
    pool = ["f" * 16] * extract.BANNER_CLUSTER
    kept, _ = extract.classify([pic(900, 200, ahash=near)], pool=pool)
    assert not kept


def commscope_corpus():
    """Records shaped like the CH3000 index.json rejects: the header logo strip,
    repeated past the cluster threshold, and the ordering-code chart drawn at
    page width in the same white and orange, so the same ahash."""
    strip = [pic(302, 110, ahash="f0f0f0f0f8ffffef")
             for _ in range(extract.BANNER_CLUSTER)]
    chart = pic(1597, 541, ahash="f0f0f0f0f8ffffef")
    return strip, chart


def test_the_banner_height_ceiling_keeps_a_page_width_chart():
    """THE COMMSCOPE CASE. The BP-35M4-CFx compatibility chart shares its hash
    with the CH3000 header strip, so without the knob it goes with the strips."""
    strip, chart = commscope_corpus()
    kept, rejected = extract.classify(strip + [chart])
    assert not kept and len(rejected) == len(strip) + 1, (
        "the chart survives the default, so this test is no longer about "
        "anything - check whether the rule changed")

    kept, rejected = extract.classify(strip + [chart], banner_max_h=200)
    assert kept == [chart], "the chart was dropped under the ceiling"
    assert len(rejected) == len(strip)
    assert {r["drop_reason"] for r in rejected} == {"banner"}, (
        "the ceiling switched the rule off for the strips it exists to drop")


def test_the_banner_height_ceiling_is_off_by_default():
    """THE CISCO CITYSCAPE is 1302x370. A default ceiling of 200 - the number
    that is right for CommScope - would hand it back on every chapter."""
    assert extract.BANNER_MAX_H is None
    pics = [pic(1302, 370, ahash="ffffffffffffffff")
            for _ in range(extract.BANNER_CLUSTER)]
    kept, rejected = extract.classify(pics)
    assert not kept and {r["drop_reason"] for r in rejected} == {"banner"}


def test_the_banner_height_ceiling_leaves_the_icon_rule_alone():
    kept, rejected = extract.classify([pic(60, 60)], banner_max_h=200)
    assert not kept and rejected[0]["drop_reason"] == "icon"


# ---- the command line -------------------------------------------------------

def test_a_failed_file_fails_the_run(tmp_path, monkeypatch, capsys):
    """The runbook reads one exit status per file. A truncated PDF printed FAIL
    and exited 0, which is what a successful conversion looks like."""
    def run(pdf, *a, **k):
        if pdf.name == "bad.pdf":
            raise RuntimeError("Data format error")
        return "ok", 3
    monkeypatch.setattr(extract, "run", run)
    out = ["--out", str(tmp_path)]
    assert extract.main(["good.pdf"] + out) == 0
    assert extract.main(["bad.pdf"] + out) == 1
    assert extract.main(["good.pdf", "bad.pdf", "good2.pdf"] + out) == 1, (
        "one failure among successes has to fail the run")
    printed = capsys.readouterr().out
    assert "FAIL bad.pdf: RuntimeError: Data format error" in printed
    assert "good2.pdf: 3 figures" in printed, "a failure stopped the batch"


def test_the_script_exits_with_mains_status(tmp_path):
    """main() returning 1 is nothing if the entry point drops it."""
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/intake/extract.py"),
         str(tmp_path / "missing.pdf"), "--out", str(tmp_path), "--reclassify"],
        capture_output=True, text=True)
    assert "FAIL missing.pdf" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 1


# ---- sectioning and the index ----------------------------------------------

def test_a_record_is_tagged_with_the_heading_above_its_caption():
    md = "# One\n\ntext\n\n## Cooling\n\nFigure 4: fan tray\n"
    recs = [pic(900, 200, caption="Figure 4: fan tray")]
    extract.sections(md, recs)
    assert recs[0]["section"] == "Cooling"


def test_a_record_with_no_caption_gets_no_section():
    recs = [pic(900, 200)]
    extract.sections("# One\n", recs)
    assert recs[0]["section"] == ""


def test_write_index_records_why_things_were_dropped(tmp_path):
    pics = ([pic(60, 60)]
            + [pic(900, 200, ahash="ffffffffffffffff") for _ in range(extract.BANNER_CLUSTER)]
            + [pic(900, 200, caption="Figure 1: real")])
    n = extract.write_index(pathlib.Path("x.pdf"), tmp_path, pics, "# H\n")
    doc = json.loads((tmp_path / "index.json").read_text())
    assert n == 1
    assert doc["drops_by_reason"] == {"icon": 1, "banner": extract.BANNER_CLUSTER}
    assert doc["dropped"] == extract.BANNER_CLUSTER + 1
