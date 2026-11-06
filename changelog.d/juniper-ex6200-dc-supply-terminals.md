### Added
- `common/hex-nut-stud@1` and `common/hex-nut-stud-pair-5-8@1`: a terminal stud drawn as a hex nut on a round washer, and a
  pair of them on the registered 5/8 in. pitch that one two-hole lug lands across. Every size is estimated off Figure 23 of the
  EX6210 Switch Hardware Guide.

### Changed
- `juniper/ex6200-pwr-dc2100@1` (1.0.0 to 1.1.0), the 2100 W DC supply of the EX6210, composes its two terminal columns as
  `common/hex-nut-stud-pair-5-8@1`, so each is a seat a two-hole lug lands across, drawn as Figure 23 of the EX6210 Switch
  Hardware Guide draws the terminals: hex nuts on studs with washers. It states one DC input port, `input`, with the roles
  `pos` (left) and `neg` (right) that the figure labels Positive and Negative input terminal. Its skin gains the bracket the
  figure draws beside the left pair. The guide names the lug of the DC input as a Panduit LCD4-14A-L, and Panduit's catalog
  "Power and Grounding Infrastructure Solutions" prints its stud hole spacing as 0.63 in., the catalog's rounding of 0.625 in.,
  the registered 5/8 in. pair. The port states no voltage (the guide's nominal is a range), no current (a pair) and no wire
  size (none is printed).
- The EX6210 (`juniper/ex6210` 0.1.1 to 0.2.1) takes a minor and a patch. The build now publishes the DC port of the supply.
- One conformance record goes: `juniper/ex6200-pwr-dc2100@1`, and the cap falls to 41. The records of
  `juniper/ex8200-pwr-dc2kr@1` and `juniper/ex8200-pwr-dc3kr@1` stay: no document held prints the spacing of their lug.
