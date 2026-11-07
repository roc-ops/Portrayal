### Changed
- The ports on 15 Cisco ASR 9000 route switch processors and route processors (A9K-RSP, A9K-RSP-8G, A9K-RSP440-SE/-TR,
  A9K-RSP5-SE/-TR, A9K-RSP880-SE/-TR, A9K-RSP880-LT-SE/-TR, A99-RP3-SE/-TR, A99-RSP-SE and ASR-9922-RP-SE/-TR) and on seven
  modular port adapters (A9K-MPA-1X40GE, -2X40GE, -2X10GE, -4X10GE, -8X10GE, -20X10GE and -20X1GE) now join port groups, so a
  port on a card seated in a bay says what it is for. A route processor has a `mgmt` cluster (the two management Ethernet ports
  at 1G, the CMP port, console, auxiliary and USB), a `timing` block (SYNC, IEEE 1588, time-of-day and inter-chassis sync jacks
  and the 10 MHz and 1 PPS inputs) and an `alarm` connector, all role `management`; the 10G SFP+ ports of the RSP-440, RSP-880,
  RSP4-S and RP are their own groups. Each adapter has one `traffic` group stating its cage and rate. A media or speed is stated
  only where the Overview and Reference Guide or the Ethernet Line Card Installation Guide prints it. Part ids, positions and
  drawn geometry are unchanged. The eight chassis that seat these cards (ASR 9001, 9006, 9010, 9904, 9906, 9910, 9912 and 9922)
  take a patch bump, which moves the drawing version line of their exported device types, and the NetBox and Nautobot module
  types of the route processors now mark their management Ethernet ports `mgmt_only`. Two lint entries for the ASR 9922
  route processors' pluggable cages are gone from the baseline.
