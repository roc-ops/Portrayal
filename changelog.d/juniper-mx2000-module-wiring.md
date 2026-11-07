### Changed
- `juniper/mx2000-lc-adapter` (now 1.1.0) seats the MPC2E NG and the MPC3E NG (`juniper/mpc2e-3d-ng@1`,
  `juniper/mpc3e-3d-ng@1`). The MX Series Interface Module Reference prints a first release for both cards on the
  MX2008, the MX2010 and the MX2020 in Table 4, and the cards are the same MX240-form MPC the adapter already
  carries. The MX2010 and MX2020 take a patch for it (now 3.1.1 and 2.1.1); nothing placed moves.
- `juniper/mx2008` (now 2.1.0) takes the MX2K-MPC8E and the MX2K-MPC9E in every line-card slot, as Table 4 and the
  MX2008 Hardware Guide's own table of MPCs print them, and says in its gap register how each family of MPC seats.
  `juniper/mx2k-mpc8e-v2k` and `juniper/mx2k-mpc9e-v2k` (now 1.1.1) name the MX2008 in their descriptions.
- This closes no gap row: the MPC catalogue entries on the three chassis stay open for the cards no part draws yet.
