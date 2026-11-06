### Changed
- The ports on the fifteen Casa cards that carry any (the SMM 2x10G, 8x10G, 300G and 300Gm, the two
  SMM Switch BDM cards, the CSC 8x10G, the OOB 2+8, the UPS 32x4, the RFD, the RFU 16x8 and the four
  6+12 I/O modules) now join port groups, so a port on a card seated in a bay says what it is for.
  The SMM cards group their 10/100BASE-T management jack (`mgmt`, no speed stated) and RS-232 console
  (`console`) as management, and their SFP, SFP+ and QSFP28 cages by family and rate (`gige` 1G,
  `xgige` 10G, `cgige` 100G, from the C100G Hardware Installation Guide's figures 1-7 to 1-10 and
  3-2). The RF coax cards (UPS 32x4, 6+12 I/O, RFD, RFU 16x8, OOB 2+8) group their MCX and F-type
  ports as `traffic` and state no speed, which no Casa document gives them. Part ids, positions and
  drawn geometry are unchanged; each card takes a minor and the C40G and C100G a patch. This
  finishes the Casa namespace: every Casa card that composes a port part declares groups.
