### Added
- `eaton/evmi2130x`, the Eaton Rack PDU G4 metered input EVMI2130X and the first
  rack PDU in the library: a 0U strip mounted `rack-side`, a fixed NEMA L21-30P
  cord, 42 outlets (24 C13, 18 Eaton C39) in six colour-coded sections, three
  20 A two-pole breakers and a hot-swappable network module. Drawn standing,
  cord end down, from Eaton drawing 9001-22301.
- `std/c13-outlet@1`, the IEC C13 outlet face a PDU moulds (a well a C14 shroud
  enters, with the nose standing in it), and its `c13-outlet` entry in the
  standards registry.
- Six Eaton parts: `eaton/c39-outlet@1` (the proprietary C13/C19 combination
  outlet), `eaton/g4-outlet-labels@1` (section colour and outlet numbers are
  fields), `eaton/g4-breaker-20a-2p@1`, `eaton/g4-mounting-button@1`,
  `eaton/g4-cord-l21-30p@1` and the network module `eaton/g4-enmc@1`.
- `eaton` in the vendor registry.
- The DCIM export writes AC power outlets: `iec-60320-c13` and `eaton-c39` join
  `OUTLET_TYPES`, both in NetBox and Nautobot, and the PDU's cord exports as a
  `nema-l21-30p` power port. No outlet states `feed_leg`: every outlet on the
  EVMI2130X is line to line.
- A device's own `interfaces:` rules now name its power outlets as they name its
  interfaces, so the EVMI2130X's outlets export as A1 to C42, as the unit prints
  them. An outlet no rule names keeps its placement id, so no other device's
  export changes.

### Changed
- `common/ground-screw-m6@1` 1.0.1: its description no longer says it is never
  placed alone - the EVMI2130X places one as its M6 bonding screw. The four
  devices that compose it take a patch.
