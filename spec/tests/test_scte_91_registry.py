"""The SCTE 91 stinger port is registered, and the library holds a part that
presents the port and a part that mates it.

The figures of the port are the documents' and no others: the Entra node guides
and data sheets name the port "SCTE-91", describe a threaded hole that takes a
stinger whose centre pin a seizure screw holds, and state neither the thread nor
the pin's diameter, so the registry entry claims neither and says so.
"""
import functools
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "spec" / "schemas" / "connectors.yaml"
COMPONENTS = ROOT / "library" / "components"


def _interfaces():
    return yaml.safe_load(REGISTRY.read_text())["interfaces"]


@functools.lru_cache(maxsize=None)
def _contracts():
    return tuple(
        (path, yaml.safe_load(path.read_text()))
        for path in sorted(COMPONENTS.glob("*/*/v*/contract.yaml"))
    )


def _mates(interface):
    out = []
    for path, c in _contracts():
        m = c.get("mates")
        names = m if isinstance(m, list) else [m]
        if interface in names:
            out.append(f"{path.parts[-4]}/{path.parts[-3]}")
    return out


def _presenters(interface):
    return [
        f"{p.parts[-4]}/{p.parts[-3]}"
        for p, c in _contracts()
        if c.get("interface") == interface
    ]


def test_scte_91_is_registered_and_claims_no_figure_a_document_does_not_state():
    entry = _interfaces()["scte-91"]
    note = " ".join(entry["note"].split())
    assert "unknown" in note, "the thread and the pin diameter are unstated and the note must say so"
    assert "standard" not in entry, "no SCTE 91 text is held, so the entry cites no standard"
    for invented in ("5/8", "24 UNEF", "UNEF"):
        assert invented not in note, f"{invented!r} is a thread no held document states"


def test_scte_91_has_a_mate_and_a_presenter():
    assert _mates("scte-91"), "no part mates scte-91"
    assert _presenters("scte-91"), "no part presents scte-91"
    assert "unmated" not in _interfaces()["scte-91"]


def test_the_port_plug_is_the_half_inch_hex_the_guides_name():
    c = yaml.safe_load((COMPONENTS / "generic" / "scte-91-port-plug" / "v1" / "contract.yaml").read_text())
    assert c["mates"] == "scte-91"
    assert c["class"] == "port"
    # the guides remove the plug with a 1/2 inch socket or wrench: 12.7 across the flats
    assert c["size"]["h"] == 12.7
    assert abs(c["size"]["w"] - 12.7 / 0.8660254) < 0.01  # across the corners
    assert c["size-confidence"]["h"] == "datasheet"


def test_the_port_presents_scte_91_and_declares_what_it_estimates():
    c = yaml.safe_load((COMPONENTS / "common" / "scte-91-port" / "v1" / "contract.yaml").read_text())
    assert c["interface"] == "scte-91"
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert c["connection-points"]["mate"]["direction"] == "front"
    assert "size" in c["provenance"]
    # the port opening takes the plug's head
    plug = yaml.safe_load((COMPONENTS / "generic" / "scte-91-port-plug" / "v1" / "contract.yaml").read_text())
    assert c["size"]["w"] >= plug["size"]["w"] and c["size"]["h"] >= plug["size"]["h"]


def test_no_sealed_fibre_gland_key_is_registered():
    # the data sheets list the fibre ports as SCTE-91 ports: a gland threads into the same port,
    # so it mates scte-91 and needs no interface of its own
    assert not [k for k in _interfaces() if "gland" in k]
