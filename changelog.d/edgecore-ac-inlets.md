### Changed
- The IEC C14 inlet of three Edgecore AC supplies is composed from `std/c14-inlet@1` as the part `inlet`, where each drew a box of its own:
  `edgecore/amx-3200-ac-psu@1` (1.0.0 to 1.1.0, the supply of the AMX3200), `edgecore/cor550-psu-ac@1` (1.0.1 to 1.1.0, the COR550's) and
  `edgecore/dcs500-psu-ac@1` (1.0.1 to 1.1.0, the DCS500's). Each supply now publishes one connector, `inlet`, that presents `iec-c14`
  and takes the C13 plug, so a power cord lands on it. The place and the turn of each inlet are estimates read off the vendor's figures
  and each contract says so; the COR550's inlet stands behind its skin, whose body is cut away where it stands, so the red release latch
  still hangs in front of it as the vendor's elevations draw it. The AMX3200's inlet has its lone blade, the earth contact, at the right
  where the drawing it replaces put it at the left. The three devices (`edgecore/amx3200`, 1.0.8 to 1.0.9; `edgecore/cor550`, 3.2.0 to 3.2.1;
  `edgecore/dcs500`, 4.2.0 to 4.2.1) take a patch each, because the lock compares only a device's own port names, with their locks and
  the drawing version line of their exported device types (40 files in NetBox and Nautobot). Three rows of the records file are gone and
  its `cap:` is 160.
- **BREAKING for DCIM data already imported.** A part's id is lower case, so the one power port that each of those supplies' module types
  exports is named `{module}/inlet`, where it was `{module}/Inlet`: in the NetBox and Nautobot module types of the AMX3200 supply
  (`AMX-3200-AC-PSU`), the COR550 supply (`cor550-psu-ac`) and the DCS500 supply (`dcs500-psu-ac`), six files. Its type, `iec-60320-c14`,
  is the same. A DCIM that already imported the old files keeps the port under its old name until the type is imported again, and anything
  that looks the port up by the old name has to look for the new one. The comment of each file names the new contract version, and
  nothing else in them moves.
