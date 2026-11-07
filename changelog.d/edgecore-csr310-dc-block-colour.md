### Changed
- The terminal block of the DC supply of the Edgecore CSR310 and CSR430 (`edgecore/csr310-psu-dc@1`, 1.1.0 to 1.1.1) is drawn dark,
  as the vendor's quick start guides and data sheet show it: a dark plastic block, grey metal plates under the screws and silver
  screws, where it used to be drawn light grey with white plates. The colours are read off the guides' pictures and are estimates;
  nothing is moved or resized, and every id, seat, pole and port is as before.
- The CSR310 (`edgecore/csr310`, 1.1.0 to 1.1.1) and the CSR430 (`edgecore/csr430`, 1.1.0 to 1.1.1) each take a patch, with their
  locks and the drawing version line of their exported device types (12 files in NetBox and Nautobot); the supply's module type
  carries the new contract version (2 files). No port, interface or id moves.
