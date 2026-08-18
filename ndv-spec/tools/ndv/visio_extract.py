#!/usr/bin/env python3
"""Extract shape artwork from Visio stencils for use as intake reference.

Handles both stencil generations:

  .vssx / .vsdx   Open Packaging Convention (a zip). Masters are XML; artwork is
                  embedded as EMF/WMF/PNG under visio/media/. Parsed directly.
  .vss  / .vsd    Legacy OLE2 compound document holding one proprietary
                  VisioDocument stream. Needs an external parser (libvisio's
                  vsd2xhtml, which emits base64 images we decode).

Output per stencil:
  <out>/<stencil>/media/…         artwork exactly as embedded
  <out>/<stencil>/svg/…           vector conversions (if Inkscape is available)
  <out>/<stencil>/by-master/…     the same files named after their Visio master
  <out>/<stencil>/index.json      master -> shape properties + files
  <out>/index.html                contact sheet across every stencil

Vendor stencils are usually licensed for making diagrams only. Extracted art is
intake REFERENCE: read facts (port counts, positions, RU heights) from it and
author original NDV art. Do not commit or publish the extracted files.
"""
import argparse
import sys
import base64
import html
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import visio_geom
import visio_meta

V = "{http://schemas.microsoft.com/office/visio/2012/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
IMAGE_EXT = (".emf", ".wmf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg")
INKSCAPE = "/Applications/Inkscape.app/Contents/MacOS/inkscape"


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-") or "unnamed"


def inkscape():
    for c in (INKSCAPE, shutil.which("inkscape")):
        if c and Path(c).exists():
            return c
    return None


# ---------------------------------------------------------------- modern (OPC)

def _rels(zf, part):
    """Relationship id -> target, for a part inside the package."""
    p = Path(part)
    rel = f"{p.parent}/_rels/{p.name}.rels"
    try:
        with zf.open(rel) as fh:
            return {r.get("Id"): r.get("Target") for r in ET.parse(fh).getroot()}
    except KeyError:
        return {}


def _docprops(zf):
    """docProps/{core,app,custom}.xml - publisher, title, dates, custom fields."""
    out = {}
    for part in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
        if part not in zf.namelist():
            continue
        try:
            root = ET.fromstring(zf.read(part))
        except ET.ParseError:
            continue
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if part.endswith("custom.xml"):
                name = el.get("name")
                text = "".join(t.text or "" for t in el).strip()
                if name and text:
                    out[name] = text
            elif (el.text or "").strip() and tag not in ("Properties", "coreProperties"):
                out[tag] = el.text.strip()
    return out


def read_opc(path):
    """-> (masters, media, docprops); masters carry name, ShapeSheet and images."""
    masters, media = [], {}
    with zipfile.ZipFile(path) as zf:
        for n in zf.namelist():
            if n.lower().endswith(IMAGE_EXT):
                media[n] = zf.read(n)
        docprops = _docprops(zf)
        mrels = _rels(zf, "visio/masters/masters.xml")
        with zf.open("visio/masters/masters.xml") as fh:
            root = ET.parse(fh).getroot()
        for m in root.findall(f"{V}Master"):
            rel = m.find(f"{V}Rel")
            target = mrels.get(rel.get(f"{R}id")) if rel is not None else None
            if not target:
                continue
            part = f"visio/masters/{Path(target).name}"
            if part not in zf.namelist():
                continue
            irels = _rels(zf, part)
            with zf.open(part) as fh:
                mx = ET.parse(fh).getroot()
            part_bytes = zf.read(part)
            sheet = visio_meta.shapesheet(part_bytes, m.attrib)
            ps = m.find(f"{V}PageSheet")
            if ps is not None:
                scale = {c.get("N"): c.get("V") for c in ps.findall(f"{V}Cell")
                         if c.get("N") in ("PageScale", "DrawingScale", "PageWidth",
                                           "PageHeight", "DrawingScaleType")}
                if scale:
                    sheet["page"] = scale
            widths = [float(c.get("V")) for sh in mx.iter(f"{V}Shape")
                      for c in sh.findall(f"{V}Cell")
                      if c.get("N") == "Width" and re.fullmatch(r"-?[\d.]+", c.get("V") or "")]
            imgs = []
            for fd in mx.iter(f"{V}ForeignData"):
                rl = fd.find(f"{V}Rel")
                if rl is None:
                    continue
                t = irels.get(rl.get(f"{R}id"))
                if t:
                    imgs.append("visio/" + t.replace("../", ""))
            entry = {"master": m.get("NameU") or Path(target).stem,
                     "width_in": (sheet.get("size_in") or {}).get("width") or (max(widths) if widths else None),
                     "props": visio_meta.summarise(sheet),
                     "shapesheet": sheet,
                     "images": imgs}
            if not imgs:      # geometry-only stencil: render the shape tree
                svg, w_in, h_in = visio_geom.master_to_svg(part_bytes)
                if svg:
                    entry["geometry_svg"] = svg
                    entry["width_in"] = entry["width_in"] or w_in
                    entry["shapesheet"].setdefault("size_in", {})["height"] = h_in
            masters.append(entry)
    return masters, media, docprops


# ---------------------------------------------------------------- legacy (OLE2)

def read_ole(path):
    """Legacy .vss/.vsd via libvisio's raw dump.

    vss2raw emits the librevenge call sequence, and each stencil master arrives
    as a page carrying its real name:

        startPage(draw:name: A9903-20HG-PEC, svg:height: 0.1525in, svg:width: 1.7188in)
          drawGraphicObject (librevenge:mime-type: image/emf, office:binary-data: ...)

    So the names Visio shows in its stencil UI are recoverable after all - they
    are simply not in the rendered XHTML output. Parsed as a stream because the
    dump runs to tens of megabytes of base64.
    """
    tool = shutil.which("vss2raw" if path.suffix.lower() == ".vss" else "vsd2raw") \
        or shutil.which("vsd2raw") or shutil.which("vss2raw")
    if not tool:
        return [], {}, ("no parser for legacy Visio - the VisioDocument stream is "
                        "proprietary and compressed. Install one with: brew install libvisio")
    page_re = re.compile(r"startPage\(draw:name: (?P<name>.*?), svg:height: (?P<h>[\d.]+)in, "
                         r"svg:width: (?P<w>[\d.]+)in\)")
    img_re = re.compile(r"librevenge:mime-type: image/(?P<kind>[\w.+-]+), "
                        r"office:binary-data: (?P<b64>[A-Za-z0-9+/=]+)")
    # the metadata block spans lines - dc:description is a revision history
    meta_start = "setDocumentMetaData("
    masters, media, docprops = [], {}, {}
    cur, n, meta_buf = None, 0, None
    try:
        proc = subprocess.Popen([tool, str(path)], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, errors="ignore")
    except OSError as exc:
        return [], {}, f"could not run {tool}: {exc}"
    with proc.stdout as out:
        for line in out:
            if meta_buf is not None or (not docprops and meta_start in line):
                meta_buf = (meta_buf or []) + [line]
                joined = "".join(meta_buf)
                if joined.rstrip().endswith(")"):
                    body = joined[joined.index(meta_start) + len(meta_start):]
                    body = body.rstrip().rstrip(")")
                    for field in re.split(r",\s+(?=[a-z-]+:[a-z-]+:)", body):
                        if ": " in field:
                            k, v = field.split(": ", 1)
                            docprops[k.strip()] = " ".join(v.split())
                    meta_buf = None
                continue
            m = page_re.search(line)
            if m:
                cur = {"master": m.group("name").strip() or None,
                       "width_in": float(m.group("w")), "height_in": float(m.group("h"))}
                continue
            m = img_re.search(line)
            if not m or cur is None:
                continue
            try:
                blob = base64.b64decode(m.group("b64"))
            except Exception:
                continue
            n += 1
            ext = {"x-emf": "emf", "x-wmf": "wmf", "jpeg": "jpg"}.get(m.group("kind"), m.group("kind"))
            name = f"media/image{n}.{ext}"
            media[name] = blob
            labels = visio_meta.emf_text(blob) if ext == "emf" else []
            masters.append({
                "master": cur["master"] or f"shape-{n:03d}",
                "width_in": cur["width_in"],
                "props": {"height_in": f"{cur['height_in']:.4f}"},
                "artwork_name": visio_meta.name_from_artwork(blob) if ext == "emf" else None,
                "shapesheet": {"master": {"NameU": cur["master"]} if cur["master"] else {},
                               "size_in": {"width": cur["width_in"], "height": cur["height_in"]},
                               "text": labels},
                "images": [name]})
            cur = None
    proc.wait()
    note = None if media else "libvisio produced no embedded artwork"
    return masters, media, docprops, note


# ---------------------------------------------------------------- conversion

def to_svg(paths, outdir, log):
    """Batch-convert vector art to SVG in one Inkscape process."""
    ink = inkscape()
    todo = [p for p in paths if p.suffix.lower() in (".emf", ".wmf")]
    if not todo:
        return {}
    if not ink:
        log("Inkscape not found - EMF/WMF left unconverted")
        return {}
    outdir.mkdir(parents=True, exist_ok=True)
    script = "".join(f"file-open:{p}; export-filename:{outdir / (p.stem + '.svg')}; "
                     f"export-do; file-close;\n" for p in todo)
    subprocess.run([ink, "--shell"], input=script.encode(), capture_output=True, timeout=1800)
    return {p.name: outdir / (p.stem + ".svg") for p in todo if (outdir / (p.stem + ".svg")).exists()}


def contact_sheet(out, stencils):
    cards = []
    for name, rows in stencils:
        n = sum(len(r["files"]) for r in rows)
        cards.append(f'<h2>{html.escape(name)} <span class=n>({n} images / {len(rows)} masters)</span></h2><div class=g>')
        for r in sorted(rows, key=lambda r: (r.get("name") or r["master"]).lower()):
            for f in r["files"]:
                p = r.get("props") or {}
                bits = [p.get("Item Number") or p.get("Part Number"),
                        f'{p["Rack Units"]}U' if p.get("Rack Units") else p.get("RackUnits"),
                        p.get("View"),
                        f'{r["width_in"]:.2f} in' if r.get("width_in") else None,
                        f'{p["connection_points"]} conn pts' if p.get("connection_points") else None]
                meta = " · ".join(x for x in bits if x)
                cards.append(f'<figure><img loading=lazy src="{html.escape(f)}">'
                             f'<figcaption>{html.escape(r.get("name") or r["master"])}'
                             f'<br><span class=m>{html.escape(meta)}</span>'
                             f'</figcaption></figure>')
        cards.append("</div>")
    (out / "index.html").write_text(f"""<!doctype html><meta charset=utf-8>
<title>Visio stencil extraction - reference only</title>
<style>
 body{{font-family:system-ui,sans-serif;background:#16181b;color:#d7dbdf;margin:1.2rem}}
 h1{{font-size:1.1rem}} h2{{font-size:.95rem;margin-top:1.6rem;border-bottom:1px solid #33373c;padding-bottom:.3rem}}
 .n,.m{{color:#7d848b;font-weight:400;font-size:.78rem}}
 .warn{{background:#3a2416;border:1px solid #7a4a1a;padding:.6rem .8rem;border-radius:8px;font-size:.82rem}}
 .g{{display:flex;flex-wrap:wrap;gap:.8rem}}
 figure{{margin:0;background:#fff;border-radius:6px;padding:.4rem;width:420px}}
 figure img{{width:100%;height:auto;display:block}}
 figcaption{{color:#2b2f33;font-size:.74rem;margin-top:.3rem;font-family:ui-monospace,monospace}}
 figcaption .m{{color:#6b7076}}
</style>
<h1>Visio stencil extraction</h1>
<p class=warn><strong>Reference only.</strong> Vendor stencils are typically licensed
for making diagrams, not for redistribution or modification. Read <em>facts</em> from
these (port counts, positions, RU heights) and author original NDV art; do not commit
or publish the extracted files.</p>
{''.join(cards)}""")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stencils", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-svg", action="store_true", help="skip EMF/WMF -> SVG conversion")
    args = ap.parse_args()
    log = lambda m: print(f"  {m}")
    args.out.mkdir(parents=True, exist_ok=True)
    sheets = []

    for src in args.stencils:
        if not src.exists():
            log(f"missing: {src}")
            continue
        print(f"{src.name}")
        head = src.open("rb").read(8)
        dest = args.out / slug(src.stem)
        note, docprops = None, {}
        if head.startswith(b"PK"):
            masters, media, docprops = read_opc(src)
        elif head.startswith(b"\xd0\xcf\x11\xe0"):
            masters, media, docprops, note = read_ole(src)
        else:
            log("unrecognised format (not OPC zip, not OLE2)")
            continue
        if note:
            log(note)
        if not media and not any(m["images"] or m.get("geometry_svg") for m in masters):
            log("no artwork found (no embedded media, no renderable geometry)")
            continue

        rendered = 0
        for m in masters:
            if m.get("geometry_svg"):
                q = dest / "svg" / f"{slug(m['master'])}-{masters.index(m):03d}.svg"
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_text(m.pop("geometry_svg"))
                m["images"] = [f"rendered:{q.name}"]
                rendered += 1
        if rendered:
            log(f"{rendered} masters rendered from native Visio geometry")
        (dest / "media").mkdir(parents=True, exist_ok=True)
        written = {}
        for name, blob in media.items():
            p = dest / "media" / Path(name).name
            p.write_bytes(blob)
            written[name] = p
        log(f"{len(written)} embedded images, {len(masters)} masters")

        svgs = {} if args.no_svg else to_svg(list(written.values()), dest / "svg", log)
        if svgs:
            log(f"{len(svgs)} converted to SVG")

        rows, used = [], {}
        for m in masters:
            stem = slug(visio_meta.suggest_name(m["master"], m.get("props") or {},
                                                m.get("artwork_name")))
            n = used.get(stem, 0) + 1
            used[stem] = n
            if n > 1:
                stem = f"{stem}-{n}"
            m["name"] = stem
            files = []
            for i, img in enumerate(m["images"]):
                if img.startswith("rendered:"):
                    src_p = dest / "svg" / img.split(":", 1)[1]
                else:
                    src_p = written.get(img) or written.get("visio/" + img)
                if not src_p or not src_p.exists():
                    continue
                conv = svgs.get(src_p.name) if src_p.suffix.lower() != ".svg" else None
                pick = conv or src_p
                tgt = dest / "by-master" / (m["name"] +
                                           ("" if len(m["images"]) == 1 else f"-{i+1}") + pick.suffix)
                tgt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pick, tgt)
                files.append(str(tgt.relative_to(args.out)))
            sheet = m.pop("shapesheet", None)
            if sheet:
                sp = dest / "shapesheet" / f"{m['name']}.json"
                sp.parent.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(sheet, indent=1))
                m["shapesheet_file"] = str(sp.relative_to(args.out))
            rows.append({**m, "files": files})
        (dest / "index.json").write_text(json.dumps(
            {"stencil": src.name, "document": docprops, "masters": rows}, indent=1))
        if docprops:
            log("document metadata: " + ", ".join(sorted(docprops)[:6]))
        nconn = sum(len((r.get("props") or {}).get("connection_points", []) if isinstance(
            (r.get("props") or {}).get("connection_points"), list) else
            [1] * ((r.get("props") or {}).get("connection_points") or 0)) for r in rows)
        if nconn:
            log(f"{nconn} connection points captured")
        sheets.append((src.stem, rows))

    if sheets:
        contact_sheet(args.out, sheets)
        print(f"\ncontact sheet: {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
