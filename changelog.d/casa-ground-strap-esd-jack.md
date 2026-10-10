### Changed
- `casa/ground-strap@2` composes `common/esd-jack@1` for its 4 mm wrist-strap
  jack instead of drawing its own circle, so the C100G's ESD point is the same
  part the Cisco and Juniper chassis place (#413). The skin keeps the marked
  plate and the earth symbol; the 1.x circle and its misnamed `bolt-hole`
  element are gone. `casa/c100g` 1.0.0 seats it, front and rear.

### Removed
- `casa/ground-strap@1`, replaced by `casa/ground-strap@2` (#413). Its
  `bolt-hole` element has no successor: the jack is the composed `jack` part.
