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
    # `power` (#1045) is the one media with no bare type: a power type is one
    # connector pair on one cord, so no cord is "power" and nothing more. The
    # kit gives a cable of that media that names no type the power-c13 cord's
    # figures. `ground`, `stack`, `usb` and `console` each have a bare type.
    media = _kit_list("kit/rack/cable-rules.js", "MEDIA")
    bare = {tid for tid, t in built["types"].items() if t["media"] == tid}
    assert media and bare == set(media) - {"power"}
    assert {"power", "ground", "stack", "usb", "console"} <= set(media)
    assert {t["media"] for t in built["types"].values()} <= set(media)


def test_the_bare_types_agree_with_the_kit_s_fill_diameters(built):
    text = (ROOT / "kit/rack/route.js").read_text()
    body = re.search(r"export const DIAMETERS = \{([^}]*)\}", text).group(1)
    fill = {k: float(v) for k, v in re.findall(r"(\w+): ([\d.]+)", body)}
    assert fill
    # `power` has no bare type; the kit takes the power-c13 cord for it
    assert fill.pop("power") == built["types"]["power-c13"]["od_mm"]
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


def test_the_one_jacket_colour_is_the_sheet_s(built):
    # #1028: Siemon's QSFP28 AOC sheet shows an aqua jacket and states 3.0 mm
    # and a 30 mm minimum bend radius. The colour is the reading the library
    # already holds on the cable end, so the two cannot drift apart.
    from portrayal.manifest import load_yaml
    t = built["types"]["aoc-siemon-q1q28f"]
    assert t["media"] == "aoc" and t["od_mm"] == 3.0
    assert t["min_bend_radius"]["installed"]["mm"] == 30
    assert t["jacket"]["color"] == "#49eaf8" and t["jacket"]["basis"] == "photo"
    assert "164,214 pixels" in t["jacket"]["note"]
    assert built["sources"]["siemon-qsfp28-aoc"]["url"].startswith("https://files.siemon.com/")
    end = load_yaml(ROOT / "library/components/siemon/qsfp28-aoc/v1/contract.yaml")
    body = next(p for p in end["parts"] if p["id"] == "body")
    assert body["attrs"]["jacket-color"] == t["jacket"]["color"]
    assert body["attrs"]["cable-od"] == t["od_mm"]


def test_no_bare_media_type_states_a_jacket(built):
    # One table holds the colour a media is drawn in: the kit's COLORS. A bare
    # type with a jacket would be a second, and would recolour every drawing
    # of that media the day a consumer read it.
    bare = [tid for tid, t in built["types"].items() if t["media"] == tid]
    assert len(bare) == 12
    assert [tid for tid in bare if "jacket" in built["types"][tid]] == []
    stated = sorted(tid for tid, t in built["types"].items() if "jacket" in t)
    assert stated == ["aoc-siemon-q1q28f"], "a new jacket colour comes with its source and its own check"


@pytest.mark.parametrize("jacket,says", [
    ({"color": "aqua", "basis": "standard", "sources": ["foa-tia568"]}, "color is # and six lower case hex digits"),
    ({"color": "#49EAF8", "basis": "standard", "sources": ["foa-tia568"]}, "color is # and six lower case hex digits"),
    ({"color": "#49eaf8", "basis": "seen", "sources": ["foa-tia568"]}, "jacket: basis must be"),
    ({"color": "#49eaf8", "basis": "standard", "sources": []}, "jacket: no sources"),
    ({"color": "#49eaf8", "basis": "standard", "sources": ["nope"]}, "jacket: unknown source"),
    ({"color": "#49eaf8", "basis": "photo", "sources": ["foa-tia568"]}, "says what was counted"),
    ({"color": "#49eaf8", "basis": "standard", "sources": ["foa-tia568"], "shade": "light"}, "jacket: unknown key 'shade'"),
    ("#49eaf8", "jacket: not a mapping"),
])
def test_a_bad_jacket_is_refused(jacket, says):
    d = _doc()
    d["types"]["dac-26awg"]["jacket"] = jacket
    assert any(says in p for p in cti.problems(d)), cti.problems(d)


def test_a_jacket_on_a_bare_media_type_is_refused():
    d = _doc()
    good = {"color": "#2bb3c8", "basis": "standard", "sources": ["foa-tia568"]}
    d["types"]["dac-26awg"]["jacket"] = dict(good)
    assert cti.problems(d) == [], "a named type may state one"
    d["types"]["om4"]["jacket"] = dict(good)
    assert cti.problems(d) == ["type om4: a bare media type states no jacket; a media's colour is the kit's COLORS"]


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


# --- DC feeds, ground wires, stack, USB, console, RPS and StackPower ---------------------

DC_FEEDS = ["dc-feed-2x14awg", "dc-feed-2x12awg", "dc-feed-2x10awg", "dc-feed-2x6awg"]
GROUND_WIRES = ["ground", "ground-14awg", "ground-12awg", "ground-8awg", "ground-6awg"]
NEW_BARE = ["stack", "usb", "console"]
POWER_CABLES = ["cab-rps2300-e", "cab-spwr-30cm", "cab-spwr-150cm"]
FLEXSTACK = ["cab-stk-e-0-5m", "cab-stk-e-1m", "cab-stk-e-3m"]
ESTIMATE = "portrayal-estimate"


def test_the_dc_ground_stack_usb_console_rps_and_stackpower_types_are_published(built):
    types = built["types"]
    for tid in DC_FEEDS + GROUND_WIRES + NEW_BARE + POWER_CABLES + FLEXSTACK:
        assert tid in types, tid
    assert {types[t]["media"] for t in DC_FEEDS + POWER_CABLES} == {"power"}
    assert {types[t]["family"] for t in DC_FEEDS + POWER_CABLES} == {"power"}
    assert {(types[t]["media"], types[t]["family"]) for t in GROUND_WIRES} == {("ground", "ground")}
    assert [(types[t]["media"], types[t]["family"]) for t in NEW_BARE] == [(t, t) for t in NEW_BARE]
    assert {(types[t]["media"], types[t]["family"]) for t in FLEXSTACK} == {("stack", "stack")}
    for tid in GROUND_WIRES[1:] + FLEXSTACK:
        assert types[tid]["media"] != tid, f"{tid} is a refinement: only the bare type has the media's id"
    assert types["ground"]["media"] == "ground" and types["stack"]["media"] == "stack"


def _figures(t):
    """Every figure of a type as (name, sources, marked unverified)."""
    out = [("od_mm", t["od_sources"], False)]
    for which in ("installed", "loaded"):
        r = t["min_bend_radius"][which]
        if r:
            out.append((which, r["sources"], r.get("unverified") is True))
    if "ampacity-a" in t:
        out.append(("ampacity-a", t["ampacity-sources"], t.get("unverified") is True))
    return out


def test_each_new_figure_is_sourced_or_marked_an_estimate(built):
    # a figure whose only source is Portrayal's own estimate says so: the radius is `unverified`, the type
    # is `unverified` where one is the ampacity, and a `note` says what is not known. A figure that cites a
    # maker's document does not need the mark.
    for tid in DC_FEEDS + GROUND_WIRES + NEW_BARE + POWER_CABLES + FLEXSTACK:
        t = built["types"][tid]
        for name, sources, marked in _figures(t):
            assert sources and all(s in built["sources"] for s in sources), (tid, name)
            if set(sources) == {ESTIMATE} and name != "od_mm":
                assert marked, f"{tid} {name}: an estimate alone is marked unverified"
        if any(set(s) == {ESTIMATE} for _, s, _ in _figures(t)):
            assert isinstance(t.get("note"), str) and t["note"].strip(), f"{tid}: an estimated figure says so in a note"


def test_a_dc_feed_names_its_conductors_by_the_roles_of_dc_yaml(built):
    from portrayal.manifest import load_yaml
    roles = set(load_yaml(cti.SCHEMAS / "dc.yaml")["roles"])
    for tid in DC_FEEDS:
        t = built["types"][tid]
        assert t["dc"] is True and t["media"] == "power"
        assert len(t["conductors"]) == 2, tid
        for c in t["conductors"]:
            assert set(c) == {"role", "awg"} and c["role"] in roles - {"gnd"} and c["awg"] > 0, (tid, c)
        assert t["ampacity-a"] > 0 and t["ampacity-sources"], tid
    # the gauges of the library's DC ends, one type each
    assert sorted(t["conductors"][0]["awg"] for t in (built["types"][x] for x in DC_FEEDS)) == [6, 10, 12, 14]
    # the AC cords are not DC feeds
    assert not any(t.get("dc") for tid, t in built["types"].items() if tid not in DC_FEEDS)


def test_the_new_sources_are_cited_by_their_makers_title_and_url(built):
    src = built["sources"]
    assert src["cisco-2960s-hig"]["url"] == "https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/hardware/installation/guide_stack/2960SHIG.pdf"
    assert "OL-19732-04" in src["cisco-2960s-hig"]["title"]
    assert src["cisco-c9300-hig"]["url"] == "https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/hardware/install/b_c9300_hig.pdf"
    assert src["waskoenig-h07v-k"]["url"].startswith("https://www.waskoenig.de/")
    for tid in FLEXSTACK + ["cab-rps2300-e"]:
        assert "cisco-2960s-hig" in built["types"][tid].get("sources", []), tid
    for tid in ("cab-spwr-30cm", "cab-spwr-150cm"):
        assert "cisco-c9300-hig" in built["types"][tid].get("sources", []), tid


@pytest.mark.parametrize("break_it,says", [
    (lambda t: t["conductors"][0].update(role="minus48"), "role 'minus48' is not one of dc.yaml's roles"),
    (lambda t: t["conductors"][0].update(role="gnd"), "ground wire"),
    (lambda t: t["conductors"][0].update(awg=0), "awg must be a positive number"),
    (lambda t: t["conductors"][0].pop("awg"), "awg must be a positive number"),
    (lambda t: t["conductors"][0].update(colour="red"), "unknown key 'colour'"),
    (lambda t: t.update(conductors=[]), "conductors is a list of one or more"),
    (lambda t: t.update(conductors="batt"), "conductors is a list of one or more"),
    (lambda t: t.update({"ampacity-a": 0}), "ampacity-a must be a positive number"),
    (lambda t: t.update({"ampacity-a": True}), "ampacity-a must be a positive number"),
    (lambda t: t.update({"ampacity-sources": []}), "ampacity-a has no ampacity-sources"),
    (lambda t: t.update({"ampacity-sources": ["nope"]}), "unknown source 'nope'"),
    (lambda t: t.pop("ampacity-a"), "a DC feed states its ampacity-a"),
    (lambda t: t.update(dc="yes"), "dc must be true or false"),
    (lambda t: t.update(dc=False), "conductors belong to a DC feed"),
    (lambda t: t.pop("conductors"), "a DC feed names its conductors"),
    (lambda t: t.update(family="copper"), "a DC feed is of the family power"),
])
def test_a_bad_dc_feed_is_refused_with_a_sentence(break_it, says):
    d = _doc()
    break_it(d["types"]["dc-feed-2x14awg"])
    assert any(says in p for p in cti.problems(d)), cti.problems(d)


def test_the_new_families_are_known_and_the_bare_rule_holds_for_the_new_media():
    assert {"ground", "stack", "usb", "console"} <= set(cti.FAMILIES)
    for media in ("ground", "stack", "usb", "console"):
        d = _doc()
        d["types"][f"{media}-refined"] = copy.deepcopy(d["types"].pop(media))
        assert any(f"media {media}: no type has the id {media}" in p for p in cti.problems(d)), media
    d = _doc()
    d["types"]["usb"]["jacket"] = {"color": "#8e6bd1", "basis": "convention", "sources": ["foa-tia568"]}
    assert any("a bare media type states no jacket" in p for p in cti.problems(d))
