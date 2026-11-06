// Which projections the 3D scene's path index records.
//
// A rear fibre is drawn only as a projection (`data-of` naming the part), and the scene builds nothing from a projection. Without a
// record the path resolves to its nearest drawn ancestor - the whole cassette.
// So a projection is indexed under the path it is of, for finding and haloing
// only; picking keeps its own index.
//
// `realPaths` is every path a face draws as a part, on any face: a part that is
// drawn wins over its projection. `projections` are `{view, path, ...box}` with
// `path` the `data-of` value. One record per face and path.
export function projectionRecords(realPaths, projections) {
  const seen = new Set();
  const out = [];
  for (const p of projections) {
    if (realPaths.has(p.path)) continue;
    const key = `${p.view}\0${p.path}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(p);
  }
  return out;
}
