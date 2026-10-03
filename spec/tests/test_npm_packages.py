"""The npm packages a build ships as, and how each is versioned (#528).

One package per device, one for the component skins, one index. A package
carries its own version, bumped from what it last published: devicelock does
not hash rendered output, so a re-render moves a device's bytes without moving
its version, and npm will not take new bytes under a version it already holds.

Most of this runs on a small dist built here, so each rule can be moved one at
a time; the last test reads the real build for the one thing only it can show -
that every device fits.
"""
import json
import pathlib

import pytest

from portrayal import npm_packages as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


# ---- versions ----------------------------------------------------------------

@pytest.mark.parametrize("version,change,want", [
    ("0.5.12", "fix", "0.5.13"),
    ("0.5.12", "additive", "0.5.13"),     # below 1.0 a caret pins the minor
    ("0.5.12", "breaking", "0.6.0"),
    ("3.0.0", "fix", "3.0.1"),
    ("3.0.0", "additive", "3.1.0"),
    ("3.2.1", "breaking", "4.0.0"),
])
def test_bump(version, change, want):
    assert P.bump(version, change) == want


def test_an_unpublished_package_starts_at_its_devices_version():
    assert P.next_version(None, "d1", 2, "24.0.0") == ("24.0.0", True)
    assert P.next_version(None, "d1", 2) == (P.FIRST, True)


def test_an_unchanged_package_keeps_its_version_and_is_not_published():
    prev = {"version": "24.0.3", "digest": "d1", "contract": 2, "device-version": "24.0.0"}
    assert P.next_version(prev, "d1", 2, "24.0.0") == ("24.0.3", False)


def test_a_rerender_alone_is_a_fix():
    """The case that rules out using the device's version: same device, new bytes."""
    prev = {"version": "24.0.0", "digest": "d1", "contract": 2, "device-version": "24.0.0"}
    assert P.next_version(prev, "d2", 2, "24.0.0") == ("24.0.1", True)


def test_the_device_moving_moves_the_package_as_far():
    prev = {"version": "24.0.1", "digest": "d1", "contract": 2, "device-version": "24.0.0"}
    assert P.next_version(prev, "d2", 2, "24.1.0") == ("24.1.0", True)
    assert P.next_version(prev, "d2", 2, "25.0.0") == ("25.0.0", True)


def test_a_contract_change_is_breaking():
    prev = {"version": "0.1.4", "digest": "d1", "contract": 1}
    assert P.next_version(prev, "d2", 2) == ("0.2.0", True)


# ---- a small build -----------------------------------------------------------

def _dist(tmp, device_version="1.2.0", contract=2, rear=b"<svg>rear</svg>"):
    dist = tmp / "dist"
    (dist / "components").mkdir(parents=True, exist_ok=True)
    (dist / "devices.json").write_text(json.dumps({"contract": contract, "devices": [
        {"name": "box-1", "ns": "acme", "manufacturer": "Acme", "model": "Box 1",
         "version": device_version, "portfolio": {"family": "Boxes"}},
        {"name": "box-2", "ns": "acme", "manufacturer": "Acme", "model": "Box 2",
         "version": "0.1.0", "portfolio": {}},
    ]}))
    (dist / "components.json").write_text('{"components": []}')
    (dist / "components" / "acme--knob--v1--default.svg").write_text("<svg>knob</svg>")
    for name in ("box-1", "box-2"):
        (dist / f"{name}.source.json").write_text('{"name": "%s"}' % name)
        (dist / f"{name}.a.front.svg").write_text("<svg>front</svg>")
        (dist / f"{name}.a.rear.svg").write_bytes(rear)
        (dist / f"{name}.front.svg").write_text("<svg>front</svg>")   # the default's copy
        # config b shares a's front and draws its own rear
        (dist / f"{name}.b.rear.svg").write_text("<svg>rear b</svg>")
        # every face has its elements file beside it (#727), the copy included
        for face in ("a.front", "a.rear", "front", "b.rear"):
            (dist / f"{name}.{face}.elements.json").write_text('{"elements": []}')
        (dist / f"{name}.configs.json").write_text(json.dumps({"device": name, "configs": [
            {"name": "a", "files": {"front": f"{name}.a.front.svg", "rear": f"{name}.a.rear.svg"}},
            {"name": "b", "files": {"front": f"{name}.a.front.svg", "rear": f"{name}.b.rear.svg"}},
        ]}))
    for f in P.LICENCE_FILES:
        (tmp / f).write_text(f)
    return dist


def _build(tmp, dist, published=None, **kw):
    return P.build(dist, tmp / "out", tmp, published, **kw)


def test_one_package_per_device_holding_what_its_configurations_draw(tmp_path):
    state, _ = _build(tmp_path, _dist(tmp_path))
    assert set(state) == {"@portrayal/acme-box-1", "@portrayal/acme-box-2",
                          "@portrayal/components", "@portrayal/index"}
    got = sorted(p.name for p in (tmp_path / "out" / "acme-box-1").iterdir())
    assert got == ["LICENSE", "NOTICE", "README.md",
                   "box-1.a.front.elements.json", "box-1.a.front.svg",
                   "box-1.a.rear.elements.json", "box-1.a.rear.svg",
                   "box-1.b.rear.elements.json", "box-1.b.rear.svg",
                   "box-1.configs.json", "box-1.source.json",
                   "package.json"], "the default's copy is left out; everything drawn is in"
    pkg = json.loads((tmp_path / "out" / "acme-box-1" / "package.json").read_text())
    assert pkg["name"] == "@portrayal/acme-box-1" and pkg["version"] == "1.2.0"
    assert pkg["license"] == "Apache-2.0" and pkg["publishConfig"] == {"access": "public"}
    assert pkg["portrayal"]["device-version"] == "1.2.0"


def test_the_index_says_where_each_device_is_and_groups_them(tmp_path):
    _build(tmp_path, _dist(tmp_path))
    idx = tmp_path / "out" / "index"
    assert (idx / "devices.json").exists() and (idx / "components.json").exists()
    assert not list(idx.glob("box-*")), "a device's own files went into the index"
    pk = json.loads((idx / "packages.json").read_text())
    assert pk["devices"]["box-1"]["package"] == "@portrayal/acme-box-1"
    assert pk["devices"]["box-1"]["version"] == "1.2.0"
    assert pk["tree"] == {"acme": {"": ["box-2"], "Boxes": ["box-1"]}}
    assert pk["components"]["package"] == "@portrayal/components"


def test_every_package_carries_the_licence_and_the_notice(tmp_path):
    _build(tmp_path, _dist(tmp_path))
    for d in (tmp_path / "out").iterdir():
        if d.is_dir():
            assert (d / "LICENSE").exists() and (d / "NOTICE").exists(), d.name


def test_a_second_run_publishes_nothing_that_did_not_change(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    again, _ = _build(tmp_path, _dist(tmp_path), first)
    assert not [n for n, s in again.items() if s["changed"]]
    assert {n: s["version"] for n, s in again.items()} == \
           {n: s["version"] for n, s in first.items()}


def test_one_redrawn_face_bumps_its_device_and_the_index_only(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    again, _ = _build(tmp_path, _dist(tmp_path, rear=b"<svg>rear, redrawn</svg>"), first)
    changed = sorted(n for n, s in again.items() if s["changed"])
    # both devices share the fixture's rear bytes, so both redraw
    assert changed == ["@portrayal/acme-box-1", "@portrayal/acme-box-2", "@portrayal/index"]
    assert again["@portrayal/acme-box-1"]["version"] == "1.2.1"
    assert again["@portrayal/components"]["version"] == first["@portrayal/components"]["version"]


def test_a_package_over_the_limit_fails_the_run(tmp_path):
    with pytest.raises(SystemExit, match="over the"):
        _build(tmp_path, _dist(tmp_path), limit_mb=0.000001)


# ---- the real build ----------------------------------------------------------

def test_every_device_in_the_library_fits_in_a_package(tmp_path):
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    state, sizes = P.build(DIST, tmp_path / "out", ROOT)
    devices = json.loads((DIST / "devices.json").read_text())["devices"]
    assert len(state) == len(devices) + 2
    assert max(sizes.values()) < P.LIMIT_MB * 1e6


# ---- the registry, with npm stood in for -------------------------------------

class _Npm:
    """Answers `npm view` from a dict and records `npm publish`."""
    def __init__(self, held):
        self.held, self.published = held, []

    def __call__(self, cmd, cwd=None, **_):
        class R:
            returncode, stdout, stderr = 0, "", ""
        r = R()
        if cmd[1] == "view":
            name = cmd[2].rsplit("@", 1)[0]
            if name in self.held:
                r.stdout = json.dumps(self.held[name])
            else:
                r.returncode, r.stdout = 1, '{"error": {"code": "E404"}}'
        else:
            self.published.append(json.loads((pathlib.Path(cwd) / "package.json").read_text())["name"])
        return r


def test_the_registry_state_is_read_off_each_packages_published_json(tmp_path):
    npm = _Npm({"@portrayal/acme-box-1": {"version": "1.2.3", "portrayal": {
        "digest": "d1", "contract": 2, "device-version": "1.2.0"}}})
    got = P.registry_state(["@portrayal/acme-box-1", "@portrayal/acme-box-2"], run=npm)
    assert got == {"@portrayal/acme-box-1": {"version": "1.2.3", "digest": "d1",
                                             "contract": 2, "device-version": "1.2.0"}}


def test_a_registry_error_that_is_not_a_miss_stops_the_run():
    def broken(cmd, **_):
        class R:
            returncode, stdout, stderr = 1, "", "npm ERR! code ETIMEDOUT"
        return R()
    with pytest.raises(SystemExit, match="ETIMEDOUT"):
        P.registry_state(["@portrayal/acme-box-1"], run=broken)


def test_publish_sends_only_what_changed_and_the_index_last(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    npm = _Npm({})
    order = P.publish(tmp_path / "out", first, run=npm)
    assert order == npm.published
    assert order[-1] == "@portrayal/index" and len(order) == 4
    again, _ = _build(tmp_path, _dist(tmp_path, device_version="1.3.0"), first)
    npm = _Npm({})
    assert P.publish(tmp_path / "out", again, run=npm) == \
        ["@portrayal/acme-box-1", "@portrayal/index"]


# ---- what the merge-queue review of #688 found ----------------------------------

def test_a_run_writes_no_state_that_could_claim_an_unpublished_version(tmp_path):
    """A dry run, or a publish that failed partway, must not leave behind a
    record the next run would read as "already out". npm is the record."""
    _build(tmp_path, _dist(tmp_path))
    assert not list((tmp_path / "out").glob("*.json")), \
        "the packager wrote a state file beside the packages"


def test_publish_refuses_to_run_without_the_registrys_state(tmp_path, capsys):
    """With no baseline every package is priced as new: a dry run passes and
    the second real release collides with the first on its first name."""
    dist = _dist(tmp_path)
    with pytest.raises(SystemExit):
        P.main(["--dist", str(dist), "--out", str(tmp_path / "out"),
                "--root", str(tmp_path), "--publish", "--dry-run"])
    assert "--from-registry" in capsys.readouterr().err


def test_a_changed_readme_is_a_changed_package(tmp_path, monkeypatch):
    first, _ = _build(tmp_path, _dist(tmp_path))
    monkeypatch.setattr(P, "_readme", lambda title, body: f"# {title}\n\nreworded\n")
    again, _ = _build(tmp_path, _dist(tmp_path), first)
    assert again["@portrayal/acme-box-1"]["changed"]


# ---- a first publish is not like the others (#526) -------------------------------

def test_a_package_npm_has_never_held_is_marked_as_a_first_publish(tmp_path):
    """npm's trusted publishing is set up per package and only on a package
    that exists, so a first publish needs a token and every later one does
    not. The run has to say which are which."""
    first, _ = _build(tmp_path, _dist(tmp_path))
    assert all(s["first"] for s in first.values())
    held = {k: v for k, v in first.items() if k != "@portrayal/acme-box-2"}
    again, _ = _build(tmp_path, _dist(tmp_path), held)
    assert P.first_publishes(again) == ["@portrayal/acme-box-2"]


def test_a_registry_run_names_its_first_publishes(tmp_path, capsys, monkeypatch):
    dist = _dist(tmp_path)
    first, _ = _build(tmp_path, dist)
    held = {k: v for k, v in first.items() if k != "@portrayal/acme-box-2"}
    monkeypatch.setattr(P, "registry_state", lambda names: held)
    P.main(["--dist", str(dist), "--out", str(tmp_path / "out"),
            "--root", str(tmp_path), "--from-registry"])
    out = capsys.readouterr().out
    assert "first publish: @portrayal/acme-box-2" in out
    assert "first publish: @portrayal/acme-box-1" not in out


def test_a_run_without_the_registry_claims_no_first_publish(tmp_path, capsys):
    """publish.sh runs with no baseline, where every package looks new. Saying
    so there would be 180 lines of noise on every build."""
    dist = _dist(tmp_path)
    P.main(["--dist", str(dist), "--out", str(tmp_path / "out"), "--root", str(tmp_path)])
    assert "first publish" not in capsys.readouterr().out


def test_a_first_publish_is_named_on_the_line_that_sent_it(tmp_path, capsys):
    """A run that fails partway has sent some new packages. The next run finds
    them on npm and calls none of them first, so the line that published one
    is the only place that says it still needs trusting."""
    first, _ = _build(tmp_path, _dist(tmp_path))
    held = {k: v for k, v in first.items() if k != "@portrayal/acme-box-2"}
    again, _ = _build(tmp_path, _dist(tmp_path, device_version="1.3.0"), held)
    P.publish(tmp_path / "out", again, run=_Npm({}))
    out = capsys.readouterr().out.splitlines()
    assert "published @portrayal/acme-box-2@0.1.0 (first publish)" in out
    assert "published @portrayal/acme-box-1@1.3.0" in out


# ---- the registry limits how fast packages arrive (#526) --------------------------

class _Limited(_Npm):
    """An npm that answers the first `refuse` publishes with E429."""
    def __init__(self, refuse):
        super().__init__({})
        self.refuse = refuse

    def __call__(self, cmd, cwd=None, **kw):
        if cmd[1] == "publish" and self.refuse:
            self.refuse -= 1

            class R:
                returncode, stdout = 1, ""
                stderr = "npm error code E429\nnpm error 429 Too Many Requests - PUT ..."
            return R()
        return super().__call__(cmd, cwd=cwd, **kw)


def _held(state):
    """`state` as a later run sees it: npm holds every package, each has moved."""
    return {n: {**s, "first": False, "changed": True} for n, s in state.items()}


def test_a_rate_limited_update_waits_and_is_tried_again(tmp_path):
    """E429 on a package npm already holds is a rate, and a rate passes."""
    first, _ = _build(tmp_path, _dist(tmp_path))
    npm, slept = _Limited(2), []
    order = P.publish(tmp_path / "out", _held(first), run=npm, sleep=slept.append)
    assert npm.published == order and len(order) == 4
    assert slept == list(P.RATE_LIMIT_WAITS[:2]), "two refusals, two waits, each longer"


def test_an_update_npm_never_relents_on_stops_the_run(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))
    npm, slept = _Limited(10 ** 6), []
    with pytest.raises(SystemExit, match="E429"):
        P.publish(tmp_path / "out", _held(first), run=npm, sleep=slept.append)
    assert slept == list(P.RATE_LIMIT_WAITS) and not npm.published


def test_a_refused_first_publish_is_a_quota_and_is_not_waited_on(tmp_path):
    """npm lets an account create about 25 packages, then none for hours. The
    second release waited 33 minutes on one package and was refused six times;
    no wait inside a run outlasts it, so the run says so and stops."""
    first, _ = _build(tmp_path, _dist(tmp_path))
    npm, slept = _Limited(10 ** 6), []
    with pytest.raises(SystemExit, match=r"first publish.*4 packages are left.*tomorrow"):
        P.publish(tmp_path / "out", first, run=npm, sleep=slept.append)
    assert not slept and not npm.published


def test_any_other_publish_failure_is_not_waited_on(tmp_path):
    first, _ = _build(tmp_path, _dist(tmp_path))

    def forbidden(cmd, **_):
        class R:
            returncode, stdout, stderr = 1, "", "npm error code E403"
        return R()
    slept = []
    with pytest.raises(SystemExit, match="E403"):
        P.publish(tmp_path / "out", first, run=forbidden, sleep=slept.append)
    assert not slept
