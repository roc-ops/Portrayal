#!/usr/bin/env python3
"""Read the ShapeSheet metadata out of a Visio master.

The artwork is only half of what a stencil knows. The ShapeSheet carries the
facts we actually want when redrawing a device:

  Property section    labelled custom properties - Manufacturer, Item Number,
                      Rack Units, Width/Depth, Description
  Connection section  connection points, i.e. where cables attach. Their
                      formulas (Width*0.2463) are FRACTIONAL, so they survive
                      without knowing the drawing scale - port positions for free
  Hyperlink section   vendor product URLs (provenance)
  User section        authoring hints (CAD import type, hatch names)
  Text                shape labels - port numbers, silkscreen

Everything is returned as plain data so it can be written next to the art.
"""
import re
import struct
import xml.etree.ElementTree as ET

V = "{http://schemas.microsoft.com/office/visio/2012/main}"


def _cells(el):
    """Cell name -> {'v': value, 'f': formula} for one row/shape."""
    out = {}
    for c in el.findall(f"{V}Cell"):
        f = c.get("F")
        out[c.get("N")] = {"v": c.get("V"), "f": f if f and f != "No Formula" else None}
    return out


def _val(cells, name, default=None):
    c = cells.get(name)
    return c["v"] if c else default


def _num(cells, name):
    try:
        return float(_val(cells, name))
    except (TypeError, ValueError):
        return None


def _section(shape, name):
    for s in shape.findall(f"{V}Section"):
        if s.get("N") == name:
            return s
    return None


def _properties(shape):
    """Property rows keyed by their human Label (Row_1 -> 'Rack Units')."""
    sec = _section(shape, "Property")
    if sec is None:
        return {}
    out = {}
    for row in sec.findall(f"{V}Row"):
        c = _cells(row)
        label = _val(c, "Label") or row.get("N")
        value = _val(c, "Value")
        if value in (None, "", "0"):      # unfilled asset fields
            continue
        out[label] = value
    return out


def _connections(shape):
    """Connection points, with the fractional formulas that make them portable."""
    sec = _section(shape, "Connection")
    if sec is None:
        return []
    out = []
    for row in sec.findall(f"{V}Row"):
        c = _cells(row)
        entry = {"name": row.get("N") or row.get("IX"),
                 "x": _num(c, "X"), "y": _num(c, "Y"),
                 "x_formula": (c.get("X") or {}).get("f"),
                 "y_formula": (c.get("Y") or {}).get("f")}
        if _val(c, "Prompt"):
            entry["prompt"] = _val(c, "Prompt")
        out.append(entry)
    return out


def _hyperlinks(shape):
    sec = _section(shape, "Hyperlink")
    if sec is None:
        return []
    out = []
    for row in sec.findall(f"{V}Row"):
        c = _cells(row)
        addr = _val(c, "Address")
        if addr:
            out.append({"description": _val(c, "Description") or "", "address": addr})
    return out


def _user(shape):
    sec = _section(shape, "User")
    if sec is None:
        return {}
    return {row.get("N"): _val(_cells(row), "Value")
            for row in sec.findall(f"{V}Row") if _val(_cells(row), "Value")}


def _text(shape):
    out = []
    for t in shape.iter(f"{V}Text"):
        s = "".join(t.itertext()).strip()
        if s:
            out.append(s)
    return out


def shapesheet(master_xml_bytes, master_attrs=None):
    """-> dict of everything the master knows, walking the whole shape tree."""
    root = ET.fromstring(master_xml_bytes)
    info = {"properties": {}, "connections": [], "hyperlinks": [], "user": {},
            "text": [], "shapes": 0, "geometry_sections": 0}
    if master_attrs:
        info["master"] = {k: v for k, v in master_attrs.items()
                          if k in ("NameU", "Name", "ID", "UniqueID", "BaseID",
                                   "Prompt", "MasterType", "Hidden") and v}

    tops = root.findall(f"{V}Shapes/{V}Shape")
    for i, sh in enumerate(tops):
        c = _cells(sh)
        if i == 0:
            info["size_in"] = {"width": _num(c, "Width"), "height": _num(c, "Height")}
            angle = _num(c, "Angle")
            if angle:
                info["size_in"]["angle_rad"] = angle

    for sh in root.iter(f"{V}Shape"):
        info["shapes"] += 1
        info["geometry_sections"] += sum(
            1 for s in sh.findall(f"{V}Section") if s.get("N") == "Geometry")
        for k, v in _properties(sh).items():
            info["properties"].setdefault(k, v)
        for k, v in _user(sh).items():
            info["user"].setdefault(k, v)
        info["hyperlinks"].extend(h for h in _hyperlinks(sh) if h not in info["hyperlinks"])
        name = sh.get("NameU") or sh.get("Name") or sh.get("ID")
        for conn in _connections(sh):
            conn["shape"] = name
            info["connections"].append(conn)
        for t in _text(sh):
            if t not in info["text"]:
                info["text"].append(t)
    return info


def summarise(info):
    """A few headline facts for listings and contact sheets."""
    p = info.get("properties", {})
    keys = ("Manufacturer", "Item Number", "Part Number", "Description",
            "Rack Units", "RackUnits", "Width", "Depth", "View")
    out = {k: p[k] for k in keys if k in p}
    if info.get("connections"):
        out["connection_points"] = len(info["connections"])
    return out


# ---------------------------------------------------------------- naming help

_FURNITURE = {
    "arial", "helvetica", "tahoma", "calibri", "verdana", "segoe ui", "wingdings",
    "status", "laser", "class 1", "class 1o", "oir ready", "active", "link",
    "console", "reset", "power", "fail", "alarm", "critical", "major", "minor",
    "aux", "mgmt", "usb", "eth", "sync", "alm", "pwr", "fan", "stat",
}
_MODEL = re.compile(r"^[A-Z][A-Z0-9]{1,}(?:[-/][A-Z0-9]+)+$", re.I)


def emf_text(blob):
    """Text drawn inside an EMF, read from its EMR_EXTTEXTOUT records.

    Parsing the record stream (rather than scanning bytes for UTF-16 runs)
    matters: a byte scan happily matches misaligned data and invents strings
    like '8t7s7s6'.
    """
    out, pos, n = [], 0, len(blob)
    while pos + 8 <= n:
        try:
            itype, size = struct.unpack_from("<II", blob, pos)
        except struct.error:
            break
        if size < 8 or pos + size > n:
            break
        if itype in (83, 84):                       # EMR_EXTTEXTOUTA / EMR_EXTTEXTOUTW
            try:
                nchars, off = struct.unpack_from("<II", blob, pos + 44)
                if off and 0 < nchars < 4096 and pos + off + nchars <= n:
                    raw = blob[pos + off: pos + off + nchars * (2 if itype == 84 else 1)]
                    s = raw.decode("utf-16le" if itype == 84 else "latin-1", "ignore").strip()
                    if s:
                        out.append(s)
            except struct.error:
                pass
        pos += size
    return out


# kept for callers that only need "some readable text"
emf_strings = emf_text


def name_from_artwork(blob):
    """Best guess at a model name from text baked into EMF artwork.

    Legacy .vss stencils lose their master names (libvisio renders pages, not
    master metadata), but the drawn labels survive. Visio splits a model number
    across several text records for kerning - 'A9903', '-', '20HG', '-', 'PEC' -
    so consecutive fragments are rejoined before scoring.
    """
    groups, cur = [], []
    for s in emf_text(blob):
        low = s.lower().strip()
        if low in _FURNITURE or s.isdigit() or len(s) > 32:
            if cur:
                groups.append("".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        groups.append("".join(cur))

    best = None
    for g in groups:
        g = g.strip(" -/")
        if len(g) < 4 or not any(ch.isdigit() for ch in g) or not any(ch.isalpha() for ch in g):
            continue
        if not _MODEL.match(g):
            continue
        if best is None or len(g) > len(best):
            best = g
    return best


def suggest_name(master_name, props, artwork_name=None):
    """Filename stem: prefer a real master name, enrich it from the ShapeSheet."""
    def clean(x):
        return re.sub(r"[\s_]+", " ", (x or "")).strip(" -_")

    name = clean(master_name)
    generic = (not name) or re.fullmatch(r"(shape|master)[-\s]?\d+", name, re.I) or \
        len(re.sub(r"[^A-Za-z0-9]", "", name)) < 3
    if generic:
        name = clean(artwork_name) or clean(props.get("Item Number") or
                                            props.get("Part Number") or
                                            props.get("Description")) or name
    item = clean(props.get("Item Number") or props.get("Part Number"))
    if item and item.lower() not in name.lower():
        name = f"{item} {name}".strip()
    # the View property is often a stencil-wide default; only add it when the
    # master name does not already say which view it is
    view = clean(props.get("View"))
    if view and not re.search(r"\b(view|front|rear|back|top|bottom|side|left|right|"
                              r"frame|door|panel|iso)\b", name, re.I):
        name = f"{name} {view}".strip()
    return name or "unnamed"
