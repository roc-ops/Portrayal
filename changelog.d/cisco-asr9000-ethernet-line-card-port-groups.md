### Changed
- The ports on 25 Cisco ASR 9000 high-rate Ethernet line card contracts now join a port group, so a port
  on a card seated in a chassis slot says what it is for. The cards are the 100G cards (`a9k-4x100ge`,
  `a9k-16x100ge-se` and `-tr`, `a9k-8x100ge-x-se` and `-tr`, `a99-12x100ge`, `a99-32x100ge-se`, `-tr`,
  `-x-se` and `-x-tr`), the 400G card (`a99-10x400ge-x-se` and `-tr`), the 5th generation multi-rate
  cards (`a9k-20hg-flex`, `a9k-8hg-flex`, `a9k-4hg-flex` and `a99-4hg-flex`, each `-se` and `-tr`), the
  2-port 100G and 20-port 10G IPoDWDM card (`a9k-400g-dwdm-tr`) and the ASR 9903 port expansion cards
  (`a9903-20hg-pec` and `a9903-8hg-pec`, both versions). Each card declares one group for each kind of
  cage it composes, `traffic`, numbered from 0 as the Ethernet Line Card Installation Guide numbers its
  ports. A group states its cage as `media`, and a `speed` only where the card's ports share one rate
  the guide or data sheet prints: the highest rate of the cage, so a QSFP28 group says 100 Gb and a
  QSFP-DD group 400 Gb. The 800G port expansion card states no speed, because its 25 Gb and 10 Gb cages
  are not told apart in any held page. Part ids, positions and drawn geometry are unchanged; each card
  takes a minor, and the eight chassis that seat them (the ASR 9006, 9010, 9903, 9904, 9906, 9910, 9912
  and 9922) take a patch. No conformance row is closed or opened.
