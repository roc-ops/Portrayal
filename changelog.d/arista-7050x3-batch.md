### Added
- Arista, four 7050X3 fixed switches (`arista/7050cx3-32s`, `arista/7050sx3-48yc12`, `arista/7050sx3-48yc8` and
  `arista/7050tx3-48c8`, #1204, slice 1): the 7050CX3-32S with 32 x 100G QSFP and 2 x SFP+ and its management ports at
  the front, the 7050SX3-48YC12 with 48 x 25G SFP and 12 x 100G QSFP in three rows of cages, the 7050SX3-48YC8 with
  48 x 25G SFP and 8 x 100G QSFP, and the 7050TX3-48C8 with 48 x 1/2.5/5/10GBASE-T RJ-45 and 8 x 100G QSFP. Each has two
  hot-swap supplies and the fan modules its data sheet gives (four for the CX3-32S and SX3-48YC12, two for the other
  two). The guide draws four generic rear panels and does not say which model uses which, so each rear is mapped by fan
  count and management port position, and every position is estimated to about 1 mm. The guide's and the data sheet's
  power figures disagree for the CX3-32S and SX3-48YC8, and its weights for the CX3-32S; the guide's are modelled and the
  data sheet's are recorded as gaps.
- Three new components for the CX3-32S and SX3-48YC12: `arista/7050x3-pwr-500-ac` (PWR-500AC-F),
  `arista/7050x3-pwr-500-dc` (PWR-500-DC-F) and `arista/7050x3-fan-7000h` (FAN-7000H-F). The SX3-48YC8 and TX3-48C8 seat
  the PWR-511 supplies and FAN-7011M fan modules the 7280SR3-48YC8 already seats, so no component is added for them. The
  rear-to-front PWR-500 and FAN-7000H parts are not modelled.
- The DCIM device types for the four devices, in the NetBox and Nautobot exports.
