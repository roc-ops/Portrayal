"""Device packs: a built dist in a few files per device, made on request.

`spec/tools/dev/dist_packs.py` reads a built dist and writes, into a folder of
its own, one pack for each device's default configuration, a second pack for
every other face the device's configurations name, and the component skins in
chunks of a namespace. The published dist and the npm packages do not change:
the packs are a form a consumer makes for itself.

The kit reads them through `fetchDist` and `packedDist` (kit/dist.js), checked
by spec/tests/js/dist-packs.mjs against the packs this tool writes from a small
library made here: two devices, one with three configurations, and two
namespaces of skins.
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

from portrayal_dev import dist_packs as P

ROOT = pathlib.Path(__file__).resolve().parents[2]
JS = ROOT / "spec/tests/js"
SCRIPT = JS / "dist-packs.mjs"

# non-ASCII, a carriage return and a final newline: a pack must give them back
# as the file holds them
TEXT = "<svg xmlns=\"http://www.w3.org/2000/svg\">\r\n<!-- µ é 日本 -->\r\n<g id=\"{}\"/>\r\n</svg>\n"
SKIN_SIZE = 400
CHUNK = 1000                     # two skins to a chunk, once escaped


def _svg(tag, size=None):
    t = TEXT.format(tag)
    return t if size is None else t.replace("<g", "<!--" + "x" * (size - len(t.encode()) - 8) + "--><g", 1)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _configs(name, default, configs):
    return json.dumps({"device": name, "default": default, "views": ["front", "rear", "side"],
                       "configs": [{"name": n, "files": f} for n, f in configs]}, indent=1)


@pytest.fixture(scope="module")
def dist(tmp_path_factory):
    d = tmp_path_factory.mktemp("lib") / "dist"
    _write(d / "devices.json", json.dumps({"contract": 2, "devices": [
        {"name": "acme-one", "ns": "acme"}, {"name": "acme-two", "ns": "acme"}]}))
    # one configuration, two views
    _write(d / "acme-one.configs.json", _configs("acme-one", "default", [
        ("default", {"front": "acme-one.front.svg", "rear": "acme-one.rear.svg"})]))
    _write(d / "acme-one.source.json", "{}")
    for f in ("front", "rear"):
        _write(d / f"acme-one.{f}.svg", _svg(f"one-{f}"))
        _write(d / f"acme-one.{f}.elements.json", "{}")
    # a drawing no configuration names: left out of every pack
    _write(d / "acme-one.default.side.svg", _svg("one-stray"))
    # three configurations; "wide" borrows the default's rear
    _write(d / "acme-two.configs.json", _configs("acme-two", "default", [
        ("default", {"front": "acme-two.front.svg", "rear": "acme-two.rear.svg", "side": "acme-two.side.svg"}),
        ("wide", {"front": "acme-two.wide.front.svg", "rear": "acme-two.rear.svg"}),
        ("tall", {"front": "acme-two.tall.front.svg"})]))
    _write(d / "acme-two.source.json", "{}")
    for f in ("front", "rear", "side", "wide.front", "tall.front"):
        _write(d / f"acme-two.{f}.svg", _svg(f"two-{f}"))
    _write(d / "components.json", json.dumps({"components": []}))
    _write(d / "racks/acme--frame.rack.json", "{}")
    for n in ("acme--knob--v1--alt", "acme--knob--v1--default", "acme--lamp--v1--default",
              "acme--zip--v1--default", "acme--zz--v1--default", "zeta--one--v1--default"):
        _write(d / "components" / f"{n}.svg", _svg(n, SKIN_SIZE))
    return d


def _tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pathlib.Path(root).rglob("*")) if p.is_file()}


def _read(path):
    return json.loads(pathlib.Path(path).read_bytes().decode("utf-8"))


@pytest.fixture(scope="module")
def packs(dist, tmp_path_factory):
    out = tmp_path_factory.mktemp("packs") / "packs"
    P.build_packs(dist, out, chunk_bytes=CHUNK)
    return out


def _face_files(dist, name):
    idx = _read(dist / f"{name}.configs.json")
    by = {c["name"]: set(c["files"].values()) for c in idx["configs"]}
    every = set().union(*by.values())
    return by[idx["default"]], every - by[idx["default"]]


# ---- the device packs ------------------------------------------------------

@pytest.mark.parametrize("name", ["acme-one", "acme-two"])
def test_every_named_face_is_in_exactly_one_pack_and_byte_for_byte(dist, packs, name):
    default, other = _face_files(dist, name)
    first = _read(packs / "devices" / f"{name}.json")["files"]
    second = _read(packs / "devices" / f"{name}.more.json")["files"] if other else {}
    assert set(first) == default and set(second) == other
    assert not set(first) & set(second)
    for f, text in {**first, **second}.items():
        assert text.encode("utf-8") == (dist / f).read_bytes(), f


def test_more_says_whether_a_second_pack_exists(dist, packs):
    assert _read(packs / "devices/acme-one.json")["more"] is False
    assert not (packs / "devices/acme-one.more.json").exists()
    assert _read(packs / "devices/acme-two.json")["more"] is True
    assert set(_read(packs / "devices/acme-two.more.json")) == {"files"}
    assert set(_read(packs / "devices/acme-two.json")) == {"more", "files"}


def test_a_drawing_no_configuration_names_is_in_no_pack(packs):
    text = "".join(p.read_text(encoding="utf-8") for p in packs.rglob("*.json"))
    assert "one-stray" not in text and "default.side" not in text


def test_the_packs_hold_text_only_and_nothing_library_wide(packs):
    names = sorted(str(p.relative_to(packs)) for p in packs.rglob("*") if p.is_file())
    assert names == ["components/acme.1.json", "components/acme.2.json", "components/acme.3.json",
                     "components/index.json", "components/zeta.1.json",
                     "devices/acme-one.json", "devices/acme-two.json", "devices/acme-two.more.json"]


# ---- the skin chunks -------------------------------------------------------

def test_skins_are_split_greedily_in_byte_order_of_the_file_name(dist, packs):
    names = sorted(p.name for p in (dist / "components").glob("acme--*"))
    chunks = [list(_read(packs / "components" / f"acme.{k}.json")["files"]) for k in (1, 2, 3)]
    assert [len(c) for c in chunks] == [2, 2, 1]
    assert [n for c in chunks for n in c] == [f"components/{n}" for n in names]
    for k in (1, 2, 3):
        path = packs / "components" / f"acme.{k}.json"
        # the FILE is at most the limit, with its JSON escapes
        assert path.stat().st_size <= CHUNK
        for f, text in _read(path)["files"].items():
            assert text.encode("utf-8") == (dist / f).read_bytes()
    # greedy: the next skin would not have fitted in the chunk before it
    for k, nxt in ((1, names[2]), (2, names[4])):
        size = (packs / "components" / f"acme.{k}.json").stat().st_size
        text = (dist / "components" / nxt).read_bytes().decode("utf-8")
        assert size + 1 + P._entry_size(f"components/{nxt}", text) > CHUNK


def test_the_index_names_the_first_skin_of_every_chunk_after_the_first(packs):
    idx = _read(packs / "components/index.json")
    assert idx == {"acme": ["acme--lamp--v1--default.svg", "acme--zz--v1--default.svg"], "zeta": []}


def test_every_skin_is_found_through_the_index(dist, packs):
    import bisect
    idx = _read(packs / "components/index.json")
    for p in sorted((dist / "components").glob("*.svg")):
        ns = p.name.split("--")[0]
        k = bisect.bisect_right(idx[ns], p.name) + 1
        files = _read(packs / "components" / f"{ns}.{k}.json")["files"]
        assert files[f"components/{p.name}"].encode("utf-8") == p.read_bytes()


def test_a_skin_larger_than_a_chunk_is_a_chunk_of_its_own(dist, tmp_path):
    out = tmp_path / "packs"
    P.build_packs(dist, out, chunk_bytes=100)
    assert sorted(p.name for p in (out / "components").glob("acme.*")) == [f"acme.{k}.json" for k in range(1, 6)]
    assert _read(out / "components/index.json")["acme"] == [
        "acme--knob--v1--default.svg", "acme--lamp--v1--default.svg",
        "acme--zip--v1--default.svg", "acme--zz--v1--default.svg"]


# ---- what the tool will not do ---------------------------------------------

def test_a_second_run_gives_identical_bytes(dist, tmp_path):
    P.build_packs(dist, tmp_path / "a", chunk_bytes=CHUNK)
    P.build_packs(dist, tmp_path / "b", chunk_bytes=CHUNK)
    assert _tree(tmp_path / "a") == _tree(tmp_path / "b") and _tree(tmp_path / "a")


def test_the_dist_is_not_touched(dist, tmp_path):
    before = _tree(dist)
    P.build_packs(dist, tmp_path / "out")
    assert _tree(dist) == before


@pytest.mark.parametrize("where", ["inside", "same", "above"])
def test_an_out_inside_the_dist_is_refused_and_nothing_is_written(dist, where, tmp_path):
    work = tmp_path / "w"
    shutil.copytree(dist, work / "dist")
    out = {"inside": work / "dist" / "packs", "same": work / "dist", "above": work}[where]
    before = _tree(work)
    with pytest.raises(SystemExit) as e:
        P.main(["--dist", str(work / "dist"), "--out", str(out)])
    assert e.value.code != 0
    assert _tree(work) == before


def test_an_out_that_already_holds_files_is_refused(dist, tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out/stale.json").write_text("{}")
    with pytest.raises(SystemExit):
        P.main(["--dist", str(dist), "--out", str(tmp_path / "out")])
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["stale.json"]


def test_a_face_the_configs_name_and_the_dist_lacks_stops_the_run(dist, tmp_path):
    work = tmp_path / "dist"
    shutil.copytree(dist, work)
    (work / "acme-two.wide.front.svg").unlink()
    with pytest.raises(SystemExit) as e:
        P.build_packs(work, tmp_path / "out")
    assert "acme-two.wide.front.svg" in str(e.value)


def test_the_command_line_writes_the_packs(dist, tmp_path):
    p = subprocess.run([sys.executable, str(ROOT / "spec/tools/dev/dist_packs.py"), "--dist", str(dist),
                        "--out", str(tmp_path / "o")], capture_output=True, text=True,
                       env={"PYTHONPATH": str(ROOT / "spec/tools"), "PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "o/devices/acme-two.more.json").is_file()


# ---- the kit reading them --------------------------------------------------

@pytest.fixture(scope="module")
def kit(dist, packs):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), str(dist), str(packs)], capture_output=True,
                       text=True, cwd=str(JS))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_packed_dist_returns_the_bytes_flat_dist_does(kit):
    e = kit["equal"]
    assert e["mismatches"] == []
    assert e["faces"] == 7 and e["skins"] == 6 and e["devices"] == 2, e
    assert e["hits"] == e["faces"] + e["skins"]


def test_dist_at_maps_each_path_to_its_url(kit):
    base = "https://page.test/dist/"
    m = kit["urls"]
    assert m["configs"] == base + "acme-two.configs.json"
    assert m["source"] == base + "acme-two.source.json"
    assert m["devices"] == base + "devices.json" and m["rack"] == base + "racks/acme--frame.rack.json"
    assert m["face"] == base + "packs/devices/acme-two.json#acme-two.wide.front.svg"
    assert m["skins"] == {
        "acme--knob--v1--alt.svg": base + "packs/components/acme.1.json#components/acme--knob--v1--alt.svg",
        "acme--knob--v1--default.svg": base + "packs/components/acme.1.json#components/acme--knob--v1--default.svg",
        "acme--lamp--v1--default.svg": base + "packs/components/acme.2.json#components/acme--lamp--v1--default.svg",
        "acme--zip--v1--default.svg": base + "packs/components/acme.2.json#components/acme--zip--v1--default.svg",
        "acme--zz--v1--default.svg": base + "packs/components/acme.3.json#components/acme--zz--v1--default.svg",
        "zeta--one--v1--default.svg": base + "packs/components/zeta.1.json#components/zeta--one--v1--default.svg"}
    assert m["inherited"] == base + "packs/components/constructor.1.json#components/constructor--x--v1--default.svg"


def test_a_plain_url_is_fetch_with_its_arguments(kit):
    assert kit["plain"] == {"url": "https://page.test/dist/acme-one.configs.json", "method": "HEAD",
                            "hashOnly": "https://page.test/x.json#frag"}


def test_a_loaded_configs_json_routes_a_face_to_the_pack_that_holds_it(kit):
    r = kit["loaded"]
    assert r["other"] == ["packs/devices/acme-two.more.json"]
    assert r["default"] == ["packs/devices/acme-two.json"]
    assert r["shared"] == []           # the default's rear is in the pack already fetched
    assert r["texts"] == [True, True, True]


def test_a_pending_configs_json_is_awaited(kit):
    r = kit["pending"]
    assert r["beforeRelease"] == ["acme-two.configs.json"], "the pack was asked for before configs.json answered"
    assert r["afterRelease"] == ["acme-two.configs.json", "packs/devices/acme-two.more.json"]
    assert r["hit"] is True


def test_a_failed_configs_json_falls_back_to_the_default_pack_then_the_second(kit):
    r = kit["failed"]
    assert r["other"] == ["packs/devices/acme-two.json", "packs/devices/acme-two.more.json"] and r["otherHit"]
    assert r["default"] == ["packs/devices/acme-two.json"] and r["defaultHit"]
    assert r["pendingThenFailed"] == ["acme-two.configs.json", "packs/devices/acme-two.json",
                                       "packs/devices/acme-two.more.json"]
    assert r["pendingThenFailedHit"]


def test_a_configs_json_without_files_falls_back(kit):
    r = kit["noFiles"]
    assert r["other"] == ["packs/devices/acme-two.json", "packs/devices/acme-two.more.json"] and r["otherHit"]
    # "more": false, so the second pack is not asked for
    assert r["noMore"] == ["packs/devices/acme-one.json"] and r["noMoreStatus"] == 404


def test_a_face_no_configuration_names_is_a_miss_with_no_request(kit):
    r = kit["unnamed"]
    assert r["requests"] == [] and r["statuses"] == [404, 404]


def test_every_miss_is_a_fresh_readable_404(kit):
    r = kit["misses"]
    assert r["statuses"] == [404] * 6
    assert r["distinct"] is True and r["readable"] is True and r["oneRequest"] is True


def test_a_packs_404_is_remembered_for_the_page(kit):
    r = kit["ghost"]
    assert r["statuses"] == [404, 404, 404] and r["requests"] == ["packs/devices/acme-ghost.json"]


def test_a_network_failure_or_a_5xx_is_retried_once_and_not_remembered(kit):
    r = kit["retry"]
    assert r["netOnce"] == {"requests": 2, "hit": True, "laterRequests": 0}
    assert r["fiveOnce"] == {"requests": 2, "hit": True, "laterRequests": 0}
    assert r["netTwice"] == {"first": "rejected", "firstRequests": 2, "second": 200, "secondRequests": 1}
    assert r["fiveTwice"] == {"first": 503, "firstRequests": 2, "second": 200, "secondRequests": 1}


def test_a_hit_is_a_fresh_response_typed_by_its_file_name(kit):
    r = kit["hit"]
    assert r["distinct"] is True and r["same"] is True and r["type"] == "image/svg+xml"


def test_clear_dist_cache_clears_the_packs(kit):
    assert kit["cleared"] == [1, 1, 2]


def test_packed_dist_resolves_only_after_its_index_has_loaded(kit):
    r = kit["ready"]
    assert r["resolvedEarly"] is False and r["resolvedAfter"] is True and r["indexRead"] is True
    assert "HTTP 404" in r["noIndex"]


def test_svg_source_refetches_after_a_rejection_and_keeps_an_empty_memo_for_a_404(kit):
    r = kit["svgSource"]
    assert r["firstRejected"] is True and r["second"].startswith("<svg") and r["requests"] == 2
    assert r["missing"] == ["", ""] and r["missingRequests"] == 1
