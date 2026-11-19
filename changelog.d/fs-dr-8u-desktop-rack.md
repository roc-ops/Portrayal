### Added
- **The FS-DR-8U desktop open frame as a rack product, `fs/fs-dr-8u`** (part of
  #1117). It is a two-post frame of 8U with 19 in rails and square holes, read from
  FS's data sheet: an outer box of 503 x 409 x 296 mm, 1.75 kg, a static load of
  50 kg, hole centres 465 mm and a clear opening of 451 mm from the sheet's front
  view. Its form is `desktop-frame`, which NetBox and Nautobot take as a two-post
  frame with a comment saying it is a desktop rack. The sheet's side view puts the
  posts at 81 degrees to the base, which leans them back 9 degrees, and dimensions
  a 296 x 73.7 mm base. The rack product has no key for a lean-back angle or a base,
  so both are in the description and in a `gaps` entry and are not data. The
  unit numbering is a stand-in, and the sheet gives no hole size and no usable
  depth. The rack type is exported for NetBox and Nautobot, and the product ships
  as an npm package, `@portrayal/racks-fs-fs-dr-8u`. No conformance record is
  closed. The rest of #1117 stays open: no held page prints a size for the
  StarTech RK12OD or the Tripp Lite SR2POST12, and the NavePoint 12U is left for a
  later part.
