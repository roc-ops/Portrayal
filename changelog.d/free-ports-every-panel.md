### Changed
- `freePorts` and `slotEnds` offer the power, ground and DC ends of the left,
  right, top and bottom panels, as they offered those of the front and the
  rear. A row names its panel in `view` (`left`, `right`, `top` or `bottom`).
  A slot end is offered where the page's `portsOf` reads it on that panel
  (a ground stud, an inlet), and where the catalogue says it is a power end. A
  DC port whose poles are all on one of those panels has that panel as its
  `view` in `dcPortsOf`. A page that reads none of those panels hands in no
  slot end, so only the catalogue's ends are offered. Those panels offer no
  data port and no slot of another kind.
- The front and the rear answer as they did, and their rows keep their order.
  The other panels follow in the order left, right, top, bottom. A device that
  draws a power, ground or DC end on one of those panels gains a row for it,
  and a device whose rows were all on the front and the rear loses nothing and
  renames nothing. A port whose poles are on two panels, and a panel the
  library does not name, are still not offered.
- How a cable lands is unchanged. `cable.add` takes a `view` of `front` or
  `rear` only, so a consumer that offers a row whose `view` is another panel
  cannot lay a cable on it yet. A cable saved on such a DC port is loose, and
  its reason now reads "is on the top of the device, and a cable end can be
  given on the front or rear only" in place of "is not on this panel".
