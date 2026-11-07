### Added
- Arista 7050X4 line (#1204, slice 1): five fixed switches, each with its front and rear panels: the 7050DX4-32S
  (`arista/7050dx4-32s`, 32 400G QSFP-DD and 2 SFP+), the 7050PX4-32S (`arista/7050px4-32s`, 32 400G OSFP and 2 SFP+), the
  7050CX4-24D8 (`arista/7050cx4-24d8`, 24 200G QSFP56, 8 400G QSFP-DD and 2 SFP+), the 7050X4-48Y-4DF
  (`arista/7050x4-48y-4df`, 48 25G SFP25 and 4 400G QSFP-DD) and the 2RU 7050CX4M-48D8 (`arista/7050cx4m-48d8`, 48 100G QSFP28, 8
  400G QSFP-DD and 2 SFP+, with its management ports on the front).
- The 7050DX4M-32S, which shares the DX4-32S's front panel, is a configuration of `arista/7050dx4-32s`
  (DCS-7050DX4M-32S-F). Each device's -F (front-to-rear) and -R (rear-to-front) builds are orderable configurations
  (DCS-7050DX4-32S-F and -R, DCS-7050PX4-32S-F and -R, DCS-7050CX4-24D8-F and -R, DCS-7050X4-48Y-4DF-F and -R,
  DCS-7050CX4M-48D8-F and -R), and a DC build of each is shown as a worked example with no part number.
- The 7050X4 line's new field-replaceable parts, family-prefixed: the supplies PWR-1512-AC-RED and -BLUE
  (`arista/7050x4-pwr-1500-ac`, `-ac-rev`) and PWR-1511-DC-BLUE (`arista/7050x4-pwr-1500-dc-rev`), and the fan module
  FAN-7012H-BLUE (`arista/7050x4-fan-7012h-rev`). The 7050 models also seat the parts the earlier Arista switches already
  carry: `arista/7280r3-pwr-500-*` (PWR-511), `arista/7280r3-pwr-1500-dc` (PWR-1511-DC-RED), `arista/7280r3-fan-m` and
  `-fan-m-rev` (FAN-7011M), `arista/7280cr3-pwr-1000-*` (PWR-1011), `arista/7280cr3-fan` and `-fan-rev` (FAN-7011H) and
  `arista/7280dr3a-fan` (FAN-7012H-RED).
- The DCIM device types for the eleven orderable 7050X4 builds and the module types for the four new parts, in the NetBox and
  Nautobot exports.
