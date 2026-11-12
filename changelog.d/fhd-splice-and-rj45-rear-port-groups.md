### Changed
- The ports on three more FS FHD contracts now join a port group, so a port on one of them seated in an enclosure
  says what it is for. They are the LC UPC OS2 12-fibre splice cassette (`fhd-splice-12-lc`), its rear face
  (`fhd-splice-12-lc-rear`) and the rear face of the six-jack RJ45 panel (`fhd-fapm6-rj45-rear`). Each declares one
  `traffic` group (`adapters`, `splices` and `terminations`) that every one of its ports joins, counted from 1. The
  one catalogue row held for the cassette and the multimedia panel datasheet print no data rate, so no group states a
  speed. Part ids, positions and drawn geometry are unchanged; each contract takes a minor, and the seven FHD
  enclosures that seat them (`fhd-1ube`, `fhd-1ufce`, `fhd-1ufmt-n`, `fhd-1ufmt-s`, `fhd-1ume`, `fhd-2ufce` and
  `fhd-4ufce`) take a patch. No conformance row is closed or opened.
