### Added
- A rack PDU states its capability as two facts, `attrs.management.metering-scope`
  (`none`, `input`, `branch`, `outlet`) and `outlet-switching`, and the class is
  derived from them and published as `pdu-class` in `<device>.configs.json` and
  `devices.json`: `basic`, `switched`, `metered-input`, `switched-metered-input`,
  `metered-branch`, `switched-metered-branch`, `metered-outlet` or `managed`
  (#934, docs/pdu-model-design.md). Lint L166 states the two together and ties
  the outlet `[on, off]` states to `outlet-switching`.
- Structured input keys in `attrs.power`: `input-cord`, `input-phase`,
  `input-wiring`, `input-voltage-v`, `input-current-a`, `plug-rating-a` and
  `capacity-kw`; `input-plug` is now the `PART_POWER` slug of the input (L167),
  and a PDU states its voltage in `input-ac` rather than `input-voltage` (L168
  warns on both). The DCIM export writes the rating on the input power port's
  description and in the comments, beside the derived class.
- A placement key `lines` (`L1`, `L2`, `L3`, `N`) on a breaker, or on an outlet
  with no breaker, and `through` may now name a fixed breaker placement as well
  as a bay (L133 widened, L135 reads bays only, L169 new). An outlet's export
  description names its breaker and lines, and `feed_leg` is written only for a
  line-to-neutral outlet on a three-phase wye input.
- `pdu-button`, the rack PDU mounting interface, in the connectors registry, and
  `configs[].mount-points` in `<device>.configs.json`: each mount point a
  configuration draws, `{mates, at}`, derived from the button placements.
- A lab's rack-side `side` takes the kit's attachment points: `left-front`,
  `left-rear`, `right-front` and `right-rear` beside `left` and `right`. L154
  checks overlap per point and refuses a side that mixes `left` with a four-post
  name; `labs.json` publishes the point as written. A rack-face `side` stays
  `left` or `right` (L153).

### Changed
- `eaton/evmi2130x` 0.2.0: `metering-scope: branch` and `outlet-switching:
  false` (class `metered-branch`), the structured input keys with `input-plug:
  nema-l21-30p` and its voltage prose moved into `input-ac`, `lines` on its three
  breakers (A L1-L2, B L2-L3, C L3-L1) and `through` on its 42 outlets. Its
  exported outlets now say which breaker and lines they are on, and its input
  power port carries the rating. No outlet states `feed_leg`: every one is line
  to line.
- `eaton/g4-mounting-button@1` 1.1.0: `mates: pdu-button` and a `mate` point on
  its axis.
