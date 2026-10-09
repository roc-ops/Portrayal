### Added
- `eaton/pdumv20hvnetlx`, the Eaton Tripp Lite series switched PDU
  PDUMV20HVNETLX and the library's first switched rack PDU: a 0U strip mounted
  `rack-side`, a C20 inlet on the face (the detachable L6-20P cord is not
  drawn), 24 outlets (20 C13, 4 C19) in two load banks of twelve named 1 to 24
  as printed, a lamp bound to each outlet with `for:`, a two-digit load meter,
  the LX Platform interface (10/100 Ethernet, an RJ45 console, USB-A) and two
  toolless mounting buttons that publish `mount-points` 1556 apart. Class
  `switched-metered-branch`; every outlet declares `[on, off]`. Drawn standing,
  from the Tripp Lite submittal drawing 17-08-067. The two bank breakers are
  not placed: no held source shows where they are (a `breaker-positions` gap).
- Three Eaton parts for the Tripp Lite series: `eaton/tripplite-led@1` (the
  round lamp window beside each outlet), `eaton/tripplite-mounting-button@1`
  (mates `pdu-button`) and `eaton/tripplite-load-meter@1` (two seven-segment
  digits and the Select / Rotate button).

### Changed
- `std/c19-outlet@1` 1.0.1: its `unplaced:` sentence is gone, since the
  PDUMV20HVNETLX now seats four of them. No other device composes it.
