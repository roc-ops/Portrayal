### Changed
- The ports on 17 Cisco ASR 9000 Gigabit, 10 Gigabit and dual-rate Ethernet line card contracts now join a
  port group, so a port on a card seated in a chassis slot says what it is for. The cards are the 40-port
  Gigabit cards (`a9k-40ge-b`, `-e` and `-l`), the dual-rate 24-port and 48-port cards
  (`a9k-24x10ge-1g-se` and `a9k-48x10ge-1g-se`), the 10 Gigabit SFP+ cards (`a9k-24x10ge-se`,
  `a9k-36x10ge-se` and `a9k-16t-8-b`) and the 10 Gigabit XFP cards (`a9k-4t`, `a9k-8t` and `a9k-8t-4`, each
  `-b`, `-e` and `-l`). Each card declares one `traffic` group, numbered from 0 as the Ethernet Line Card
  Installation Guide numbers its ports. A group states its cage as `media` and the rate the guide prints
  for it as `speed`; the two dual-rate cards also list both rates they take, 1 Gb and 10 Gb, and state the
  higher. Part ids, positions and drawn geometry are unchanged; each card takes a minor, and the seven
  chassis that seat them (the ASR 9006, 9010, 9904, 9906, 9910, 9912 and 9922) take a patch. The
  CPAK cards and the CFP2 cages of the IPoDWDM card are drawn openings and are not touched. No
  conformance row is closed or opened.
