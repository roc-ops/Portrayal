"""The console and USB receptacles of sixteen devices are parts a plug lands on, or are named for what they are.

Twelve devices draw a Mini-USB Type-B console as panel art (the EX2200-C, EX2300 and EX2300-C, with decor named for a
console, and the EX3400, with two unlabelled boxes): each places the registry's Mini-B receptacle, `std/mini-usb@1`, where
the art was. Eight devices (six Juniper, two MikroTik) already place a USB-A receptacle and draw its surround as a decor
box named `usb-shell` or `usb-bezel`; the box is renamed for what it is, so that lint L197 no longer reads it as a port.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEV = ROOT / "library" / "devices"
NAMES = yaml.safe_load((ROOT / "spec" / "schemas" / "connector-decor-names.yaml").read_text())["names"]
ART = {"console-shell", "console-opening", "console-pins", "usb-shell", "usb-bezel"}

# device -> (the placed console's `at`, its `rel-pos`, the device's mgmt group)
CONSOLE = {
    "juniper/ex2200-c-12p": ([228.65, 34.35], 3), "juniper/ex2200-c-12t": ([228.65, 34.35], 3),
    "juniper/ex2300-24p": ([425.7, 39.35], 0), "juniper/ex2300-24t": ([425.7, 39.35], 0),
    "juniper/ex2300-48p": ([425.7, 39.35], 0), "juniper/ex2300-48t": ([425.7, 39.35], 0),
    "juniper/ex2300-c-12p": ([233.95, 29.55], 3), "juniper/ex2300-c-12t": ([233.95, 29.55], 3),
    "juniper/ex3400-24p": ([424.55, 38.05], 2), "juniper/ex3400-24t": ([424.55, 38.05], 2),
    "juniper/ex3400-48p": ([424.55, 38.05], 2), "juniper/ex3400-48t": ([424.55, 38.05], 2),
}
# device -> the kind its USB-A surround is named now
SURROUND = {
    "juniper/ex2200-c-12p": "port-shell", "juniper/ex2200-c-12t": "port-shell",
    "juniper/ex2300-24mp": "port-shell", "juniper/ex2300-48mp": "port-shell",
    "juniper/ex2300-c-12p": "port-shell", "juniper/ex2300-c-12t": "port-shell",
    "mikrotik/ccr2116-12g-4s-plus": "bezel", "mikrotik/crs418-8p-8g-2s-plus-rm": "bezel",
}
SIXTEEN = sorted(set(CONSOLE) | set(SURROUND))


def device(slug):
    return yaml.safe_load((DEV / slug / "device.yaml").read_text())


def front(slug):
    return device(slug)["views"]["front"]


def decor(slug):
    return front(slug)["panel"]["decor"]


def placed(slug):
    return {p["id"]: p for p in front(slug)["components"]["placements"]}


def test_the_names_this_order_clears_are_still_the_ones_lint_reads_as_connectors():
    assert ART <= set(NAMES), "a decor name was dropped from the list this test is about"


@pytest.mark.parametrize("slug", sorted(CONSOLE))
def test_the_mini_usb_console_is_a_placed_registry_receptacle(slug):
    at, rel_pos = CONSOLE[slug]
    port = placed(slug)["console-usb"]
    assert port["ref"] == "std/mini-usb@1" and port["attrs"] == {"role": "console"}
    assert port["at"] == at and port["group"] == "mgmt" and port["rel-pos"] == rel_pos
    assert any(c.get("id") == "console-usb" and c["size"] == [7.7, 3.9] and c["at"] == at
               for c in front(slug)["panel"]["cutouts"] if "id" in c), "the faceplate has no opening for it"


@pytest.mark.parametrize("slug", SIXTEEN)
def test_no_decor_draws_a_console_or_usb_receptacle_any_more(slug):
    kinds = {d.get("kind") for view in device(slug)["views"].values() for d in (view.get("panel") or {}).get("decor") or []}
    assert not kinds & ART, sorted(kinds & ART)


@pytest.mark.parametrize("slug", ["juniper/ex3400-24p", "juniper/ex3400-24t", "juniper/ex3400-48p", "juniper/ex3400-48t"])
def test_the_ex3400_has_no_unlabelled_box_where_the_console_is(slug):
    boxes = [d for d in decor(slug) if "kind" not in d and "pattern" not in d and d.get("at", [0, 0])[1] > 37]
    assert not boxes, boxes


@pytest.mark.parametrize("slug", sorted(SURROUND))
def test_each_usb_surround_frames_a_usb_a_receptacle_that_was_already_placed(slug):
    shells = [d for d in decor(slug) if d.get("id") in ("usb-shell", "usb-bezel")]
    assert [d["kind"] for d in shells] == [SURROUND[slug]]
    assert placed(slug)["usb"]["ref"] == "std/usb-a@1"
    sx, sy = shells[0]["at"]
    ex, ey = shells[0]["size"]
    # the receptacle's own opening, turned upright, lies inside the surround
    cut = next(c for c in front(slug)["panel"]["cutouts"] if c.get("id") == "usb")
    assert sx <= cut["at"][0] and cut["at"][0] + cut["size"][0] <= sx + ex
    assert sy <= cut["at"][1] and cut["at"][1] + cut["size"][1] <= sy + ey


@pytest.mark.parametrize("slug", sorted(CONSOLE))
def test_each_console_says_its_shell_is_the_registrys_and_not_the_makers(slug):
    gaps = {g["what"]: g for g in device(slug).get("gaps") or []}
    assert "mini-usb-console-port" not in gaps
    gap = gaps["mini-usb-console-shell"]
    assert gap["scope"] == ["console-usb"] and gap["reason"] == "needs-photo"
    assert "Molex" in " ".join(gap["note"].split())


def test_the_two_consoles_no_held_source_places_are_still_gaps():
    # the EX9251 guide lists a Mini-USB Type-B console among its cables and draws none on the chassis; the NCS 5011 guide lists a USB interface
    # on the fan side and names no connector; neither is placed here
    ex9251 = device("juniper/ex9251")
    assert any(g["what"] == "console-usb" for g in ex9251["gaps"])
    assert not [p for v in ex9251["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "std/mini-usb@1"]
    ncs = yaml.safe_load((DEV / "cisco/ncs-5011/device.yaml").read_text())
    assert any(g["what"] == "usb-port" for g in ncs["gaps"])
