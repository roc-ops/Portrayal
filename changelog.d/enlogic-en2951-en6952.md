### Added
- **Enlogic EN2951** (`enlogic/en2951`) and **Enlogic EN6952** (`enlogic/en6952`): the input-metered and the outlet-metered
  Advantage Series three-phase PDUs, 0U, 1826 and 1780 mm long, each with a fixed 1.8 m cord (a CS8365 plug on the EN2951, an
  IEC 60309 3P+E 9h plug on the EN6952) and 42 switched outlets in six colour-coded banks (21 C13/C15 and 21 C13/C15/C19
  combination outlets), every bank behind its own 20 A double-pole breaker, with the hot-swap network module drawn between banks
  three and four: two Ethernet ports, a USB-C port and a reset pinhole are placed, the display and the two sensor ports are
  drawn. All six faces are stated; the two toolless buttons on the back are placed 1555 mm apart as the maker's drawing dimensions
  them. The devices close no row of the records file.
- **`enlogic/combo-outlet-c13-c15@1`**, **`enlogic/combo-outlet-c13-c15-c19@1`**, **`enlogic/en-breaker-20a-2p@1`**,
  **`enlogic/pdu-cord-cs8365@1`** and **`enlogic/pdu-cord-60309-3pe-9h@1`**: the two combination outlets (they present `iec-c13`
  and the new `enlogic-combo`), the bank breaker (the plate colour and legends are fields), and the two fixed input cords (a `cs8365c` power
  port and an `other` one labelled as an IEC 60309 plug). The wells' and the plates' figures are read from the maker's drawings;
  the glands' end-on shape and size, the wells' contours and the plate colours are estimates, declared in each contract.
- **`enlogic-combo`**, a connector key for the Enlogic C13/C15/C19 combination outlet, which `generic/c14-plug` and `generic/c20-plug`
  now mate (each one minor up, 1.6.0).
