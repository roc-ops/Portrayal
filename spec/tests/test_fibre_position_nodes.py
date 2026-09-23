"""L110: every fibre position a connector declares is a node you can point at.

A fibre endpoint `X.n` in `optical.paths` is drawn at path `X/n`. The explorer
and every consumer turn one into the other without a table, which only holds
if the connector draws nodes `1`..`N` for its `optical.positions: N` - a
composed bore, or a contracted element of class `fibre`.
"""
import pathlib

import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = [str(ROOT / "library")]
P = "library/components/common/x-adapter/v1/contract.yaml"


def l110(data, path=P):
    got = []
    real = lint.err
    lint.err = lambda p, rule, msg: got.append((rule, msg))
    try:
        lint.lint_component_optical_position_nodes(path, data, LIB)
    finally:
        lint.err = real
    return [m for r, m in got if r == "L110"]


def port(n, parts=(), elements=None):
    d = {"class": "port", "optical": {"positions": n}, "parts": list(parts)}
    if elements is not None:
        d["elements"] = elements
    return d


def el(x):
    return {"at": [x, 0.0], "size": [0.1, 0.1], "class": "fibre"}


def test_composed_bores_numbered_pass():
    assert l110(port(2, [{"id": "1", "ref": "std/lc-bore@3"}, {"id": "2", "ref": "std/lc-bore@3"}])) == []


def test_elements_numbered_pass():
    assert l110(port(3, elements={"1": el(0), "2": el(1), "3": el(2), "opening": el(5)})) == []


def test_tx_rx_bores_fail_naming_both_positions():
    msgs = l110(port(2, [{"id": "tx", "ref": "std/lc-bore@3"}, {"id": "rx", "ref": "std/lc-bore@3"}]))
    assert msgs and "[1, 2]" in msgs[0]


def test_a_missing_position_fails():
    msgs = l110(port(12, elements={str(i): el(i) for i in range(1, 12)}))
    assert msgs and "[12]" in msgs[0]


def test_a_position_beyond_n_fails():
    msgs = l110(port(1, elements={"1": el(0), "2": el(1)}))
    assert msgs and "2" in msgs[0]


def test_not_a_port_or_no_positions_is_not_judged():
    assert l110({"class": "filter", "optical": {"positions": 2}}) == []
    assert l110({"class": "port"}) == []


def test_an_exempt_part_is_not_judged():
    p = "library/components/common/mdc-adapter/v1/contract.yaml"
    assert "common/mdc-adapter" in lint.POSITION_EXEMPT
    assert l110(port(4), path=p) == []


def test_a_rear_id_that_is_also_a_front_id_fails():
    d = {"class": "cassette", "parts": [{"id": "mtp1", "ref": "common/mpo-adapter@1"}],
         "faces": {"rear": {"ref": "fs/fhd-2mtp12-lc-rear@2"}}}
    msgs = l110(d)
    assert msgs and "mtp1" in msgs[0]


def test_every_exemption_names_a_part_that_exists_and_says_why():
    for key, why in lint.POSITION_EXEMPT.items():
        ns, name = key.split("/")
        assert list((ROOT / "library/components" / ns / name).glob("v*/contract.yaml")), key
        assert len(why.split()) >= 8, f"{key}: an exemption needs a reason, not a word"


def _position_ports():
    for f in sorted((ROOT / "library/components").glob("*/*/v*/contract.yaml")):
        d = yaml.safe_load(f.read_text())
        if d.get("class") == "port" and (d.get("optical") or {}).get("positions"):
            yield f, d


def test_every_position_bearing_port_is_covered():
    seen, failing = 0, {}
    for f, d in _position_ports():
        seen += 1
        msgs = l110(d, path=str(f.relative_to(ROOT)))
        if msgs:
            failing[str(f.relative_to(ROOT / "library/components"))] = msgs[0]
    assert seen >= 12, f"only {seen} position-bearing ports found - has the library moved?"
    assert not failing, failing


def test_the_exemptions_are_exactly_these():
    assert set(lint.POSITION_EXEMPT) == {"common/mdc-adapter", "common/fibre-splice"}


def test_fhd_1ufce_draws_each_fibre_at_its_endpoint_path():
    """lc01.1 is drawn at .../lc01/1 on the front; rear:mtp2.2 at .../mtp2/2 on the rear."""
    from portrayal import render
    lib = render.Library(LIB)
    dev = yaml.safe_load((ROOT / "library/devices/fs/fhd-1ufce/device.yaml").read_text())
    af = next(r for r in dev["views"]["front"]["components"]["bays"][0]["accepts"]
              if r.startswith("fs/fhd-2mtp12-lc-os2-af@"))
    cfg = {"bays": {"bay-1": af}}

    def paths(view):
        out = render.render_view(dev, view, dev["views"][view], lib, config_name="t", config=cfg)
        root = render.ET.fromstring(out) if isinstance(out, str) else out
        return ({e.get("data-path") for e in root.iter() if e.get("data-path")},
                {e.get("data-of") for e in root.iter() if e.get("data-of")})

    front, _ = paths("front")
    _, rear_of = paths("rear")
    assert {"bay-1/module/lc01/1", "bay-1/module/lc01/2"} <= front
    assert not any(p.endswith(("/tx", "/rx")) for p in front if p.startswith("bay-1/"))
    assert {f"bay-1/module/mtp2/{i}" for i in range(1, 13)} <= rear_of
    assert "bay-1/module/mtp2/opening" in rear_of
