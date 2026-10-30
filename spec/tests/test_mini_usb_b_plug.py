"""The Mini-B cable plug, and the two parts that present `mini-usb-b`.

`generic/mini-usb-b-plug@1` mates the registered `mini-usb-b` interface, which
std/mini-usb@1 (six Cisco switches) and juniper/ex4300-console-usb-mini@1
(eight Juniper switches) present. These run against the real library, a
components index built by the indexer the build runs and device copies
rendered here, never a possibly stale dist.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from portrayal.manifest import presented_interface
from test_coax_slots import _contract, _skin_path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"

PLUG = "generic/mini-usb-b-plug@1"
USB_A_PLUG = "generic/usb-a-plug@1"
CONSOLE = "juniper/ex4300-console-usb-mini@1"
RECEPTACLE = "std/mini-usb@1"

# device -> the id its Mini-B console is placed under
JUNIPER = {
    "juniper/ex4300-24p": "console", "juniper/ex4300-24t": "console",
    "juniper/ex4300-32f": "console", "juniper/ex4300-48mp": "console",
    "juniper/ex4300-48p": "console", "juniper/ex4300-48t": "console",
    "juniper/ex4550-32f": "console-mini", "juniper/ex4550-32t": "console-mini",
}
CISCO = {
    "cisco/c9300-24p": "console-usb", "cisco/c9300-24u": "console-usb",
    "cisco/c9300-48p": "console-usb", "cisco/c9300-48t": "console-usb",
    "cisco/c9300-48u": "console-usb", "cisco/ws-c3650-48pd": "usb-console",
}

# What the plug reads from the USB 2.0 Mini-B connector ECN (rev D), figure by
# figure. Each is pinned with the figure it comes from.
SHELL_W = 6.8          # fig 6-15: 6.8 +0.04/-0.05
SHELL_H = 3.0          # fig 6-15: 3 +0.04/-0.05
SHELL_CUT_AT = 1.08    # fig 6-15: 1.08 +/-0.05, where the sides start to cut in
SHELL_NECK = 1.65      # fig 6-15: 1.65 +/-0.05, where the cut ends
SHELL_FLAT = 5.67      # fig 6-15: 5.67 +/-0.05, the bottom flat
SHELL_LEN = 6.8        # fig 6-8 and 6-15: 6.8 MIN, front of the shell to the overmould
OVERMOULD_W = 11.0     # fig 6-8: 11.0 MAX (the end view stands the opening on end)
OVERMOULD_H = 8.5      # fig 6-8: 8.5 MAX
OVERMOULD_LEN = 20.0   # fig 6-8: 20.0 REF
OVERALL_LEN = 27.0     # fig 6-8: 27.0 REF, overmould and strain relief
RECEPTACLE_DEPTH = 5.5  # fig 6-11: 5.5 +0.1/-0, receptacle mouth to the wall
MODELLED_DEPTH = 9.0   # std/mini-usb@1's own size.d
STUB = 30.0
INSERTED = SHELL_LEN - RECEPTACLE_DEPTH            # 1.3 of shell stands in front
RELIEF_LEN = OVERALL_LEN - OVERMOULD_LEN           # 7.0
BODY_END = INSERTED + OVERMOULD_LEN                # 21.3
BOOT_END = BODY_END + RELIEF_LEN                   # 28.3


def feats():
    return {f["node"]: f for f in _contract(PLUG)["relief"]["features"]}


def prov(key):
    return " ".join(_contract(PLUG)["provenance"][key].split())


# --- 1. the plug ---------------------------------------------------------------

def test_the_plug_is_a_port_that_mates_mini_usb_b():
    d = _contract(PLUG)
    assert d["class"] == "port" and d["mates"] == "mini-usb-b"
    assert "interface" not in d and "behaviour" not in d
    assert d["attrs"] == {"media": "mini-usb-b", "connector": "mini-usb-b"}
    assert d["unplaced"] == _contract(USB_A_PLUG)["unplaced"]


def test_the_plug_states_no_standard_and_no_depth():
    """No `standards.yaml` entry is written for it, and a behaviour-less
    part's `size.d` would be built as a pit."""
    d = _contract(PLUG)
    assert "conforms" not in d
    assert "d" not in d["size"]
    assert set(d["fields"]) == {"cable-od", "jacket-color"}


# --- 2. the console part -------------------------------------------------------

def test_the_juniper_console_presents_mini_usb_b_and_kept_its_drawing():
    d = _contract(CONSOLE)
    assert d["version"] == "1.1.0"
    got, at, _lift = presented_interface(d, lambda r: _contract(r))
    assert got == "mini-usb-b"
    assert d["size"] == {"w": 7.9, "h": 4.6}
    assert d["connection-points"]["mate"]["at"] == [3.95, 2.3]
    assert d["attrs"] == {"media": "mini-usb-b", "role": "console"}
    assert at == pytest.approx([3.95, 2.3])
    assert "interface" in d["provenance"]


# --- 3 and 4. the slots on the devices ----------------------------------------

@pytest.fixture(scope="module")
def slots(tmp_path_factory):
    """{device: {placement id: the connector slot the build publishes}}."""
    tmp = tmp_path_factory.mktemp("miniusbslots")
    out = {}
    for device in list(JUNIPER) + list(CISCO):
        name = device.split("/")[1]
        dev = tmp / name / "device.yaml"
        shutil.copytree(LIB / "devices" / device, dev.parent)
        o = tmp / name / "o"
        r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                            "--out", str(o)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        configs = json.loads((o / f"{name}.configs.json").read_text())
        out[device] = {c["id"]: c for cages in configs["cages"].values() for c in cages}
    return out


@pytest.mark.parametrize("device", sorted(JUNIPER))
def test_a_juniper_console_is_a_mini_usb_b_slot_that_offers_the_plug(slots, device):
    slot = slots[device][JUNIPER[device]]
    assert slot["kind"] == "connector" and slot["interface"] == "mini-usb-b", slot
    assert PLUG in slot["accepts"], slot


@pytest.mark.parametrize("device", sorted(CISCO))
def test_a_cisco_console_slot_offers_the_plug(slots, device):
    slot = slots[device][CISCO[device]]
    assert slot["kind"] == "connector" and slot["interface"] == "mini-usb-b", slot
    assert PLUG in slot["accepts"], slot


def test_the_plug_is_listed_by_the_indexer():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    refs = {f"{e['ns']}/{e['name']}@{e['major'][1:]}" for e in doc["components"]}
    assert PLUG in refs


# --- 5. the figures, as the provenance says it read them ------------------------

def test_the_overmould_is_the_maximum_the_ecn_gives():
    d = _contract(PLUG)
    assert d["size"] == {"w": OVERMOULD_W, "h": OVERMOULD_H}
    assert d["size-confidence"] == {"w": "drawing", "h": "drawing"}
    text = prov("size")
    assert "figure 6-8" in text and "11.0 MAX" in text and "8.5 MAX" in text
    assert d["connection-points"]["mate"]["at"] == [OVERMOULD_W / 2, OVERMOULD_H / 2]


def test_the_shell_skin_is_the_figure_6_15_outline():
    """The path's points, read back: 6.8 x 3.0, straight for 1.08, cut to the
    1.65 line, a 5.67 flat, centred in the overmould."""
    d = _skin_path(PLUG).read_text()
    path = d[d.index('id="shell"'):].split("/>", 1)[0].split(' d="', 1)[1].split('"', 1)[0]
    toks = path.split()
    pts, x, y, i = [], None, None, 0
    while i < len(toks):
        t = toks[i]
        if t in ("M", "L"):
            x, y = float(toks[i + 1]), float(toks[i + 2]); i += 3
        elif t == "H":
            x = float(toks[i + 1]); i += 2
        elif t == "V":
            y = float(toks[i + 1]); i += 2
        else:
            assert t == "Z", t
            i += 1
            continue
        pts.append((round(x, 3), round(y, 3)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    assert max(xs) - min(xs) == pytest.approx(SHELL_W)
    assert max(ys) - min(ys) == pytest.approx(SHELL_H)
    assert (min(xs) + max(xs)) / 2 == pytest.approx(OVERMOULD_W / 2)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(OVERMOULD_H / 2)
    top, bottom = min(ys), max(ys)
    assert sorted({y - top for y in ys}) == pytest.approx([0, SHELL_CUT_AT, SHELL_NECK, SHELL_H])
    flat = [p[0] for p in pts if p[1] == bottom]
    assert max(flat) - min(flat) == pytest.approx(SHELL_FLAT)


def test_the_solids_chain_from_the_receptacle_face_to_the_stub():
    f = feats()
    assert set(f) == {"shell", "body", "relief-boot", "stub"}
    assert f["shell"]["out"] == pytest.approx(INSERTED) and not f["shell"].get("lift")
    assert f["body"]["lift"] == pytest.approx(INSERTED)
    assert f["body"]["out"] == pytest.approx(BODY_END)
    assert f["relief-boot"]["lift"] == pytest.approx(BODY_END)
    assert f["relief-boot"]["cyl"] == pytest.approx(RELIEF_LEN)
    assert f["stub"]["lift"] == pytest.approx(BOOT_END)
    assert f["stub"]["cyl"] == pytest.approx(STUB)
    assert "color" not in f["stub"]    # L73: the node a field paints states no colour


def test_the_skin_draws_what_the_relief_builds():
    s = _skin_path(PLUG).read_text()
    for node in feats():
        assert f'id="{node}"' in s, node
    boot = s[s.index('id="relief-boot"'):].split("/>", 1)[0]
    assert 'r="4.0"' in boot                      # 8.0 across, provenance.relief-boot
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub and 'data-fill-from="jacket-color"' in stub
    assert float(stub.split('r="', 1)[1].split('"', 1)[0]) == pytest.approx(
        _contract(PLUG)["fields"]["cable-od"]["default"] / 2, abs=0.005)


def test_every_figure_not_read_from_the_ecn_is_estimated_and_names_its_drawing():
    f = feats()
    assert f["shell"]["confidence"] == "drawing"
    for node in ("body", "relief-boot", "stub"):
        assert f[node]["confidence"] == "estimated", node
    for key in ("body", "relief-boot", "cable-od", "size"):
        assert "needs-drawing" in prov(key), key


def test_the_seated_depth_ruling_is_recorded_with_its_arithmetic():
    text = prov("seated-depth")
    assert "MEASURED FROM THE FACE THE RECEPTACLE PRESENTS" in text
    assert "THE RECEPTACLE AS MODELLED DISAGREES" in text and "REVISIT" in text
    assert "6.8 - 5.5 = 1.3" in text
    assert f"{MODELLED_DEPTH:g}" in text and f"{MODELLED_DEPTH - RECEPTACLE_DEPTH:g}" in text
    assert INSERTED == pytest.approx(1.3)


def test_the_receptacle_still_models_the_depth_the_plug_quotes():
    """Fails by design when std/mini-usb@1's depth is revised: the plug's
    provenance quotes it, and is to be read again. Nothing the plug builds
    follows it."""
    assert _contract(RECEPTACLE)["size"]["d"] == pytest.approx(MODELLED_DEPTH)
    assert MODELLED_DEPTH > RECEPTACLE_DEPTH + 0.25


def test_the_plug_names_which_way_is_up():
    text = prov("orientation")
    assert "CUT CORNERS" in text and "BOTTOM" in text and RECEPTACLE in text
