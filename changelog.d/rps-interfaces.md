### Added
- `cisco/rps2300-connector@1`, the RPS connector of a Catalyst 2960-S that takes a Cisco RPS 2300: it presents `cisco-rps2300`, with a mate point at the centre of its shroud. It is drawn from the Catalyst 2960-S Switch Hardware Installation Guide (Figures 1-10 and 1-12) and the community NetBox rear elevation of the WS-C2960S-48LPD-L, the plate and shroud read at 3.41 px per mm and the depth estimated. The cover of Figure 1-15 is not modelled. No device places it yet; the Catalyst 2960-S rear in #1322 will.
- `juniper/ex3300-rps-plug@1` and `cisco/rps2300-plug@1`, the cable ends that mate `ex3300-rps` and `cisco-rps2300`. No drawing of either plug is held, so each is drawn estimated from the opening it enters, and its provenance names the drawing it wants.
- `juniper/ex2200-rps-port@1`, the RPS port of the EX2200, as a placed part. It presents no interface: the EX2200 guide names no connector type and `ex3300-rps` covers the EX3300 only, so nothing mates it yet. Each EX2200 declares an `rps-port-connector` gap for what is missing.

### Changed
- `juniper/ex3300-rps-port@1` is 1.1.0: it presents `ex3300-rps` and has a `mate` point at the centre of its opening. Its size, opening, class and behaviour are unchanged, and it now publishes a connector slot that takes `juniper/ex3300-rps-plug@1`.
- The EX2200's RPS plate and opening, drawn as panel art, are now the `rps` placement of `juniper/ex2200-rps-port@1` in the EX2200-24P, -24T (both rears), -48P and -48T, in the `mgmt` group after the console port. The four plate screws stay placed as they were.
- The EX2200-24P, -24T, -48P and -48T are 0.2.0, and the EX3300-24P, -24T, -48P and -48T are 0.1.1, as `devicelock.py` asked.
