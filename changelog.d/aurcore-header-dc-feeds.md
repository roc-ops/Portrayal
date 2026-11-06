### Changed
- The five-position power header of the ten AurCore AIS switches (`common/terminal-header-508-5f@2`, 2.0.0 to 2.1.0) states its two
  DC feeds as two DC ports of two poles each, `feed-a` and `feed-b`, on four connection points at the contacts its skin already
  draws, so a feed lands on each pair. The roles are what the housing prints, `+` for `pos` and `-` for `neg`, and the feeds are
  named in the printed order from the end marked `1`; no document says which input the switch treats as its first. The contact
  between the pairs is the earth: it is in neither port and is not a connection point, because it is a pluggable header's contact
  and not a screw a lug lands on. The ports state no voltage, current, wire size or side: the data sheets print a different supply
  range for the models ("DC 12-55 V" and "DC 48-57 V") and no input current or wire size. The skin is not redrawn and the header
  stands where it did on each switch.
- The AIS2001, AIS2001P, AIS2002, AIS2002P, AIS2003, AIS2003P, AIS2004, AIS2004P, AIS4001 and AIS4001P (`aurcore/ais2001` and the
  nine others, 2.0.1 to 2.1.0) each take a minor, because the build now publishes two DC ports for them, with their pinned hashes and the
  drawing version line of their exported device types (20 files in NetBox and Nautobot). No port, interface or id
  moves. Ten rows of the records file are gone and its `cap:` is 135.
