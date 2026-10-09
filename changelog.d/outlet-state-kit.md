### Added
- `@portrayal/kit` 0.10.0: an outlet's state is shown on its lamp (#934;
  `docs/pdu-model-design.md` section 3.2). A state set on the path of an
  element that declares states - a switched PDU outlet - is applied to every
  lamp `for:` binds to it as well: by a marks document (`marks.js` apply), by
  the Explorer's chips, and in the 3D scene (`relief.js` applyNodeStates,
  `viewer3d.js` setStates), through one rule in `@portrayal/kit/states`:
  `boundLamps(svg)` (path -> the bound lamps) and `expandStates(map,
  bindings)`. A seated plug or silkscreen naming the outlet declares no states
  and is left alone, and a port declares none of its own, so no drawing
  already in the library changes. `relief.js` gains `noteLampBindings`,
  `clearLampBindings`, `lampBindings` and `expandedNodeStates`.
- A drawing marks an element a lamp is bound to with `data-lamped="true"`,
  and the base stylesheet dims a power outlet that is `off` and has no lamp
  (opacity 0.55); one with a lamp is never dimmed. No device in the library
  has a switched outlet yet.

### Changed
- `off` in the Explorer is a state that can be lit, not only the absence of
  one: the `off` chip sets `state-off` on an outlet (so a G4 outlet lamp shows
  its declared red, or a lamp-less outlet dims) and on any element that
  declares a colour for `off`, and clears only a lamp or a plain element with
  none, as before. `states.js` `paints` measures a declared `off` rather than
  assuming it. A custom lamp colour is not shown on a lamp that is `off`
  however it came to be off - its own mark, another mark, or its outlet - in
  2D as in 3D.
