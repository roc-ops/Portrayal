### Changed
- The power inlets of three Cisco Nexus 9500 supplies are composed from the library's inlet parts, where each drew a box of its own:
  `cisco/n9k-pac-3000w-b@1` (1.0.0 to 1.1.0, the 3 kW AC supply) composes `std/c20-inlet@1` as the part `inlet`;
  `cisco/n9k-puv-3000w-b@1` (1.0.0 to 1.1.0, the 3 kW universal AC/DC supply) composes `std/saf-d-grid@1` as the part `inlet`; and
  `cisco/n9k-puv2-3000w-b@1` (1.0.0 to 1.1.0, the 3.15 kW dual input supply) composes `std/saf-d-grid@1` twice, as `inlet-1` and
  `inlet-2`. Each inlet is now a published connector, so a power cord lands on it: the C19 cord on the first supply, the Saf-D-Grid
  cord on the other two. The place and the turn of every inlet are estimates read off the vendor's figures and each contract says so;
  the dual input supply's vent is 2.4 mm shorter than the other two supplies' so that its two receptacles stand clear of it, and the
  two Saf-D-Grid supplies no longer declare `inlet: other`, which a composed part makes the weaker of two statements. The three
  chassis that seat them (`cisco/n9k-c9504`, 2.1.0 to 2.1.1; `cisco/n9k-c9508`, 1.1.0 to 1.1.1; `cisco/n9k-c9516`, 2.1.0 to 2.1.1)
  take a patch each, because the lock compares only a device's own port names, with their locks and the drawing version line of their
  exported device types (six files, in NetBox and Nautobot). Three rows of the records file are gone and its `cap:` is 169.
- **BREAKING for DCIM data already imported.** A part's id is lower case, so the power ports that those supplies' module types export
  change, in the NetBox and Nautobot files of `N9K-PAC-3000W-B`, `N9K-PUV-3000W-B` and `N9K-PUV2-3000W-B` (six files). The first
  supply's one port is named `{module}/inlet` where it was `{module}/Inlet`, and its type, `iec-60320-c20`, is the same. The second's
  one port is named `{module}/inlet` where it was `{module}/Inlet`, and its type is `saf-d-grid` where it was `other`. The third's one
  port, `{module}/Inlet` of type `other`, becomes two, `{module}/inlet-1` and `{module}/inlet-2`, each of type `saf-d-grid`, one for
  each of the supply's two input lines. A DCIM that already imported the old files keeps the old port under its old name and type until
  the type is imported again, and anything that looks a port up by the old name has to look for the new ones. The comment of each file
  names the new contract version, and nothing else in them moves.
