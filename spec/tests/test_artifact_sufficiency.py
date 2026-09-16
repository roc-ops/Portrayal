"""A consumer holding only `dist/` can export DCIM YAML.

THE POINT. Exporting a NetBox document used to require a checkout: the exporter
read `spec/schemas/vendors.yaml` and `devices/*/*/overlays/*.yaml` off the source
tree. Everything else it needed already shipped - the compiled SVG embeds the
whole device manifest in its <metadata>, and components.json carries every
contract field the exporter takes off a component - so those two files were the
entire distance between "download the development environment" and "fetch some
JSON". registry_index.py publishes them; these tests are what keeps them
published, and keeps them whole.

Each test below names the artifact a consumer would be missing if it failed.
"""
import json
import pathlib
import re
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"

pytestmark = pytest.mark.skipif(
    not (DIST / "vendors.json").exists(),
    reason="dist/ not built; run ./build.sh")


def load(name):
    return json.loads((DIST / name).read_text())


# ---- the two newly published files ------------------------------------------

def test_every_vendor_in_the_registry_ships():
    src = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())
    assert set(load("vendors.json")["vendors"]) == set(src["vendors"] or {})


def test_the_namespaces_ship_too():
    """`common` and `std` are not companies, and a consumer resolving a component
    ref hits them first. Publishing vendors without them exports a document that
    attributes a standard SFP cage to a manufacturer called 'std'."""
    assert load("vendors.json")["namespaces"], "namespaces were dropped"


def test_every_overlay_on_disk_is_published():
    on_disk = {f"{f.parents[2].name}/{f.parents[1].name}:{f.stem}"
               for f in ROOT.glob("library/devices/*/*/overlays/*.yaml")}
    shipped = {f"{dev}:{prof}"
               for dev, profs in load("overlays.json")["overlays"].items()
               for prof in profs}
    assert on_disk == shipped


def test_an_overlay_ships_whole_not_just_its_identity():
    """The exporter reads `identity:` today. `terms`, `interfaces` and
    `entity-map` are the NOS mapping - what says the port silkscreened 1 is
    called swp1 and answers to sfp1 over OpenConfig - and a consumer joining a
    drawing to a live device wants precisely that. Publishing half of a document
    only buys a second pass later to publish the other half."""
    ov = load("overlays.json")["overlays"]["edgecore/as7726-32x"]["arcos"]
    src = yaml.safe_load(
        (ROOT / "library/devices/edgecore/as7726-32x/overlays/arcos.yaml").read_text())
    assert ov == src, "the published overlay is not the overlay"


def test_an_identitys_vendor_resolves_in_the_published_registry():
    """The join the exporter actually performs: an overlay names a vendor key,
    the registry turns it into a display name. If a key resolved only in the
    source tree, a consumer would export the raw key - 'arrcus', not 'Arrcus'."""
    vendors = load("vendors.json")["vendors"]
    seen = 0
    for _, profs in load("overlays.json")["overlays"].items():
        for doc in profs.values():
            ident = doc.get("identity")
            if not ident:
                continue
            seen += 1
            assert ident["vendor"] in vendors, \
                f"overlay names vendor {ident['vendor']!r}, absent from the registry"
    assert seen, "no overlay declares an identity; this test proved nothing"


# ---- what already shipped, asserted so it keeps shipping ---------------------

# The five keys dcim_export reads off a resolved component contract.
CONTRACT_FIELDS = ("attrs", "description", "kind", "name", "parts")


def test_components_json_carries_every_contract_field_the_exporter_reads():
    comps = load("components.json")["components"]
    entries = comps if isinstance(comps, list) else list(comps.values())
    for field in CONTRACT_FIELDS:
        assert any(field in e for e in entries), \
            f"no component publishes {field!r}; the exporter reads it off contract.yaml"


def test_a_published_part_is_shaped_like_the_one_it_stands_for():
    """PRESENCE IS NOT SUFFICIENCY, which is how this file was wrong once.

    The check above asks whether `parts` is published and passed while the index
    flattened every part to a bare ref string. The exporter reads `ref`, `id` and
    `attrs` off a part - the id because `d0` is a downstream port and `u0` an
    upstream one where the ref says only that both are MCX, and the attrs because
    a placement is more specific than its cage: the same SFP is 1G or 10G
    depending on `attrs.speed`.

    Reading the index instead of the contract therefore dropped all eighteen
    interfaces off a 6+12 I/O card and exported ten Casa SMM ports at the wrong
    speed. Both were caught by diffing output, not by this file - so it now
    checks the shape.
    """
    comps = load("components.json")["components"]
    entries = comps if isinstance(comps, list) else list(comps.values())
    withparts = [e for e in entries if e.get("parts")]
    assert withparts, "no component publishes any parts"
    for e in withparts:
        for part in e["parts"]:
            assert isinstance(part, dict), \
                f"{e.get('ns')}/{e.get('name')}: a part is {type(part).__name__}, not a mapping"
            assert "ref" in part, f"{e.get('name')}: a part with no ref"
    # and the two fields that carry meaning beyond the ref are actually present
    # somewhere, or the drop would go unnoticed again
    assert any(p.get("id") for e in withparts for p in e["parts"]), "no part carries an id"
    assert any(p.get("attrs") for e in withparts for p in e["parts"]), "no part carries attrs"


def test_the_compiled_svg_embeds_the_device_manifest():
    """Why a consumer needs no device.yaml. Not a stripped summary - the source
    manifest, every view of it."""
    svg = (DIST / "as7726-32x.ac-f2b.front.svg").read_text()
    meta = json.loads(re.search(r"<metadata[^>]*>(.*?)</metadata>", svg, re.S).group(1))
    src = meta["source"]
    for key in ("attrs", "chassis", "configurations", "groups", "manufacturer", "model"):
        assert key in src, f"the embedded manifest is missing {key!r}"
    assert len(src["views"]) > 1, "only one view embedded; a consumer sees one face"


# ---- the gap this did NOT close ---------------------------------------------

def test_the_overlays_declared_interface_names_are_what_the_exporter_reads():
    """THE JOIN, NOW A READ RATHER THAN A PIN.

    `nos_name()` used to hardcode arcos as swp{n}/ma1 in Python while the arcos
    overlay declared exactly that as data, and this test held the two together
    by asserting they agreed. The exporter now reads the published overlay -
    `overlay_names()` over overlays.json - so there is one statement of the
    fact and this checks it is the published one being read: a JS consumer and
    the exporter answer "what does ArcOS call port 7" from the same bytes.
    `spec/tests/test_dcim_nos_overlay.py` runs the export itself.
    """
    from portrayal.dcim_export import overlay_names
    doc = load("overlays.json")["overlays"]["edgecore/as7726-32x"]["arcos"]
    names = overlay_names(doc)
    assert names["port-7"][0] == "swp7"
    assert names["mgmt-eth"][0] == "ma1"
    assert names["port-7"][1]["modes"], "the breakout modes the Python never read"


# ---- the export runs against a build, with no library in sight --------------

def test_the_dcim_export_needs_no_source_tree():
    """THE CLAIM THIS FILE EXISTS TO MAKE, RUN RATHER THAN ARGUED.

    The export is copied into a bare directory with `dist/` beside it and
    NOTHING ELSE - no library/, no spec/ - and asked to produce a device type.
    If it opens a contract, a manifest or vendors.yaml, it cannot find one and
    the test fails.

    That is what makes the exporter portable rather than merely relocatable: the
    same run works from a release tarball, which is the whole point of publishing
    the artifacts in the first place.
    """
    import shutil
    import subprocess
    import tempfile

    tools = ROOT / "spec/tools/portrayal"
    with tempfile.TemporaryDirectory() as tmp:
        sand = pathlib.Path(tmp)
        (sand / "tools").mkdir()
        # CODE travels with the exporter; DATA is what must come from dist.
        # manifest.py is imported for `view_parts`, which flattens a view dict
        # and opens nothing - a helper, not a route back into the library.
        # optical_ports.py, optical.py and faces.py are the fibre-graph
        # projection `build_module` now calls for any module with `optical.paths`;
        # they take an index entry and a lookup function, same as manifest.py,
        # so they travel the same way.
        for f in ("dcim_export.py", "artifacts.py", "manifest.py",
                  "optical_ports.py", "optical.py", "faces.py"):
            shutil.copy(tools / f, sand / "tools" / f)
        # dist/ is the ONLY input. Copied by name so that anything not on the
        # published contract is genuinely absent rather than merely unused.
        (sand / "dist").mkdir()
        for name in ("devices.json", "components.json", "vendors.json", "overlays.json"):
            shutil.copy(DIST / name, sand / "dist" / name)
        for svg in DIST.glob("as7726-32x.*.svg"):
            shutil.copy(svg, sand / "dist" / svg.name)

        r = subprocess.run(
            [sys.executable, str(sand / "tools" / "dcim_export.py"),
             "--dist", str(sand / "dist"), "--out", str(sand / "out"),
             "--device", "as7726-32x", "--nos", "arcos"],
            capture_output=True, text=True, cwd=tmp)
        assert r.returncode == 0, f"export failed away from the tree:\n{r.stderr[-800:]}"

        made = sorted(p.name for p in (sand / "out").rglob("*.yaml"))
        assert made, "no device type written"
        # the overlay identity has to survive the journey too: this device is
        # sold as ArcOS on Edgecore metal, and that fact lives in overlays.json
        assert any(n.startswith("ArcOS on ") for n in made), made[:4]
        doc = yaml.safe_load((sand / "out").rglob("ArcOS on *.yaml").__next__().read_text())
        assert doc["manufacturer"] == "Arrcus", doc["manufacturer"]
        assert doc.get("interfaces"), "no interfaces named for the NOS"


def test_a_module_image_is_asked_for_by_a_name_the_build_publishes():
    """The export's own filename construction, checked against the real tree.

    A module's picture is `{ns}--{name}--{major}--default.svg` in `dist/`, and
    `major` arrives from components.json ALREADY prefixed - it is the version
    directory's name. Prefixing it again yields `--vv1--`, which no build
    produces, and `rasterize` answers None for an absent drawing rather than
    raising: the whole pass rendered 0 of 376 and said so on a line `publish.sh`
    sends to /dev/null.

    So this asserts the name rather than the count. `rasterize` is stood in for,
    because what is being checked is which path the export asks for - not
    whether cairosvg is installed.
    """
    from portrayal import dcim_export

    asked = []
    real, dcim_export.rasterize = dcim_export.rasterize, (
        lambda src, png, scale: asked.append(pathlib.Path(src)) or src)
    try:
        dist = dcim_export.Dist(DIST)
        contracts = [c for c in dist.modules() if dist.manufacturer_of(c.get("ns"))]
        assert contracts, "no module contracts with a manufacturer"
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dcim_export.export_modules(dist, tmp, images=str(DIST))
    finally:
        dcim_export.rasterize = real

    assert asked, "no module image was even attempted"
    missing = sorted({p.name for p in asked if not p.exists()})
    assert not missing, (
        f"{len(missing)} of {len(asked)} module images named a drawing that is "
        f"not in the build: {missing[:4]}")
