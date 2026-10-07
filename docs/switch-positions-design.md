# Switch positions: a field that moves what it sets

Status: built, 2026-10-07 (#872, with the follow-ups of #874). Issue #808. Builds on fields
([`library/components/README.md`](../library/components/README.md), "Skins") and on
`kit/fields.js`, which paints a field in 2D and 3D.

## 1. What exists, and what is missing

A switch has positions. Nothing in a contract can say which one it is in, so every switch
in the library is drawn in one position, fixed in its skin.

| part | drawn as | what cannot be said |
|---|---|---|
| `common/dip-switch-2@1` | both sliders at the OFF end | that Fast Ring or SCP is on |
| `common/rocker-switch@1` | I side down | that the supply is off |
| `common/power-switch-slide@1` | one end | the other end |
| a plug-in breaker's handle | one position | on, off or tripped |
| an eight-way alarm DIP on a breaker panel | all eight up | that a fitted position's alarm is enabled |

The last row is the case that makes a drawing wrong and not merely silent: a panel's guide
requires the switch of every fitted position down and every empty one up, so a
configuration that fits breakers and cannot move the switches shows a panel set up
incorrectly.

Two mechanisms are near and neither fits.

- **`states`** are a lamp vocabulary. A state changes how an element is painted and never
  where it is, and everything that reads `data-states` treats its bearer as an indicator.
  `common/power-switch-slide@1` records the consequence: an `on`/`off` element on a switch
  reads as a lamp the hardware does not have, which L47 exists to catch.
- **`fields`** set a node's text, its fill, its stroke and a circle's radius. A position is
  none of those.

## 2. Decisions

1. **A position is a field.** It is a `choice` field on the component, like a supply's
   wattage or a breaker's rating. It is set where every field is set: a placement's
   `attrs`, a configuration's `bay-attrs` and `component-attrs`, the kit's `setFields`, the
   explorer's field editor and the `fields=` location string. No second vocabulary, no
   second setter.
2. **A field gains two effects on a skin node: MOVE and SHOW.** They are the two things a
   position does to a drawing - an actuator travels, and a flag or a legend appears - and
   between them they cover every row of the table above.
3. **The table of moves is in the skin, on the node that moves.** It is geometry, and a
   skin is where geometry is. The contract declares the field and its options; the skin
   says what each option does to each node.
4. **The default option is what the skin draws.** A skin stays a valid drawing on its own,
   as it does for every other field: with the field unset, nothing moves and the node
   shown is the one drawn visible.
5. **What a position MEANS is stated by the thing that places the part,** as a lamp's
   meaning is. Switch 3 of side A enables the alarm for breaker position A3; the DIP part
   knows only that it has eight switches with two positions each.
6. **In 3D a position change re-shapes.** A colour field repaints a texture and leaves the
   relief alone. A moved actuator stands somewhere else, so the part's relief is rebuilt.

## 3. The contract

Nothing new. A position is a `choice` field:

```yaml
# library/components/common/dip-switch-2/v1/contract.yaml
fields:
  sw-1: {label: Switch 1, type: choice, options: ['off', 'on'], default: 'off'}
  sw-2: {label: Switch 2, type: choice, options: ['off', 'on'], default: 'off'}
```

`default` is the option the skin draws. Lint checks that it is one of `options`, which it
already does for every choice field.

## 4. The skin

Two attribute pairs, each naming a field and saying what its values do to this node.

```svg
<!-- MOVE: the slider is drawn at the OFF end; `on` carries it 3.4 up its slot -->
<rect id="slider-1" x="1.1" y="6.0" width="2.0" height="2.8"
      data-move-from="sw-1" data-move="on: 0 -3.4"/>

<!-- SHOW: a breaker's flag is green when on, red when off or tripped -->
<rect id="flag-on"  ... data-show-from="state" data-show="on"/>
<rect id="flag-off" ... data-show-from="state" data-show="off tripped" display="none"/>
```

- **`data-move-from="<key>"` with `data-move="<option>: dx dy[, <option>: dx dy]"`.** The
  node is translated by `dx dy` millimetres, in the skin's own frame, when the field holds
  that option. An option not listed moves it nowhere, which is how the default says
  nothing. A node may also turn: `<option>: dx dy r` rotates it `r` degrees about its own
  centre, for a rocker and for a toggle handle.
- **`data-show-from="<key>"` with `data-show="<option> <option>"`.** The node is displayed
  when the field holds one of the listed options and hidden otherwise. The skin draws the
  default: a node that the default shows is drawn visible, and one it hides carries
  `display="none"`.

A node carries at most one of each. One field may drive several nodes - a breaker's
`state` moves its handle and shows one of two flags.

**Elements follow.** An `elements:` entry gives a node's box in the default position, as
it does now. Where a position moves a node that is an element, the compiled drawing's
`data-at` for it is the moved box, so a hit test and a halo land on the actuator where it
is drawn.

## 5. The build and the kit

One rule, written twice, as the stroke shade and the radius are.

| where | what it does |
|---|---|
| `render.py` `fill_from_attrs` | applies MOVE as a `transform="translate(...) rotate(...)"` on the node and SHOW as the presence or absence of `display="none"`, from the instance's merged attrs |
| `kit/fields.js` `paintFields` | the same, at runtime, remembering the drawn `transform` and `display` the first time, as it remembers a drawn fill; `unpaintFields` puts them back |

An option the field does not declare is not a position: the build fails on it in a
configuration, and the kit's `fieldAccepts` refuses it from a form or a link.

`paintFields` today un-hides a `data-from` text node whenever it writes a value to it. A
node under `data-show-from` is shown or hidden by that field alone, and writing its text
does not change that.

## 6. 3D

`viewer3d.js` `setFields` repaints the textures of the faces a changed part is on. A
position needs more: the relief of a moved node is built from the node's box.

- The build writes each relief node's position from the node as moved, so a scene built
  from a configuration that sets a position is already right.
- At runtime, a field that carries `data-move-from` or `data-show-from` on a node with
  relief marks its part as needing a rebuild, and the viewer rebuilds the scene the way it
  rebuilds one after a configuration switch (there is no per-part rebuild). A field with
  neither effect keeps today's path: repaint, no rebuild.
- A node a position hides is removed before the face is measured, as a pulled part is. So
  that a part whose only SHOW node starts hidden still rebuilds when that node should
  appear, each part group first records the position fields its nodes use, as
  `data-position-fields`, and the viewer reads that mark as well as the nodes (#874).

## 7. Lint

- **L73** (a field prints somewhere) accepts `data-move-from` and `data-show-from` as the
  node a field is kept by.
- **New: every option of a moving or showing field is answered.** For a `data-move-from`
  node, each key in `data-move` is one of the field's options. For a field with any
  `data-show-from` node, each option shows at least one node, or the field lists it in
  `drawn-by-absence` - a breaker that is simply on, with no flag (L148).
- **New: a moved node stays inside its part.** The box of a node under each of its moves
  lies within the component's `size`, so an actuator cannot be configured off its own
  face.
- **L47** is unchanged. A switch declares no `states`, so it draws no lamp.
- **L19** (an indicator declares `for:`) is unchanged; a switch is not an indicator.

## 8. What a position means

A component's field says `sw-3: off | on`. What switch 3 does is a fact of the device.
The device says it on the placement, beside the lamp meanings it already states:

```yaml
- id: dip-a
  ref: amphenol-ns/alarm-dip-8@1
  positions:
    sw-3: {on: alarm enabled for breaker position A3, 'off': alarm silenced}
```

`positions:` is documentation carried into the drawing as data, as `states:` meanings
are. It sets nothing; the value is set by `attrs`.

## 9. First users, in order

1. `common/dip-switch-2@1`: `sw-1`, `sw-2`. Its ten placements are unchanged, because the
   default is the position drawn today.
2. The eight-way alarm DIP of the 300CB08, with its `populated` and `with-fuses`
   configurations setting the switches of their fitted positions down.
3. The plug-in breaker's `state`: `on`, `off`, `tripped`, moving the handle and showing a
   flag.
4. `common/rocker-switch@1` and `common/power-switch-slide@1`.

Each is a contract minor: a field is added and nothing that exists moves.

## 10. Open questions

- **Two flags or one painted flag.** A breaker's red and green could be one node whose
  fill follows the field, if a choice field's option could name a colour. SHOW with two
  nodes is used here because it needs no mapping from an option to a colour.
- **A position that depends on what is seated.** The alarm switch of a position should be
  down when that position holds a breaker. This note leaves that to the configuration,
  which states both. Deriving one from the other would be the first rule that sets a field
  from the contents of a bay.
- **Momentary controls.** A reset button has a pressed position nobody configures. Not in
  scope.
