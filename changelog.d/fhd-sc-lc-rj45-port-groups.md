### Changed
- The ports on six more FS FHD contracts now join a port group, so a port on one of them seated in an enclosure
  says what it is for. They are the MTP-12 to six SC duplex cassette (`fhd-1mtp12-sc-os2-a`) and its rear face
  (`fhd-1mtp12-sc-rear`), the 12-adapter OM5 LC duplex adapter panel (`fhd-fap12lcd-om5`) and its rear face
  (`fhd-fap12lcd-om5-rear`), the six-jack RJ45 panel (`fhd-fapm6-rj45`) and the Cat6 keystone jack
  (`keystone-rj45-cat6`). Each declares one `traffic` group (`adapters`, or `jacks` and `jack`) that every one of
  its ports joins, counted from 1. FS's cassette, panel and multimedia panel datasheets and cabling guide print no
  data rate for a passive adapter or a Cat6 jack, so no group states a speed. Part ids, positions and drawn
  geometry are unchanged; each contract takes a minor, and the seven FHD enclosures that seat them (`fhd-1ube`,
  `fhd-1ufce`, `fhd-1ufmt-n`, `fhd-1ufmt-s`, `fhd-1ume`, `fhd-2ufce` and `fhd-4ufce`) take a patch. The splice
  cassette and its rear face, and the rear face of the RJ45 panel, are not touched. No conformance row is closed
  or opened.
