### Added
- `eaton/pdumh20net`, the Eaton Tripp Lite series switched PDU PDUMH20NET: a
  1U horizontal rack PDU with 16 NEMA 5-15/20R outlets, eight on the front and
  eight on the rear, named 1 to 16 as printed, each `fed-by` the fixed L5-20P
  input cord and each with a lamp bound to it by `for:`. Class
  `switched-metered-input`; every outlet declares `[on, off]`. The WEBCARDLX
  network card sits in a bay, the two-digit load meter on the front, and the
  ground screw and the factory DE-9 on the rear. The bolt-on brackets are
  `chassis.ears` with flush (default), recessed and rear positions. No drawing
  exists: every position is read off the two straight-on Eaton photographs,
  with the scale proved on the DE-9's standoffs and the outlet faces.
- Three Eaton parts for it: `eaton/webcardlx@1` (the network card module),
  `eaton/tripplite-ammeter@1` (the two-digit load meter) and
  `eaton/tripplite-cord-l5-20p@1` (the fixed input cord, exported as a
  `nema-l5-20p` power port).

### Changed
- `std/nema-5-20r@1` 1.0.1: its `unplaced:` sentence is gone, since the
  PDUMH20NET now seats sixteen of them. No other device composes it.
