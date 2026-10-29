// WHICH FILE DRAWS A FACE (Portrayal #670).
//
// A drawing is written once and shared by every configuration that draws it
// identically, and the file is named after the FIRST of those configurations in
// manifest order - so r740xd's `lff12-mlff4-rlff2-rc0-noriser` front is
// `r740xd.lff12-rc0-noriser.front.svg`, and which name a configuration's face
// carries is not something to guess (configs.json does not list them in manifest
// order). `<device>.configs.json` says which
// file each configuration's face is, in `configs[].files`. Every face the site
// fetches by configuration goes through here; check-contract.py holds that no
// other code builds such a name by hand.
//
// `faceFile` is the kit's own (Portrayal kit/dist.js, since #670): look the
// file up in configs[].files, falling back to the pre-#670 name.
import {jdist, faceFile} from '../../dist.js';
export {faceFile} from '../../dist.js';

/** The URL of `view` of `ref` in configuration `config`, reading ref's configs.json.
 *  `distAt` is the library's: a function from a path in the build to its URL. */
export async function faceUrl(distAt, ref, config, view) {
  await Promise.resolve(distAt.ready).catch(() => {});   // a layered library knows its roots first
  const index = await jdist(distAt(`${ref}.configs.json`)).catch(() => null);
  return distAt(faceFile(index || {device: ref}, config, view));
}
