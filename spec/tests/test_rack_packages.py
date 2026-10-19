"""#935, decided 2026-10-09: racks ship as npm packages.

A rack is a product of its own kind, so the packager (npm_packages.py) writes
one `@portrayal/racks-<vendor>-<name>` package per rack, beside the device and
component packages, and `@portrayal/index`'s `packages.json` says which package
and version holds each. The package holds the compiled product and the schema it
was checked against, so a reader with the tarball alone can read a rack and
validate it. The kit's resolver loads a rack from that package
(`readRack` in kit/dist.js, run by test_kit_package_dist.py).

The fixtures here are small and move one rule at a time; the last tests read the
real build.
"""
import json
import pathlib
import shutil
import subprocess
import tarfile

import pytest
from jsonschema import Draft202012Validator

from portrayal import npm_packages as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
SCHEMA = ROOT / "spec/schemas/rack-product.schema.json"

RACK = {
    "format": 1, "kind": "rack", "name": "frame-4p", "version": "1.2.0",
    "maturity": "modelled", "manufacturer": "Acme", "model": "FRAME-4P",
    "form": "4-post-frame", "ru": 42, "numbering": {"direction": "bottom-up", "start": 1},
    "holes": {"style": "square"}, "rails": [{"id": "front"}, {"id": "rear"}],
}


def _dist(tmp, rack_version="1.2.0", ru=42, racks=(("acme", "frame-4p"),)):
    dist = tmp / "dist"
    (dist / "components").mkdir(parents=True, exist_ok=True)
    (dist / "racks").mkdir(exist_ok=True)
    (dist / "devices.json").write_text(json.dumps({"contract": 2, "devices": [
        {"name": "box-1", "ns": "acme", "manufacturer": "Acme", "model": "Box 1",
         "version": "1.0.0", "portfolio": {}}]}))
    (dist / "components.json").write_text('{"components": []}')
    (dist / "box-1.source.json").write_text('{"name": "box-1"}')
    (dist / "box-1.a.front.svg").write_text("<svg/>")
    (dist / "box-1.a.front.elements.json").write_text('{"elements": []}')
    (dist / "box-1.configs.json").write_text(json.dumps({"device": "box-1", "configs": [
        {"name": "a", "files": {"front": "box-1.a.front.svg"}}]}))
    rows = []
    for vendor, name in racks:
        doc = {**RACK, "name": name, "version": rack_version, "ru": ru}
        (dist / "racks" / f"{vendor}--{name}.rack.json").write_text(json.dumps(doc))
        major = int(rack_version.split(".")[0])
        rows.append({"ref": f"{vendor}/{name}@{major}", "vendor": vendor, "name": name,
                     "version": rack_version, "major": major, "manufacturer": "Acme",
                     "model": doc["model"], "form": doc["form"], "ru": ru,
                     "file": f"racks/{vendor}--{name}.rack.json"})
    (dist / "racks" / "rack-product.schema.json").write_text(SCHEMA.read_text())
    (dist / "rack-products.json").write_text(json.dumps({"format": 1, "contract": 2, "racks": rows}))
    for f in P.LICENCE_FILES:
        (tmp / f).write_text(f)
    return dist


def _build(tmp, dist, published=None, **kw):
    return P.build(dist, tmp / "out", tmp, published, **kw)


# ---- the package -----------------------------------------------------------------

def test_a_rack_ships_as_a_package_of_its_own(tmp_path):
    state, _ = _build(tmp_path, _dist(tmp_path))
    assert set(state) == {"@portrayal/acme-box-1", "@portrayal/racks-acme-frame-4p",
                          "@portrayal/index"}
    d = tmp_path / "out" / "racks-acme-frame-4p"
    assert sorted(p.name for p in d.iterdir()) == [
        "LICENSE", "NOTICE", "README.md", "acme--frame-4p.rack.json",
        "package.json", "rack-product.schema.json"]
    pkg = json.loads((d / "package.json").read_text())
    assert pkg["name"] == "@portrayal/racks-acme-frame-4p" and pkg["version"] == "1.2.0"
    assert pkg["license"] == "Apache-2.0" and pkg["publishConfig"] == {"access": "public"}
    assert pkg["portrayal"]["rack"] == "acme/frame-4p"
    assert pkg["portrayal"]["rack-version"] == "1.2.0"
    assert "device-version" not in pkg["portrayal"]


def test_the_index_says_where_each_rack_is(tmp_path):
    _build(tmp_path, _dist(tmp_path))
    idx = tmp_path / "out" / "index"
    assert (idx / "rack-products.json").exists()
    assert not list(idx.glob("acme--*")), "a rack's own file went into the index"
    pk = json.loads((idx / "packages.json").read_text())
    assert pk["racks"] == {"acme/frame-4p": {
        "package": "@portrayal/racks-acme-frame-4p", "version": "1.2.0", "vendor": "acme",
        "manufacturer": "Acme", "model": "FRAME-4P", "form": "4-post-frame", "ru": 42,
        "rack-version": "1.2.0", "major": 1}}
    assert "frame-4p" not in pk["devices"] and "frame-4p" not in json.dumps(pk["tree"])


def test_a_build_with_no_rack_products_writes_no_rack_package(tmp_path):
    dist = _dist(tmp_path)
    (dist / "rack-products.json").unlink()
    state, _ = _build(tmp_path, dist)
    assert set(state) == {"@portrayal/acme-box-1", "@portrayal/index"}
    pk = json.loads((tmp_path / "out" / "index" / "packages.json").read_text())
    assert pk["racks"] == {}


def test_every_rack_package_carries_the_licence_and_the_notice(tmp_path):
    _build(tmp_path, _dist(tmp_path))
    d = tmp_path / "out" / "racks-acme-frame-4p"
    assert (d / "LICENSE").exists() and (d / "NOTICE").exists()


def test_the_registry_is_asked_about_every_rack_package(tmp_path):
    names = P.package_names(_dist(tmp_path, racks=(("acme", "frame-4p"), ("acme", "frame-2p"))))
    assert names[-3:] == ["@portrayal/racks-acme-frame-2p", "@portrayal/racks-acme-frame-4p",
                          "@portrayal/index"]


# ---- versions ----------------------------------------------------------------------

def test_a_second_run_publishes_nothing_that_did_not_change(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    again, _ = _build(tmp_path, _dist(tmp_path), first)
    assert not [n for n, s in again.items() if s["changed"]]


def test_a_rack_moving_moves_its_package_as_far_and_the_index(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    again, _ = _build(tmp_path, _dist(tmp_path, rack_version="1.3.0", ru=44), first)
    assert again["@portrayal/racks-acme-frame-4p"]["version"] == "1.3.0"
    assert sorted(n for n, s in again.items() if s["changed"]) == \
        ["@portrayal/index", "@portrayal/racks-acme-frame-4p"]
    major, _ = _build(tmp_path, _dist(tmp_path, rack_version="2.0.0", ru=44), first)
    assert major["@portrayal/racks-acme-frame-4p"]["version"] == "2.0.0"


def test_a_rewritten_rack_under_the_same_version_is_a_fix(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    again, _ = _build(tmp_path, _dist(tmp_path, ru=44), first)
    assert again["@portrayal/racks-acme-frame-4p"]["version"] == "1.2.1"


def test_the_registry_state_keeps_a_racks_version(tmp_path):
    class Npm:
        def __call__(self, cmd, **_):
            class R:
                returncode, stderr = 0, ""
                stdout = json.dumps({"version": "1.2.3", "portrayal": {
                    "digest": "d1", "contract": 2, "rack-version": "1.2.0"}})
            return R()
    got = P.registry_state(["@portrayal/racks-acme-frame-4p"], run=Npm())
    assert got["@portrayal/racks-acme-frame-4p"]["rack-version"] == "1.2.0"
    assert "device-version" not in got["@portrayal/racks-acme-frame-4p"]


def test_a_registry_run_versions_a_rack_against_what_npm_holds(tmp_path):
    held = {"@portrayal/racks-acme-frame-4p": {
        "version": "1.2.3", "digest": "old", "contract": 2, "rack-version": "1.2.0"}}
    state, _ = _build(tmp_path, _dist(tmp_path), held)
    assert state["@portrayal/racks-acme-frame-4p"]["version"] == "1.2.4"
    assert not state["@portrayal/racks-acme-frame-4p"]["first"]


def test_a_new_rack_package_is_a_first_publish_and_is_named_so(tmp_path):
    """npm lets an account create about 25 new packages; every rack is one."""
    state, _ = _build(tmp_path, _dist(tmp_path))
    assert "@portrayal/racks-acme-frame-4p" in P.first_publishes(state)


# ---- names ---------------------------------------------------------------------------

def test_a_device_cannot_take_a_racks_package_name(tmp_path):
    dist = _dist(tmp_path)
    d = json.loads((dist / "devices.json").read_text())
    d["devices"][0].update(ns="racks", name="acme-frame-4p")
    (dist / "devices.json").write_text(json.dumps(d))
    for f in list(dist.glob("box-1.*")):
        f.rename(dist / f.name.replace("box-1", "acme-frame-4p", 1))
    cfg = dist / "acme-frame-4p.configs.json"
    cfg.write_text(cfg.read_text().replace("box-1", "acme-frame-4p"))
    with pytest.raises(SystemExit, match="two packages are named @portrayal/racks-acme-frame-4p"):
        _build(tmp_path, dist)


def test_a_rack_the_catalogue_names_but_dist_lacks_fails_the_run(tmp_path):
    dist = _dist(tmp_path)
    (dist / "racks" / "acme--frame-4p.rack.json").unlink()
    with pytest.raises(SystemExit, match="acme--frame-4p.rack.json"):
        _build(tmp_path, dist)


# ---- the packed tarball ------------------------------------------------------------------

def _pack(pkg_dir, dest):
    if shutil.which("npm") is None:
        pytest.skip("npm not installed")
    dest.mkdir(exist_ok=True)
    r = subprocess.run(["npm", "pack", "--silent", "--pack-destination", str(dest)],
                       cwd=str(pkg_dir), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return dest / r.stdout.strip().splitlines()[-1]


def _read(tarball, name):
    with tarfile.open(tarball) as t:
        return t.extractfile(f"package/{name}").read()


def test_a_rack_is_readable_from_the_packed_tarball(tmp_path):
    _build(tmp_path, _dist(tmp_path))
    ball = _pack(tmp_path / "out" / "racks-acme-frame-4p", tmp_path / "packed")
    with tarfile.open(ball) as t:
        names = sorted(n.removeprefix("package/") for n in t.getnames())
    assert "acme--frame-4p.rack.json" in names and "rack-product.schema.json" in names
    doc = json.loads(_read(ball, "acme--frame-4p.rack.json"))
    assert doc["kind"] == "rack" and doc["name"] == "frame-4p"
    schema = json.loads(_read(ball, "rack-product.schema.json"))
    assert list(Draft202012Validator(schema).iter_errors(doc)) == []


# ---- the real build ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def real(tmp_path_factory):
    if not (DIST / "rack-products.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    out = tmp_path_factory.mktemp("real")
    state, sizes = P.build(DIST, out / "out", ROOT)
    return out, state, sizes


def test_every_library_rack_has_its_package(real):
    _, state, sizes = real
    racks = json.loads((DIST / "rack-products.json").read_text())["racks"]
    assert {r["ref"] for r in racks} >= {"apc/ar203a@1", "apc/ar201@1"}
    for r in racks:
        pkg = P.package_name("racks", f"{r['vendor']}-{r['name']}")
        assert pkg in state, pkg
        assert sizes[pkg] < P.LIMIT_MB * 1e6


def test_the_real_ar203a_is_readable_from_its_tarball(real):
    out, _, _ = real
    ball = _pack(out / "out" / "racks-apc-ar203a", out / "packed")
    doc = json.loads(_read(ball, "apc--ar203a.rack.json"))
    schema = json.loads(_read(ball, "rack-product.schema.json"))
    assert list(Draft202012Validator(schema).iter_errors(doc)) == []
    assert (doc["form"], doc["ru"]) == ("4-post-frame", 44)
