"""cable-types.json (#919): the named cable types, each with a media, a typical
outside diameter and a sourced minimum bend radius `{installed, loaded}`. The
bundle bend check (#922) reads the installed radius through the kit's
rack/cable-types.js; these pin the published shape, a few sourced values, and
that every Rack Builder media names a type."""
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from portrayal import cable_types_index as cti

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built():
    return cti.build()


def test_the_file_states_its_format_version_and_source(built):
    assert built["format"] == 1
    assert re.fullmatch(r"\d+\.\d+\.\d+", built["version"])
    assert built["generated-from"] == "spec/schemas/cable-types.yaml"


def test_every_type_has_the_published_shape(built):
    assert len(built["types"]) >= 12, "the table is nearly empty - the build is reading the wrong file"
    for tid, t in built["types"].items():
        assert t["id"] == tid
        assert t["media"] and t["family"] in cti.FAMILIES
        assert t["od_mm"] > 0 and t["od_sources"]
        mbr = t["min_bend_radius"]
        assert set(mbr) == {"installed", "loaded"}, tid
        for which in ("installed", "loaded"):
            r = mbr[which]
            if r is None:
                assert which == "loaded", f"{tid}: no installed radius"
                continue
            assert len({"mm", "xOD"} & set(r)) == 1, (tid, which)
            assert r["basis"] in ("standard", "convention")
            assert r["sources"] and all(s in built["sources"] for s in r["sources"])


def test_every_source_is_a_public_https_url(built):
    for sid, s in built["sources"].items():
        assert s["title"] and s["url"].startswith("https://"), sid


def test_the_issue_s_coverage(built):
    # #919: OM3, OM4, OM5, OS2 with G.657.A1/A2, Cat6 and Cat6A UTP and
    # screened, DAC, AOC and power cords.
    need = {"om3", "om4", "om5", "os2", "os2-g657a1", "os2-g657a2", "cat6", "cat6-ftp",
            "cat6a", "cat6a-ftp", "dac", "aoc"}
    assert need <= set(built["types"])
    assert any(t["family"] == "power" for t in built["types"].values())


def _kit_list(path, name):
    text = (ROOT / path).read_text()
    m = re.search(rf"export const {name} = \[([^\]]*)\]", text)
    return re.findall(r"'([^']+)'", m.group(1))


def test_every_rack_builder_media_is_a_type_of_its_own(built):
    # So a rack cable's media names its type with no mapping.
    # The bare types (id == media) are exactly the Rack Builder's media: a new
    # media without a type, or a bare type no media names, fails here.
    media = _kit_list("kit/rack/cable-rules.js", "MEDIA")
    bare = {tid for tid, t in built["types"].items() if t["media"] == tid}
    assert media and bare == set(media)


def test_the_bare_types_agree_with_the_kit_s_fill_diameters(built):
    text = (ROOT / "kit/rack/route.js").read_text()
    body = re.search(r"export const DIAMETERS = \{([^}]*)\}", text).group(1)
    fill = {k: float(v) for k, v in re.findall(r"(\w+): ([\d.]+)", body)}
    assert fill
    for k, d in fill.items():
        assert built["types"][k]["od_mm"] == d, k


@pytest.mark.parametrize("tid,which,rule", [
    # TIA-568 via the FOA: a two-fibre inside-plant cable, 25 mm, 50 mm pulled
    ("om4", "installed", {"mm": 25}),
    ("om4", "loaded", {"mm": 50}),
    # OS2 cords take TIA's cord rule too; G.652.D's 30 mm is its test radius
    ("os2", "installed", {"mm": 25}),
    # screened stranded patch cords are 4x OD, as unscreened ones (trueCABLE)
    ("cat6a-ftp", "installed", {"xOD": 4}),
    ("cat6-ftp", "installed", {"xOD": 4}),
    ("os2-g657a2", "installed", {"mm": 25}),
    # TIA-568 / ISO 11801 balanced cable: 4x OD installed, 8x pulled
    ("cat6a", "installed", {"xOD": 4}),
    ("cat6a", "loaded", {"xOD": 8}),
    # Smartoptics SO-SFP28-PCUxM: AWG30 23 mm, AWG26 28 mm
    ("dac", "installed", {"mm": 23}),
    ("dac-26awg", "installed", {"mm": 28}),
])
def test_sourced_values(built, tid, which, rule):
    r = built["types"][tid]["min_bend_radius"][which]
    assert {k: r[k] for k in ("mm", "xOD") if k in r} == rule


def test_the_bases_say_how_sure_each_figure_is(built):
    t = built["types"]
    assert t["om4"]["min_bend_radius"]["installed"]["basis"] == "standard"
    assert t["cat6a-ftp"]["min_bend_radius"]["installed"]["basis"] == "standard"
    assert t["cat6a-ftp"]["min_bend_radius"]["installed"]["sources"] == ["truecable-bend"]
    assert t["dac"]["min_bend_radius"]["installed"]["basis"] == "convention"
    assert t["os2-g657a1"]["fiber"]["min_bend"]["mm"] == 10
    # TIA-568 does not cover AOC assemblies: its rule is applied by analogy
    for which in ("installed", "loaded"):
        r = t["aoc"]["min_bend_radius"][which]
        assert r["basis"] == "convention" and r["unverified"] is True
    # G.652.D's 30 mm is a test radius, kept on the fibre and citing the Recommendation
    assert t["os2"]["fiber"]["min_bend"]["mm"] == 30
    assert set(t["os2"]["fiber"]["min_bend"]["sources"]) == {"itu-g652", "hfcl-macrobend"}
    # a power type names its cord, so another cord is another type
    assert t["power-c13"]["conductor"] == "H05VV-F 3G1.0"
    assert t["power-c19"]["conductor"] == "H05VV-F 3G1.5"


def _doc():
    from portrayal.manifest import load_yaml
    return copy.deepcopy(load_yaml(cti.SCHEMAS / "cable-types.yaml"))


def test_the_source_table_passes_its_own_checks():
    assert cti.problems(_doc()) == []


@pytest.mark.parametrize("break_it,says", [
    (lambda d: d["types"]["om4"]["min_bend_radius"]["installed"].update(xOD=10), "exactly one of mm or xOD"),
    (lambda d: d["types"]["om4"]["min_bend_radius"]["installed"].update(sources=[]), "no sources"),
    (lambda d: d["types"]["om4"]["min_bend_radius"]["installed"].update(sources=["nope"]), "unknown source"),
    (lambda d: d["types"]["om4"]["min_bend_radius"]["installed"].update(basis="folklore"), "basis must be"),
    (lambda d: d["types"]["om4"]["min_bend_radius"].update(installed=None), "installed: missing"),
    (lambda d: d["types"]["om4"]["min_bend_radius"]["installed"].update({"in": "x"}), "unknown key"),
    (lambda d: d["types"]["cat6"].pop("od_mm"), "od_mm must be"),
    (lambda d: d["types"].pop("om4"), "media om4: no type has the id om4"),
    (lambda d: d["types"]["cat6"].update(fiber={"mode": "multimode"}), "only a fiber type"),
    (lambda d: d["types"]["power-c13"].pop("conductor"), "names its cord's `conductor`"),
])
def test_a_bad_table_is_refused(break_it, says):
    d = _doc()
    if "media om4" in says:
        d["types"]["om4-bi"] = dict(d["types"]["om4"])
    break_it(d)
    assert any(says in p for p in cti.problems(d)), cti.problems(d)


@pytest.mark.parametrize("doc,says", [
    ([], "the table is not a mapping"),
    ({"format": 1, "version": "1.0.0", "sources": ["foa"], "types": {}}, "sources is not a mapping"),
    ({"format": 1, "version": "1.0.0", "sources": {}, "types": ["om4"]}, "types is not a mapping"),
])
def test_a_malformed_table_gets_a_sentence_not_a_traceback(doc, says):
    assert says in cti.problems(doc)


def test_malformed_entries_inside_a_type_get_sentences():
    d = _doc()
    d["types"]["om4"]["fiber"] = "OM4"
    d["types"]["om3"]["min_bend_radius"]["installed"]["sources"] = [{"not": "an id"}]
    d["types"]["om5"]["media"] = ["om5"]
    got = cti.problems(d)
    assert any("om4: fiber is not a mapping" in p for p in got), got
    assert any("om3 installed: unknown source" in p for p in got), got
    assert any("om5: no media" in p for p in got), got


def test_build_sh_writes_it():
    assert "cable_types_index.py" in (ROOT / "build.sh").read_text()


def test_the_kit_exports_its_helper():
    pkg = json.loads((ROOT / "kit/package.json").read_text())
    assert pkg["exports"]["./rack/cable-types"] == "./rack/cable-types.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_resolves_the_published_table(built, tmp_path):
    (tmp_path / "cable-types.json").write_text(json.dumps(built))
    helper = (ROOT / "kit/rack/cable-types.js").as_uri()
    script = (f"import {{bendLookup}} from '{helper}';\n"
              "import {readFileSync} from 'node:fs';\n"
              "const j = JSON.parse(readFileSync(process.argv[2], 'utf8'));\n"
              "const b = bendLookup(j.types);\n"
              "console.log(JSON.stringify(['om4','os2','cat6','cat6a','aoc','dac','power-c13','nope']"
              ".map(media => b({media}))));\n")
    (tmp_path / "probe.mjs").write_text(script)
    out = subprocess.run(["node", str(tmp_path / "probe.mjs"), str(tmp_path / "cable-types.json")],
                         capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == [25, 25, 24, 30, 30, 23, 42.6, None]
