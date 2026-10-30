"""The S9720-56ED states its service cages as 18 pairs, and draws the blue patch on 18 of them.

UfiSpace's data sheet (page 2) and Hardware Installation Guide (page 12, Figures 8 and 9) say the 36
service cages are 18 pairs: each pair runs as one 800G port or as two ports at 400G or lower. The guide's
Figure 9 highlights one cage of each pair in blue and joins it to its column neighbour with a red line,
and the vendor's front render carries the blue label patch on exactly those 18 cages. The guide's text
does not say which cage of a pair runs the 800G port, so that is read from the figure and declared.
"""
import functools
import hashlib
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "ufispace" / "s9720-56ed" / "device.yaml"

# The cage of each pair Figure 9 highlights: the second row of the upper band, the first row of the lower.
HIGHLIGHTED = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 20, 22, 24, 26, 28, 30, 32, 34]
PARTNERS = [p for p in range(36) if p not in HIGHLIGHTED]

HIGH_SPEEDS = ["100g", "200g", "400g", "800g"]
LOW_SPEEDS = ["100g", "200g", "400g"]

BLUE = "#2e54ac"
MAGENTA = "#b0246b"
YELLOW = "#c6c33b"
SERVICE_REASONS = {"vendor-silent", "sources-disagree", "nos-dependent", "needs-hardware", "needs-photo",
                   "needs-drawing"}

# Every placement's id, ref, at, rotate, rel-pos and group, every cutout, region and bay, the group ids and
# the chassis block, as `main` had them before this change: a canonical JSON digest.
UNMOVED_DIGEST = "903ac3bb108ccc4fd3c4252e0e558582de07f28cd6f4e51cb789586b9995bd49"


@functools.lru_cache(maxsize=None)
def _device():
    return yaml.safe_load(DEVICE.read_text())


def _placements(view="front"):
    return _device()["views"][view]["components"]["placements"]


def _service_ports():
    ports = {}
    for p in _placements():
        if p.get("group") == "qsfpdd-800g-service":
            ports[int(p["id"].split("-")[1])] = p
    return ports


def _patches(fill):
    return [d for d in _device()["views"]["front"]["panel"]["decor"] if d.get("fill") == fill]


def _gap(what):
    return next(g for g in _device()["gaps"] if g["what"] == what)


def test_the_highlighted_cages_state_800g_and_the_rest_400g():
    """The 18 cages Figure 9 highlights state 800G up to 800G; the other 18 state 400G up to 400G."""
    ports = _service_ports()
    assert sorted(ports) == list(range(36))
    for n in HIGHLIGHTED:
        attrs = ports[n].get("attrs") or {}
        assert attrs.get("speed") == "800g" and attrs.get("speeds") == HIGH_SPEEDS, f"port-{n}"
    for n in PARTNERS:
        attrs = ports[n].get("attrs") or {}
        assert attrs.get("speed") == "400g" and attrs.get("speeds") == LOW_SPEEDS, f"port-{n}"


def test_the_service_group_declares_its_media_and_no_speed():
    """The group holds cages at 800G and at 400G, so it states the cage and leaves each speed to the port."""
    group = _device()["groups"]["qsfpdd-800g-service"]
    assert group["attrs"].get("media") == "qsfp-dd"
    assert "speed" not in group["attrs"]


def test_each_pair_is_one_highlighted_cage_and_its_column_neighbour():
    """The pairs are 0-1, 2-3 ... 34-35: the even port is the partner, the odd one beside it is highlighted."""
    pairs = {(min(h, h - 1), max(h, h - 1)) for h in HIGHLIGHTED if h % 2 == 1}
    pairs |= {(h, h + 1) for h in HIGHLIGHTED if h % 2 == 0}
    assert sorted(pairs) == [(2 * k, 2 * k + 1) for k in range(18)]


def _cage_of(patch, cages):
    """The service cage whose left edge the patch abuts, on the patch's own row."""
    right = patch["at"][0] + patch["size"][0]
    hits = [n for n, c in cages.items()
            if abs(c["at"][0] - right) < 0.6 and abs(c["at"][1] - patch["at"][1]) < 0.6]
    assert len(hits) <= 1, patch
    return hits[0] if hits else None


def test_the_blue_patch_sits_beside_the_highlighted_cages_only():
    """Each kept blue patch abuts one of the 18 highlighted cages, and no other service cage has one."""
    cages = _service_ports()
    beside = [_cage_of(p, cages) for p in _patches(BLUE)]
    assert None not in beside
    assert sorted(beside) == sorted(HIGHLIGHTED)


def test_the_kept_patches_share_one_fill():
    """All 18 patches use the blue the colour samples decided: the three samples agree, so #2e54ac stays."""
    fills = {d["fill"] for d in _patches(BLUE)}
    assert fills == {BLUE}
    assert len(_patches(BLUE)) == 18


def test_the_fabric_patches_and_the_sfp28_legend_are_unchanged():
    """Twenty magenta fabric patches in five columns and four rows, and the one yellow SFP28 legend."""
    xs = [289.83, 317.81, 345.79, 373.77, 401.75]
    ys = [9.40, 22.30, 51.30, 66.10]
    want = sorted((x, y) for x in xs for y in ys)
    got = sorted(tuple(d["at"]) for d in _patches(MAGENTA))
    assert got == want
    assert all(d["size"] == [3.30, 9.90] and d["rx"] == 0.30 for d in _patches(MAGENTA))
    legend = _patches(YELLOW)
    assert len(legend) == 1
    assert legend[0]["at"] == [56.19, 42.50] and legend[0]["size"] == [14.90, 8.60]


def test_nothing_moved():
    """No placement's id, ref, at, rotate, rel-pos or group, no cutout, region or bay, no group id and no
    chassis value differs from the device before the change."""
    d = _device()
    placements, cutouts, regions, bays = [], {}, {}, {}
    for vname, v in d["views"].items():
        comp = v.get("components") or {}
        for c in comp.get("placements") or []:
            placements.append([vname, c.get("id"), c.get("ref"), c.get("at"), c.get("rotate"),
                               c.get("rel-pos"), c.get("group")])
        if comp.get("bays"):
            bays[vname] = comp["bays"]
        if (v.get("panel") or {}).get("cutouts"):
            cutouts[vname] = v["panel"]["cutouts"]
        if v.get("regions"):
            regions[vname] = v["regions"]
    blob = json.dumps({"placements": placements, "cutouts": cutouts, "regions": regions, "bays": bays,
                       "groups": list(d["groups"]), "chassis": d["chassis"]},
                      sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(blob.encode()).hexdigest() == UNMOVED_DIGEST
    assert d["chassis"]["color"] == "#373737"
    assert "qsfpdd-800g-service" in d["groups"]
    assert d["groups"]["qsfpdd-800g-service"]["attrs"] == {"media": "qsfp-dd"}


def test_port_modes_states_the_pair_rule_and_where_the_800g_cage_is_read_from():
    """The pair rule is stated, and the 800G member is said to be read from Figure 9 and not stated."""
    text = " ".join(str(_device()["attrs"]["performance"]["port-modes-qsfp-dd"]).split())
    assert "18 pairs" in text
    assert "800G port or two ports" in text
    assert "Figure 9" in text
    assert "red line" in text
    assert "not stated in its text" in text


def test_zr_ports_names_exactly_the_highlighted_eighteen():
    """The ZR/ZR+ ports are the 18 Figure 9 highlights, and the note says they are read off the figure."""
    text = " ".join(str(_device()["attrs"]["features"]["zr-ports"]).split())
    listed = text.split("blue - ", 1)[1].split(", the 18", 1)[0].replace(" and ", ", ")
    assert [int(n) for n in listed.split(", ")] == HIGHLIGHTED
    assert "read off the figure" in text


def test_the_two_gaps_are_declared_with_a_reason_and_a_wanted():
    """The pair exclusion cannot be stated as data (nos-dependent); the 800G member is vendor-silent."""
    exclusion = _gap("port-pair-exclusion-not-statable")
    assert exclusion["reason"] == "nos-dependent" and exclusion["reason"] in SERVICE_REASONS
    assert exclusion["scope"] == ["qsfpdd-800g-service"]
    assert exclusion["wanted"].strip()
    member = _gap("which-cage-of-a-pair-runs-800g")
    assert member["reason"] == "vendor-silent" and member["reason"] in SERVICE_REASONS
    assert member["scope"] == [f"port-{n}" for n in range(36)]
    assert member["wanted"].strip()
    assert "does not say" in " ".join(member["note"].split())
    assert "read from Figure 9" in " ".join(member["note"].split())


def test_no_attr_states_which_cage_of_a_pair_runs_800g_beyond_the_figure_reading():
    """Only the 18 placements' speeds and the figure-reading prose say it: no group or device attr does."""
    d = _device()
    for name, grp in d["groups"].items():
        if name == "qsfpdd-800g-service":
            assert grp["attrs"] == {"media": "qsfp-dd"}
    stating = {n for n, p in _service_ports().items() if (p.get("attrs") or {}).get("speed") == "800g"}
    assert stating == set(HIGHLIGHTED)
    for section, key in (("performance", "port-modes-qsfp-dd"), ("features", "zr-ports")):
        text = " ".join(str(d["attrs"][section][key]).split())
        assert "Figure 9" in text, key
    assert "is not stated in its text" in " ".join(d["groups"]["qsfpdd-800g-service"]["description"].split())


def test_the_committed_device_types_say_what_the_placements_say():
    """In both exports the 18 highlighted cages are 800G and the other 18 are 400G; the fabric stays 800G."""
    for target in ("netbox", "nautobot"):
        path = LIB / "exports" / target / "device-types" / "UfiSpace" / "S9720-56ED.yaml"
        doc = yaml.safe_load(path.read_text())
        types = {i["name"]: i["type"] for i in doc["interfaces"]}
        for n in HIGHLIGHTED:
            assert types[f"port-{n}"] == "800gbase-x-qsfpdd", (target, n)
        for n in PARTNERS:
            assert types[f"port-{n}"] == "400gbase-x-qsfpdd", (target, n)
        assert all(types[f"fabric-{n}"] == "800gbase-x-qsfpdd" for n in range(20))
