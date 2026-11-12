### Added
- A bay can say what is seen through its opening when it is empty: the optional
  key `seen-through` on a device bay, a list of drawn items in the face's own
  coordinates. A bay's opening is painted over the panel decor, so decor could
  not show it. The items are drawn in the opening, clipped to it, over the dark
  of the hole and under any part seated there; a configuration that seats the
  bay, and a swap that does, hides them, and emptying the bay shows them again.
  It is a 2D drawing and builds no 3D geometry of its own. `format` stays 1.
  The Fibrain HD 1U frame draws the slotted band its front elevation shows
  behind the posts, and the FS FHD-1UFMT-N draws the two slack spools its
  front view shows in openings 1 and 4.
