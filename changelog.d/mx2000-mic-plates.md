### Changed
- The MX2000 multirate MICs (`juniper/mic-mrate`, `juniper/mic-macsec-mrate`), the
  vertical MIC blank (`juniper/mx-mic-blank-v`) and the MPC8E and MPC9E carriers
  (`juniper/mx2k-mpc8e-v2k`, `juniper/mx2k-mpc9e-v2k`) take a new major. The MICs are
  drawn at the 168.8 x 29.2 mm MIC plate the horizontal MICs state, where they were the
  27.0 x 168.0 mm window read off the carrier, and say in `size-confidence` that the
  figure is borrowed because these models were not photographed. The carriers' two MIC
  bays are the plate, each centred where its window was; the cards' own outline is
  unchanged and still estimated. The MX2008, MX2010 and MX2020 seat the new majors and
  take a major of their own. Each retired major stays, deprecated, so a manifest that
  names it still resolves. Re-import the three chassis device types and the five module
  types: the drawing versions in their comments move and nothing else in a port,
  interface or bay id does.
