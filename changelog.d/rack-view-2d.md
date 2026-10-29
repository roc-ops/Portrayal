### Added
- The 2D rack elevation is in the kit, under `kit/rack/view/` (#1298, order 1 of
  `docs/rack-views-design.md`): `mountRack2d(container, {document, doc, rackId,
  face, chassisOf, ctx, dist})` draws one face of one rack as SVG and returns the
  handle `{ready, update, select, on, dispose}`, with a `pick` event that names
  what was clicked as a path (`joinPath` and `splitPath`: `item:`, `zeroU:`,
  `cable:`, `bundle:`, `tie:` and `u:` keys). A document of several racks draws any
  one by `rackId`; a backboard surface is refused with a sentence. The modules
  moved from portrayal-site are `elevation`, `face`, `faces`, `ear-holes`,
  `settable` and `dom`, and they make every node through the `document` they are
  given. The export paths are `./rack/view/view`, `./rack/view/elevation`,
  `./rack/view/dom`, `./rack/view/face`, `./rack/view/faces`,
  `./rack/view/ear-holes` and `./rack/view/settable`, and `rack/view/*.js` is
  published and checked by `npm test`. The Rack Builder still draws from its own
  copy until the site switches to the kit. The kit version is not bumped.
