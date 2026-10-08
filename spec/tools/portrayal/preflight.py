#!/usr/bin/env python3
"""Preflight: the mechanical misses, caught in seconds, before a review.

    python3 spec/tools/portrayal/preflight.py [--base origin/main] [--json] [--only NAME,...]

WHY IT EXISTS (#924). On one day five of six branches went back for a second
review round, and every round-1 blocker was mechanical rather than a judgement:
exports not regenerated after a device change, a new skip reason missing from
`spec/allowed-skips.txt`, a local path in committed text. Each one is a line
a tool could have printed, and each round re-ran a full suite and a publish on
a shared machine. This runs the cheap half of those gates against the diff and
says PASS or FAIL per check, with the command that fixes it.

WHAT IT IS NOT. It runs no build and no suite. It is the step before asking for
review; CI is still the gate.

THE DIFF is everything between the merge base with `--base` and the WORKING
TREE - commits, staged and unstaged edits - plus untracked files that are not
ignored. A preflight that read only commits would pass the export somebody
regenerated and forgot to `git add`.

THE CHECKS

  exports    The DCIM exports, regenerated from this tree into a temporary
             directory and compared byte for byte with `library/exports`, and
             nothing under `library/exports` left uncommitted. No build: the
             exporter reads a dist, and everything it reads from one - the
             device manifest as `<device>.source.json`, which configurations
             draw which faces, and the four indexes - is derived here from the
             sources without rendering a drawing (see `_stub_dist`). That is
             the whole tree in about ten seconds, so a component change is
             covered for every device that places it without walking anything.
  skips      Every `pytest.skip` / `skipif` / `importorskip` reason ADDED in the
             diff is allowed by `spec/allowed-skips.txt`, the list CI's
             `check_skips.py` holds a run to, or is, in full, one of the few
             sentences naming what CI always provides (`PREREQUISITES`: node,
             a built dist) and so can never fire there.
  private    No machine path, private address, login against an address,
             personal email or listed name in an ADDED line - the patterns of
             `spec/tests/test_no_internal_hosts.py`, imported from it.
  changelog  A fragment under `changelog.d/` when `library/`, `spec/` or `kit/`
             changed, and every fragment well formed (`changelog.py --check`).
  devicelock `devicelock.py --library library` reports nothing; and a device
             whose lock the diff re-recorded is also checked against the lock
             at the merge base, which catches `--update` run before the bump.
             THAT HALF IS STRICTER THAN CI ON PURPOSE: CI sees only the lock
             the branch committed, which `--update` has already made agree.
  lint       Lint on the devices the diff touches, and on every device that
             places a touched component (the `device_dependencies` walk), plus
             the library-wide rules a `--device` run skips (L89 only when the
             diff can change what reaches a component major), with no warning
             that `library/lint-baseline.json` does not already carry. A change
             lint cannot scope to devices - a schema, a listing, a lab, lint
             itself - gets the full lint instead.
  kit        `npm test` in `kit/` when `kit/` changed, and the `spec/tests/*_js.py`
             files that name a changed kit module.

Exit status is 1 when any check fails. `--json` prints one document for an
agent to read instead of the table.
"""
import argparse
import ast
import concurrent.futures as futures
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
TOOLS_ROOT = TOOLS.parents[1]          # the checkout this file belongs to
SCHEMAS = TOOLS_ROOT / "spec" / "schemas"

CHECKS = ("exports", "skips", "private", "changelog", "devicelock", "lint", "kit")


def _pin_toolchain():
    """THIS CHECKOUT'S `portrayal`, or start again with it on PYTHONPATH.

    Run by path, `portrayal` is either not importable or is whichever checkout
    was pip-installed (#561), and a preflight that checked this tree with
    another tree's lint would pass what it should fail. toolchain.sh pins the
    shell scripts by exporting PYTHONPATH; this does the same by re-running
    itself, once, rather than editing sys.path (#178). Children inherit it.
    """
    found = importlib.util.find_spec("portrayal")
    here = TOOLS / "portrayal"
    if found and found.origin and Path(found.origin).resolve().parent == here:
        return
    if os.environ.get("PORTRAYAL_PREFLIGHT_PINNED"):
        raise SystemExit(f"preflight: cannot import portrayal from {here}")
    env = _env()
    env["PORTRAYAL_PREFLIGHT_PINNED"] = "1"
    os.execve(sys.executable, [sys.executable, __file__, *sys.argv[1:]], env)


# ------------------------------------------------------------------ results ---

class Result:
    def __init__(self, name, ok, summary, details=(), fix=None):
        self.name, self.ok, self.summary = name, ok, summary
        self.details, self.fix = list(details), fix
        self.seconds = 0.0

    def as_dict(self):
        return {"name": self.name, "status": "PASS" if self.ok else "FAIL",
                "summary": self.summary, "details": self.details, "fix": self.fix,
                "seconds": round(self.seconds, 1)}


def passed(name, summary, details=()):
    return Result(name, True, summary, details)


def failed(name, summary, details=(), fix=None):
    return Result(name, False, summary, details, fix)


# --------------------------------------------------------------------- git ---

def git(root, *args, check=True):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"preflight: git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def merge_base(root, base):
    return git(root, "merge-base", base, "HEAD").strip()


def changed_files(root, mbase):
    """Every path that differs from the merge base in the working tree, plus
    untracked files that are not ignored. Sorted, relative, deletions included."""
    out = set(git(root, "diff", "--name-only", "--no-renames", mbase).splitlines())
    out |= set(git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    return sorted(p for p in out if p)


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(root, mbase, files):
    """{path: {line number: text}} for the lines the diff adds. An untracked
    file is added whole. Binary and deleted files are left out."""
    out = {}
    known = set(git(root, "ls-tree", "-r", "--name-only", mbase).splitlines()) if mbase else set()
    for rel in files:
        p = Path(root) / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        if rel not in known:
            out[rel] = {n: l for n, l in enumerate(lines, 1)}
            continue
        nums = set()
        for line in git(root, "diff", "-U0", "--no-renames", mbase, "--", rel).splitlines():
            m = HUNK.match(line)
            if m:
                start, count = int(m.group(1)), int(m.group(2) or 1)
                nums.update(range(start, start + count))
        out[rel] = {n: lines[n - 1] for n in sorted(nums) if 0 < n <= len(lines)}
    return out


class Context:
    """What every check reads: the checkout, the diff, and where the tools are."""

    def __init__(self, root, mbase, changed, added=None, jobs=None):
        self.root = Path(root)
        self.library = self.root / "library"
        self.mbase = mbase
        self.changed = list(changed)
        self._added = added
        self.jobs = jobs or min(8, os.cpu_count() or 4)

    @property
    def added(self):
        if self._added is None:
            self._added = added_lines(self.root, self.mbase, self.changed)
        return self._added

    @property
    def base_files(self):
        """Every path the merge base holds, as a set."""
        if getattr(self, "_base_files", None) is None:
            self._base_files = set(git(self.root, "ls-tree", "-r", "--name-only",
                                       self.mbase).splitlines()) if self.mbase else set()
        return self._base_files

    def touches(self, *prefixes):
        return [p for p in self.changed if p.startswith(prefixes)]


def _env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(TOOLS) + (os.pathsep + env["PYTHONPATH"]
                                      if env.get("PYTHONPATH") else "")
    return env


def _tool(name):
    return str(TOOLS / "portrayal" / f"{name}.py")


def _worker(name, payload, cwd):
    """Run one of this file's workers in a child process; its JSON answer."""
    r = subprocess.run([sys.executable, __file__, "--_worker", name],
                       input=json.dumps(payload), capture_output=True, text=True,
                       cwd=cwd, env=_env())
    if r.returncode:
        raise RuntimeError(f"{name} worker failed:\n{(r.stderr or r.stdout)[-2000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


# ----------------------------------------------------------------- exports ---

# Anything here, changed, can change an export. Markdown under library/ cannot.
EXPORT_INPUTS = ("library/", "spec/tools/", "spec/schemas/", "LICENSE", "NOTICE")


def _stub_dist(library, out):
    """The part of a dist the exporter reads, derived without rendering.

    `artifacts.Dist` opens devices.json, components.json, vendors.json,
    listings.json, `<device>.source.json`, and - only to decide `front_image`
    and `rear_image` - which face file `<device>.configs.json` names for each
    configuration. The two index files come from their own tools. The rest is
    written here, and each piece says where the real one comes from:

    - `<device>.source.json` is `render.source_bytes` of the loaded manifest,
      the same call render.py makes;
    - a configuration draws exactly the faces `manifest.resolve_views` returns
      for it, which is the loop render.py writes its files from, so an empty
      file per face answers "does this configuration have a front" as a
      rendered one would;
    - devices.json carries the fields the exporter reads (name, ns, model,
      manufacturer, datasheet, version) in devices_index.py's order. Its
      `capability` is most of devices_index's time and nothing here reads it.

    test_preflight.py proves the stub against the committed exports: on a
    clean tree the regeneration matches `library/exports` byte for byte.
    """
    from portrayal import libwalk, manifest, render
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    devices = []
    for f in libwalk.iter_devices([library]):
        d = manifest.load_yaml(f)
        if not d or d.get("kind") != "device":
            continue
        devices.append({"name": d["name"], "model": d.get("model", d["name"]),
                        "manufacturer": d.get("manufacturer", ""),
                        "ns": f.parent.parent.name,
                        "datasheet": d.get("datasheet") or {},
                        "version": d.get("version", "")})
        (out / f"{d['name']}.source.json").write_bytes(render.source_bytes(d))
        configs = d.get("configurations") or {"default": {"default": True}}
        entries = []
        for cname, cfg in configs.items():
            files = {}
            for face in manifest.resolve_views(d, cfg):
                fn = f"{d['name']}.{cname}.{face}.svg"
                (out / fn).touch()
                files[face] = fn
            entries.append({"name": cname, "files": files})
        (out / f"{d['name']}.configs.json").write_text(json.dumps({"configs": entries}))
    devices.sort(key=lambda x: (x["manufacturer"], x["name"]))
    (out / "devices.json").write_text(json.dumps({"devices": devices}))
    return len(devices)


def regenerate_exports(root, out):
    """Write this tree's exports under `out`, the way publish.sh would. Returns
    a list of error strings; empty means `out` holds the full export."""
    root, out = Path(root), Path(out)
    library = root / "library"
    with tempfile.TemporaryDirectory(prefix="preflight-dist-") as dist:
        steps = [subprocess.Popen([sys.executable, _tool(ix), "--library", str(library),
                                   "--out", dist], cwd=root, env=_env(),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                 for ix in ("components_index", "registry_index")]
        errors = []
        try:
            _worker("stub-dist", {"library": str(library), "out": dist}, root)
        except RuntimeError as e:
            errors.append(str(e))
        for p in steps:
            _, err = p.communicate()
            if p.returncode:
                errors.append(f"{p.args[1]}: {err.strip()[-1500:]}")
        if errors:
            return errors
        base = [sys.executable, _tool("dcim_export"), "--dist", dist, "--out", str(out),
                "--images", "--no-raster"]
        runs = [subprocess.Popen(base + extra, cwd=root, env=_env(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                for extra in ([], ["--modules"])]
        for p in runs:
            _, err = p.communicate()
            if p.returncode:
                errors.append(f"dcim_export {' '.join(p.args[8:]) or '(devices)'}: "
                              f"{err.strip()[-1500:]}")
    for f in ("LICENSE", "NOTICE"):
        if (root / f).exists():
            shutil.copyfile(root / f, out / f)
    return errors


def _tree_files(tree, root=None):
    """The export files a reviewer would see: tracked or untracked-not-ignored
    when `tree` is in the checkout, every file otherwise."""
    tree = Path(tree)
    if root is not None:
        try:
            rel = tree.resolve().relative_to(Path(root).resolve())
        except ValueError:
            rel = None
        if rel is not None:
            listed = git(root, "ls-files", "-co", "--exclude-standard", "--", str(rel))
            return {str(Path(p).relative_to(rel)) for p in listed.splitlines()
                    if p and (Path(root) / p).is_file()}
    return {str(p.relative_to(tree)) for p in tree.rglob("*") if p.is_file()}


def compare_exports(fresh, tree, root=None):
    """(stale, missing, extra): files whose bytes differ, files the exporter
    writes that the tree lacks, files the tree has that nothing writes."""
    have = _tree_files(tree, root)
    want = _tree_files(fresh)
    stale = sorted(f for f in want & have
                   if (Path(fresh) / f).read_bytes() != (Path(tree) / f).read_bytes())
    return stale, sorted(want - have), sorted(have - want)


def check_exports(ctx):
    name = "exports"
    if not ctx.touches(*EXPORT_INPUTS):
        return passed(name, "nothing that feeds the exports changed")
    fix = "./publish.sh --no-images, then commit library/exports"
    with tempfile.TemporaryDirectory(prefix="preflight-exports-") as out:
        errors = regenerate_exports(ctx.root, out)
        if errors:
            return failed(name, "the exporter failed on this tree", errors, fix)
        stale, missing, extra = compare_exports(out, ctx.library / "exports", ctx.root)
        n = len(_tree_files(out))
    details = ([f"stale: {f}" for f in stale] + [f"not written: {f}" for f in missing]
               + [f"no longer exported: {f}" for f in extra])
    if details:
        return failed(name, f"{len(stale) + len(missing) + len(extra)} of {n} export "
                            "file(s) differ from what this tree produces", details, fix)
    dirty = git(ctx.root, "status", "--porcelain", "--untracked-files=all", "--",
                "library/exports").splitlines()
    if dirty:
        return failed(name, f"library/exports is current but {len(dirty)} file(s) are "
                            "not committed", dirty, "git add library/exports && git commit")
    return passed(name, f"regenerated {n} export files from this tree; all match "
                        "library/exports")


# ------------------------------------------------------------------- skips ---

SKIP_CALLS = {"skip", "skipif", "importorskip"}
# A REASON THAT NAMES SOMETHING CI ALWAYS PROVIDES cannot fire there: CI runs
# publish.sh (the dist, the indexes, the exports) and installs node before the
# suite. These are the skips a fresh checkout reports and CI never does, which
# is why they are deliberately NOT in the allow-list - if one ever fires on CI,
# check_skips must fail the run.
#
# WHOLE-REASON MATCHES, AND NARROW. A substring test passed "cairosvg not
# installed" (CI has no cairosvg), "common/some-part not built" (a part, not a
# build output) and any sentence that happened to mention ./build.sh. Each
# pattern names exactly a thing CI provides; anything else is the allow-list's
# decision, not this file's.
#
# THE SUBJECT IS ALWAYS A FIXED BUILD OUTPUT, never an interpolation: `_literal`
# reads f"{part} not built" as "{...} not built", and on CI that expands to a
# part name check_skips does not allow. A runtime value may follow the fixed
# prefix (`library/dist not built: {...}`), where it only says which file.
BUILD_OUTPUTS = ("library/dist", "library/exports", "dist", "dist/",
                 # the indexes build.sh writes into the dist, by name
                 "devices.json", "components.json", "components-detail.json",
                 "labs.json", "gaps.json", "vendors.json", "listings.json",
                 "comparable-facts.json", "rack.json", "devices.lock.json")
PREREQUISITES = tuple(re.compile(p) for p in (
    r"(node|npm) not installed",
    r"(" + "|".join(re.escape(o) for o in BUILD_OUTPUTS) + r") not built"
    r"((?: - |; )run \./(build|publish)\.sh( --no-images)?)?(: \{\.\.\.\})?",
))


def _literal(node):
    """A reason's text with `{...}` for what only runs at test time, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{...}"
                       for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left = _literal(node.left)
        right = _literal(node.right) if isinstance(node.op, ast.Add) else "{...}"
        return None if left is None or right is None else left + right
    return None


def skip_reasons(source):
    """[(line, end line, reason or None)] for every skip call in a test file."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        attr = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if attr not in SKIP_CALLS:
            continue
        kw = {k.arg: k.value for k in node.keywords}
        if "reason" in kw:
            reason = _literal(kw["reason"])
        elif attr == "skip" and (node.args or "msg" in kw):
            reason = _literal(node.args[0] if node.args else kw["msg"])
        elif attr == "importorskip" and node.args:
            mod = _literal(node.args[0])
            reason = None if mod is None else f"could not import '{mod}'"
        elif attr == "skip":
            reason = "unconditional skip"
        else:
            reason = None
        out.append((node.lineno, getattr(node, "end_lineno", node.lineno), reason))
    return out


def reason_allowed(reason, allowed):
    if reason is None:
        return False
    return any(a in reason for a in allowed) or any(p.fullmatch(reason) for p in PREREQUISITES)


def check_skips(ctx):
    from portrayal import check_skips as cs
    name = "skips"
    allowlist = ctx.root / "spec" / "allowed-skips.txt"
    allowed = cs.allowed(allowlist) if allowlist.exists() else []
    bad, seen = [], 0
    for rel, lines in sorted(ctx.added.items()):
        if not (rel.startswith("spec/tests/") and rel.endswith(".py")) or not lines:
            continue
        try:
            calls = skip_reasons((ctx.root / rel).read_text(encoding="utf-8"))
        except SyntaxError as e:
            bad.append(f"{rel}: does not parse ({e.msg}, line {e.lineno})")
            continue
        for start, end, reason in calls:
            if not any(n in lines for n in range(start, end + 1)):
                continue
            seen += 1
            if not reason_allowed(reason, allowed):
                bad.append(f"{rel}:{start}: "
                           + (repr(reason) if reason else "reason is not a literal"))
    if bad:
        return failed(name, f"{len(bad)} added skip reason(s) that spec/allowed-skips.txt "
                            "does not allow", bad,
                      "make the test run instead of skipping, or add the reason to "
                      "spec/allowed-skips.txt with a comment saying why it is a fact "
                      "about the world (CI's check_skips.py fails on any other)")
    return passed(name, f"{seen} added skip call(s), all allowed" if seen
                  else "no skip calls added")


# ----------------------------------------------------------------- private ---

def _host_patterns(root):
    """test_no_internal_hosts, imported rather than copied: one set of patterns."""
    path = Path(root) / "spec" / "tests" / "test_no_internal_hosts.py"
    if not path.exists():
        path = TOOLS_ROOT / "spec" / "tests" / "test_no_internal_hosts.py"
    spec = importlib.util.spec_from_file_location("_preflight_hosts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def private_hits(rel, line, hosts):
    """What in one added line test_no_internal_hosts would report."""
    hits = [m.group(0) for pat in (hosts.PRIVATE_IP, hosts.SSH_TARGET, hosts.MACHINE_PATH)
            for m in pat.finditer(line)]
    hits += [m.group(0) for m in hosts.EMAIL.finditer(line) if not hosts._allowed_email(m)]
    hits += [f"a listed private name (hash {hosts._h(w)})"
             for w in hosts.private_names_in(rel, line)]
    return hits


def check_private(ctx):
    name = "private"
    hosts = _host_patterns(ctx.root)
    bad, n = [], 0
    for rel, lines in sorted(ctx.added.items()):
        if rel in hosts.EXEMPT:
            continue
        for num, line in lines.items():
            n += 1
            for h in private_hits(rel, line, hosts):
                bad.append(f"{rel}:{num}: {h}")
    if bad:
        return failed(name, f"{len(bad)} private string(s) in added lines", bad,
                      "write paths relative to the repository root (or /home/me/ as an "
                      "example), use RFC 5737 addresses and example.com, say 'the "
                      "maintainer' - see spec/tests/test_no_internal_hosts.py")
    return passed(name, f"{n} added line(s) read, nothing private")


# --------------------------------------------------------------- changelog ---

def check_changelog(ctx):
    from portrayal import changelog
    name = "changelog"
    errors = changelog.check(ctx.root)
    if errors:
        return failed(name, "a changelog fragment is malformed", errors,
                      "fix the fragment; changelog.d/README.md has the four headings")
    if not ctx.touches("library/", "spec/", "kit/"):
        return passed(name, "library/, spec/ and kit/ unchanged; no fragment needed")
    frags = [p for p in ctx.changed
             if re.fullmatch(r"changelog\.d/[^/]+\.md", p) and p != "changelog.d/README.md"
             and (ctx.root / p).is_file()]
    if not frags:
        return failed(name, "library/, spec/ or kit/ changed and no changelog.d/ fragment "
                            "was added", [],
                      "add changelog.d/<branch-or-topic>.md (changelog.d/README.md says "
                      "how), then python3 spec/tools/portrayal/changelog.py --check")
    return passed(name, f"fragment {', '.join(frags)}; every fragment well formed")


# -------------------------------------------------------------- devicelock ---

LOCK = re.compile(r"^library/devices/([^/]+/[^/]+)/device\.lock\.json$")


def _devicelock_worker(payload):
    """devicelock.check, and the same check for the re-locked devices against
    their locks at the merge base, keeping only the bump findings."""
    import pathlib
    from portrayal import devicelock
    library = pathlib.Path(payload["library"])
    findings = [m for _, _, m in devicelock.check(library)]
    base = payload.get("base_locks") or {}
    if base:
        orig_load, orig_files, orig_listings = (devicelock.load_lock, devicelock.device_files,
                                                devicelock.check_listings)
        wanted = {library / "devices" / s / "device.yaml" for s in base}

        def load_lock(lib):
            got = orig_load(lib)
            got["devices"].update(base)
            return got
        devicelock.load_lock = load_lock
        devicelock.device_files = lambda lib: [f for f in orig_files(lib) if f in wanted]
        devicelock.check_listings = lambda lib: []
        try:
            findings += [f"against the merge base: {m}" for _, kind, m in devicelock.check(library)
                         if kind in ("unbumped", "backwards")]
        finally:
            devicelock.load_lock, devicelock.device_files, devicelock.check_listings = \
                orig_load, orig_files, orig_listings
    return {"findings": findings}


def check_devicelock(ctx):
    name = "devicelock"
    # the fingerprint is computed by devicelock over manifest.py's reading of
    # the YAML and libwalk's walk of it, so a change to either can move it
    if not ctx.touches("library/", *(f"spec/tools/portrayal/{m}.py"
                                      for m in ("devicelock", "manifest", "libwalk"))):
        return passed(name, "library/ and the lock's tools unchanged")
    base_locks = {}
    for p in ctx.changed:
        m = LOCK.match(p)
        if m and ctx.mbase and (ctx.library / "devices" / m.group(1) / "device.yaml").exists():
            r = subprocess.run(["git", "show", f"{ctx.mbase}:{p}"], cwd=ctx.root,
                               capture_output=True, text=True)
            if r.returncode == 0:
                base_locks[m.group(1)] = json.loads(r.stdout)
    out = _worker("devicelock", {"library": str(ctx.library), "base_locks": base_locks},
                  ctx.root)
    if out["findings"]:
        return failed(name, f"{len(out['findings'])} finding(s)", out["findings"],
                      "bump the device's version first (check it against the lock on "
                      "main), THEN python3 spec/tools/portrayal/devicelock.py --library "
                      "library --update")
    extra = f"; {len(base_locks)} re-locked device(s) also checked against the merge base" \
        if base_locks else ""
    return passed(name, "0 findings" + extra)


# -------------------------------------------------------------------- lint ---

def _portrayal_imports(path, seen=None):
    """The portrayal modules a tool imports, transitively, by reading them."""
    seen = set() if seen is None else seen
    pkg = Path(path).parent
    for node in ast.walk(ast.parse(Path(path).read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.ImportFrom) and node.module == "portrayal":
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("portrayal."):
            names = [node.module.split(".", 1)[1]]
        elif isinstance(node, ast.Import):
            names = [a.name.split(".", 1)[1] for a in node.names
                     if a.name.startswith("portrayal.")]
        for n in names:
            f = pkg / f"{n}.py"
            if f.exists() and f.name not in seen:
                seen.add(f.name)
                _portrayal_imports(f, seen)
    return seen


DEVICE_FILE = re.compile(r"^library/devices/([^/]+)/([^/]+)/")
COMPONENT_DIR = re.compile(r"^library/components/([^/]+)/([^/]+)/(v\d+)/")


# A changed line that can move what reaches a component major: a ref (`ns/x@2`),
# a bay's `accepts`, a placement's `default`, a part's `unplaced:` waiver - or
# a YAML anchor or alias (`&cards`, `*cards`), because an alias carries a list
# of refs that the changed line itself does not spell.
REACH = re.compile(r"\baccepts\b|\bdefault\b|\bunplaced\b|[a-z0-9-]/[a-z0-9._-]+@\d"
                   r"|(?:^|[\s\[,:-])[*&][A-Za-z_][\w-]*")


def _reach_changed(ctx, yamls):
    """Did the diff add or remove a component major, or change a line that
    decides what reaches one? Only then is L89's library walk worth its time."""
    base = ctx.base_files
    for p in yamls:
        if p.endswith("/contract.yaml") and ((p in base) != (ctx.root / p).exists()):
            return True                    # a major added or removed
        if p not in base:
            text = (ctx.root / p).read_text(encoding="utf-8") if (ctx.root / p).exists() else ""
        else:
            text = "\n".join(l[1:] for l in git(ctx.root, "diff", "-U0", "--no-renames",
                                                  ctx.mbase, "--", p).splitlines()
                             if l[:1] in "+-" and not l.startswith(("+++", "---")))
        if REACH.search(text):
            return True
    return False


def lint_plan(ctx):
    """(devices, contracts, full, majors): device dirs to lint, touched contract
    files, the paths only a full lint can answer for, and whether L89 must run."""
    lint_mods = {"lint.py"} | _portrayal_imports(TOOLS / "portrayal" / "lint.py")
    devices, contracts, full, yamls = set(), set(), [], []
    for p in ctx.changed:
        if p.startswith("spec/schemas/") or (
                p.startswith("spec/tools/portrayal/") and Path(p).name in lint_mods):
            full.append(p)
        if not p.startswith("library/") or p.startswith("library/exports/") \
                or p.endswith(".md"):
            continue
        m, c = DEVICE_FILE.match(p), COMPONENT_DIR.match(p)
        if m:
            d = ctx.root / "library" / "devices" / m.group(1) / m.group(2)
            if (d / "device.yaml").exists():
                devices.add(d)
                if p.endswith(".yaml"):
                    yamls.append(p)
            else:
                full.append(p)            # a listing, or a device that is gone
        elif c:
            f = ctx.root / "library" / "components" / c.group(1) / c.group(2) / c.group(3) \
                / "contract.yaml"
            if f.exists():
                contracts.add(f)
                if p.endswith(".yaml"):
                    yamls.append(p)
            else:
                full.append(p)            # a major that is gone
        else:
            full.append(p)                # labs, the baseline, anything library-wide
    if contracts:
        from portrayal import libwalk, lint
        targets = {f.resolve() for f in contracts} | {(ctx.root / p).resolve()
                                                      for p in ctx.changed}
        for dev in libwalk.iter_devices([ctx.library]):
            deps = {Path(x).resolve() for x in lint.device_dependencies(dev, [str(ctx.library)])}
            if deps & targets:
                devices.add(dev.parent)
    majors = not full and _reach_changed(ctx, yamls)
    return sorted(devices), sorted(contracts), full, majors


# What `lint.main` runs only WITHOUT --device, because one device cannot answer
# it - and so what a scoped run silently skipped until preflight ran it again
# here. L89 (`lint_unplaced_majors`) is the slow one and is separate.
LIBRARY_RULES = ("comparable_facts", "aliases", "listings", "bay_size_per_module",
                 "vendor_registry", "pluggable_family_interfaces")


def _lint_worker(payload):
    """One lint run in this process; its errors and its warning counts.

    `mode` is `scoped` (lint.main with --device), `full` (lint.main as CI runs
    it), `library` (the library-wide rules a scoped run skips, over every
    device and contract) or `unplaced` (L89 alone). Waived warnings are left
    out, as lint.main leaves them out of what it compares with the baseline.
    """
    from portrayal import lint
    library, mode = payload["library"], payload["mode"]
    extra = {Path(p) for p in payload.get("extra") or []}
    if extra:
        orig = lint.device_dependencies
        lint.device_dependencies = lambda f, roots: orig(f, roots) | extra
    argv = ["lint.py", "--schemas", payload["schemas"], "--library", library]
    devices = payload.get("devices") or []
    if mode in ("library", "unplaced"):
        # lint.main loads the vocabularies the rules read; a selector that
        # matches nothing makes that all it does
        devices = ["\0preflight: no device\0"]
    for d in devices:
        argv += ["--device", d]
    sys.argv = argv
    # THROUGH lint.collecting(), the one sanctioned way to read what a rule
    # found: it saves and restores the globals, so nothing here writes them.
    with contextlib.redirect_stdout(io.StringIO()):
        with lint.collecting() as found:
            try:
                lint.main()
            except SystemExit:
                pass
        if mode in ("library", "unplaced"):
            # what main found was only its own setup; the rules below are the run
            with lint.collecting() as found:
                root = Path(library)
                if mode == "unplaced":
                    lint.lint_unplaced_majors(root)
                else:
                    from portrayal import libwalk
                    matrix, comp = [], []
                    for f in libwalk.iter_devices([root]):
                        d = lint.load_yaml(f)
                        if isinstance(d, dict) and d.get("kind") == "device":
                            matrix.append((f, d))
                            waive = (d.get("lint") or {}).get("waive") or {}
                            if waive:
                                lint.WAIVED[str(Path(f).resolve())] = dict(waive)
                    for f in libwalk.iter_components([root]):
                        d = lint.load_yaml(f)
                        if isinstance(d, dict):
                            comp.append((f, d))
                    lint.lint_library_comparable_facts([root], matrix)
                    lint.lint_library_aliases(matrix)
                    lint.lint_library_listings([library])
                    lint.lint_library_bay_size_per_module(matrix + comp, [library])
                    lint.lint_vendor_registry(root)
                    lint.lint_pluggable_family_interfaces(root)
    # lint.main drops waived warnings itself; the library-wide rules did not
    # run through it, so the same filter is applied to every mode here
    warnings = [w for w in found.warnings if not lint._is_waived(w)]
    counts = lint._warning_counts(warnings, library)
    examples = {}
    for w in warnings:
        if "[" in w:
            key = f"{lint._rel(w.split(':')[0].strip(), library)}|{w.split('[')[1].split(']')[0]}"
            examples.setdefault(key, w)
    return {"errors": list(found.errors), "counts": counts, "examples": examples}


def _add(into, counts, combine):
    for f, rules in counts.items():
        for code, n in rules.items():
            into.setdefault(f, {})[code] = combine(into.get(f, {}).get(code, 0), n)


def check_lint(ctx):
    name = "lint"
    devices, contracts, full, majors = lint_plan(ctx)
    if not devices and not contracts and not full:
        return passed(name, "no device, component or lint input changed")
    payload = {"schemas": str(SCHEMAS), "library": str(ctx.library)}
    if full:
        scoped, wide = [dict(payload, mode="full")], []
        scope = f"full lint ({full[0]}{' and more' if len(full) > 1 else ''} needs it)"
    else:
        sels = [f"devices/{d.parent.name}/{d.name}/device.yaml" for d in devices]
        if not sels:
            # A COMPONENT NO DEVICE PLACES YET. Lint only checks components a
            # selected device reaches, so one device carries it in.
            from portrayal import libwalk
            first = libwalk.iter_devices([ctx.library])[0]
            sels = [f"devices/{first.parent.parent.name}/{first.parent.name}/device.yaml"]
        size = max(8, -(-len(sels) // ctx.jobs))
        scoped = [dict(payload, mode="scoped", devices=sels[i:i + size])
                  for i in range(0, len(sels), size)]
        scoped[0]["extra"] = [str(f) for f in contracts]
        wide = [dict(payload, mode="library")] + ([dict(payload, mode="unplaced")]
                                                  if majors else [])
        scope = (f"{len(devices)} device(s)"
                 + (f", {len(contracts)} touched component(s)" if contracts else "")
                 + " + library-wide rules" + (" + L89" if majors else ""))
    with futures.ThreadPoolExecutor(len(scoped) + len(wide)) as pool:
        got = list(pool.map(lambda j: _worker("lint", j, ctx.root), scoped + wide))
    # A COMPONENT IS LINTED IN FULL BY EVERY CHUNK THAT REACHES IT, so the scoped
    # chunks combine by max (device files are disjoint between chunks). The
    # library-wide passes are other rules on the same files, so they add.
    counts, errors, examples = {}, [], {}
    for i, r in enumerate(got):
        _add(counts, r["counts"], max if i < len(scoped) else (lambda a, b: a + b))
        errors += [e for e in r["errors"] if e not in errors]
        for k, w in r["examples"].items():
            examples.setdefault(k, w)
    base_file = ctx.library / "lint-baseline.json"
    base = json.loads(base_file.read_text()) if base_file.exists() else {}
    new = {f: {c: n - (base.get(f) or {}).get(c, 0) for c, n in rules.items()
               if n > (base.get(f) or {}).get(c, 0)} for f, rules in counts.items()}
    new = {f: r for f, r in new.items() if r}
    details = [f"error: {e}" for e in errors]
    for f, rules in sorted(new.items()):
        for code, n in sorted(rules.items()):
            details.append(f"+{n} [{code}] {f} - e.g. " + examples.get(f"{f}|{code}", ""))
    sel = " ".join(f"--device {d.parent.name}/{d.name}" for d in devices[:3])
    fix = ("python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library "
           + (sel + " " if sel and not full else "") + "and fix what it reports (the "
           "library-wide rules need the run without --device); a warning you mean to "
           "keep is argued in the device's lint.waive")
    if errors or new:
        return failed(name, f"{scope}: {len(errors)} error(s), "
                            f"{sum(sum(r.values()) for r in new.values())} warning(s) not in "
                            "the baseline", details, fix)
    return passed(name, f"{scope}: no errors, no warning beyond the baseline")


# --------------------------------------------------------------------- kit ---

def check_kit(ctx):
    name = "kit"
    if not ctx.touches("kit/"):
        return passed(name, "kit/ unchanged")
    npm = shutil.which("npm")
    if not npm:
        return failed(name, "kit/ changed and npm is not installed", [],
                      "install node, then cd kit && npm test")
    r = subprocess.run([npm, "test"], cwd=ctx.root / "kit", capture_output=True, text=True)
    if r.returncode:
        return failed(name, "npm test failed", (r.stdout + r.stderr).strip().splitlines()[-20:],
                      "cd kit && npm test")
    # `npm test` is a syntax check. The kit's BEHAVIOUR is tested from python,
    # by spec/tests/*_js.py driving node; run the ones that name a changed
    # module. A test that names none of them is not run here - CI runs it.
    mods = {Path(p).name for p in ctx.touches("kit/") if p.endswith(".js")}
    tests = sorted(str(t.relative_to(ctx.root)) for t in (ctx.root / "spec/tests").glob("*_js.py")
                   if any(m in t.read_text(encoding="utf-8") for m in mods)) if mods else []
    if not tests:
        return passed(name, "npm test passed; no *_js.py test names a changed module")
    # THE CHILD'S TEMPORARY FILES GO BESIDE THE CHECKOUT, not on the system
    # disk: parallel suites have filled that before. The directory name holds
    # "pytest", which pytest's tmp_path machinery expects of its base.
    with tempfile.TemporaryDirectory(prefix=".pytest-preflight-", dir=ctx.root.parent) as tmp:
        env = dict(_env(), TMPDIR=tmp)
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider",
                            "-n", str(ctx.jobs), *tests], cwd=ctx.root, env=env,
                           capture_output=True, text=True)
    # A SKIP IS NOT A PASS, and a behaviour test that skipped for want of a
    # build tested nothing: say how many, and which.
    skips = [l.strip() for l in r.stdout.splitlines() if l.startswith("SKIPPED")]
    n_skip = sum(int(m.group(1)) for l in skips for m in [re.match(r"SKIPPED \[(\d+)\]", l)] if m)
    if r.returncode:
        return failed(name, f"npm test passed; {len(tests)} kit behaviour test file(s) failed",
                      (r.stdout + r.stderr).strip().splitlines()[-20:],
                      "python3 -m pytest -q " + " ".join(tests))
    return passed(name, f"npm test and {len(tests)} kit behaviour test file(s) passed"
                        + (f", {n_skip} test(s) skipped" if n_skip else ", none skipped"),
                  skips)


# -------------------------------------------------------------------- main ---

RUNNERS = {"exports": check_exports, "skips": check_skips, "private": check_private,
           "changelog": check_changelog, "devicelock": check_devicelock,
           "lint": check_lint, "kit": check_kit}


def run(ctx, only=CHECKS):
    def one(name):
        t = time.time()
        try:
            res = RUNNERS[name](ctx)
        except Exception as e:                      # a crash is a FAIL, never a pass
            res = failed(name, f"the check itself failed: {type(e).__name__}",
                         str(e).splitlines()[-20:])
        res.seconds = time.time() - t
        return res
    with futures.ThreadPoolExecutor(len(only)) as pool:
        return list(pool.map(one, only))


def render_text(results, base, mbase, n_changed, seconds):
    lines = [f"preflight: {n_changed} changed file(s) against {base} ({mbase[:12]})"]
    for r in results:
        lines.append(f"{'PASS' if r.ok else 'FAIL'}  {r.name:<10}  {r.summary}  "
                     f"({r.seconds:.1f}s)")
        # a FAIL's details are the findings; a PASS carries details only when
        # it has something to declare (the kit's skipped tests)
        for d in r.details[:25]:
            lines.append(f"        {d}")
        if len(r.details) > 25:
            lines.append(f"        ... and {len(r.details) - 25} more")
        if not r.ok and r.fix:
            lines.append(f"        fix: {r.fix}")
    bad = [r.name for r in results if not r.ok]
    lines.append(f"preflight: {'FAIL (' + ', '.join(bad) + ')' if bad else 'PASS'} "
                 f"in {seconds:.1f}s")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--base", default="origin/main",
                    help="what the branch is compared against (default: origin/main)")
    ap.add_argument("--json", action="store_true", help="one JSON document, for agents")
    ap.add_argument("--only", help=f"comma-separated subset of {','.join(CHECKS)}")
    ap.add_argument("--jobs", type=int, help="lint processes at once (default: cores, max 8)")
    ap.add_argument("--root", default=str(TOOLS_ROOT), help=argparse.SUPPRESS)
    ap.add_argument("--_worker", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args._worker:
        payload = json.loads(sys.stdin.read() or "{}")
        if args._worker == "stub-dist":
            out = {"devices": _stub_dist(payload["library"], payload["out"])}
        elif args._worker == "lint":
            out = _lint_worker(payload)
        elif args._worker == "devicelock":
            with contextlib.redirect_stdout(io.StringIO()):
                out = _devicelock_worker(payload)
        else:
            raise SystemExit(f"unknown worker {args._worker}")
        print(json.dumps(out))
        return 0
    only = tuple(c.strip() for c in args.only.split(",")) if args.only else CHECKS
    unknown = [c for c in only if c not in CHECKS]
    if unknown:
        ap.error(f"unknown check(s) {', '.join(unknown)}; choose from {', '.join(CHECKS)}")
    t = time.time()
    root = Path(args.root)
    mbase = merge_base(root, args.base)
    ctx = Context(root, mbase, changed_files(root, mbase), jobs=args.jobs)
    results = run(ctx, only)
    seconds = time.time() - t
    ok = all(r.ok for r in results)
    if args.json:
        print(json.dumps({"ok": ok, "base": args.base, "merge_base": mbase,
                          "changed": ctx.changed, "seconds": round(seconds, 1),
                          "checks": [r.as_dict() for r in results]}, indent=1))
    else:
        print(render_text(results, args.base, mbase, len(ctx.changed), seconds))
    return 0 if ok else 1


if __name__ == "__main__":
    _pin_toolchain()
    sys.exit(main())
