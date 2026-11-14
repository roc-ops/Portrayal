"""The parts of the open state that talk to three.js, run against the real three.js.

`kit/share.js` hands three's exporters a scene, and `kit/viewer3d.js` hands `planWallFace` the normal of a
raycast hit, which is a `THREE.Vector3`: a plain array or object in a unit test is not the viewer's call. So
these tests import the real library. three.js is an optional peer dependency (kit/NOTICE), not part of this
repository: point `PORTRAYAL_THREE_DIR` at a folder holding `three.module.js` and `addons/` (r161) to run
them; without it they skip, and what they hold is taken in the real viewer instead (the pictures and the
exports of the pull request).

What is held: the USDZ of a mesh with a list of materials (a box's six faces, a plan-outline body, an open
half with its invisible slot) is a zip with the geometry in it, and as many vertices as the groups use; a
mesh with one material is exported as it was; the GLB path does not take the split; and a ray that hits an
open half's rim cap answers the side it is on, from a real `Vector3`, with no face path.
"""
import base64
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import zipfile

import pytest

from test_plan_body_js import THREE
from test_section_split_js import with_seam

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
THREE_DIR = os.environ.get("PORTRAYAL_THREE_DIR")

needs_three = pytest.mark.skipif(
    not (THREE_DIR and (pathlib.Path(THREE_DIR) / "three.module.js").is_file() and shutil.which("node")),
    reason="three.js is not installed here (an optional peer dependency)")

SCRIPT = """
import * as THREE from 'three';
import { toUSDZ } from './kit/share.js';
import { sectionArrays, splitSection, planWallFace, SEAM_INDEX, PLAN_WALL_INDEX } from './kit/section.js';
const box = JSON.parse(process.argv[2]);
const geometry = a => {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(a.positions, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(a.normals, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(a.uvs, 2));
  g.setIndex(a.indices);
  for (const x of a.groups) g.addGroup(x.start, x.count, x.materialIndex);
  return g;
};
const lambert = (c, extra = {}) => new THREE.MeshLambertMaterial({color: c, ...extra});
const sizes = {};
const bytes = {};
const scene = name => { const s = new THREE.Scene(); s.name = name; return s; };
const take = async (name, root, count) => {
  root.updateMatrixWorld(true);
  const out = await toUSDZ(root);
  bytes[name] = Buffer.from(out).toString('base64');
  sizes[name] = count;
};

// a plain box with its six face materials
{
  const s = scene('box');
  const m = new THREE.Mesh(new THREE.BoxGeometry(40, 20, 30), Array.from({length: 6}, (_, i) => lambert(0x333333 + 0x111111 * i)));
  m.position.set(5, 6, 7);
  s.add(m);
  await take('box', s, 24);
}
// the closed plan-outline body: eight slots, one invisible
{
  const a = sectionArrays(box.section, box.width, box.height, box.depth, null, undefined, box['plan-outline']);
  const s = scene('body');
  const mats = Array.from({length: 8}, (_, i) => lambert(0x222222 + 0x101010 * i));
  mats[SEAM_INDEX] = new THREE.MeshBasicMaterial({visible: false});
  s.add(new THREE.Mesh(geometry(a), mats));
  await take('body', s, a.groups.filter(g => g.materialIndex !== SEAM_INDEX).reduce((n, g) => {
    const used = new Set(a.indices.slice(g.start, g.start + g.count)); return n + used.size; }, 0));
}
// a single material: exported as before
{
  const s = scene('single');
  s.add(new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10), lambert(0x884422)));
  await take('single', s, 24);
}
// an open half, placed the way the viewer places the lid
const cut = splitSection(box.section, box.width, box.height, box.depth, null, box.halves, box['plan-outline']);
{
  const s = scene('lid');
  const a = cut.lid.arrays;
  const mats = Array.from({length: 8}, (_, i) => lambert(0x444444, {side: THREE.DoubleSide}));
  mats[SEAM_INDEX] = new THREE.MeshBasicMaterial({visible: false});
  const m = new THREE.Mesh(geometry(a), mats);
  m.position.set(...cut.lid.center);
  m.quaternion.setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
  s.add(m);
  await take('lid', s, a.groups.filter(g => g.materialIndex !== SEAM_INDEX).reduce((n, g) => {
    const used = new Set(a.indices.slice(g.start, g.start + g.count)); return n + used.size; }, 0));
}
// a ray down onto the base's rim cap: the hit's normal is three's Vector3
const hits = [];
for (const [name, from, dir] of [['base', -400, 1], ['lid', 400, -1]]) {
  const a = cut[name].arrays;
  const mats = Array.from({length: 8}, () => lambert(0x555555, {side: THREE.DoubleSide}));
  const m = new THREE.Mesh(geometry(a), mats);
  m.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(0, box.height / 2 - box.halves.base.stands + from, 0), new THREE.Vector3(0, dir, 0));
  const hit = ray.intersectObject(m, false).sort((p, q) => p.distance - q.distance)[0];
  hits.push({name, slot: hit.face.materialIndex, isVector: hit.face.normal instanceof THREE.Vector3,
             answer: planWallFace(hit.face.normal), asArray: planWallFace(hit.face.normal.toArray())});
}
console.log(JSON.stringify({sizes, bytes, hits, PLAN_WALL_INDEX}));
"""


def run_node(tmp_path):
    root = tmp_path / "app"
    kit = root / "kit"
    kit.mkdir(parents=True)
    for name in ("share.js", "section.js", "bevel.js", "plan-body.js", "plan.js"):
        shutil.copy(KIT / name, kit / name)
    pkg = root / "node_modules" / "three"
    (pkg / "addons" / "exporters").mkdir(parents=True)
    (pkg / "addons" / "libs").mkdir()
    (pkg / "addons" / "utils").mkdir()
    src = pathlib.Path(THREE_DIR)
    shutil.copy(src / "three.module.js", pkg / "three.module.js")
    for rel in ("exporters/GLTFExporter.js", "exporters/USDZExporter.js", "libs/fflate.module.js",
                "utils/TextureUtils.js"):
        shutil.copy(src / "addons" / rel, pkg / "addons" / rel)
    (pkg / "package.json").write_text(json.dumps({
        "name": "three", "type": "module",
        "exports": {".": "./three.module.js", "./addons/*": "./addons/*"}}))
    (root / "package.json").write_text('{"type": "module"}')
    (root / "t.mjs").write_text(SCRIPT)
    box = {**THREE, "halves": with_seam(144.0)}
    p = subprocess.run(["node", "t.mjs", json.dumps(box)], capture_output=True, text=True, cwd=root)
    assert p.returncode == 0, p.stderr[-2000:]
    got = json.loads(p.stdout)
    got["zips"] = {k: base64.b64decode(v) for k, v in got.pop("bytes").items()}
    return got


@pytest.fixture(scope="module")
def three_run(tmp_path_factory):
    return run_node(tmp_path_factory.mktemp("three"))


def points_in(zbytes):
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    assert z.testzip() is None
    names = z.namelist()
    geo = [n for n in names if n.startswith("geometries/")]
    total = 0
    for n in geo:
        m = re.search(r"point3f\[\] points = \[(.*?)\]\n", z.read(n).decode(), re.S)
        total += m.group(1).count("(")
    return names, geo, total


@needs_three
@pytest.mark.parametrize("name", ["box", "body", "single", "lid"])
def test_the_usdz_of_a_body_with_several_materials_holds_its_geometry(three_run, name):
    names, geo, total = points_in(three_run["zips"][name])
    assert names[0] == "model.usda" and geo, f"{name}: the file holds no geometry: {names}"
    assert total == three_run["sizes"][name], (name, total, three_run["sizes"][name])


@needs_three
def test_a_box_with_six_materials_is_six_meshes_and_a_single_material_is_one(three_run):
    assert len(points_in(three_run["zips"]["box"])[1]) == 6
    assert len(points_in(three_run["zips"]["single"])[1]) == 1


@needs_three
def test_the_invisible_slot_is_not_in_the_usdz_of_the_body(three_run):
    # slot 6 is invisible: the closed body has none and the half's is dropped before the split
    names = points_in(three_run["zips"]["lid"])[0]
    assert len([n for n in names if n.startswith("geometries/")]) >= 2


@needs_three
def test_a_hit_on_a_rim_cap_answers_the_side_it_is_on_from_a_real_vector(three_run):
    hits = {h["name"]: h for h in three_run["hits"]}
    for h in hits.values():
        assert h["isVector"] and h["slot"] == three_run["PLAN_WALL_INDEX"], h
        assert h["answer"] == h["asArray"]
    # the base's cap looks down at the lid, the lid's looks up at the base
    assert hits["base"]["answer"] == "bottom" and hits["lid"]["answer"] == "top"


def test_the_glb_export_does_not_take_the_material_split():
    src = (KIT / "share.js").read_text()
    glb = src[src.index("export async function toGLB"):src.index("// three's USDZ exporter")]
    assert "splitByMaterial" not in glb and "forExport(root)" in glb
    assert "splitByMaterial(forExport(root))" in src[src.index("export async function toUSDZ"):]
