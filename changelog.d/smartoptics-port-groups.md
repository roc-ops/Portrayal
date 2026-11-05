### Changed
- The ports on Smartoptics' DCP-404, DCP-F-A22 and eight passive plug-in modules (PPM-AD1-1510,
  PPM-AD1-1625, PPM-DCM10/20/40/80, PPM-OCU-50-50, PPM-OCU-97-3) now join port groups, so a port on a
  module seated in a bay says what it is for. The DCP-404 has `client-100g` (QSFP28, four ports, 100G;
  the manual's section 2.2.4) and `line-400g` (QSFP-DD, 400G). The DCP-F-A22 has `mgmt-rj45` and
  `mgmt-sfp` (1G, from the datasheet's 10/100/1000 Base-T and 1000 Base-X), `edfa` and `monitor`.
  The passive modules' LC ports state `media: fiber` and no `speed`: no Smartoptics document prints a
  data rate for them. Part ids, positions and drawn geometry are unchanged; the card minors rise
  (dcp-404 1.2.0, dcp-f-a22 2.2.0, ppm-ad1-1510 and ppm-ad1-1625 2.4.0, the other PPMs 2.3.0) and
  `smartoptics/dcp-2` takes a patch (2.1.4).
