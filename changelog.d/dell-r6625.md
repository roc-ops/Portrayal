### Added
- Dell PowerEdge R6625 (`dell/r6625`, draft, part of #40), the 1U two-socket AMD EPYC rack server, modelled
  from Dell's own Installation and Service Manual, Technical Guide and Spec Sheet. Six fronts as variant
  views - 10 x 2.5 inch, 8 x 2.5 inch with the Smart Flow vent, 4 x 3.5 inch, no backplane, and 14 and
  16 x EDSFF E3.S - and the rear for riser configurations 1 to 4 and 7 of the ISM's table 101 with every
  front, plus configurations 5 (R3P, two rear 2.5 inch drives) and 6 (R2S + R3S, two rear E3.S drives) with
  the 4 x 3.5 inch and 10 x 2.5 inch fronts the ISM pairs them with: 34 orderable builds, each exporting as
  a DCIM device type of its distinct chassis, and a populated example. The top view carries the system
  board, two heatsinks, 24 DDR5 sockets named from the memory label, the fans, the air shroud and the covers,
  with the seated supplies, risers, OCP card, LOM, rear I/O board and boot module projecting into it.
  Configuration 0 (no riser), the paddle-card configurations 8 to 10 and Direct Liquid Cooling are left out
  and recorded as gaps. It seats the 16th-generation parts the R660 introduced and adds three of its own,
  `dell/r6625-system-board`, `dell/r6625-heatsink` (the AMD SP5 heatsink, not the R660's) and
  `dell/r6625-air-shroud`.
