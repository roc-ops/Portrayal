### Added
- Seven connector keys in `connectors.yaml`, each naming the header or connector on the device and never the plug: `wire-wrap-3`, `screw-terminal-5`, `screw-terminal-2`, `terminal-381-5`, `terminal-350-6`, `screw-terminal-4` and `orv3-busbar`. A key whose pitch no document states claims none. No part presents any of them, so no slot is published.
- The family file of the part-conformance runner lists the stack, StackPower, Virtual Chassis and redundant-power keys, `rj45` and the seven new keys, so `--by-family` places a cause on a part presenting one in its family.

### Fixed
- `--by-family` no longer puts the two bus-bar parts in "USB" (the word "busbar" contains "usb"): a name with `busbar` or `bus-bar` gives the DC family before `usb` is tried.
- `--by-family` no longer puts a DC supply in "power inlets (AC)" when its `attrs` carry `role: dc-power-supply` or `dc` is a hyphen-delimited word of its name. An HVDC supply on its AC inlet stays in the AC family.
- The C21 text in the runner says what the check finds: a connector or cage slot with no mate in its `accepts` and no sentence saying none can exist.
- `docs/part-conformance-design.md` section 10.5 states the family rules as they are, and `docs/dc-power-design.md` says why the port-usable checks name no cause on `nokia/lpwr-f@1`.
