#!/usr/bin/env python3
"""Render native Visio shape geometry (OPC stencils) to SVG.

Many modern stencils carry no bitmaps at all - the artwork is Visio's own
geometry rows (MoveTo/LineTo/ArcTo/EllipticalArcTo/Ellipse/NURBSTo) in
shape-local inch coordinates. This module walks the shape tree, applies each
shape's placement (Pin/LocPin/Width/Height/Angle/Flip) and emits SVG paths.

Coordinates: Visio is y-up from the bottom-left; SVG is y-down. The whole
drawing is emitted inside one flip group so shape maths stays in Visio space.

Approximations (flagged in output metadata): NURBSTo and PolylineTo degrade to
straight segments to their endpoint, and theme-indexed colours fall back to a
neutral palette because the theme part is not parsed.
"""
import math
import re
import xml.etree.ElementTree as ET

V = "{http://schemas.microsoft.com/office/visio/2012/main}"
IN2MM = 25.4


def _cells(el):
    out = {}
    for c in el.findall(f"{V}Cell"):
        v = c.get("V")
        try:
            out[c.get("N")] = float(v)
        except (TypeError, ValueError):
            out[c.get("N")] = v
    return out


def _num(d, k, default=0.0):
    v = d.get(k, default)
    return v if isinstance(v, float) else default


def _colour(v, fallback):
    if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v or ""):
        return v
    return fallback


def _geom_path(sec, w, h):
    """One Geometry section -> SVG path data (shape-local inches)."""
    d, last = [], None
    for row in sec.findall(f"{V}Row"):
        t = row.get("T")
        c = _cells(row)
        x, y = _num(c, "X"), _num(c, "Y")
        if t == "MoveTo":
            d.append(f"M {x:.4f} {y:.4f}")
            last = (x, y)
        elif t in ("LineTo", "PolylineTo", "NURBSTo", "SplineStart", "SplineKnot"):
            d.append(f"L {x:.4f} {y:.4f}")
            last = (x, y)
        elif t == "ArcTo":
            bow = _num(c, "A")
            if last is None or abs(bow) < 1e-9:
                d.append(f"L {x:.4f} {y:.4f}")
            else:
                cx, cy = (last[0] + x) / 2, (last[1] + y) / 2
                chord = math.hypot(x - last[0], y - last[1])
                r = (bow * bow * 4 + chord * chord) / (8 * abs(bow)) if bow else 0
                sweep = 1 if bow > 0 else 0
                d.append(f"A {r:.4f} {r:.4f} 0 0 {sweep} {x:.4f} {y:.4f}")
            last = (x, y)
        elif t == "EllipticalArcTo":
            # control point (A,B), angle C of the ellipse x-axis, aspect D
            a, b, ang, asp = _num(c, "A"), _num(c, "B"), _num(c, "C"), _num(c, "D", 1.0)
            if last is None:
                d.append(f"M {x:.4f} {y:.4f}")
            else:
                rx = max(1e-6, math.hypot(x - last[0], y - last[1]) / 2)
                ry = max(1e-6, rx * (asp if asp else 1.0))
                cross = (a - last[0]) * (y - last[1]) - (b - last[1]) * (x - last[0])
                sweep = 0 if cross > 0 else 1
                d.append(f"A {rx:.4f} {ry:.4f} {math.degrees(ang):.2f} 0 {sweep} {x:.4f} {y:.4f}")
            last = (x, y)
        elif t == "Ellipse":
            cx, cy = x, y
            rx = abs(_num(c, "A") - cx) or abs(_num(c, "C") - cx)
            ry = abs(_num(c, "D") - cy) or abs(_num(c, "B") - cy)
            d.append(f"M {cx - rx:.4f} {cy:.4f} a {rx:.4f} {ry:.4f} 0 1 0 {2 * rx:.4f} 0 "
                     f"a {rx:.4f} {ry:.4f} 0 1 0 {-2 * rx:.4f} 0 Z")
        elif t == "RelMoveTo":
            d.append(f"M {x * w:.4f} {y * h:.4f}")
        elif t == "RelLineTo":
            d.append(f"L {x * w:.4f} {y * h:.4f}")
    return " ".join(d)


def _shape_svg(shape, depth=0):
    c = _cells(shape)
    w, h = _num(c, "Width"), _num(c, "Height")
    pin_x, pin_y = _num(c, "PinX"), _num(c, "PinY")
    loc_x, loc_y = _num(c, "LocPinX", w / 2), _num(c, "LocPinY", h / 2)
    angle = _num(c, "Angle")
    fx, fy = _num(c, "FlipX"), _num(c, "FlipY")
    tf = [f"translate({pin_x:.4f} {pin_y:.4f})"]
    if angle:
        tf.append(f"rotate({math.degrees(angle):.3f})")
    if fx or fy:
        tf.append(f"translate({loc_x if fx else 0:.4f} {loc_y if fy else 0:.4f})")
        tf.append(f"scale({-1 if fx else 1} {-1 if fy else 1})")
        tf.append(f"translate({-loc_x if fx else 0:.4f} {-loc_y if fy else 0:.4f})")
    tf.append(f"translate({-loc_x:.4f} {-loc_y:.4f})")

    fill = _colour(c.get("FillForegnd"), "#d8dade")
    line = _colour(c.get("LineColor"), "#3a3f44")
    if _num(c, "FillPattern", 1) == 0:
        fill = "none"
    stroke = "none" if _num(c, "LinePattern", 1) == 0 else line
    lw = _num(c, "LineWeight", 0.003) or 0.003

    body = []
    for sec in shape.findall(f"{V}Section"):
        if sec.get("N") != "Geometry":
            continue
        rows = _cells(sec)
        if str(rows.get("NoShow", 0)) in ("1", "1.0"):
            continue
        d = _geom_path(sec, w, h)
        if not d:
            continue
        f = "none" if str(rows.get("NoFill", 0)) in ("1", "1.0") else fill
        s = "none" if str(rows.get("NoLine", 0)) in ("1", "1.0") else stroke
        body.append(f'<path d="{d}" fill="{f}" stroke="{s}" stroke-width="{lw:.4f}"/>')

    for sub in shape.findall(f"{V}Shapes/{V}Shape"):
        body.append(_shape_svg(sub, depth + 1))

    if not body:
        return ""
    name = shape.get("NameU") or shape.get("Name") or f"shape{shape.get('ID', '')}"
    ident = re.sub(r"[^A-Za-z0-9_.-]", "-", name)
    return f'<g id="{ident}" transform="{" ".join(tf)}">{"".join(body)}</g>'


def master_to_svg(master_xml_bytes):
    """-> (svg_text, width_in, height_in) or (None, None, None) if empty.

    Master coordinates are not origin-based, so the canvas is the union of the
    top-level shapes' own boxes and the viewBox is offset to match.
    """
    root = ET.fromstring(master_xml_bytes)
    tops = root.findall(f"{V}Shapes/{V}Shape")
    if not tops:
        return None, None, None
    body, boxes = [], []
    for sh in tops:
        c = _cells(sh)
        w, h = _num(c, "Width"), _num(c, "Height")
        x0 = _num(c, "PinX") - _num(c, "LocPinX", w / 2)
        y0 = _num(c, "PinY") - _num(c, "LocPinY", h / 2)
        if w > 0 and h > 0:
            boxes.append((x0, y0, x0 + w, y0 + h))
        g = _shape_svg(sh)
        if g:
            body.append(g)
    if not body or not boxes:
        return None, None, None
    minx = min(b[0] for b in boxes); miny = min(b[1] for b in boxes)
    maxx = max(b[2] for b in boxes); maxy = max(b[3] for b in boxes)
    w, h = maxx - minx, maxy - miny
    if w <= 0 or h <= 0:
        return None, None, None
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * IN2MM:.2f}mm" '
           f'height="{h * IN2MM:.2f}mm" viewBox="{minx:.4f} {miny:.4f} {w:.4f} {h:.4f}">'
           f'<g transform="matrix(1 0 0 -1 0 {miny + maxy:.4f})">{"".join(body)}</g></svg>')
    return svg, w, h
