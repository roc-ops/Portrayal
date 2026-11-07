### Added
- **Rittal DK 7979.175** (`rittal/dk-7979-175`): the three-phase basic PDU, 0U, 1094
  mm long, with a fixed 3 m cord ending in a 16 A CEE plug and 27 outlets in three
  phase groups of nine: six IEC C13, one IEC C19 and two CEE 7/3 earthing-pin
  sockets each. All six faces are stated; the two push-button attachments on the
  back are placed 933.45 mm apart as the maker's drawing dimensions them. The
  device closes no row of the records file.
- **`rittal/cee-7-3-outlet@1`** and **`generic/cee-7-7-plug@1`**: the earthing-pin
  socket and the plug that mates it, with the new interface key `cee-7-3`. Neither
  is dimensioned by a document held, so both are declared estimates. The socket
  exports as an `other` power outlet labelled CEE 7/3.
- **`rittal/pdu-cord-cee-16a@1`** and **`rittal/pdu-mounting-button@1`**: the fixed
  input cord, which exports as an `other` power port labelled as a 16 A CEE plug,
  and the push-button attachment, which mates `pdu-button`.
