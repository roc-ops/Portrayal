### Changed
- `juniper/dpc-r-4xge-xfp@3`: the four XFP ports sit on the 76.1 mm pitch the
  MX240 and MX480 photographs agree on (card x 105.55 to 333.8, y 18.85), with
  each port's TUNNEL and LINK lamps side by side to its left and its legends
  printed upward, as photographed; 2.x had them on a 53.4 pitch from x 95.5
  (#891).
- `juniper/scb-mx@3`: the Routing Engine bay is 271.9 wide, to the right end
  both photographs put the RE plate at (it stopped 9.5 mm short), and the SCB's
  two panel screws are where the photographs show them (#891).
  `juniper/re-s-1300@2` and `juniper/re-s-2000@2` take the same width and draw
  the plate's right captive screw.
- `juniper/dpce-r-40ge-sfp@2` 2.1.0: the card's own OK/FAIL lamp under its
  legend, with states ok, fail and absent from the module reference (#891,
  #899).
- `juniper/mx240` 5.0.0, `juniper/mx480` 6.0.0, `juniper/mx960` 4.0.0: their
  slots accept the new majors. Ports keep their ids.

### Removed
- `juniper/dpc-r-4xge-xfp@2`, replaced by `juniper/dpc-r-4xge-xfp@3`;
  `juniper/scb-mx@2`, replaced by `juniper/scb-mx@3`; `juniper/re-s-1300@1` and
  `juniper/re-s-2000@1`, replaced by `juniper/re-s-1300@2` and
  `juniper/re-s-2000@2` (#891). Nothing in the library seats them any more, so
  per #448 the superseded majors are removed rather than kept; a manifest that
  pins one moves to its replacement.
