### Changed
- `common/drive-carrier-25@2` and `common/drive-blank-25@2` are the 2.5 inch
  carrier at its own face, 15.3 x 73.0 (#721). `@1` drew 17.868 x 79.4, which
  is the bay pitch and seam extent of the Dell R740xd and not the carrier.
  Four Dell drawings of the part agree on the new size. The art is the `@1`
  art rescaled onto that face, not redrawn, and the element ids are
  unchanged (`lamp-activity`, `lamp-status`, `features` on the carrier).
  `dell/r740xd` 26.0.0 keeps its measured 17.868 x 79.4 bays and seats `@2`
  centred in them; `dell/r660` seats the same carrier lying flat.

### Removed
- `common/drive-carrier-25@1`, replaced by `common/drive-carrier-25@2`
  (#721). A manifest that pins `@1` moves to `@2`; a bay drawn at the `@1`
  size shows 2.6 mm of chassis between carriers.
- `common/drive-blank-25@1`, replaced by `common/drive-blank-25@2` (#721),
  for the same reason.
