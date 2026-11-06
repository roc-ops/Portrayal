### Added
- **`common/ground-stud-pair-5-8-10-32@1`**: two bare 10-32 studs on 5/8 in.
  centres, presenting `stud-pair-5-8`, the sibling of the M4, M6 and 1/4-20
  pairs. A device places it where its documents name two 10-32 studs that a
  two-hole lug lands across. Each stud is the new `common/ground-stud-10-32@1`,
  a brass-coloured stud end 4.826 across (the thread's nominal size) standing
  12 mm out, with no nut.
- **`common/ground-hole-pair-5-8-1-4@1`**: two bare tapped 1/4-20 holes on
  5/8 in. centres, presenting `stud-pair-5-8`, the sibling of the bare M5 and
  10-32 pairs. Each hole is the new `common/ground-hole-1-4@1`, a dark opening
  6.35 across (the thread's nominal size).
- **`mikrotik/earth-stud-disc@1`**: the earth stud of the MikroTik CRS309,
  CRS326 and CSS326 drawn as the plain disc their rear art used, a pale base 8.0
  across and a darker nut 4.0 across, presenting `terminal-stud`. It stands in
  for the stud's wing nut until a wing-nut part is drawn.

### Changed
- **The earth studs of seven devices are parts a ground lug lands on**, where
  they were decor: the Nokia 7750 SR-12, SR-1e, SR-2e and SR-3e and the MikroTik
  CRS309-1G-8S+IN, CRS326-24G-2S+RM and CSS326-24G-2S+RM. The SR-1e, SR-2e and
  SR-3e place the pair of bare studs, the SR-12 places the pair of bare 1/4-20
  receptacles and the three MikroTik switches place the disc. The SR-e studs and
  the MikroTik disc are drawn as they were; the SR-12's two nuts become two bare
  receptacles. Each device says in a gap what is estimated or inferred. Each takes
  a minor, its lock and the `Drawing version` line of its exported device types,
  and no exported port moves. Lint L197 no longer warns on the seven.
