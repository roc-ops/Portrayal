"""A lab's placements, checked and resolved to rack positions.

A lab places library devices in one rack. Most are `rack` devices, which sit
between the posts on the rack units they span. A `rack-face` part - a cable
manager, a lacer bar - bolts to the rail face over a rack unit it shares with
whatever is behind it, so a placement says which face, and either the rack
unit (`ru`) or the host it sits on (`on`, `unit`). docs/cable-managers-design.md
section 6 is the design. A `rack-side` part - a full-height vertical cable
manager - stands beside the rack on the side of an upright, outside the rails,
so it says which `side` and the rack unit it starts at; and a `rack-face` part
narrower than the opening (a 5U finger bracket on one rail) may say which side
of the opening it bolts to, so two of them share a unit and a face
(docs/vertical-cable-managers-design.md sections 3.4 and 3.5).

Two callers, one answer. `labs_index.py` resolves every placement into the
absolute rack unit, face and host that labs.json carries, and refuses to write a
lab it cannot resolve; `lint.py` reports the same findings under their codes
(L139-L143, L153, L154) in the full run. Both ask `check`, so the build and the linter can
never disagree about a lab.

RACK UNITS ARE COUNTED THE WAY THE RACK COUNTS: U1 at the bottom, and a
placement's `ru` is the lowest unit it occupies, so a 4U device at `ru: 10`
takes 10-13. `unit` counts the host's units the same way, from 1 at the host's
bottom: `unit: 3` on that host is rack unit 12.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from portrayal.manifest import load_yaml

SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "lab.schema.json"
RACK_FACE = "rack-face"
RACK_SIDE = "rack-side"
SIDES = ("left", "right")
# THE CLEAR OPENING BETWEEN A 19-INCH RACK'S RAILS, 17.72 in (EIA-310). A
# rack-face part as wide as this or wider lies across the opening - a
# horizontal manager, its ears on both rails - and takes the whole unit on its
# face; one narrower stands at one rail's side of it and can say which.
RACK_OPENING_MM = 450.0
DEFAULT_HEIGHT_RU = 42

_validator = None


def schema_errors(lab):
    """Every schema violation, as 'path: message' strings."""
    global _validator
    if _validator is None:
        _validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    return [f"{'/'.join(str(p) for p in e.path) or '(top)'}: {e.message}"
            for e in _validator.iter_errors(lab)]


def find_device(ref, roots):
    """The manifest a lab `ref` names, or None. A ref is a device's `name`,
    which is its directory - the name its compiled files are published under."""
    if not isinstance(ref, str) or not ref or "/" in ref:
        return None
    for r in roots:
        for f in sorted(Path(r).glob(f"devices/*/{ref}/device.yaml")):
            d = load_yaml(f)
            if isinstance(d, dict) and d.get("kind") == "device" and d.get("name") == ref:
                return d
    return None


def _mount(dev):
    return str(((dev or {}).get("chassis") or {}).get("mount") or "rack")


def _height(dev):
    ru = ((dev or {}).get("chassis") or {}).get("ru")
    return ru if isinstance(ru, int) and ru >= 1 else 1


def _width(dev):
    w = ((dev or {}).get("chassis") or {}).get("width")
    return float(w) if isinstance(w, (int, float)) else None


def _sided(dev):
    """True for a rack-face part narrower than the rack opening."""
    w = _width(dev)
    return _mount(dev) == RACK_FACE and w is not None and w < RACK_OPENING_MM


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(lab, roots):
    """Check a lab and resolve its placements.

    Returns `(findings, placements)`. A finding is `(code, severity, message)`
    with severity "error" or "warning". `placements` is every placement in the
    lab's order, each a copy of what the lab wrote with its position added:
    `ru` (the lowest absolute rack unit), `face` (front or rear), `mount`
    (rack, rack-face or rack-side), `host` (the id of the rack device behind
    it, or None), `unit` (which of the host's units, or None without a host)
    and `side` (left or right for a rack-side part and a sided rack-face part,
    else None). A position that cannot be resolved is None, and there is an
    error saying why.
    """
    found = []

    def error(code, msg):
        found.append((code, "error", msg))

    def warning(code, msg):
        found.append((code, "warning", msg))

    rack_h = ((lab.get("rack") or {}).get("height-ru")) or DEFAULT_HEIGHT_RU
    raw = [p for p in (lab.get("devices") or []) if isinstance(p, dict)]

    # L139 - every ref is a library device, every id is one placement's
    devs, seen = {}, set()
    for p in raw:
        pid = p.get("id")
        if pid in seen:
            error("L139", f"placement id {pid!r} is used twice. `on` and every link "
                  "name a placement by id, so each id is one placement")
        seen.add(pid)
        dev = find_device(p.get("ref"), roots)
        if dev is None:
            error("L139", f"{pid}: ref {p.get('ref')!r} is not a device in the library. "
                  "A lab names a device by its `name`, e.g. `fhd-1ufce`")
        elif p.get("cfg") is not None and p["cfg"] not in (dev.get("configurations") or {}):
            error("L139", f"{pid}: cfg {p['cfg']!r} is not one of {p['ref']}'s configurations "
                  f"({', '.join(sorted(dev.get('configurations') or {}))})")
        devs[pid] = dev
    by_id = {p.get("id"): p for p in raw}
    for p in raw:
        on = p.get("on")
        if on is not None and on not in by_id:
            error("L139", f"{p.get('id')}: on {on!r} names no placement in this lab")
        elif on is not None and on == p.get("id"):
            error("L139", f"{p.get('id')}: is `on` itself")

    # L140 - face, on and unit belong to rack-face parts, which have on or ru
    for p in raw:
        pid, dev = p.get("id"), devs.get(p.get("id"))
        if dev is None:
            continue
        mount = _mount(dev)
        if mount == RACK_SIDE:
            continue                            # its keys are L153's
        if mount == RACK_FACE:
            if "on" in p and "ru" in p:
                error("L140", f"{pid}: states both `on` and `ru`. A rack-face part is placed "
                      "on a host (`on`, `unit`) or at a rack unit (`ru`), not both")
            elif "on" not in p and "ru" not in p:
                error("L140", f"{pid}: a rack-face part is placed by `on` (a host placement) "
                      "or by `ru`, and this states neither")
            if "unit" in p and "on" not in p:
                error("L140", f"{pid}: `unit` counts a host's rack units, and this names "
                      "no host. Add `on`, or state the rack unit as `ru`")
        else:
            stray = [k for k in ("face", "on", "unit") if k in p]
            if stray:
                error("L140", f"{pid}: {', '.join(f'`{k}`' for k in stray)} "
                      f"{'is' if len(stray) == 1 else 'are'} for a rack-face part, and "
                      f"{p.get('ref')} mounts `{mount}`. A rack device spans the rack front "
                      "to back on the units it takes; place it by `ru`")
            elif mount == "rack" and "ru" not in p:
                error("L140", f"{pid}: a rack device is placed by `ru`, its lowest rack unit")

    # L153 - `side` belongs to rack-side parts, which state it, and to rack-face
    # parts narrower than the opening; a rack-side part has no host
    for p in raw:
        pid, dev = p.get("id"), devs.get(p.get("id"))
        if dev is None:
            continue
        mount = _mount(dev)
        if mount == RACK_SIDE:
            if "side" not in p:
                error("L153", f"{pid}: a rack-side part stands beside the rack on one side "
                      "of it, and this states no `side`. Say `side: left` or `side: right`, "
                      "seen from the front")
            stray = [k for k in ("on", "unit") if k in p]
            if stray:
                error("L153", f"{pid}: {', '.join(f'`{k}`' for k in stray)} "
                      f"{'names' if len(stray) == 1 else 'name'} a host, and a rack-side "
                      "part has none: it bolts to the side of an upright. Place it by "
                      "`ru`, its bottom unit")
        elif "side" in p and not _sided(dev):
            if mount == RACK_FACE:
                error("L153", f"{pid}: `side` is for a rack-face part narrower than the "
                      f"{RACK_OPENING_MM:g} mm rack opening, and {p.get('ref')} is "
                      f"{_width(dev):g} wide: it lies across the opening and takes the "
                      "whole unit on its face. Drop `side`")
            else:
                error("L153", f"{pid}: `side` is for a rack-side part or a rack-face part "
                      f"narrower than the opening, and {p.get('ref')} mounts `{mount}`. "
                      "Drop it")

    # resolve: rack devices first, then rack-face parts onto them
    out = []
    for p in raw:
        pid, dev = p.get("id"), devs.get(p.get("id"))
        q = dict(p)
        q["mount"] = _mount(dev) if dev is not None else None
        q["face"] = p.get("face") or "front"
        q["host"] = None
        q["unit"] = None
        q["side"] = p.get("side") if p.get("side") in SIDES else None
        on_host = q["mount"] == RACK_FACE and "on" in p
        q["ru"] = p.get("ru") if _int(p.get("ru")) and not on_host else None
        if q["mount"] == RACK_SIDE and "ru" not in p:
            q["ru"] = 1                         # its bottom unit, default 1
        out.append(q)
    res = {q.get("id"): q for q in out}

    # L141 - a host is a rack device placed by ru, and unit is within its height
    for q in out:
        if q["mount"] != RACK_FACE or "on" not in q or q.get("on") not in res:
            continue
        pid, host = q.get("id"), res[q["on"]]
        hdev = devs.get(host.get("id"))
        if hdev is None:
            continue                            # its ref is already an error
        if host["mount"] != "rack":
            error("L141", f"{pid}: on {host.get('id')!r}, which mounts `{host['mount']}`. "
                  "A host is a rack device, the one behind the rail face this part bolts to")
            continue
        if host["ru"] is None:
            continue                            # the host's own placement is the error
        unit = by_id[pid].get("unit", 1)
        h = _height(hdev)
        if not _int(unit) or not 1 <= unit <= h:
            error("L141", f"{pid}: unit {unit!r} on {host.get('id')!r}, which is {h}U "
                  f"({host.get('ref')}). `unit` counts the host's rack units from 1 at its "
                  f"bottom, so it is 1 to {h}")
            continue
        q["ru"], q["host"], q["unit"] = host["ru"] + unit - 1, host.get("id"), unit

    # L142 - everything fits in the rack, and nothing claims a unit twice. A
    # rack-face part claims its unit on its face per SIDE of the opening: one
    # narrower than the opening placed at a `side` takes that side only, so a
    # bracket on each rail shares the unit; anything else takes both.
    rack_units, face_units = {}, {}
    for q in out:
        dev = devs.get(q.get("id"))
        if dev is None or q["ru"] is None or q["mount"] == RACK_SIDE:
            continue
        h = _height(dev)
        lo, hi = q["ru"], q["ru"] + h - 1
        if lo < 1 or hi > rack_h:
            error("L142", f"{q.get('id')}: {q.get('ref')} at rack unit {lo} takes "
                  f"{lo}-{hi}, outside the {rack_h}U rack")
        if q["mount"] == "rack":
            claims = [rack_units]
        elif q["mount"] == RACK_FACE:
            sides = [q["side"]] if q["side"] and _sided(dev) else list(SIDES)
            claims = [face_units.setdefault((q["face"], s), {}) for s in sides]
        else:
            continue
        clash = None
        for u in range(lo, hi + 1):
            clash = next(((u, c[u]) for c in claims if c.get(u) is not None), None)
            if clash:
                break
        if clash:
            u, other = clash
            if q["mount"] == "rack":
                error("L142", f"{q.get('id')}: rack unit {u} is already {other}'s. Two rack "
                      "devices cannot share a rack unit")
            else:
                where = f" on the {q['face']} face" + (
                    f", {q['side']} side" if len(claims) == 1 else "")
                error("L142", f"{q.get('id')}: rack unit {u}{where} is already {other}'s. "
                      "Two rack-face parts cannot share a rack unit on one face and side")
            continue
        for u in range(lo, hi + 1):
            for c in claims:
                c[u] = q.get("id")

    # L154 - a rack-side part fits the rack's height, and two on one side of the
    # rack do not overlap: each runs beside the units from its `ru` up
    side_units = {}
    for q in out:
        dev = devs.get(q.get("id"))
        if dev is None or q["mount"] != RACK_SIDE or q["ru"] is None:
            continue
        lo, hi = q["ru"], q["ru"] + _height(dev) - 1
        if lo < 1 or hi > rack_h:
            error("L154", f"{q.get('id')}: {q.get('ref')} from rack unit {lo} runs beside "
                  f"{lo}-{hi}, beyond the {rack_h}U rack it stands against")
        if q["side"] is None:
            continue                            # its missing side is L153's
        claim = side_units.setdefault(q["side"], {})
        other = next((claim[u] for u in range(lo, hi + 1) if u in claim), None)
        if other is not None:
            error("L154", f"{q.get('id')}: overlaps {other} on the {q['side']} side of the "
                  "rack. Two rack-side parts on one side stand one above the other")
            continue
        for u in range(lo, hi + 1):
            claim[u] = q.get("id")

    # L143 - a rack-face part placed by ru, with a host behind it, is reported
    for q in out:
        dev = devs.get(q.get("id"))
        if dev is None or q["mount"] != RACK_FACE or "on" in q or q["ru"] is None:
            continue
        host = rack_units.get(q["ru"])
        if host is None:
            continue
        q["host"], q["unit"] = host, q["ru"] - res[host]["ru"] + 1
        warning("L143", f"{q.get('id')}: placed by `ru: {q['ru']}` on the {q['face']} face, "
                f"over {host!r} ({res[host].get('ref')}). Placed `on: {host}` with "
                f"`unit: {q['unit']}` it would move with its host")
    return found, out
