### Added
- Six connector keys in `spec/schemas/connectors.yaml`, presented by no part yet, so no slot is published and no device changes: `flexstack` (the Catalyst 2960-S FlexStack module's stack port), `stackwise-480` and `stackpower` (the Catalyst 9300 stack and power-stack connectors), `ex4200-vcp` (the EX4200 Virtual Chassis port), `cisco-rps2300` (the 2960-S RPS connector) and `ex3300-rps` (the EX3300 RPS port). Each is the vendor's own connector and cites no standard; each note says what the held guides show and what they leave open, which is why the EX2200's RPS port and the Catalyst 9300X's StackWise-1T and StackPower+ connectors have no key of their own yet.
- The entry keys `turns` and `unmated` are documented in the header of `spec/schemas/connectors.yaml`, and `unmated`, a map from a rate to a sentence, in the header of `spec/schemas/pluggables.yaml`. Nothing reads `unmated` yet.

### Fixed
- The `mini-usb-b` note said that no part presents the interface; `std/mini-usb@1`, the console of the Catalyst 9300 and 3650, does. The registry test now also lists `mini-usb-b` among the interfaces a published connector slot may have.
