// Shared relief pipeline.
//
// Face art is an SVG whose nodes carry data-cavity / data-z-* attributes saying
// which parts of the faceplate are recessed, raised, domed or vented. This module
// turns that into something a viewer can build geometry from, and rasterises the
// art at a chosen density.
//
// It lives here rather than in 3d.html because rack.html needs exactly the same
// reading of a face, and two copies would drift. Dependencies are injected once
// rather than threaded through every signature, so the function bodies are the
// same code that has been running in the device viewer.

let THREE, renderer, PXMM, FRU_PATHS;

export function configureRelief(deps) {
  ({THREE, renderer, PXMM, FRU_PATHS} = deps);
}

// Every view SVG was fetched with cache: 'no-store' from four separate call
// sites - svgCanvas (once per box face), extractRelief, and twice more in the
// page - so switching configuration re-downloaded the same six files dozens of
// times. On the demo host that was 9.4 of the 11.8 seconds a switch took. The
// URL already carries the config name, so memoising per URL is safe; a build
// tool writes new files under new names.
const SVG_CACHE = new Map();
export function svgSource(url) {
  if (!SVG_CACHE.has(url))
    SVG_CACHE.set(url, fetch(url, {cache: 'no-store'}).then(r => r.text()));
  return SVG_CACHE.get(url);
}
export function clearSvgCache() { SVG_CACHE.clear(); }

// A flat drawing outlines the faceplate and rounds its corners so the sheet
// metal reads as a part on a page. On a box, the outline of a face IS the box's
// edge, and both devices cost us something in 3D: the 0.5mm stroke sits half
// inside each face, so where two textured faces meet - front to side, rear to
// side - you get 0.5mm of near-black that reads as a gap you can see through,
// and rx="1.2" makes the four corners genuinely transparent under alphaTest, so
// at each box vertex you really can. Top edges escaped notice only because the
// lid art paints a bright line along them that swamps the seam. Square and
// de-stroke the faceplate before it becomes a texture; the geometry draws the
// edge.
export function squareFaceplate(text) {
  return text.replace(/<rect\b[^>]*\bid="chassis-faceplate"[^>]*>/,
    m => m.replace(/\s(?:rx|ry|stroke|stroke-width)="[^"]*"/g, ''));
}

export async function svgCanvas(url, wmm, hmm, flipX = false, flipYax = false) {
  const text = await svgSource(url);
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([text], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  cv.width = Math.round(wmm * PXMM); cv.height = Math.round(hmm * PXMM);
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipYax) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  URL.revokeObjectURL(blobUrl);
  cv._svgText = text;      // kept for adaptive re-rasterisation (see LOD below)
  return cv;
}
// A face canvas is inevitably non-power-of-two (a 548x44mm side is 2192x176 at
// 4px/mm). WebGL2 mipmaps NPOT textures natively, so rescaling to POT buys
// nothing - and it costs: a 2192x176 side squashed to 2048x128 is 1.07x
// horizontally but 1.38x vertically, and that anisotropic resample distorts fine
// repeating detail (the AS5912's 488x5mm vent strips) into something that beats
// against the pixel grid and crawls under motion. Feed the native raster instead.
// ?tex=plain drops mipmaps and anisotropy. Edge artefacts at a corner seen
// nearly edge-on are a sampler question, and samplers differ by GPU and browser
// in ways this machine cannot reproduce - so make the suspect switchable rather
// than argue about it. A corner line that survives ?tex=plain is not sampling.
const TEX_MODE = new URLSearchParams(location.search).get('tex') || '';
export function canvasTex(cv) {
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  if (TEX_MODE === 'plain') {
    tex.anisotropy = 1;
    tex.generateMipmaps = false;
    tex.minFilter = THREE.LinearFilter;
  } else {
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
  }
  tex.needsUpdate = true;
  return tex;
}
// crop a mm-rect out of a face canvas (no mirroring: the rear floor plane's
// 180-degree rotation and the box rear-face UVs already reverse X to match)
export function crop(cv, r) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(r.w * PXMM)); c.height = Math.max(1, Math.round(r.h * PXMM));
  const ctx = c.getContext('2d');
  ctx.drawImage(cv, Math.round(r.x * PXMM), Math.round(r.y * PXMM), c.width, c.height, 0, 0, c.width, c.height);
  return c;
}

// standards-relief extraction: cavities (with interior features) + outward protrusions.
// Interior/plate art is re-rendered STANDALONE from its own nodes so bezel plates
// can carry arbitrary shapes (plug-outline apertures, LED holes) via alpha.
export async function extractRelief(url) {
  const div = document.createElement('div');
  div.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px;visibility:hidden';
  div.innerHTML = await svgSource(url);
  document.body.appendChild(div);
  const svg = div.querySelector('svg');
  const inv = svg.getScreenCTM().inverse();
  const mmRect = el => {
    const b = el.getBBox();
    const m = inv.multiply(el.getScreenCTM());
    const pts = [[b.x, b.y], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => ({x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f}));
    const x0 = Math.min(pts[0].x, pts[1].x), y0 = Math.min(pts[0].y, pts[1].y);
    return {x: x0, y: y0, w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y)};
  };
  const shared = [...svg.querySelectorAll('style, defs')].map(n => n.outerHTML).join('');
  // HOW FAR OFF THE FACE A FEATURE STARTS, summed up the ANCESTOR CHAIN.
  //
  // `lift` is not always written on the node that carries the feature. A composed
  // part gets its lift on the part's instance GROUP (render.py writes it there,
  // because that is the thing being positioned), while the `cyl` or `dome` that
  // has to move sits on a child of it - and `dataset` does not inherit. So an
  // MCX jack mounted on a block standing 15.9mm proud read lift 0 and drew at
  // the panel, underneath its own block.
  //
  // Sum rather than look one level up: a part on a raised block on a raised
  // bezel is a real shape, and the third case arrives the day after the second
  // is special-cased.
  //
  // THIS IS THE SECOND BUG OF EXACTLY THIS SHAPE IN ONE AFTERNOON, and the
  // pattern is worth naming because there will be a third. This module decides
  // what exists in 3D by QUERYING THE DOM FOR ATTRIBUTES, so every query is a
  // chance to miss data that is correctly present. The other case was the FRU
  // class list below, which asked for psu/fan/tab and so could not see the
  // twelve parts that spell the same classes `power` and `cooling`. In both,
  // the manifest was right, the compiled SVG was right, and the extractor threw
  // the answer away - which looks exactly like a modelling gap and is not one.
  // When something declared does not appear in 3D, suspect the selector first.
  const liftOf = el => {
    let z = 0;
    for (let n = el; n && n !== svg; n = n.parentElement) z += +(n.dataset.zLift || 0);
    return z;
  };
  // owning FRU (bay module / pull tab) of a node, for animated removal
  const ownerOf = el => {
    const a = el.closest('[data-path]');
    if (!a) return null;
    const root = a.dataset.path.split('/')[0];
    return FRU_PATHS.has(root) ? root : null;
  };
  const nodeSvg = (el, rect) => {
    const m = inv.multiply(el.getScreenCTM());
    const clone = el.cloneNode(true);
    clone.removeAttribute('transform');   // the CTM below already includes it
    // raised descendants (collars, handles) render as their own geometry -
    // keep them out of cavity floors and plate textures
    for (const r of clone.querySelectorAll(
        '[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle],[data-z-dome][data-z-lift]'))
      r.style.display = 'none';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${rect.w} ${rect.h}"` +
      ` width="${rect.w}mm" height="${rect.h}mm">${shared}` +
      `<g transform="matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e - rect.x} ${m.f - rect.y})">` +
      clone.outerHTML + `</g></svg>`;
  };
  const cavities = [...svg.querySelectorAll('[data-depth]')]
    .filter(el => !el.querySelector('[data-depth]'))
    .map(el => {
      const cavNode = el.dataset.cavity &&
        svg.querySelector(`[id="${CSS.escape(el.id + '--' + el.dataset.cavity)}"]`);
      const rect = mmRect(cavNode || el);
      const grpRect = mmRect(el);
      const features = [...el.querySelectorAll('[data-z-top],[data-z-sink]')].map(f => ({
        ...mmRect(f),
        kind: f.dataset.zTop ? 'top' : 'sink',
        val: +(f.dataset.zTop || f.dataset.zSink),
        color: f.dataset.zColor || '#0a0c0e',
      }));
      return {...rect, owner: ownerOf(el), d: +el.dataset.depth, wall: el.dataset.wall || '#a7adb4',
              lift: liftOf(el),
              round: !!el.dataset.round, cavSvg: nodeSvg(cavNode || el, rect),
              grpRect, grpSvg: nodeSvg(el, grpRect), features};
    });
  // pressed grooves: shallow standalone cavities whose own art is the floor
  for (const el of svg.querySelectorAll('[data-groove]')) {
    const rect = mmRect(el);
    cavities.push({...rect, owner: ownerOf(el), d: +el.dataset.groove, wall: '#25282c', round: false,
                   cavSvg: nodeSvg(el, rect), grpRect: rect,
                   grpSvg: nodeSvg(el, rect), features: []});
  }
  const outs = [...svg.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), out: el.dataset.zOut && +el.dataset.zOut,
            cyl: el.dataset.zCyl && +el.dataset.zCyl,
            bar: el.dataset.zBar && +el.dataset.zBar,
            uhandle: el.dataset.zUhandle && +el.dataset.zUhandle,
            lift: liftOf(el),
            knurl: !!el.dataset.zKnurl,
            thread: el.dataset.zThread && +el.dataset.zThread,
            color: el.dataset.zColor || null,
            svgText: nodeSvg(el, rect)};
  });
  const domes = [...svg.querySelectorAll('[data-z-dome]')].map(el => {
    const rect = mmRect(el);
    // a lamp on a raised indicator bezel domes from THAT surface, not the panel
    return {...rect, owner: ownerOf(el), dome: +el.dataset.zDome, lift: liftOf(el),
            svgText: nodeSvg(el, rect)};
  });
  const vents = [...svg.querySelectorAll('[data-vent],[data-z-vent]')].map(el => {
    const rect = mmRect(el);
    return {...rect, owner: ownerOf(el), depth: +(el.dataset.vent || el.dataset.zVent),
            svgText: nodeSvg(el, rect)};
  });
  // component instances only (data-ref) - contract elements can share a class
  // name (pull-tab has an element called "tab"), which would shadow the module
  const frus = [];
  // WHICH CLASSES GET A BODY. A component is field-replaceable because of what it
  // IS, and this list is the renderer's view of that. It was psu/fan/tab, which
  // silently excluded two whole classes that behave identically:
  //   power    - power ENTRY modules and trays. NOT a mislabelled psu: a PEM is a
  //              conduit that neither draws nor supplies, and collapsing the two
  //              would lose a distinction the power model depends on. 5 parts.
  //   cooling  - casa/ and cisco/ call a fan `cooling` where edgecore/, ufispace/
  //              and common/ call the same object `fan`. 7 parts against 3. That
  //              duplication is a DATA defect and is recorded in working/notes/;
  //              admitting both here is the renderer refusing to be the place it
  //              gets fixed, not an endorsement of it.
  // The visible symptom was that every Casa and Cisco fan and PEM drew as art
  // painted on the chassis plate, with no body and no ejection - and edgecore
  // "worked in 3D" for no better reason than its choice of word.
  const BODY_CLASSES = ['psu', 'fan', 'tab', 'power', 'cooling'];
  for (const el of svg.querySelectorAll(BODY_CLASSES.map(c => `[data-class="${c}"]`).join(','))) {
    if (!el.dataset.ref) continue;
    const path = (el.dataset.path || '').split('/')[0];
    if (!path || frus.some(f => f.path === path)) continue;
    frus.push({path, ref: el.dataset.ref.split(':')[0], cls: el.dataset.class, ...mmRect(el)});
  }
  for (const el of svg.querySelectorAll('[data-z-out],[data-z-cyl],[data-z-bar],[data-z-uhandle]'))
    el.style.display = 'none';
  const cleanText = svg.outerHTML;
  div.remove();
  return {cavities, outs, domes, vents, frus, cleanText};
}

export async function rasterize(svgText, wmm, hmm, pxmm = PXMM, flipX = false, flipY = false) {
  const img = new Image();
  const blobUrl = URL.createObjectURL(new Blob([svgText], {type: 'image/svg+xml'}));
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = blobUrl; });
  const cv = document.createElement('canvas');
  cv.width = Math.max(1, Math.round(wmm * pxmm)); cv.height = Math.max(1, Math.round(hmm * pxmm));
  const ctx = cv.getContext('2d');
  if (flipX) { ctx.translate(cv.width, 0); ctx.scale(-1, 1); }
  if (flipY) { ctx.translate(0, cv.height); ctx.scale(1, -1); }
  ctx.drawImage(img, 0, 0, cv.width, cv.height);
  URL.revokeObjectURL(blobUrl);
  return cv;
}

// six-sided FRU body: same art the component tab shows, reused inside the device

// Build the relief geometry for one face: the recesses, raised parts, domes,
// vents and FRU sub-groups a compiled face describes. Returns nothing - it
// fills the collections the caller owns, because a device viewer wants these
// parented per instance while a rack viewer wants them built once per model.
export async function buildFaceRelief(F, ctx) {
  const {src, faceCv, faceSvg, facePunch, meshes,
         FRU_GROUPS, FRU_META, BODY_META, D, bodyBoxMesh} = ctx;
    const fw = F.fw(), fh = F.fh();
    // a device need not declare every view; fall back to a plain face
    if (!(await fetch(src, {method: 'HEAD', cache: 'no-store'})).ok) {
      const cv0 = document.createElement('canvas');
      cv0.width = Math.round(fw * PXMM); cv0.height = Math.round(fh * PXMM);
      const c0 = cv0.getContext('2d');
      c0.fillStyle = '#3a3f44'; c0.fillRect(0, 0, cv0.width, cv0.height);
      faceCv[F.view] = cv0;
      return;
    }
    const {cavities, outs, domes, vents, frus, cleanText} = await extractRelief(src);
    const faceText = squareFaceplate(cleanText);
    const cv = await rasterize(faceText, fw, fh);
    faceCv[F.view] = cv;
    faceSvg[F.view] = faceText;   // LOD re-rasterises from this; keep it squared
    facePunch[F.view] = [];
    const grp = new THREE.Group();
    grp.position.set(...F.pos());
    grp.rotation.set(...F.rot);
    const LX = (x, w) => x + w / 2 - fw / 2;
    const LY = (y, h) => (F.flipLY ? -1 : 1) * (fh / 2 - (y + h / 2));
    const sideMats = c => Array.from({length: 6},
      () => new THREE.MeshLambertMaterial({color: c}));
    // each FRU gets a subgroup so its art and relief travel together when ejected
    const fruGroups = {};
    for (const f of frus) {
      const fg = new THREE.Group();
      grp.add(fg);
      fruGroups[f.path] = fg;
      FRU_GROUPS[f.path] = fg;
      const bd = BODY_META[f.ref];
      const depth = bd ? bd.depth : 60;
      // captive modules declare how far they pull out; removable FRUs clear the chassis
      const captive = bd && bd.travel;
      FRU_META[f.path] = {cls: f.cls, view: F.view, body: bd, captive: !!captive,
                          pull: Math.min(captive || depth * 1.5 + 25, D - 10)};
    }
    let curOwner = null;
    const addTo = obj => (curOwner && fruGroups[curOwner] ? fruGroups[curOwner] : grp).add(obj);
    for (const c of cavities) {
      curOwner = c.owner;
      const d = Math.min(c.d, D - 2);
      // floor + feature art comes from the cavity group rendered standalone, so
      // raised bezel plates (drawn over the cavity on the face) never leak in
      const gcv = await rasterize(c.grpSvg, c.grpRect.w, c.grpRect.h);
      const floorCv = crop(gcv, {x: c.x - c.grpRect.x, y: c.y - c.grpRect.y, w: c.w, h: c.h});
      const fctx = floorCv.getContext('2d');
      for (const ft of c.features) {
        ft.faceCv = crop(gcv, {x: ft.x - c.grpRect.x, y: ft.y - c.grpRect.y, w: ft.w, h: ft.h});
        // remove the feature art from the floor (it lives on its own box now)
        const px = [Math.round((ft.x - c.x) * PXMM), Math.round((ft.y - c.y) * PXMM),
                    Math.round(ft.w * PXMM), Math.round(ft.h * PXMM)];
        if (ft.kind === 'sink') fctx.clearRect(...px);
        else { fctx.fillStyle = '#0d0f11'; fctx.fillRect(...px); }
      }
      // shape-accurate punch: the cavity node's own art defines the hole
      if (!c.lift) {   // a lifted cavity recesses from a raised part, so the
        // chassis face beneath it is already covered - punching it would leave
        // a hole straight through the faceplate
        const pctx = cv.getContext('2d');
        pctx.globalCompositeOperation = 'destination-out';
        pctx.drawImage(await rasterize(c.cavSvg, c.w, c.h),
                       Math.round(c.x * PXMM), Math.round(c.y * PXMM));
        pctx.globalCompositeOperation = 'source-over';
        facePunch[F.view].push({kind: 'shape', svg: c.cavSvg,
                                x: c.x, y: c.y, w: c.w, h: c.h});
      }
      // walls are double-sided: the interior is the recess, and the exterior is
      // the cage/housing body seen through neighboring vent holes. The back face
      // is a separate dark exterior; the textured floor plane sits just inside it
      // (sink pockets punch through the floor's alpha, so the back stays clear
      // of the floor by the sink allowance).
      const wallMat = new THREE.MeshLambertMaterial({color: c.wall, side: THREE.DoubleSide});
      const backMat = new THREE.MeshLambertMaterial({color: 0x23262b, side: THREE.DoubleSide});
      let walls;
      if (c.round) {
        walls = new THREE.Mesh(
          new THREE.CylinderGeometry(c.w / 2, c.w / 2, d, 24, 1, true), wallMat);
        walls.rotation.x = Math.PI / 2;
      } else {
        const noFace = new THREE.MeshBasicMaterial({visible: false});
        walls = new THREE.Mesh(new THREE.BoxGeometry(c.w, c.h, d),
          [wallMat, wallMat, wallMat, wallMat, noFace, noFace]);
      }
      walls.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - d / 2);
      addTo(walls);
      // textured floor: the aperture art, pushed to the back of the recess
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h),
        new THREE.MeshBasicMaterial({map: canvasTex(floorCv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      floor.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d - 0.1));
      addTo(floor);
      // closed exterior back, deep enough to clear any sink pockets
      const maxSink = Math.max(0, ...c.features.filter(f => f.kind === 'sink').map(f => f.val));
      const back = new THREE.Mesh(new THREE.PlaneGeometry(c.w, c.h), backMat);
      back.position.set(LX(c.x, c.w), LY(c.y, c.h), c.lift - (d + maxSink + 0.15));
      addTo(back);
      for (const ft of c.features) {
        if (ft.kind === 'top') {
          const hgt = Math.min(ft.val, d - 0.2);
          const mats = sideMats(ft.color);
          mats[4] = new THREE.MeshBasicMaterial({map: canvasTex(ft.faceCv)});
          const m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, hgt), mats);
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), c.lift - (d - hgt / 2));
          addTo(m);
        } else {   // sink: a deeper pocket beyond the floor
          const m = new THREE.Mesh(new THREE.BoxGeometry(ft.w, ft.h, ft.val),
            new THREE.MeshLambertMaterial({color: ft.color, side: THREE.DoubleSide}));
          m.position.set(LX(ft.x, ft.w), LY(ft.y, ft.h), -(d + ft.val / 2));
          addTo(m);
        }
      }
    }
    // Air vents stay as painted art rather than punched alpha. Punching them made
    // each honeycomb cell an alphaTest cutout, and alphaTest is a binary decision
    // taken AFTER texture filtering - at a grazing angle, with dozens of cells
    // falling in one pixel, the filtered alpha sits near the threshold and speckles.
    // Neither mipmaps nor alphaToCoverage can fix that; both act before the cut.
    // Left as colour, mipmapping averages the cells to smooth shading, which is
    // what you actually see on a real chassis from any distance.
    // Large openings (cavities, FRU bays) are punched elsewhere and do not moire,
    // being a handful of big rectangles rather than a fine repeating lattice.
    for (const v of vents) {
      // Vents are painted into the face art (see above), so the face is opaque
      // here and a box behind it can only ever show through as z-fighting. It sat
      // 0.05mm back, far finer than the depth buffer resolves, which is what was
      // speckling along the side faces. Nothing to draw.
      curOwner = v.owner;
    }
    for (const dm of domes) { // gentle domes: node art draped on a paraboloid cap
      curOwner = dm.owner;
      // (LED lamps, bulged fan guards); apex proud, rim sunk 0.15 into the face
      const dcv = await rasterize(dm.svgText, dm.w, dm.h);
      const geo = new THREE.CircleGeometry(0.5, 48);
      const pos = geo.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const rr = Math.min(1, Math.hypot(pos.getX(i), pos.getY(i)) * 2);
        pos.setZ(i, 1 - rr * rr);
      }
      geo.computeVertexNormals();
      const m = new THREE.Mesh(geo, new THREE.MeshLambertMaterial(
        {map: canvasTex(dcv), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      m.scale.set(dm.w, dm.h, dm.dome + 0.15);
      m.position.set(LX(dm.x, dm.w), LY(dm.y, dm.h), (dm.lift || 0) - 0.15);
      addTo(m);
    }
    for (const o of outs) {   // protrusions: bezel plates, handles, studs, tubes
      curOwner = o.owner;
      const ocv = await rasterize(o.svgText, o.w, o.h);
      if (!o.color) {   // side color: sample the node's own art
        const px = ocv.getContext('2d').getImageData(
          Math.floor(ocv.width / 2), Math.floor(ocv.height / 2), 1, 1).data;
        o.color = `rgb(${px[0]},${px[1]},${px[2]})`;
      }
      const faceTex = new THREE.MeshBasicMaterial(
        {map: canvasTex(ocv), transparent: true, alphaTest: 0.1, alphaToCoverage: true});
      if (o.uhandle !== undefined && o.uhandle !== '') {
        const far = +o.uhandle;
        const horizontal = o.w >= o.h;
        const dia = Math.min(o.w, o.h), r = dia / 2, Rb = dia;
        const zBar = far - r, legH = Math.max(0.5, zBar - Rb);
        const uLen = Math.max(o.w, o.h);
        const u0 = horizontal ? o.x : o.y;
        const a = u0 + r, b = u0 + uLen - r;          // leg centerlines (svg coords)
        const cc = horizontal ? o.y + o.h / 2 : o.x + o.w / 2;  // cross-axis center
        const mat = new THREE.MeshLambertMaterial({color: o.color});
        const P = (u, z) => horizontal
          ? [u - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - cc), z]
          : [cc - fw / 2, (F.flipLY ? -1 : 1) * (fh / 2 - u), z];
        for (const u of [a, b]) {                     // legs
          const leg = new THREE.Mesh(new THREE.CylinderGeometry(r, r, legH, 16), mat);
          leg.rotation.x = Math.PI / 2;
          leg.position.set(...P(u, legH / 2));
          addTo(leg);
        }
        const barLen = (b - Rb) - (a + Rb);           // crossbar between the bends
        if (barLen > 0.1) {
          const bar = new THREE.Mesh(new THREE.CylinderGeometry(r, r, barLen, 16), mat);
          if (horizontal) bar.rotation.z = Math.PI / 2;
          bar.position.set(...P((a + b) / 2, zBar));
          addTo(bar);
        }
        for (const [u, near] of [[a + Rb, a], [b - Rb, b]]) {   // continuous bends
          const holder = new THREE.Group();
          holder.position.set(...P(u, zBar - Rb));
          holder.rotation.z = horizontal ? 0 : Math.PI / 2;
          const elbow = new THREE.Mesh(new THREE.TorusGeometry(Rb, r, 12, 16, Math.PI / 2), mat);
          // low-u corner sweeps (-u -> +z), high-u corner (+u -> +z), in holder-local xy
          const legLocalU = horizontal ? near : -near;   // svg y runs opposite to local up
          const cornerLocalU = horizontal ? u : -u;
          elbow.rotation.set(Math.PI / 2, 0, legLocalU < cornerLocalU ? Math.PI / 2 : 0);
          holder.add(elbow);
          addTo(holder);
        }
      } else if (o.bar !== undefined && o.bar !== '') {
        // round tube along the node's long axis, lift..lift+bar off the face
        const len = Math.max(o.w, o.h), r = o.bar / 2;
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 16),
          new THREE.MeshLambertMaterial({color: o.color}));
        if (o.w >= o.h) m.rotation.z = Math.PI / 2;   // horizontal bar
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + r);
        addTo(m);
      } else if (o.cyl !== undefined && o.cyl !== '') {
        // cylinder: lift..lift+cyl, top cap carries the node art
        const r = Math.min(o.w, o.h) / 2;
        let side;
        if (o.thread) {
          // single-start helix: one diagonal per tile, tiled once around the
          // circumference and once per pitch along the axis, so the stripe meets
          // itself at the seam and reads as a continuous thread rather than rings
          const tc = document.createElement('canvas');
          tc.width = 32; tc.height = 32;
          const tx = tc.getContext('2d');
          tx.fillStyle = o.color; tx.fillRect(0, 0, 32, 32);
          tx.strokeStyle = 'rgba(0,0,0,0.42)'; tx.lineWidth = 7;
          tx.lineCap = 'butt';
          for (const dy of [-32, 0, 32]) {          // wrap copies keep it seamless
            tx.beginPath(); tx.moveTo(0, 32 + dy); tx.lineTo(32, dy); tx.stroke();
          }
          tx.strokeStyle = 'rgba(255,255,255,0.20)'; tx.lineWidth = 2.5;
          for (const dy of [-32, 0, 32]) {
            tx.beginPath(); tx.moveTo(0, 27 + dy); tx.lineTo(32, dy - 5); tx.stroke();
          }
          const ttex = canvasTex(tc);
          ttex.wrapS = ttex.wrapT = THREE.RepeatWrapping;
          ttex.repeat.set(1, Math.max(1, Math.round(o.cyl / o.thread)));
          side = new THREE.MeshLambertMaterial({map: ttex});
        } else if (o.knurl) {  // fine grip ridges wrapped around the circumference
          const kc = document.createElement('canvas');
          kc.width = 8; kc.height = 8;
          const kctx = kc.getContext('2d');
          kctx.fillStyle = o.color; kctx.fillRect(0, 0, 8, 8);
          kctx.fillStyle = 'rgba(0,0,0,0.45)'; kctx.fillRect(4, 0, 4, 8);
          const ktex = canvasTex(kc);
          ktex.wrapS = THREE.RepeatWrapping;
          ktex.repeat.set(Math.max(12, Math.round(2 * Math.PI * r / 0.5)), 1);
          ktex.magFilter = THREE.NearestFilter;
          side = new THREE.MeshLambertMaterial({map: ktex});
        } else {
          side = new THREE.MeshLambertMaterial({color: o.color});
        }
        const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, o.cyl, 24),
          [side, faceTex, side]);
        m.rotation.x = Math.PI / 2;
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + o.cyl / 2);
        addTo(m);
      } else {
        // box: lift..out (lift defaults to 0 = sits on the face)
        const depth = o.out - o.lift;
        const mats = sideMats(o.color);
        mats[4] = faceTex;
        const m = new THREE.Mesh(new THREE.BoxGeometry(o.w, o.h, depth), mats);
        m.position.set(LX(o.x, o.w), LY(o.y, o.h), o.lift + depth / 2);
        addTo(m);
      }
    }
    curOwner = null;
    for (const f of frus) {   // move the FRU's face art into its group; leave a bay
      const fg = fruGroups[f.path];
      const faceCrop = crop(cv, f);
      const plane = new THREE.Mesh(new THREE.PlaneGeometry(f.w, f.h),
        new THREE.MeshBasicMaterial({map: canvasTex(faceCrop), transparent: true, alphaTest: 0.1, alphaToCoverage: true}));
      plane.position.set(LX(f.x, f.w), LY(f.y, f.h), 0.3);
      fg.add(plane);
      // CLEAR, never fill: an opaque patch on the chassis face would occlude
      // everything behind it (the module's own cavities, pins, bay interior)
      cv.getContext('2d').clearRect(Math.round(f.x * PXMM), Math.round(f.y * PXMM),
                                    Math.round(f.w * PXMM), Math.round(f.h * PXMM));
      facePunch[F.view].push({kind: 'rect', x: f.x, y: f.y, w: f.w, h: f.h});
      const meta = FRU_META[f.path];
      if (meta.body) {   // full module body travels with the FRU
        const {mesh, fp, d} = await bodyBoxMesh(meta.body, f.w, f.h);
        mesh.position.set(LX(f.x + fp.at[0], fp.size[0]),
                          LY(f.y + fp.at[1], fp.size[1]), -d / 2 - 0.05);
        fg.add(mesh);
      }
      // empty bay: interior surfaces only, so it never occludes the module's
      // own cavities (the C14 inlet pins live inside this volume)
      const bd = meta.body ? meta.body.depth : 60;
      const bay = new THREE.Mesh(new THREE.BoxGeometry(f.w + 0.6, f.h + 0.6, bd),
        new THREE.MeshLambertMaterial({color: 0x0a0c0e, side: THREE.BackSide}));
      bay.position.set(LX(f.x, f.w), LY(f.y, f.h), -bd / 2 - 0.2);
      grp.add(bay);
    }
  meshes.push(grp);
}
