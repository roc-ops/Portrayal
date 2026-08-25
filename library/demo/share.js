// Export a live Portrayal scene as a file other people can open.
//
// The demo pages are only useful to someone who can reach the demo host. A GLB
// is not: it carries geometry and textures in one binary, and it opens by
// double-click in macOS Quick Look and Windows 3D Viewer, drags into PowerPoint,
// Keynote and Teams, uploads to Sketchfab, and imports into Blender or Unreal.
// USDZ is the same idea for AR Quick Look on an iPhone or iPad.
//
// Nothing here touches the scene: both exporters read it and hand back a buffer.

import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { USDZExporter } from 'three/addons/exporters/USDZExporter.js';

const save = (data, filename, type) => {
  const url = URL.createObjectURL(new Blob([data], {type}));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  // revoke on the next tick: Safari has not finished reading it synchronously
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const kb = n => n < 1024 * 1024
  ? `${Math.round(n / 1024)} KB`
  : `${(n / (1024 * 1024)).toFixed(1)} MB`;

// glTF and USDZ are both PBR formats. Lambert carries no roughness or metalness,
// so exporting it straight through lands on the defaults and everything arrives
// flat matte. Convert on a clone - clone() shares geometry and only the material
// reference, so assigning new materials here cannot touch the live scene.
// A cavity is a box whose front cap is a material with visible=false - that is
// what leaves it open to look into. glTF has no invisible material, so a naive
// conversion turns the cap into an opaque lid and seals the recess. Strip those
// faces out of the geometry instead: drop each group whose material is hidden
// and renumber what is left.
function dropHiddenFaces(mesh) {
  const mats = mesh.material;
  if (!Array.isArray(mats) || mats.every(m => m && m.visible)) return false;
  const geo = mesh.geometry.clone();
  const kept = [], newMats = [], remap = new Map();
  for (const g of geo.groups) {
    const m = mats[g.materialIndex];
    if (!m || !m.visible) continue;
    if (!remap.has(g.materialIndex)) {
      remap.set(g.materialIndex, newMats.length);
      newMats.push(m);
    }
    kept.push([g.start, g.count, remap.get(g.materialIndex)]);
  }
  geo.clearGroups();
  for (const [start, count, idx] of kept) geo.addGroup(start, count, idx);
  mesh.geometry = geo;
  mesh.material = newMats.length === 1 ? newMats[0] : newMats;
  return true;
}

function forExport(root) {
  const copy = root.clone(true);
  const drop = [];
  copy.traverse(o => {
    if (o.isLight) { drop.push(o); return; }   // viewers bring their own lighting
    if (!o.isMesh) return;
    // a wholly hidden mesh has no business in a file meant to be passed around
    const single = !Array.isArray(o.material) && o.material && !o.material.visible;
    if (!o.visible || single) { drop.push(o); return; }
    dropHiddenFaces(o);
    const one = m => {
      if (!m || m.isMeshStandardMaterial) return m;
      return new THREE.MeshStandardMaterial({
        color: m.color, map: m.map || null, side: m.side,
        transparent: m.transparent, opacity: m.opacity, alphaTest: m.alphaTest,
        // a plausible painted-metal/plastic finish. Not measured - nothing in
        // the library records surface finish, so this is presentation only.
        metalness: 0.15, roughness: 0.55,
      });
    };
    o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material);
  });
  for (const l of drop) l.parent?.remove(l);
  return copy;
}

export async function toGLB(root) {
  const buf = await new Promise((resolve, reject) => {
    new GLTFExporter().parse(forExport(root), resolve, reject, {binary: true});
  });
  return buf;                       // ArrayBuffer, magic 'glTF'
}

export async function toUSDZ(root) {
  return await new USDZExporter().parse(forExport(root));   // Uint8Array (a zip)
}

/**
 * Mount a small export panel.
 *
 * @param root      the object to export - usually the scene. Pass a group when
 *                  the scene holds things nobody wants in the file (a scrim, a
 *                  ground plane, helpers).
 * @param baseName  filename without extension, or a function
 *                  returning one - 3d.html swaps device without reloading
 * @param opts.note optional line shown under the buttons
 */
export function mountShare(root, baseName, opts = {}) {
  const wrap = document.createElement('div');
  wrap.id = 'portrayal-share';
  wrap.innerHTML = `
    <style>
      #portrayal-share { position: fixed; right: 0.9rem; bottom: 0.9rem; z-index: 40;
        font-family: system-ui, sans-serif; font-size: 0.74rem; text-align: right; }
      #portrayal-share button { font: inherit; cursor: pointer; margin-left: 0.35rem;
        background: #23272c; color: #d7dbdf; border: 1px solid #3a4046;
        border-radius: 6px; padding: 0.32rem 0.62rem; }
      #portrayal-share button:hover:not(:disabled) { background: #2c3137; border-color: #4d545b; }
      #portrayal-share button:disabled { opacity: 0.55; cursor: progress; }
      #portrayal-share .msg { color: #8d939a; margin-top: 0.3rem; min-height: 1.1em; }
      #portrayal-share .msg.bad { color: #f59e0b; }
    </style>
    <div>
      <button data-fmt="glb" title="Geometry and textures in one file. Opens in Quick Look, Windows 3D Viewer, PowerPoint, Blender, Sketchfab.">Download GLB</button>
      <button data-fmt="usdz" title="AR Quick Look on iPhone and iPad.">USDZ</button>
    </div>
    <div class="msg">${opts.note || ''}</div>`;
  document.body.appendChild(wrap);

  const msg = wrap.querySelector('.msg');
  const say = (text, bad = false) => {
    msg.textContent = text;
    msg.classList.toggle('bad', bad);
  };

  for (const btn of wrap.querySelectorAll('button')) {
    btn.onclick = async () => {
      const fmt = btn.dataset.fmt;
      const all = [...wrap.querySelectorAll('button')];
      all.forEach(b => { b.disabled = true; });
      say(`building ${fmt.toUpperCase()}…`);
      try {
        const name = typeof baseName === 'function' ? baseName() : baseName;
        const data = fmt === 'glb' ? await toGLB(root) : await toUSDZ(root);
        const size = data.byteLength ?? data.length;
        save(data, `${name}.${fmt}`,
             fmt === 'glb' ? 'model/gltf-binary' : 'model/vnd.usdz+zip');
        say(`${name}.${fmt} — ${kb(size)}`);
      } catch (err) {
        // USDZ is fussier than GLB, so say which one failed and why
        say(`${fmt.toUpperCase()} failed: ${err.message || err}`, true);
      } finally {
        all.forEach(b => { b.disabled = false; });
      }
    };
  }
  return wrap;
}
