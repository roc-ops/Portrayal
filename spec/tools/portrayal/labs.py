"""A lab's placements, checked and resolved to rack positions.

A lab places library devices in one rack. Most are `rack` devices, which sit
between the posts on the rack units they span. A `rack-face` part - a cable
manager, a lacer bar - bolts to the rail face over a rack unit it shares with
whatever is behind it, so a placement says which face, and either the rack
unit (`ru`) or the host it sits on (`on`, `unit`). docs/cable-managers-design.md
section 6 is the design.

Two callers, one answer. `labs_index.py` resolves every placement into the
absolute rack unit, face and host that labs.json carries, and refuses to write a
lab it cannot resolve; `lint.py` reports the same findings under their codes
(L132-L136) in the full run. Both ask `check`, so the build and the linter can
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


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(lab, roots):
    """Check a lab and resolve its placements.

    Returns `(findings, placements)`. A finding is `(code, severity, message)`
    with severity "error" or "warning". `placements` is every placement in the
    lab's order, each a copy of what the lab wrote with its position added:
    `ru` (the lowest absolute rack unit), `face` (front or rear), `mount`
    (rack or rack-face), `host` (the id of the rack device behind it, or None)
    and `unit` (which of the host's units, or None without a host). A position
    that cannot be resolved is None, and there is an error saying why.
    """
    found = []

    def error(code, msg):
        found.append((code, "error", msg))

    def warning(code, msg):
        found.append((code, "warning", msg))

    rack_h = ((lab.get("rack") or {}).get("height-ru")) or DEFAULT_HEIGHT_RU
    raw = [p for p in (lab.get("devices") or []) if isinstance(p, dict)]

    # L132 - every ref is a library device, every id is one placement's
    devs, seen = {}, set()
    for p in raw:
        pid = p.get("id")
        if pid in seen:
            error("L132", f"placement id {pid!r} is used twice. `on` and every link "
                  "name a placement by id, so each id is one placement")
        seen.add(pid)
        dev = find_device(p.get("ref"), roots)
        if dev is None:
            error("L132", f"{pid}: ref {p.get('ref')!r} is not a device in the library. "
                  "A lab names a device by its `name`, e.g. `fhd-1ufce`")
        elif p.get("cfg") is not None and p["cfg"] not in (dev.get("configurations") or {}):
            error("L132", f"{pid}: cfg {p['cfg']!r} is not one of {p['ref']}'s configurations "
                  f"({', '.join(sorted(dev.get('configurations') or {}))})")
        devs[pid] = dev
    by_id = {p.get("id"): p for p in raw}
    for p in raw:
        on = p.get("on")
        if on is not None and on not in by_id:
            error("L132", f"{p.get('id')}: on {on!r} names no placement in this lab")
        elif on is not None and on == p.get("id"):
            error("L132", f"{p.get('id')}: is `on` itself")

    # L133 - face, on and unit belong to rack-face parts, which have on or ru
    for p in raw:
        pid, dev = p.get("id"), devs.get(p.get("id"))
        if dev is None:
            continue
        mount = _mount(dev)
        if mount == RACK_FACE:
            if "on" in p and "ru" in p:
                error("L133", f"{pid}: states both `on` and `ru`. A rack-face part is placed "
                      "on a host (`on`, `unit`) or at a rack unit (`ru`), not both")
            elif "on" not in p and "ru" not in p:
                error("L133", f"{pid}: a rack-face part is placed by `on` (a host placement) "
                      "or by `ru`, and this states neither")
            if "unit" in p and "on" not in p:
                error("L133", f"{pid}: `unit` counts a host's rack units, and this names "
                      "no host. Add `on`, or state the rack unit as `ru`")
        else:
            stray = [k for k in ("face", "on", "unit") if k in p]
            if stray:
                error("L133", f"{pid}: {', '.join(f'`{k}`' for k in stray)} "
                      f"{'is' if len(stray) == 1 else 'are'} for a rack-face part, and "
                      f"{p.get('ref')} mounts `{mount}`. A rack device spans the rack front "
                      "to back on the units it takes; place it by `ru`")
            elif mount == "rack" and "ru" not in p:
                error("L133", f"{pid}: a rack device is placed by `ru`, its lowest rack unit")

    # resolve: rack devices first, then rack-face parts onto them
    out = []
    for p in raw:
        pid, dev = p.get("id"), devs.get(p.get("id"))
        q = dict(p)
        q["mount"] = _mount(dev) if dev is not None else None
        q["face"] = p.get("face") or "front"
        q["host"] = None
        q["unit"] = None
        on_host = q["mount"] == RACK_FACE and "on" in p
        q["ru"] = p.get("ru") if _int(p.get("ru")) and not on_host else None
        out.append(q)
    res = {q.get("id"): q for q in out}

    # L134 - a host is a rack device placed by ru, and unit is within its height
    for q in out:
        if q["mount"] != RACK_FACE or "on" not in q or q.get("on") not in res:
            continue
        pid, host = q.get("id"), res[q["on"]]
        hdev = devs.get(host.get("id"))
        if hdev is None:
            continue                            # its ref is already an error
        if host["mount"] != "rack":
            error("L134", f"{pid}: on {host.get('id')!r}, which mounts `{host['mount']}`. "
                  "A host is a rack device, the one behind the rail face this part bolts to")
            continue
        if host["ru"] is None:
            continue                            # the host's own placement is the error
        unit = by_id[pid].get("unit", 1)
        h = _height(hdev)
        if not _int(unit) or not 1 <= unit <= h:
            error("L134", f"{pid}: unit {unit!r} on {host.get('id')!r}, which is {h}U "
                  f"({host.get('ref')}). `unit` counts the host's rack units from 1 at its "
                  f"bottom, so it is 1 to {h}")
            continue
        q["ru"], q["host"], q["unit"] = host["ru"] + unit - 1, host.get("id"), unit

    # L135 - everything fits in the rack, and nothing claims a unit twice
    rack_units, face_units = {}, {}
    for q in out:
        dev = devs.get(q.get("id"))
        if dev is None or q["ru"] is None:
            continue
        h = _height(dev)
        lo, hi = q["ru"], q["ru"] + h - 1
        if lo < 1 or hi > rack_h:
            error("L135", f"{q.get('id')}: {q.get('ref')} at rack unit {lo} takes "
                  f"{lo}-{hi}, outside the {rack_h}U rack")
        claim = rack_units if q["mount"] == "rack" else (
            face_units.setdefault(q["face"], {}) if q["mount"] == RACK_FACE else None)
        if claim is None:
            continue
        for u in range(lo, hi + 1):
            other = claim.get(u)
            if other is not None:
                where = "" if q["mount"] == "rack" else f" on the {q['face']} face"
                error("L135", f"{q.get('id')}: rack unit {u}{where} is already "
                      f"{other}'s. Two {'rack devices' if q['mount'] == 'rack' else 'rack-face parts'} "
                      "cannot share a rack unit")
                break
            claim[u] = q.get("id")

    # L136 - a rack-face part placed by ru, with a host behind it, is reported
    for q in out:
        dev = devs.get(q.get("id"))
        if dev is None or q["mount"] != RACK_FACE or "on" in q or q["ru"] is None:
            continue
        host = rack_units.get(q["ru"])
        if host is None:
            continue
        q["host"], q["unit"] = host, q["ru"] - res[host]["ru"] + 1
        warning("L136", f"{q.get('id')}: placed by `ru: {q['ru']}` on the {q['face']} face, "
                f"over {host!r} ({res[host].get('ref')}). Placed `on: {host}` with "
                f"`unit: {q['unit']}` it would move with its host")
    return found, out
