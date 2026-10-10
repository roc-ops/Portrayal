### Added
- The kit device picker offers the NOS vendors and the boxes each lists
  (#711). `createDevicePicker` in `@portrayal/kit/devsel` takes two optional
  inputs, `listings` (the build `listings.json`) and `listing` (the entry to
  start on). Choosing a listing loads the drawing of the hardware it lists
  and keeps the listing as the selection. Nothing an existing caller uses
  changes shape: `onchange(name)` still receives the device name, with
  `{listing}` as a second argument, and `picker.value` is still the device
  name, beside the new `picker.listing`. `pickerEntries(devices, listings)`
  is exported, and gives the entries the picker shows. The explorer writes
  `?listing=<ns>/<id>` beside `?device=`, so a reload lands on the same entry.
- `@portrayal/kit/nosnames`, a new export: what a listing says its NOS calls
  each port (#719). `listingNames(listing)` and `nosNameFor(listing, path)`
  give the names, `expandName(pattern, n)` expands one pattern, and
  `breakoutNote(breakout, n)` words a breakout. It is the grammar of the DCIM
  export, ported, and a test holds the two to identical names over every
  listing in the build. With a listing chosen, the explorer inspector shows
  the NOS name of a selected port. Only the top-level ports of a device are
  looked up, and a port the listing does not name is never guessed: the
  inspector names the listing gap that explains it.

### Fixed
- `dcim_export` refuses a listing name pattern that does not parse, by name,
  where it raised a bare `SyntaxError` (#719).
