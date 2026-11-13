### Changed
- The FS FS-PDUBK PDU bracket now draws what the product page's photographs show of it (#939).
  Each long edge of the plate turns back into a lip. The lips are about 5 mm clear of the plate, on the
  side away from the foot. So the bracket is 35 mm across the rack's face and no longer 30.
  Three gussets join the plate to the foot, at the 31.5 mm pitch of the keyholes.
  The two outer holes of the foot are slots that run across it. Each has a small tail toward the plate.
  They were drawn the other way about. The foot's two free corners are rounded.
  The lips are drawn in the front, rear, top and bottom views, and along the plate's edges from its far side.
  The gussets are drawn in the top and bottom views, on the plate and on the foot.
  A gusset is 6.5 mm thick at the plate and 3.5 mm at its tip, counted in pixels on the dimensioned render.
  Every position and size is read from the maker's photographs and is an estimate.
  A new gap, `lip-and-gusset-sizes`, asks for a dimensioned drawing.
  It also records that the bends are drawn square and the lips and gussets are not drawn in 3D.
  A second new gap, `lip-end-tabs`, names the small hook at the free end of each lip.
  Each reaches 3.2 to 3.5 mm. The hooks are not drawn.
  A trial with the depth and the four views at 139 kept capability level 4.
  The depth is a stated figure, so the gap asks the maintainer whether it may read 139.
  The device takes a major version because its width changes. No keyhole moves, and no port or export id changes.
  The foot and plate parts take a patch, and `fs/fs-pdubk-gusset-plan@1` and `fs/fs-pdubk-lip-plan@1` are added.
  This closes no row of the conformance records.
