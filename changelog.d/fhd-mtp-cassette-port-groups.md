### Changed
- The ports on 29 FS FHD MTP-to-LC cassette contracts now join a port group, so a port on a cassette seated
  in an enclosure says what it is for. The cassettes are the 6-adapter cassettes (`fhd-1mtp6lcd-os2-a`, `-om4-a`,
  `-om5-a`, `-os2-af`, `-os2-u` and `-om4-u`), the 24-fibre cassettes with one MTP-24 (`fhd-1mtp24-lc-os2-a`,
  `-om4-a`, `-om5-a`, `-om3-a` and `-os2-af`), the 24-fibre cassettes with two MTP-12 (`fhd-2mtp12-lc-os2-a`,
  `-om4-a`, `-om5-a`, `-om3-a`, `-os2-af`, `-os2-u` and `-om4-u`), the 36-fibre cassettes (`fhd-3mtp18-lc-os2-a` and
  `-om4-a`), and the nine rear faces of those families. Each front declares one `traffic` group of its LC duplex
  adapters and each rear one `traffic` group of its MTP adapters, counted from 1 as the contracts' part ids
  are. The FHD MTP-12/24 Cassettes Datasheet prints no data rate for a passive cassette, so no group states a speed.
  Part ids, positions and drawn geometry are unchanged; each contract takes a minor, and the seven FHD enclosures
  that seat them (`fhd-1ube`, `fhd-1ufce`, `fhd-1ufmt-n`, `fhd-1ufmt-s`, `fhd-1ume`, `fhd-2ufce` and `fhd-4ufce`)
  take a patch. The SC and splice cassettes are not touched. No conformance row is closed or opened.
