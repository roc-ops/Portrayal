"""What a model can do, and why it cannot do the rest.

Two halves of one statement. A capability level says what a model CANNOT do; a
gap says WHY and what would fix it. A level without a reason is a grade, and a
gap without a level has no sense of how much it costs, so they are computed
together, here, and emitted side by side.

Nothing in here is declared. There is no `capability:` or `level:` key in
device.yaml and adding one would be a bug: the moment an author can write
`level: 3` it lies, first when they are optimistic and then when the model
changes underneath it. `maturity` already works the right way - L15 walks the
component tree and refuses `verified` if anything is `estimated` - and this
follows it.

Capability is orthogonal to maturity, deliberately. Maturity says how much you
should trust the numbers; capability says how much of the model exists. A
front-only faceplate traced off a mechanical drawing is `verified` and minimal;
a six-view model guessed from a photograph is `draft` and complete. Merging the
two axes destroys both, which is also why there is no `sourced` capability.
"""
from pathlib import Path

import yaml

from manifest import view_parts

# The chain. Each step strictly requires the one before it, which is what makes
# a single number honest: you cannot have six consistent faces without two.
LEVELS = ((1, "flat"), (2, "faced"), (3, "solid"), (4, "addressable"))
LEVEL_NAME = dict(LEVELS)
FACES = ("front", "rear", "top", "bottom", "left", "right")
FLAGS = ("specified", "wired", "templated")

# Two faces of one box have to agree to within this, in mm. Not exact equality:
# these are floats read out of YAML and a device written 43.5 in one view and
# 43.50 in another is the same device. Well below any real modelling difference
# - the error this exists to catch was 44mm.
DIM_TOL = 0.05

_PROFILES = None


def load_profiles(schemas_dir):
    """Read profiles.yaml once. Missing file means no profile is evaluable."""
    global _PROFILES
    if _PROFILES is None:
        f = Path(schemas_dir) / "profiles.yaml"
        _PROFILES = ((yaml.safe_load(f.read_text()) or {}).get("profiles") or {}
                     if f.exists() else {})
    return _PROFILES


def _plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _by_view(items):
    """[(view, id), ...] -> 'front 64, rear 3' in view order of first appearance."""
    counts = {}
    for v, _ in items:
        counts[v] = counts.get(v, 0) + 1
    return ", ".join(f"{v} {n}" for v, n in counts.items())


# ---------------------------------------------------------------- geometry

def effective_size(name, view, chassis):
    """The width and height the renderer will actually draw this view at.

    A view may omit `size`, and render.py then falls back to the chassis - so
    `front` with no size is genuinely sized, and treating it as absent would
    report four devices as level 1 that draw perfectly. The fallback is only
    honest for front and rear, where the face IS width x height; for a top view
    the second number is depth, and a top with no size renders as a wrong box.
    That one is reported as unsized, which is the point.
    """
    s = (view or {}).get("size") or {}
    if s.get("w") and s.get("h"):
        return (float(s["w"]), float(s["h"]))
    if name in ("front", "rear"):
        w, h = (chassis or {}).get("width"), (chassis or {}).get("height")
        if w and h:
            return (float(w), float(h))
    return None


def _has_content(view):
    """Something is drawn on this face beyond the bare rectangle.

    Note `panel` is not required. It carries decor and cutouts, both optional,
    and the faceplate rect is drawn from the size whether or not it exists -
    six of thirteen devices have views with no `panel` block and all of them
    render. Requiring it would have put the best-modelled device in the
    portfolio at level 0.
    """
    vp = view_parts(view or {})
    return any(vp[k] for k in ("decor", "cutouts", "silkscreen", "bays",
                               "placements", "regions"))


def _consistency(views, chassis):
    """Six views must describe ONE box. Returns a list of disagreements.

    This is the valuable half of level 3, and it is not "six views exist". The
    AGR420 was written 480mm deep while its provenance said the top, bottom and
    sides "are the AGR400 shell" - and the AGR400 is 524. Both cannot be true.
    A human caught that one; this catches it every time, at build, for free.

    The chassis block is included as a member of each set rather than trusted
    as the answer, because it can be the thing that is wrong.
    """
    ch = chassis or {}
    sz = {n: effective_size(n, views.get(n), ch) for n in FACES}

    def member(view, axis):
        s = sz.get(view)
        return None if s is None else s[axis]

    sets = (
        ("chassis width", [(f"{v}.w", member(v, 0)) for v in
                           ("front", "rear", "top", "bottom")]
                          + [("chassis.width", ch.get("width"))]),
        ("chassis height", [(f"{v}.h", member(v, 1)) for v in
                            ("front", "rear", "left", "right")]
                           + [("chassis.height", ch.get("height"))]),
        ("chassis depth", [(f"{v}.w", member(v, 0)) for v in ("left", "right")]
                          + [(f"{v}.h", member(v, 1)) for v in ("top", "bottom")]
                          + [("chassis.depth", ch.get("depth"))]),
    )
    bad = []
    for axis, members in sets:
        known = [(k, float(v)) for k, v in members if v is not None]
        if len(known) < 2:
            continue
        lo, hi = min(v for _, v in known), max(v for _, v in known)
        if hi - lo > DIM_TOL:
            bad.append(f"{axis} disagrees: "
                       + ", ".join(f"{k}={v:g}" for k, v in known))
    return bad


# ---------------------------------------------------------------- the chain

def _chain(data):
    """(level, [{'level':n,'name':..,'needs':..}, ...] for every level NOT met).

    The level is the longest satisfied PREFIX, so a device can satisfy a higher
    predicate and not be at that level - the c100g carries `group` and `rel-pos`
    on all 39 of its placements but has only two views, so it is `faced` with
    level 4 already met. Listing every unsatisfied level rather than only the
    next one is what makes that visible, and it tells the author the shortest
    real path: one missing thing, not four.
    """
    views = data.get("views") or {}
    ch = data.get("chassis") or {}
    drawable = {n for n in views
                if effective_size(n, views[n], ch) and _has_content(views[n])}
    met, needs = {}, {}

    met[1] = bool(drawable)
    needs[1] = ("no view has both a size and anything on it"
                if views else "no views at all")

    missing2 = [n for n in ("front", "rear") if n not in drawable]
    met[2] = not missing2
    needs[2] = f"{_plural(len(missing2), 'view')} {', '.join(missing2)}"

    missing3 = [n for n in FACES if n not in drawable]
    clashes = _consistency(views, ch)
    met[3] = not missing3 and not clashes
    parts = []
    if missing3:
        parts.append(f"{_plural(len(missing3), 'view')} {', '.join(missing3)} "
                     "(six faces describe one box)")
    parts += clashes
    needs[3] = "; ".join(parts)

    no_group, no_relpos = [], []
    for vn in views:
        vp = view_parts(views[vn] or {})
        for it in vp["placements"] + vp["bays"]:
            if not it.get("group"):
                no_group.append((vn, it["id"]))
            if it.get("rel-pos") is None:
                no_relpos.append((vn, it["id"]))
    thin = sorted(g for g, d in (data.get("groups") or {}).items()
                  if not (d or {}).get("term") or (d or {}).get("index-origin") is None)
    met[4] = not (no_group or no_relpos or thin)
    parts = []
    if no_group:
        parts.append(f"`group` on {_plural(len(no_group), 'placement')} "
                     f"({_by_view(no_group)})")
    if no_relpos:
        parts.append(f"`rel-pos` on {_plural(len(no_relpos), 'placement')} "
                     f"({_by_view(no_relpos)})")
    if thin:
        parts.append("`term` and `index-origin` on "
                     f"{_plural(len(thin), 'group')} {', '.join(thin)}")
    needs[4] = "; ".join(parts)

    level = 0
    for n, _ in LEVELS:
        if not met[n]:
            break
        level = n
    blocked = [{"level": n, "name": LEVEL_NAME[n], "needs": needs[n]}
               for n, _ in LEVELS if not met[n]]
    return level, blocked


# ---------------------------------------------------------------- the flags

def _specified(data, profiles):
    """(bool | None, needs). None means the device declares no profile.

    Unevaluable is a third answer and it has to stay distinct from false, which
    is why this returns a name for the gap as well. "This device does not state
    its power draw" and "nobody said what kind of thing this is" want different
    fixes from different people, and collapsing them onto `no` produces exactly
    the failure the whole exercise is against: the two most complete models in
    the portfolio - level 4, `modelled`, nineteen and twenty-three attrs off a
    datasheet - scored a bare `no` here, indistinguishable from a device that
    was checked and came up short. A reader sees that and concludes the
    predicate is broken. The right report is "cannot evaluate", and the right
    fix is filed against `profile:`, not against the attrs.

    Filling those profiles in is deliberately NOT done here. Which profile an
    AS7946-30XB is may be obvious and an ES1010 may not be, and guessing is how
    a taxonomy vocabulary goes wrong on the first dozen devices.
    """
    prof = data.get("profile")
    if not prof:
        return None, ("a top-level `profile:` naming the device class, so that "
                      "`specified` has something to judge the attrs against - see "
                      "spec/schemas/profiles.yaml for the classes that exist"), \
            "profile-undeclared"
    spec = profiles.get(prof)
    if spec is None:
        return None, (f"an entry for profile {prof!r} in spec/schemas/profiles.yaml, "
                      "which is where the minimum set for a class is defined"), \
            "profile-undefined"
    attrs = data.get("attrs") or {}
    missing = [fact for fact, keys in (spec.get("requires") or {}).items()
               if not any(k in attrs for k in keys)]
    if not missing:
        return True, "", None
    return False, (f"attrs stating {', '.join(missing)} "
                   f"(profile `{prof}` - see spec/schemas/profiles.yaml)"), None


def _wired(data):
    """`physical-context` on every bay and every port group.

    Aspirational today and that is the correct result, not a bug: the flag
    exists to show a real gap rather than to be satisfied on day one. It is the
    join between a drawing and a running box - the reason an ENTITY-MIB row or a
    Redfish sensor can be laid over the bay it describes - and until it is
    declared, no overlay can be more than a guess at which shape to light up.
    """
    groups = data.get("groups") or {}
    bare_bays, port_groups, total = [], set(), 0
    for vn, view in (data.get("views") or {}).items():
        vp = view_parts(view or {})
        total += len(vp["bays"])
        for b in vp["bays"]:
            if not (b.get("physical-context")
                    or (groups.get(b.get("group")) or {}).get("physical-context")):
                bare_bays.append((vn, b["id"]))
        for p in vp["placements"]:
            g = p.get("group")
            if g and p["id"].startswith("port"):
                port_groups.add(g)
    total += len(port_groups)
    bare_groups = sorted(g for g in port_groups
                         if not (groups.get(g) or {}).get("physical-context"))
    if not total:
        # Vacuously true is not true. A device with no bays and no grouped ports
        # has nothing to correlate an ENTITY-MIB row against, so "everything is
        # wired" would be the flag reporting a hole as a feature - which is the
        # exact failure this whole exercise exists to stop.
        return False, ("no bays and no grouped ports to correlate against, so "
                       "there is nothing to wire yet - group the ports first"), None
    if not bare_bays and not bare_groups:
        return True, "", None
    parts = []
    if bare_bays:
        parts.append(f"`physical-context` on {_plural(len(bare_bays), 'bay')} "
                     f"({_by_view(bare_bays)})")
    if bare_groups:
        parts.append("`physical-context` on port "
                     f"{'group' if len(bare_groups) == 1 else 'groups'} "
                     f"{', '.join(bare_groups)}")
    return False, "; ".join(parts), None


def _templated(data):
    """The Nautobot exporter resolves at least one interface under some NOS.

    Asked of the exporter rather than re-derived here, because "would this
    export" and "does this export" have to be the same question. The exporter
    can raise on a manifest it was not written for; that is a false answer, not
    a crash worth propagating into every build.
    """
    try:
        import nautobot_export
    except ImportError:                        # pragma: no cover
        return False, "the Nautobot exporter is not importable", None
    for nos in ("arcos", "sonic"):
        try:
            if nautobot_export.build(data, nos).get("interfaces"):
                return True, "", None
        except Exception:
            continue
    return False, ("ports the Nautobot exporter recognises - each port placement "
                   "needs `attrs.media` and `attrs.speed` in a combination it maps"), None


# ---------------------------------------------------------------- assembly

def assess(data, schemas_dir=None, profiles=None):
    """The `capability` block for one device manifest.

    {"level": 3, "name": "solid", "flags": [...], "unknown": [...],
     "blocked": [{...}]}

    `blocked` says how to fix it, in words. That is the whole difference between
    a tool and a scoreboard: "level 4 needs `rel-pos` on 12 placements in view
    rear" is something an author can act on this afternoon; a bare 3 is a grade.

    `unknown` lists the flags that could not be EVALUATED, and it is not the
    same list as "flags minus earned". A flag missing from both lists was tested
    and failed; a flag in `unknown` was never testable, and telling a reader
    which is which is the difference between "this model is short of facts" and
    "nobody told the tool what class of thing this is". Absent, the two most
    complete devices in the portfolio read identically to the least.
    """
    profiles = profiles if profiles is not None else load_profiles(schemas_dir or ".")
    level, blocked = _chain(data)
    results = {"specified": _specified(data, profiles),
               "wired": _wired(data),
               "templated": _templated(data)}
    return {"level": level,
            "name": LEVEL_NAME.get(level, "none"),
            "flags": [f for f in FLAGS if results[f][0] is True],
            "unknown": [f for f in FLAGS if results[f][0] is None],
            "blocked": blocked}, results


def declared_gaps(data):
    """The `gaps:` blocks, as records. What no rule can ever see."""
    out = []
    for g in data.get("gaps") or []:
        rec = {"kind": "declared", "what": g["what"],
               "scope": list(g.get("scope") or []),
               "because": g["reason"], "wanted": g["wanted"],
               # An author field, and empty is a fine answer. The S9510's
               # port-lamp gap blocks no capability today - the lamps render,
               # nothing downstream is waiting on their vocabulary - and
               # inventing a blocker to fill the field would make the join
               # meaningless for the gaps that really do block something.
               "blocks": list(g.get("blocks") or [])}
        if g.get("note"):
            rec["note"] = " ".join(str(g["note"]).split())
        out.append(rec)
    return out


# One record per rule per device, not per occurrence: forty ports missing a
# media is one gap of size forty, and listing it forty times buries the other
# four. `wanted` is the field that turns a count into a request.
#
# Every record says WHY it is open in one field, `because`, whichever kind it
# is: a lint code for a derived gap, a reason token for a declared one. They had
# separate fields and a renderer could not tell by position which it was holding,
# so both landed in the same badge and read as one vocabulary. `kind` says how to
# read `because`; there is one thing to read.
RULE_GAPS = {
    "L18": ("port-media",
            "the real media on each port placement, or once on its group - a "
            "family cage component can only ever answer `sfp`"),
    "L19": ("indicator-subject",
            "a `for:` on each indicator naming what it reports on"),
    "L20": ("state-vocabulary",
            "state names as tokens, with the vendor's sentence moved to "
            "`description` beside them"),
    "L21": ("silkscreen-legibility",
            "the buried marks moved clear of the components that paint over them"),
}

CAP_GAPS = {
    "specified": "the About panel, and comparison against other devices",
    "wired": "ENTITY-MIB / Redfish correlation and monitoring overlays",
    "templated": "NetBox / Nautobot device-type export",
}


def derived_gaps(path, data, lib_roots, capability, flag_results):
    """Everything a rule can find. Never hand-maintained, so never stale.

    The lint rules are asked, not reimplemented. A second copy of L18 here would
    be one bad afternoon away from disagreeing with the first, and then the
    register would be reporting gaps that lint says are closed.
    """
    out = []
    for code, ws in sorted(_rule_warnings(path, data, lib_roots).items()):
        if code not in RULE_GAPS:
            continue
        what, wanted = RULE_GAPS[code]
        out.append({"kind": "derived", "what": what, "because": code,
                    "count": len(ws), "wanted": wanted, "blocks": []})
    # The CHAIN is deliberately not here. `capability.blocked` already carries
    # every unsatisfied level with the same sentence, and a gap record repeating
    # it verbatim is one statement printed twice a few inches apart - which
    # consumers were left to de-duplicate by string equality. One statement, one
    # place. What survives here is the flags, which say something `blocked` does
    # not: they are independent of the chain and of each other.
    for flag in FLAGS:
        ok, needs, blocker = flag_results[flag]
        if ok is True:
            continue
        # An unevaluable flag files its gap against the thing that is actually
        # missing. `specified: no` on a device with twenty-four datasheet attrs
        # reads as a broken predicate; `profile-undeclared` reads as one line of
        # YAML somebody has to decide on, which is what it is.
        #
        # No `count` on either: there is nothing being counted, and `count: 0`
        # reads as "nothing found" rather than "nothing to count". A field that
        # measures nothing is better absent than zero.
        #
        # `blocks` is what lets a consumer join a flag to its explanation. It
        # matters most exactly where the gap is named for the CAUSE rather than
        # the symptom: an About panel showing a `?specified` chip cannot find
        # `profile-undeclared` by name, and was reduced to matching the flag in
        # backticks inside the sentence below - which works until somebody
        # rewords it, and then fails silently.
        if ok is None and blocker:
            out.append({"kind": "derived", "what": blocker, "because": "CAP",
                        "blocks": [flag],
                        "wanted": f"{needs}, which unlocks `{flag}` and with it "
                                  f"{CAP_GAPS[flag]}"})
            continue
        out.append({"kind": "derived", "what": flag, "because": "CAP",
                    "blocks": [flag],
                    "wanted": f"{needs} - unlocks {CAP_GAPS[flag]}"})
    return out


def _rule_warnings(path, data, lib_roots):
    """{code: [message, ...]} from running the device rules over one manifest.

    lint.py holds the rules and this borrows them. The import is deferred
    because lint.py imports this module for the portfolio matrix, and its
    warning list is a module global, so it is swapped out and back rather than
    appended to - running this must not put anything into the report lint is
    about to print.
    """
    import lint
    saved_e, saved_w = lint.ERRORS[:], lint.WARNINGS[:]
    lint.ERRORS.clear()
    lint.WARNINGS.clear()
    try:
        lint.lint_device(path, _NoSchema(), lib_roots)
        found = {}
        for w in lint.WARNINGS:
            found.setdefault(w.split("[", 1)[1].split("]", 1)[0], []).append(w)
    finally:
        lint.ERRORS[:] = saved_e
        lint.WARNINGS[:] = saved_w
    return found


class _NoSchema:
    """Schema validation is lint's job and it has already done it."""

    def iter_errors(self, _data):
        return iter(())


def report(path, data, lib_roots, schemas_dir):
    """{'capability': {...}, 'gaps': [...]} for one device. The whole API."""
    cap, flags = assess(data, schemas_dir)
    return {"capability": cap,
            "gaps": declared_gaps(data)
                    + derived_gaps(path, data, lib_roots, cap, flags)}
