"""A lamp can be marked as a programmable-colour light (#1271).

Some switches light each port in a colour the user chooses, not only a fixed link
and activity colour. The mark is `programmable: true` on a device's port group or
placement, with `programmable-note` naming the maker's own feature. It is drawn as
a neutral ring round the port the lamp belongs to, and carried in the elements
file, the device index and the DCIM comments.

Every document here is synthetic and lives in `tmp_path`: no library device
carries the mark. The ring is the one thing the mark adds to a face, so the
unmarked face is pinned by taking the ring and the attributes back out of the
marked one and comparing what is left to the face built without the mark.
"""
import copy
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "device-template.yaml"
TOOLS = ROOT / "spec" / "tools" / "portrayal"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())

from portrayal import dcim_export     # noqa: E402
from portrayal import render          # noqa: E402

SVG = "{http://www.w3.org/2000/svg}"
GROUP = ("  port-leds:\n    term: LED\n    role: indicator\n    index-origin: 1\n"
         "    description: one link/activity lamp above each SFP+ port\n")
LED4 = "{id: led-port-4, ref: common/led-dot@1, at: [75.75, 11.0], for: port-4, group: port-leds, rel-pos: 4}"
SYS = "attrs: {role: system}, group: status, rel-pos: 1}"


def marked_text():
    """The template with the group of four port lamps marked, the fourth lamp
    taking the mark back (a placement wins over its group), and the system lamp,
    which belongs to no port, marked on its own."""
    text = TEMPLATE.read_text()
    for old, new in ((GROUP, GROUP + "    programmable: true\n    programmable-note: Etherlighting\n"),
                     (LED4, LED4[:-1] + ", programmable: false}"),
                     (SYS, SYS[:-1] + ", programmable: true}")):
        assert old in text, old
        text = text.replace(old, new, 1)
    return text


def make_library(base, text):
    """A throwaway library holding one device, the real components linked."""
    lib = base / "library"
    (lib / "devices" / "example" / "ex-1u").mkdir(parents=True)
    (lib / "devices" / "example" / "ex-1u" / "device.yaml").write_text(text)
    (lib / "components").symlink_to(ROOT / "library" / "components", target_is_directory=True)
    schemas = base / "schemas"
    shutil.copytree(ROOT / "spec" / "schemas", schemas)
    vendors = schemas / "vendors.yaml"
    vendors.write_text(vendors.read_text().replace(
        "\nvendors:\n",
        "\nvendors:\n\n  example:\n    display: Example\n    role: hardware\n"
        "    source: 'a fictional vendor for a synthetic test'\n", 1))
    return lib, schemas


def build(base, text):
    lib, schemas = make_library(base, text)
    out = base / "dist"
    r = subprocess.run([sys.executable, str(TOOLS / "render.py"),
                        str(lib / "devices" / "example" / "ex-1u" / "device.yaml"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return lib, schemas, out


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    return build(tmp_path_factory.mktemp("plain"), TEMPLATE.read_text())


@pytest.fixture(scope="module")
def lit(tmp_path_factory):
    return build(tmp_path_factory.mktemp("lit"), marked_text())


def face(out):
    return (out / "ex-1u.base.front.svg").read_text()


def rows(out):
    doc = json.loads((out / "ex-1u.base.front.elements.json").read_text())
    return {r.get("path") or r.get("of"): r for r in doc["elements"]}


def rings(svg_text):
    return [e for e in ET.fromstring(svg_text).iter() if e.get("data-class") == "programmable-ring"]


# ---- the schema --------------------------------------------------------------

def errors(doc):
    return [f"{'/'.join(map(str, e.path))}: {e.message}"
            for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(doc)]


def test_the_schema_accepts_the_mark_on_a_group_and_on_a_placement():
    doc = yaml.safe_load(marked_text())
    assert doc["groups"]["port-leds"]["programmable"] is True
    placements = doc["views"]["front"]["components"]["placements"]
    assert [p["programmable"] for p in placements if "programmable" in p] == [False, True]
    assert errors(doc) == []


def test_the_template_without_the_mark_is_valid_as_before():
    assert errors(yaml.safe_load(TEMPLATE.read_text())) == []


@pytest.mark.parametrize("where", ["chassis", "bay", "view", "top"])
def test_the_schema_refuses_the_mark_in_any_other_home(where):
    doc = yaml.safe_load(TEMPLATE.read_text())
    target = {"chassis": doc["chassis"],
              "bay": doc["views"]["rear"]["components"]["bays"][0],
              "view": doc["views"]["front"],
              "top": doc}[where]
    target["programmable"] = True
    assert errors(doc), f"programmable accepted on {where}"


@pytest.mark.parametrize("home", ["group", "placement"])
@pytest.mark.parametrize("key,value", [("programmable", "yes"), ("programmable", 1),
                                       ("programmable-note", 3), ("programmable-note", True)])
def test_the_schema_refuses_a_value_of_the_wrong_kind(home, key, value):
    doc = yaml.safe_load(TEMPLATE.read_text())
    target = (doc["groups"]["port-leds"] if home == "group"
              else doc["views"]["front"]["components"]["placements"][4])
    target[key] = value
    assert errors(doc), f"{key}: {value!r} accepted on a {home}"


# ---- the drawing -------------------------------------------------------------

def test_an_unmarked_face_has_no_ring_and_no_attribute(plain):
    _lib, _schemas, out = plain
    text = face(out)
    assert not rings(text)
    assert "programmable" not in text


def test_a_marked_group_draws_a_ring_round_each_port_whose_lamp_it_marks(lit):
    _lib, _schemas, out = lit
    got = rings(face(out))
    # three of the four port lamps (the fourth took the mark back) and the system
    # lamp, which names no drawn port, rings itself
    of = sorted(e.get("data-ring-of") for e in got)
    assert of == ["port-1", "port-2", "port-3", "sys"], of
    assert all(e.get("data-programmable") == "true" for e in got)


def test_the_ring_is_neutral_grey_and_drawn_under_the_port(lit):
    _lib, _schemas, out = lit
    root = ET.fromstring(face(out))
    order = [e.get("id") for e in root]
    for ring in rings(face(out)):
        assert ring.get("stroke") == render.PROGRAMMABLE_RING
        assert ring.get("fill") == "none"
        assert render.PROGRAMMABLE_RING == "#9aa0a8"
        host = ring.get("data-ring-of")
        assert order.index(ring.get("id")) < order.index(host), \
            f"the ring of {host} is drawn over it"


def test_the_ring_encloses_the_port_and_reaches_no_neighbour(lit):
    _lib, _schemas, out = lit
    boxes = {r["path"]: r["box"] for r in rows(out).values()
             if r.get("path") in ("port-1", "port-2", "port-3", "port-4")}
    ring = next(e for e in rings(face(out)) if e.get("data-ring-of") == "port-2")
    x, y, w, h = (float(ring.get(k)) for k in ("x", "y", "width", "height"))
    b = boxes["port-2"]
    assert x < b["x"] and y < b["y"] and x + w > b["x"] + b["w"] and y + h > b["y"] + b["h"]
    reach = float(ring.get("stroke-width")) / 2
    for other in ("port-1", "port-3"):
        o = boxes[other]
        assert x - reach >= o["x"] + o["w"] or x + w + reach <= o["x"], \
            f"the ring of port-2 reaches {other}"


def test_the_marked_face_less_the_ring_is_the_unmarked_face(plain, lit):
    """An unmarked lamp draws as it always did: the mark adds the rings and the
    attributes and changes nothing else."""
    def bare(out):
        root = ET.fromstring(face(out))
        parents = {c: p for p in root.iter() for c in p}
        for e in [e for e in root.iter() if e.get("data-class") == "programmable-ring"]:
            parents[e].remove(e)
        for e in root.iter():
            for k in [k for k in e.attrib if k.startswith("data-programmable")]:
                del e.attrib[k]
        # the metadata names the hash of the source, which is not the same file
        for m in [e for e in root if e.tag == SVG + "metadata"]:
            root.remove(m)
        return ET.tostring(root)
    assert bare(plain[2]) == bare(lit[2])


# ---- the elements file -------------------------------------------------------

def test_the_elements_row_of_a_marked_lamp_carries_the_mark_and_the_note(lit):
    r = rows(lit[2])
    for lamp in ("led-port-1", "led-port-2", "led-port-3", "sys"):
        assert r[lamp]["programmable"] is True, lamp
    assert r["led-port-1"]["programmable-note"] == "Etherlighting"
    assert "programmable-note" not in r["sys"]


def test_no_other_row_and_no_unmarked_file_carries_the_key(plain, lit):
    for lamp in ("led-port-4", "port-1", "chassis"):
        assert "programmable" not in rows(lit[2])[lamp]
    text = (plain[2] / "ex-1u.base.front.elements.json").read_text()
    assert "programmable" not in text


@pytest.mark.heavy
def test_the_elements_files_differ_only_by_the_rows_the_mark_names(plain, lit):
    a, b = rows(plain[2]), rows(lit[2])
    assert a.keys() == b.keys()
    moved = {k for k in a if a[k] != b[k]}
    assert moved == {"led-port-1", "led-port-2", "led-port-3", "sys"}
    for k in moved:
        assert {x: y for x, y in b[k].items() if not x.startswith("programmable")} == a[k]


# ---- the device index and the DCIM export ------------------------------------

def index_entry(lib, out):
    r = subprocess.run([sys.executable, str(TOOLS / "devices_index.py"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((out / "devices.json").read_text())["devices"][0]


def test_the_index_says_ports_light_up_only_for_a_device_with_a_marked_lamp(plain, lit, tmp_path):
    a = index_entry(plain[0], tmp_path / "a")
    b = index_entry(lit[0], tmp_path / "b")
    assert "programmable-light" not in a
    assert b["programmable-light"] is True
    # the one new key; the rest of the entry, the search blob included, is as before
    assert {k: v for k, v in b.items() if k != "programmable-light"} == a


def test_the_fact_is_derived_never_authored():
    doc = yaml.safe_load(TEMPLATE.read_text())
    doc["programmable-light"] = True
    assert errors(doc), "a device must not be able to state the derived fact itself"


def test_the_dcim_comments_name_it_only_for_a_marked_device():
    plain_doc = yaml.safe_load(TEMPLATE.read_text())
    lit_doc = yaml.safe_load(marked_text())
    assert "programmable colour" not in dcim_export.comments_for(plain_doc, "base", None)
    lit_text = dcim_export.comments_for(lit_doc, "base", None)
    assert lit_text.count("programmable colour") == 1
    assert "Lamps with a programmable colour, set by the user (Etherlighting)." in lit_text
    unlit = copy.deepcopy(lit_doc)
    del unlit["groups"]["port-leds"]["programmable"]
    for p in unlit["views"]["front"]["components"]["placements"]:
        p.pop("programmable", None)
    assert "programmable colour" not in dcim_export.comments_for(unlit, "base", None)


def test_a_mark_on_a_group_nothing_uses_lights_nothing():
    doc = yaml.safe_load(TEMPLATE.read_text())
    doc["groups"]["status"]["programmable"] = True
    for p in doc["views"]["front"]["components"]["placements"]:
        if p.get("group") == "status":
            p["group"] = "port-leds"
    assert "programmable colour" not in dcim_export.comments_for(doc, "base", None)


# ---- the linter ---------------------------------------------------------------

@pytest.mark.heavy
def test_the_marked_synthetic_device_lints_as_the_unmarked_one_does(plain, lit):
    def codes(lib_schemas):
        lib, schemas, _out = lib_schemas
        r = subprocess.run([sys.executable, str(TOOLS / "lint.py"), "--schemas", str(schemas),
                            "--library", str(lib), "--device", "ex-1u"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        return sorted(re.findall(r"\[(L\d+)\]", r.stdout))
    assert codes(lit) == codes(plain)
    assert "L21" not in codes(lit) and "L13" not in codes(lit)
