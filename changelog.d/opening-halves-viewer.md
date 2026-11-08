### Added
- **A box that opens, shown open.** For a device that states `chassis.halves`, the 3D viewer
  draws an open state beside the closed box: each half standing its `stands` from the seam, the lid
  turned about its hinge edge by `angle`, both interiors visible, and the bays of each half as
  plates on its floor. It is closed by default, and a box with no halves, or a viewer that does not
  know the key, shows the closed box exactly as before. `createViewer(el, {housing: 'open'})` and
  `viewer.setHousing('open' | 'closed')` choose it, `viewer.halves()` lists the halves and the
  bays in each, and the Explorer has an Open / Close button for a box that opens: in 3D it turns
  the lid, in 2D it selects the authored open drawing. The new `kit/housing.js` holds the open
  state as numbers with no three.js and no DOM. Opening the box frames the camera on the open
  state (`openBounds` in `housing.js`), keeping the view direction, and closing it frames the
  closed box again. This closes no row.
