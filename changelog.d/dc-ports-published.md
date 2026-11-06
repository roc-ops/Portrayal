### Added

- **`dc-ports` in the published build** (`docs/dc-power-design.md` section
  5.2). A part that states DC ports in its
  `dc` block now has them on its entry in `components.json`, one per port in the
  order it states them, beside `cages`; and each configuration in a device's
  `<device>.configs.json` carries `configs[].dc-ports`, the ports its parts
  present with each placement's `dc` override applied and the path a feed lands
  on. Each entry holds `id`, `path`, `direction`, `voltage`, `rating-a`, `awg`,
  `side` and `poles` (`role`, `slot`, and `stand-in` where stated), and
  `configs.json` adds `ref`. A port's `path` is always the part's path and the
  port's id (`feed-a/input`), whether the part has one port or several, so a
  port added later moves no other port's path. Both are omitted when there is nothing to
  publish. A part in a bay is in the configurations that seat it, which is why
  the list is per configuration. `docs/format-stability.md` records the shape.
  Neither key raises `contract`, which is still 2.
- **The device fingerprint reads a published DC port as an export fact.** A
  device that gains a port is a minor; one whose port goes, or whose path,
  direction, poles or a pole's role change, is a major. A voltage, rating, awg
  or side stated where there was none is a minor, and one changed or dropped is
  a major. A device that presents no port records nothing new.
- **No library part states a DC port yet**, so no published file, no device
  fingerprint and no export changes with this release.
