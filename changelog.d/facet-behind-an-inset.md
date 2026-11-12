### Fixed
- **A facet whose root an inset takes behind the plate keeps its slope in the 3D build**
  (`render.py`). A part mounted `inset` mm behind the face has the wedge of every facet on it
  lowered by the inset, but the lowered profile was clamped at the plate, so the wedge lost the
  inset: its slope flattened, and the kit, which rebuilds a facet's wedge from the profile's
  lowest height, stood the proud edge up by the whole inset. The profile now keeps its negative
  root, as the profile of a facet sunk in a pocket does. A facet wholly behind the plate is
  still dropped. A facet with no inset, a card in a well and a facet sunk in a pocket publish
  exactly what they did. The tests now pin a card sunk in a well: its wedge sinks with the
  card, and a cage and an optic stand on it.
  No record of the conformance list is closed.
