### Added
- The key `edgecore-ais800-dc-block-6` for the DC power connector of the Edgecore AIS800-64D and AIS800-64O 3000 W DC supply: a
  grey housing with six round sockets in two rows of three, each with a slotted contact (Edgecore AIS800-64D Quick Start Guide,
  "Connect Power", the figure with its four numbered callouts). The guide and the data sheet name no maker, series, part number or
  pitch, so the key claims none. `edgecore/ais800-64-dc-header@1` presents it and `edgecore/ais800-64-dc-plug@1`, the cable
  connector, mates it; both are declared stand-ins with estimated sizes.
- `generic/screw-terminal-2-plug@1`, a stand-in for the cable plug of the two-pole pluggable DC block, which mates the registered key
  `screw-terminal-2`. `common/dc-terminal-plug-2@1` now presents that key (1.0.0 to 1.1.0), so the block of the ECS4120-28Fv2-I and
  the ECS4530-54CSFP-DC-I is a place a cable lands. Neither document states a pitch, so the key still claims none.

### Changed
- `edgecore/ais800-64-psu-dc@1` (1.0.1 to 1.1.0) composes its connector as the part `dc-header`, standing in the box its skin already
  reserves for it, and its description says six sockets where it said six studs: the guide's figure shows sockets in a housing. The
  roles of the contacts are recorded in its provenance and no DC port is stated. Its exported power port is `{module}/dc-header` of
  type `other` where it was `{module}/Inlet` of type `dc-terminal`.
- `common/dc-terminal-24@1` and `common/dc-terminal-27@1` (each 1.0.1 to 1.1.0), the three-screw terminal blocks of the CSR180 and
  CSR200, state one DC input port whose poles are the screws they already compose: ground on the left screw, the -36 to -72 V feed on
  the middle one and the return on the right, as the Edgecore guides' callouts read. The current is 6 A; the CSR200's guide prints one
  wire size (14 AWG) and the CSR180's prints two, so only the CSR200 port states one; neither port states a voltage, because the
  guides print a range. No skin is edited.
- The eight devices that compose these parts take a version bump with their recorded contents and the drawing version line of their
  exported device types: the CSR180 and CSR200 a minor, the AIS800-64D, AIS800-64O, ECS4120-28Fv2-I, ECS4530-54CSFP-DC-I and the two
  Telco Systems TM-8104 and TM-8106 (which compose the CSR180's terminal block in their supply) a patch. Five rows of the records
  file are gone. The 650 W module `common/psu-dc-650@2` keeps its row: no held document draws its terminal as it is drawn.
