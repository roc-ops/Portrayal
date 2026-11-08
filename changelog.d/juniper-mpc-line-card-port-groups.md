### Changed
- The ports on 17 Juniper MPC line card contracts now join a port group, so a port on a card seated in a chassis
  slot says what it is for and, where the Interface Module Reference prints it, the rate it runs at. The cards are
  the MPC-3D-16XGE-SFPP, the MPC4E (32x10GE and 2x100GE + 8x10GE), the MPC5E (6x40GE + 24x10GE and 2x100GE +
  4x10GE), the MPC7E (10G and MRATE), the MPC10E (10C-MRATE and 15C-MRATE) and the MX2K-MPC11E, each in the
  drawing the book's chassis use and in its MX2000 vertical drawing where it has one. Each card declares one
  `traffic` group per cage and rate, numbered from 0 as the book labels its ports. A group states its cage as
  `media` and the rate the book prints for it as `speed`; the multi-rate groups also list the rates the book
  says those ports take. The MX2K-MPC11E's forty ports share one group with no rate, because the book prints
  its rates for the first port of each five-port PIC and the contract's ids do not say which cage that is.
  Part ids, positions and drawn geometry are unchanged; each card takes a minor, and the six chassis that seat
  them (the MX240, MX480, MX960, MX2008, MX2010 and MX2020) take a patch. The five QSFP56-DD ports of the
  MPC10E-10C-MRATE and MPC10E-15C-MRATE now export as `400gbase-x-qsfpdd` instead of `100gbase-x-qsfp28`, the
  type their 400 Gbps rate gives; no other exported port changes. Six L96 warnings in the baseline no
  longer occur and are removed from it. No conformance row is closed or opened.
