### Changed
- The ports on six Dell OCP NIC 3.0 cards (the 2 x 100 GbE QSFP56, the 2 x 25 GbE and 4 x 25 GbE SFP28, and the
  2 x 10 GbE, 4 x 10 GbE and 4 x 1 GbE RJ45 cards) now join one port group per card, so a port on a card seated in a
  PowerEdge says what it is for. All 18 port parts are `traffic`, numbered from 1 as the part ids number them. Each group
  states its cage as `qsfp56`, `sfp28` or `rj45` and its speed as `100g`, `25g`, `10g` or `1g`, from the port type, port
  speed and port count that Dell's PowerEdge technical guides list for each card in their table of supported OCP cards.
  Part ids, positions and drawn geometry are unchanged; each card takes a minor, and the six servers that seat one
  (R660, R660xs, R6615, R6625, R760 and R960) take a patch. The four-port network daughter card of the R740xd is not part
  of this change. This closes no record row.
