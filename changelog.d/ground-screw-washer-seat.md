### Changed
- **`common/ground-screw-washer@1` (1.0.0 to 1.1.0) is a place a ring lug lands.** The chassis grounding screw on its captive
  washer presents the nominal `terminal-stud` interface at the top of its screw head, as the other single ground screws and
  studs of the library do, and claims no screw size, because no document held prints one. Its drawing is unchanged. The ten
  AurCore AIS switches (AIS2001 to AIS2004, AIS4001, each with its P model), the Eaton PDUMH20NET and the Supermicro
  SYS-111E-FDWTR (through its DC supply) each take a patch, with their locks and the `Drawing version` line of their exported
  device types. No exported port moves. Two rows of the port-usable records are closed: this part's, and the Supermicro DC
  supply's, which composes it and now offers the screw as a place a lug lands.
