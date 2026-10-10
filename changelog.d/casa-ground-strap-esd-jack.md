### Changed
- `casa/ground-strap@2` composes `common/esd-jack@1` for its 4 mm wrist-strap
  jack instead of drawing its own circle, so the C100G's ESD point is the same
  part the Cisco and Juniper chassis place (#413). The skin keeps the marked
  plate and the earth symbol; the 1.x circle and its misnamed `bolt-hole`
  element are gone. `casa/c100g` 1.0.0 seats it, front and rear.

### Removed
- `casa/ground-strap@1`, replaced by `casa/ground-strap@2` (#413). Its
  `bolt-hole` element has no successor: the jack is the composed `jack` part.

### Fixed
- L39 reads a composed leaf with no registry entry (no `conforms`, no parts of
  its own, a size, and not a lamp, latch or printing) as the opening of the
  part that composes it, as `_aperture_of` already did, so the C100G's strap
  plate is checked against its jack's cutout rather than reported 4.5 mm off
  it (#413).
