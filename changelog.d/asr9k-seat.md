### Changed
- ASR 9000 route switch processors seat where a Cisco document names the
  chassis (roc-ops/Portrayal#262). `cisco/asr-9006` 3.1.0 takes the
  A9K-RSP-4G, RSP-8G, both RSP440s and both RSP5s in slots 0 and 1;
  `cisco/asr-9010` 1.1.0 adds the RSP-8G, RSP440s and RSP5s to slots 4 and 5;
  `cisco/asr-9904` 3.1.0 adds the RSP440s and RSP5s to slots 1 and 2; and
  `cisco/asr-9906` and `cisco/asr-9910` 1.1.0 add the RSP5s to their outer
  RSP slots. Sources: RSP datasheet c78-500699 Table 3, RSP440 datasheet
  c78-674143 Table 3, the IOS XR 64-Bit datasheet c78-737841 System
  requirements and the RSP5 datasheet c78-741128. Each chassis names its
  sources under `provenance.rsp-chassis-support`. Nothing is renamed or
  removed; the DCIM exports change in their bay descriptions only.
- The 1-port and 2-port 100GE MPAs seat in the modular line cards
  (roc-ops/Portrayal#262). `cisco/a9k-mod400-se@2` and `-tr@2` (2.1.0) take
  both in both bays, from the Ethernet Line Card Installation Guide list for
  the 400G card. `cisco/a9k-mod200-se@2` and `-tr@2` (2.1.0) take the 1-port
  in both bays and the 2-port in bay 0 only, which is what the guide states
  and is how the one-2-port-per-card limit of data sheet c78-735809 holds.
- The `unplaced:` sentence on the twelve ASR 9000 parts still seated by
  nothing now names what blocks each one: no compatibility statement in the
  corpus (four line cards), a double-height SPA, the ASR 9906 rear that has no
  fabric bays, power trays with no tray-level bay, and two parts with no
  document or part number.
