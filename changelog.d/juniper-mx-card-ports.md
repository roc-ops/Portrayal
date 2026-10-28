### Fixed
- **Juniper MX line cards state their ports.** Twenty-six Juniper cards drew
  their ports but stated no count and no rate, so anything that reads a card's
  port-count attrs found none: the MPC7E-MRATE, MPC7E-10G, MPC10E-10C-MRATE,
  MPC10E-15C-MRATE, MPC5E (both), MPC4E (both), MPC-3D-16XGE-SFPP and
  MX2K-MPC11E; the MIC3 10x10GE, 1x100GE CFP and 1x100GE CXP, MIC6 24x10GE,
  CFP2 and CXP, MIC-MRATE, MIC-MACSEC-MRATE, JNP-MIC1, 16-port E1/T1 and
  8-port DS3/E3 MICs; the MX10K-LC2101, LC480 and LC9600; the MX304-LMIC16; and
  the DPCE-R-40GE-TX. Each now carries a count per cage kind, with the rate
  quoted from Juniper's module reference or chassis guide in `provenance`. The
  MPC7E-MRATE counts four QSFP28 and eight QSFP+ ports along the ports its
  guide names, and its placements say so in `media`. The MPC10E-10C and 15C
  count their QSFP56-DD ports as `qsfp-dd`; their drawing still shows QSFP28
  cages, which is left for a later change. The MIC-MRATE and MIC-MACSEC-MRATE
  count twelve 40G ports, because their 100G ports depend on the carrier. Each
  card takes a minor version, and the thirteen MX devices that seat them take a
  patch version. No drawing changes.
