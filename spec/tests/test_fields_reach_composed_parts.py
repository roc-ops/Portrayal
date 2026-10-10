"""A composed part takes its host's field value when both declare the field
(docs/pluggables-heads-design.md decision 4). The kit already does this at
runtime - kit/fields.js paints every matching node inside the part's group -
and the build did not, which is why the QSFP generics painted their own tab."""
import pathlib

from portrayal import render as render_mod

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
FIELD = {"latch-color": {"label": "Latch colour", "type": "text", "default": "#6f6f6f"}}


def _lib(tmp_path, child_fields, part_attrs=None):
    lib = render_mod.Library([str(LIB)])
    for name, body in (("host", '<rect id="body" width="10" height="5"/>'),
                       ("tab", '<rect id="grip" width="10" height="1" fill="#6f6f6f" '
                               'data-fill-from="latch-color"/>')):
        d = tmp_path / name / "skins"; d.mkdir(parents=True)
        (d / "default.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
    part = {"ref": "local/tab@1", "id": "tab", "at": [0, 0]}
    if part_attrs:
        part["attrs"] = part_attrs
    lib.cache["local/host@1"] = ({"format": 1, "kind": "component", "name": "host",
        "version": "1.0.0", "class": "transceiver", "size": {"w": 10, "h": 5},
        "skins": ["default"], "fields": FIELD, "parts": [part]}, tmp_path / "host/skins")
    lib.cache["local/tab@1"] = ({"format": 1, "kind": "component", "name": "tab",
        "version": "1.0.0", "class": "latch", "size": {"w": 10, "h": 1},
        "skins": ["default"], "fields": child_fields}, tmp_path / "tab/skins")
    return lib


def grip_fill(lib, attrs):
    g, _ = render_mod.instance_group(lib, "local/host@1", "h", [0, 0], None, attrs, None, None)
    return next(e for e in g.iter() if (e.get("id") or "").endswith("grip")).get("fill")


def test_the_hosts_value_reaches_a_composed_part_that_declares_the_field(tmp_path):
    assert grip_fill(_lib(tmp_path, FIELD), {"latch-color": "#1f5fbf"}) == "#1f5fbf"


def test_a_composed_part_that_does_not_declare_it_keeps_its_own(tmp_path):
    assert grip_fill(_lib(tmp_path, {}), {"latch-color": "#1f5fbf"}) == "#6f6f6f"


def test_the_parts_own_attrs_still_win(tmp_path):
    lib = _lib(tmp_path, FIELD, part_attrs={"latch-color": "#c22f2f"})
    assert grip_fill(lib, {"latch-color": "#1f5fbf"}) == "#c22f2f"


def test_unset_leaves_the_drawn_default(tmp_path):
    assert grip_fill(_lib(tmp_path, FIELD), None) == "#6f6f6f"


BEIGE = {"latch-color": {"label": "Latch colour", "type": "text", "default": "#d9cba3"}}


def _host_default(lib, default):
    host = lib.cache["local/host@1"][0]
    host["fields"] = {"latch-color": {**FIELD["latch-color"], "default": default}}
    return lib


def test_a_hosts_own_default_reaches_the_part_when_it_differs(tmp_path):
    """A host that defaults its tab to beige composes a tab whose own default
    is grey (generic/qsfp-mpo@1 did, until #773). Unset, the tab wears the
    host default."""
    lib = _host_default(_lib(tmp_path, FIELD), "#d9cba3")
    assert grip_fill(lib, None) == "#d9cba3"


def test_a_value_still_beats_the_hosts_default(tmp_path):
    lib = _host_default(_lib(tmp_path, FIELD), "#d9cba3")
    assert grip_fill(lib, {"latch-color": "#1f5fbf"}) == "#1f5fbf"


def test_a_default_equal_to_the_parts_own_is_not_handed_down(tmp_path):
    """So no drawing that agreed before gains an attribute."""
    lib = _lib(tmp_path, FIELD)
    g, _ = render_mod.instance_group(lib, "local/host@1", "h", [0, 0], None, None, None, None)
    tab = next(e for e in g.iter() if e.get("id") == "h--tab")
    assert tab.get("data-latch-color") is None


def test_an_empty_value_is_as_drawn_and_takes_the_hosts_default(tmp_path):
    """An empty string is the build's "leave it as drawn", the same as no
    value. With the key absent the tab wears the host's default; cleared to
    empty it must wear the same, not fall back to the tab's own grey."""
    lib = _host_default(_lib(tmp_path, FIELD), "#d9cba3")
    assert grip_fill(lib, {"latch-color": ""}) == "#d9cba3"
    assert grip_fill(lib, {"latch-color": ""}) == grip_fill(lib, None)
