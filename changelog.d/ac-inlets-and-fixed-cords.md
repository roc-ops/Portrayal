### Changed
- Two fixed power cords and one supply whose inlet is elsewhere carry an `unmated` sentence that says why nothing lands on
  them: `eaton/tripplite-cord-l5-20p@1` (the input cord of the Eaton Tripp Lite PDUMH20NET) and `fs/fan-cord-5-15p@1` (the mains
  cord of the FS FANP3U3F, FANS1U2F and FANS1U4F) end in a plug of their own, and `casa/c40g-psu-ac@1`, the C40G's front-loaded
  AC supply, has its AC inlet at the other end of the module, which the chassis draws as the rear AC input panel. None presents
  an interface, a slot or a mate. Each part takes a patch, and so do the five devices that compose one (version +0.0.1, its lock
  and the `Drawing version` line of its exported device types, and nothing else in them); the Casa supply's module types carry
  the new contract version.
- Three decor entries that lint L197 read as connectors drawn as panel art are named for what they are: the moulding round the
  C20 inlet that the Eaton PDU12IEC and PDUMV20HVNETLX already place (`inlet-flange` is now `inlet-moulding`) and the strip of
  terminals at the cord end of the FS FANP3U3F's back (`terminal-block` is now `wiring-strip`). Nothing is drawn differently.
  The two Eaton devices take a patch for it, and the three warnings leave the lint baseline.
- Three rows of the port-usable records file are gone and its `cap:` is 194.
