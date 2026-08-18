"""Visio stencil extraction: geometry rendering and the OPC path.

Self-contained - builds a tiny .vssx in a temp dir rather than depending on
vendor stencils or on libvisio being installed.
"""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

SPEC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPEC / "tools" / "ndv"))
import visio_geom  # noqa: E402

NS = "http://schemas.microsoft.com/office/visio/2012/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

MASTER = f"""<?xml version='1.0' encoding='utf-8'?>
<MasterContents xmlns='{NS}' xmlns:r='{REL}'><Shapes>
 <Shape ID='1' NameU='Panel' Type='Group'>
  <Cell N='PinX' V='2'/><Cell N='PinY' V='1'/>
  <Cell N='Width' V='4'/><Cell N='Height' V='2'/>
  <Cell N='LocPinX' V='2'/><Cell N='LocPinY' V='1'/>
  <Shapes>
   <Shape ID='2' NameU='Face'>
    <Cell N='PinX' V='2'/><Cell N='PinY' V='1'/>
    <Cell N='Width' V='4'/><Cell N='Height' V='2'/>
    <Cell N='LocPinX' V='2'/><Cell N='LocPinY' V='1'/>
    <Cell N='FillForegnd' V='#112233'/>
    <Section N='Geometry' IX='0'>
     <Row T='MoveTo' IX='1'><Cell N='X' V='0'/><Cell N='Y' V='0'/></Row>
     <Row T='LineTo' IX='2'><Cell N='X' V='4'/><Cell N='Y' V='0'/></Row>
     <Row T='LineTo' IX='3'><Cell N='X' V='4'/><Cell N='Y' V='2'/></Row>
     <Row T='LineTo' IX='4'><Cell N='X' V='0'/><Cell N='Y' V='2'/></Row>
    </Section>
   </Shape>
  </Shapes>
 </Shape>
</Shapes></MasterContents>"""

MASTERS = f"""<?xml version='1.0' encoding='utf-8'?>
<Masters xmlns='{NS}' xmlns:r='{REL}'>
 <Master ID='1' NameU='Test Panel'><Rel r:id='rId1'/></Master>
</Masters>"""

RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="{REL}/master" Target="master1.xml"/></Relationships>"""


def _stencil(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("visio/masters/masters.xml", MASTERS)
        z.writestr("visio/masters/_rels/masters.xml.rels", RELS)
        z.writestr("visio/masters/master1.xml", MASTER)
    return path


def test_geometry_renders_to_svg():
    svg, w, h = visio_geom.master_to_svg(MASTER.encode())
    assert svg and "<path" in svg
    assert abs(w - 4.0) < 1e-6 and abs(h - 2.0) < 1e-6
    # inches converted to mm on the root element
    assert 'width="101.60mm"' in svg and 'height="50.80mm"' in svg
    # y-up geometry emitted inside the flip group
    assert "matrix(1 0 0 -1" in svg
    # declared fill colour survives
    assert "#112233" in svg


def test_extractor_names_output_by_master(tmp_path):
    src = _stencil(tmp_path / "Test Stencil.vssx")
    out = tmp_path / "out"
    subprocess.run([sys.executable, str(SPEC / "tools/ndv/visio_extract.py"),
                    str(src), "--out", str(out)], check=True, capture_output=True)
    stencil = out / "test-stencil"
    index = json.loads((stencil / "index.json").read_text())
    assert index["stencil"].endswith(".vssx")
    masters = index["masters"]
    assert masters[0]["master"] == "Test Panel"
    assert masters[0]["files"], "master should have a rendered file"
    named = stencil / "by-master" / "test-panel.svg"
    assert named.exists() and "<path" in named.read_text()
    assert (out / "index.html").exists()


# --------------------------------------------------------------- shapesheet

import struct  # noqa: E402

import visio_meta  # noqa: E402

SHEET = f"""<?xml version='1.0' encoding='utf-8'?>
<MasterContents xmlns='{NS}' xmlns:r='{REL}'><Shapes>
 <Shape ID='1' NameU='Cab' Type='Group'>
  <Cell N='Width' V='2'/><Cell N='Height' V='6'/>
  <Section N='Property'>
   <Row N='Row_1'><Cell N='Value' V='Vericom'/><Cell N='Label' V='Manufacturer'/></Row>
   <Row N='Row_2'><Cell N='Value' V='42'/><Cell N='Label' V='Rack Units'/></Row>
   <Row N='Row_3'><Cell N='Value' V='0'/><Cell N='Label' V='Asset Number'/></Row>
  </Section>
  <Section N='Connection'>
   <Row N='Con_1'><Cell N='X' V='0.5' F='Width*0.25'/><Cell N='Y' V='1'/></Row>
  </Section>
  <Section N='Hyperlink'>
   <Row N='Row_1'><Cell N='Description' V='Item Info'/><Cell N='Address' V='https://example.invalid/p'/></Row>
  </Section>
 </Shape>
</Shapes></MasterContents>"""


def test_shapesheet_keys_properties_by_label():
    info = visio_meta.shapesheet(SHEET.encode(), {"NameU": "Cab", "ID": "1"})
    assert info["properties"]["Manufacturer"] == "Vericom"
    assert info["properties"]["Rack Units"] == "42"
    # unfilled asset fields are dropped rather than recorded as "0"
    assert "Asset Number" not in info["properties"]
    assert info["master"]["NameU"] == "Cab"


def test_shapesheet_keeps_connection_formulas_and_links():
    info = visio_meta.shapesheet(SHEET.encode())
    conn = info["connections"][0]
    assert conn["x"] == 0.5
    # the formula is what makes a connection point portable across scales
    assert conn["x_formula"] == "Width*0.25"
    assert info["hyperlinks"][0]["address"] == "https://example.invalid/p"


def _emf_with_text(*parts):
    """Minimal EMF carrying one EMR_EXTTEXTOUTW record per fragment."""
    out = b""
    for s in parts:
        data = s.encode("utf-16le")
        pad = (-len(data)) % 4
        size = 76 + len(data) + pad
        rec = struct.pack("<II", 84, size) + b"\0" * 16 + struct.pack("<III", 1, 0, 0)
        rec += b"\0" * 8 + struct.pack("<II", len(s), 76) + b"\0" * 4 + b"\0" * 16 + b"\0" * 4
        rec += data + b"\0" * pad
        out += rec
    return out


def test_emf_text_reads_records_not_stray_bytes():
    blob = _emf_with_text("A9903", "-", "20HG", "STATUS")
    assert visio_meta.emf_text(blob) == ["A9903", "-", "20HG", "STATUS"]


def test_name_from_artwork_rejoins_split_model_numbers():
    blob = _emf_with_text("A9903", "-", "20HG", "-", "PEC", "STATUS", "0", "1")
    assert visio_meta.name_from_artwork(blob) == "A9903-20HG-PEC"
    # nothing model-like -> no guess, rather than a junk name
    assert visio_meta.name_from_artwork(_emf_with_text("CLASS 1", "LASER", "7")) is None


def test_suggest_name_uses_metadata_without_repeating_itself():
    p = {"Item Number": "VC5-8842", "View": "Side view"}
    assert visio_meta.suggest_name("VC5-8842-", p) == "VC5-8842 Side view"
    # master name already names the view - do not append the stencil-wide default
    assert visio_meta.suggest_name("VC5-8842-Top view", p) == "VC5-8842-Top view"
    # generic master name falls back to the artwork guess
    assert visio_meta.suggest_name("shape-002", {}, artwork_name="A9903-20HG") == "A9903-20HG"


def test_legacy_raw_dump_keeps_master_names(tmp_path, monkeypatch):
    """The raw libvisio dump names each master; the extractor must use it."""
    import base64 as _b64
    import visio_extract

    blob = _emf_with_text("A9903", "-", "20HG")
    dump = (
        "startDocument()\n"
        "  setDocumentMetaData(dc:creator: Visimation Inc., dc:title: Test Stencil)\n"
        f"  startPage(draw:name: A9903-20HG-PEC, svg:height: 0.15in, svg:width: 1.72in)\n"
        f"    drawGraphicObject (librevenge:mime-type: image/emf, "
        f"office:binary-data: {_b64.b64encode(blob).decode()})\n"
        "  endPage()\n")
    fake = tmp_path / "vss2raw"
    fake.write_text("#!/bin/sh\ncat <<'EOF'\n" + dump + "EOF\n")
    fake.chmod(0o755)
    monkeypatch.setattr(visio_extract.shutil, "which",
                        lambda n: str(fake) if n in ("vss2raw", "vsd2raw") else None)

    src = tmp_path / "legacy.vss"
    src.write_bytes(b"\xd0\xcf\x11\xe0" + b"\0" * 16)
    masters, media, docprops, note = visio_extract.read_ole(src)
    assert note is None
    assert len(media) == 1
    assert masters[0]["master"] == "A9903-20HG-PEC"
    assert masters[0]["width_in"] == 1.72
    assert docprops["dc:creator"] == "Visimation Inc."
    assert docprops["dc:title"] == "Test Stencil"
    assert visio_meta.suggest_name(masters[0]["master"], masters[0]["props"]) == "A9903-20HG-PEC"
