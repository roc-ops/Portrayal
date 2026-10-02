#!/usr/bin/env python3
"""Split a published build into the npm packages it ships as (#528).

ONE PACKAGE PER DEVICE, because one package for the library cannot be: jsDelivr
serves a package of at most 50 MB and `library/dist` is several times that. A
vendor, or a vendor's family, is bounded by nothing - UfiSpace alone was 92 MB
and grows with every model - and a family package would have to be split and
renamed under its consumers the day it outgrew the limit. A device is bounded
by itself. So:

- `@portrayal/<vendor>-<device>` - one device: its `configs.json`, its
  `source.json` and each distinct face (#665) with its `.elements.json` (#727).
  The default-configuration copies (`<device>.<view>.svg` and its elements
  file) are left out; `configs.json` names the default and `files` finds its
  faces.
- `@portrayal/components` - the component skins every device shares.
- `@portrayal/index` - the portfolio: the library-wide JSON (`devices.json`,
  `components.json` and the rest) and `packages.json`, which says which package
  and version holds each device, and a vendor -> family -> device tree to browse
  by. The vendor and family are how a reader finds a device, not how it ships.

EACH PACKAGE HAS ITS OWN VERSION, NOT THE DEVICE'S. devicelock deliberately does
not hash rendered output, so a toolchain change moves every face of every
device without moving a device version - and npm will not take new bytes under
a version it already holds. A package is versioned from what npm holds for it
now (`--from-registry`, read off each package's latest package.json - the only
record of what is out; nothing local is trusted to know): an unchanged digest
keeps the version and is not published again; a changed one bumps it by the
largest thing that changed:

- the dist `contract` - breaking;
- the device's own version - the same level as the device moved;
- anything else (a re-render, a new component, a regenerated index) - a fix,
  which is always a patch.

A breaking change is a minor below 1.0 and a major from it, as #449 promises
for the format. A package's first version is its device's version; the
components and the index start at 0.1.0.

Without `--from-registry` every package is versioned as if it had never been
published. That is what publish.sh runs, to lay the packages out and fail on
one over the size limit; it publishes nothing, and `--publish` refuses to run
without the registry's state.

Every package carries `LICENSE` and `NOTICE`: Apache-2.0 asks a redistribution
to carry the NOTICE, which is why build.sh copies both into dist.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCOPE = "@portrayal"
REPO = "git+https://github.com/roc-ops/Portrayal.git"
LICENCE_FILES = ("LICENSE", "NOTICE")
# jsDelivr's documented package limit. A package over it is not served at all,
# so the build fails rather than ship one; WARN_MB is the headroom to notice.
LIMIT_MB = 50
WARN_MB = 25
FIRST = "0.1.0"
# the npm name rules a generated name has to meet (lowercase, url-safe, <=214)
_NPM_NAME = re.compile(r"^@portrayal/[a-z0-9][a-z0-9._-]*$")


# ---- versions --------------------------------------------------------------

def _parse(v):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(v))
    if not m:
        raise ValueError(f"not a plain semver version: {v!r}")
    return tuple(int(x) for x in m.groups())


def moved(old, new):
    """How far a version moved: 'major', 'minor', 'patch', or None."""
    a, b = _parse(old), _parse(new)
    for level, x, y in zip(("major", "minor", "patch"), a, b):
        if x != y:
            return level
    return None


def bump(version, change):
    """`version` bumped for a change that is 'breaking', 'additive' or 'fix'.

    Below 1.0 a caret range pins the minor, so a breaking change moves the
    minor and everything else the patch. From 1.0 it is ordinary semver.
    """
    major, minor, patch = _parse(version)
    if major == 0:
        return f"0.{minor + 1}.0" if change == "breaking" else f"0.{minor}.{patch + 1}"
    if change == "breaking":
        return f"{major + 1}.0.0"
    if change == "additive":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


_RANK = {"fix": 0, "additive": 1, "breaking": 2}
_BY_LEVEL = {"major": "breaking", "minor": "additive", "patch": "fix", None: "fix"}


def next_version(prev, digest, contract, device_version=None, first=FIRST):
    """(version, changed) for a package against what it last published.

    `prev` is that package's entry in the previous state, or None if it has
    never been published.
    """
    if not prev:
        return (device_version or first), True
    if prev["digest"] == digest:
        return prev["version"], False
    change = "fix"
    if prev.get("contract") != contract:
        change = "breaking"
    if device_version and prev.get("device-version"):
        dev = _BY_LEVEL[moved(prev["device-version"], device_version)]
        change = max(change, dev, key=_RANK.get)
    return bump(prev["version"], change), True


# ---- content ---------------------------------------------------------------

def digest(files, meta=None):
    """One digest over a package's payload: each file's path and bytes, and
    the `portrayal` block of its package.json (the device's version, the
    contract), so a package whose description moved is republished even when
    no file did.

    The rest of package.json is not part of it - it carries the version, which
    is what the digest decides.
    """
    h = hashlib.sha256(json.dumps(meta or {}, sort_keys=True).encode())
    for rel, src in sorted(files.items()):
        h.update(rel.encode() + b"\0" + hashlib.sha256(Path(src).read_bytes()).digest())
    return h.hexdigest()


def device_files(dist, name):
    """{published path: source} for one device's package."""
    out = {f"{name}.configs.json": dist / f"{name}.configs.json",
           f"{name}.source.json": dist / f"{name}.source.json"}
    idx = json.loads((dist / f"{name}.configs.json").read_text())
    for c in idx["configs"]:
        for f in c.get("files", {}).values():
            out[f] = dist / f
            # each face's elements file travels with it (#727); a default
            # copy's is left out, as the default copy of the SVG is
            ej = f[:-len(".svg")] + ".elements.json"
            out[ej] = dist / ej
    missing = [k for k, v in out.items() if not v.exists()]
    if missing:
        raise SystemExit(f"{name}: configs.json names files dist does not have: {missing[:5]}")
    return out


def components_files(dist):
    return {p.name: p for p in sorted((dist / "components").glob("*")) if p.is_file()}


def index_files(dist, device_names):
    """The library-wide files: every top-level JSON that is no one device's."""
    own = re.compile(r"^(%s)\." % "|".join(map(re.escape, device_names)))
    return {p.name: p for p in sorted(dist.glob("*.json")) if not own.match(p.name)}


# ---- packages --------------------------------------------------------------

def package_name(ns, device):
    name = f"{SCOPE}/{ns}-{device}"
    if not _NPM_NAME.match(name) or len(name) > 214:
        raise SystemExit(f"{name!r} is not a valid npm package name")
    return name


def _readme(title, body):
    return f"# {title}\n\n{body}\n\nPart of [Portrayal](https://github.com/roc-ops/Portrayal). " \
           "Apache-2.0; see `NOTICE`.\n"


def _write(out, name, version, description, files, meta, readme):
    d = out / name.split("/", 1)[1]
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for rel, src in files.items():
        shutil.copyfile(src, d / rel)
    (d / "README.md").write_text(readme)
    pkg = {"name": name, "version": version, "description": description,
           "license": "Apache-2.0",
           "repository": {"type": "git", "url": REPO, "directory": "library"},
           "publishConfig": {"access": "public"},
           "portrayal": meta}
    (d / "package.json").write_text(json.dumps(pkg, indent=2, sort_keys=False) + "\n")
    size = sum(p.stat().st_size for p in d.iterdir())
    return d, size


def build(dist, out, root, published=None, limit_mb=LIMIT_MB):
    """Write every package under `out`; return ({name: state}, {name: bytes}).

    `published` is what npm holds now (`registry_state`), or nothing. Nothing
    is written back: npm is the record of what is out, and a state file written
    here would claim versions that a dry run or a failed publish never sent.
    """
    dist, out, root = Path(dist), Path(out), Path(root)
    published = published or {}
    devices_json = json.loads((dist / "devices.json").read_text())
    contract = devices_json["contract"]
    licence = {f: root / f for f in LICENCE_FILES}
    out.mkdir(parents=True, exist_ok=True)
    state, sizes, tree, entries = {}, {}, {}, {}

    def add(name, version_of, description, files, meta, readme):
        files = {**files, **licence}
        meta = {**meta, "contract": contract}
        # the generated README and description are in the tarball too, so a
        # change to either is a change to the package
        dg = digest(files, {**meta, "description": description, "readme": readme})
        version, changed = version_of(published.get(name), dg)
        meta = {**meta, "digest": dg}
        d, size = _write(out, name, version, description, files, meta, readme)
        state[name] = {"version": version, "digest": dg, "contract": contract,
                       "changed": changed, **({"device-version": meta["device-version"]}
                                              if "device-version" in meta else {})}
        sizes[name] = size
        return version

    for dev in sorted(devices_json["devices"], key=lambda d: d["name"]):
        name, ns = dev["name"], dev["ns"]
        pkg = package_name(ns, name)
        family = (dev.get("portfolio") or {}).get("family") \
            or (dev.get("portfolio") or {}).get("series") or None
        who = f"{dev['manufacturer']} {dev['model']}"
        version = add(
            pkg,
            lambda prev, dg, v=dev["version"]: next_version(prev, dg, contract, v),
            f"Portrayal drawings of the {who}: every configuration's faces, its "
            f"configurations and its source manifest.",
            device_files(dist, name),
            {"device": name, "vendor": ns, "device-version": dev["version"]},
            _readme(f"{who} - Portrayal drawings",
                    f"`{name}.configs.json` lists the configurations; `configs[].files` "
                    f"names the SVG that draws each face, and the `.elements.json` "
                    f"beside it lists that face's elements. `{name}.source.json` is the "
                    f"source manifest."))
        entries[name] = {"package": pkg, "version": version, "vendor": ns,
                         "manufacturer": dev["manufacturer"], "model": dev["model"],
                         "family": family, "device-version": dev["version"]}
        tree.setdefault(ns, {}).setdefault(family or "", []).append(name)

    comp_version = add(
        f"{SCOPE}/components",
        lambda prev, dg: next_version(prev, dg, contract),
        "Portrayal component skins: the SVG every device drawing's parts are made of.",
        components_files(dist), {},
        _readme("Portrayal components",
                "One SVG per component skin, `<ns>--<name>--<major>--<skin>.svg`; "
                "`components.json` in `@portrayal/index` describes each."))

    staging = out / ".index"
    staging.mkdir(exist_ok=True)
    (staging / "packages.json").write_text(json.dumps({
        "contract": contract,
        "components": {"package": f"{SCOPE}/components", "version": comp_version},
        "devices": entries,
        # vendor -> family -> devices; "" is a device whose manifest names none
        "tree": {v: {f: sorted(ds) for f, ds in sorted(fams.items())}
                 for v, fams in sorted(tree.items())},
    }, indent=1, sort_keys=True) + "\n")
    add(f"{SCOPE}/index",
        lambda prev, dg: next_version(prev, dg, contract),
        "The Portrayal portfolio: every device and component, and which package holds each.",
        {**index_files(dist, list(entries)), "packages.json": staging / "packages.json"},
        {},
        _readme("Portrayal index",
                "`packages.json` maps each device to the package and version that "
                "holds its drawings, with a vendor -> family -> device tree. "
                "`devices.json` and `components.json` are the portfolio itself."))
    shutil.rmtree(staging)

    over = {n: s for n, s in sizes.items() if s > limit_mb * 1e6}
    if over:
        raise SystemExit("over the %d MB package limit: %s" % (
            limit_mb, ", ".join(f"{n} {s / 1e6:.1f} MB" for n, s in over.items())))
    for n, s in sizes.items():
        if s > WARN_MB * 1e6:
            print(f"warning: {n} is {s / 1e6:.1f} MB, over half the {limit_mb} MB limit",
                  file=sys.stderr)
    return state, sizes


# ---- the registry -----------------------------------------------------------

def package_names(dist):
    """Every package a build of `dist` would write, without writing any."""
    devices = json.loads((Path(dist) / "devices.json").read_text())["devices"]
    return [package_name(d["ns"], d["name"]) for d in devices] + \
        [f"{SCOPE}/components", f"{SCOPE}/index"]


def registry_state(names, run=subprocess.run, workers=8):
    """What npm holds now, as `build` takes it: {name: state}.

    Read off each package's latest published package.json, whose `portrayal`
    block carries the digest and contract it was built with. A package npm
    has never seen is absent. Any other failure stops the run: publishing
    against a state we could not read would re-version everything.
    """
    def one(name):
        try:
            r = run(["npm", "view", f"{name}@latest", "--json"], capture_output=True,
                    text=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"npm view {name}: no answer in 120 s")
        if r.returncode:
            if "E404" in (r.stdout + r.stderr):
                return name, None
            raise SystemExit(f"npm view {name}: {(r.stderr or r.stdout).strip()[-400:]}")
        pkg = json.loads(r.stdout)
        meta = pkg.get("portrayal") or {}
        if not meta.get("digest"):
            raise SystemExit(f"{name}@{pkg.get('version')} on npm carries no portrayal digest")
        entry = {"version": pkg["version"], "digest": meta["digest"],
                 "contract": meta.get("contract")}
        if meta.get("device-version"):
            entry["device-version"] = meta["device-version"]
        return name, entry
    with ThreadPoolExecutor(workers) as pool:
        return {n: e for n, e in pool.map(one, names) if e}


def publish(out, state, run=subprocess.run, dry_run=False):
    """`npm publish` every changed package: devices and components first, the
    index LAST, so the index never names a version npm does not have yet.
    Returns the names published, in order."""
    changed = [n for n, s in sorted(state.items()) if s["changed"]]
    order = [n for n in changed if n != f"{SCOPE}/index"] + \
        [n for n in changed if n == f"{SCOPE}/index"]
    for name in order:
        cmd = ["npm", "publish"] + (["--dry-run"] if dry_run else [])
        try:
            r = run(cmd, cwd=Path(out) / name.split("/", 1)[1], capture_output=True,
                    text=True, timeout=900)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"npm publish {name}: no answer in 900 s")
        if r.returncode:
            raise SystemExit(f"npm publish {name}: {(r.stderr or r.stdout).strip()[-400:]}")
        print(f"{'would publish' if dry_run else 'published'} {name}@{state[name]['version']}")
    return order


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="library/dist")
    ap.add_argument("--out", default="library/packages")
    ap.add_argument("--root", default=".", help="where LICENSE and NOTICE are")
    ap.add_argument("--from-registry", action="store_true",
                    help="version against what npm holds now (required with --publish)")
    ap.add_argument("--publish", action="store_true", help="npm publish what changed")
    ap.add_argument("--dry-run", action="store_true", help="with --publish: npm publish --dry-run")
    ap.add_argument("--limit-mb", type=float, default=LIMIT_MB)
    args = ap.parse_args(argv)
    if args.publish and not args.from_registry:
        # with no baseline every package is priced as brand new; a dry run
        # passes, and the first real publish after the first collides
        ap.error("--publish needs --from-registry: npm is the only record of what is out")
    published = registry_state(package_names(args.dist)) if args.from_registry else {}
    state, sizes = build(args.dist, args.out, args.root, published, args.limit_mb)
    changed = sorted(n for n, s in state.items() if s["changed"])
    big = max(sizes, key=sizes.get)
    print(f"wrote {len(state)} packages -> {args.out} ({len(changed)} changed); "
          f"largest {big} {sizes[big] / 1e6:.1f} MB")
    if args.publish:
        publish(args.out, state, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
