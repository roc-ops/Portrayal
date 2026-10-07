### Added
- `nokia/sr-1-dc-stud@1` and `nokia/sr-1-dc-pole@1`: one 10-32 stud of the
  7750 SR-1 DC terminal block, and a pole of two of them on 5/8 in. centres
  presenting `stud-pair-5-8` (#828). `nokia/sr-1-dc-terminal-block@1` (1.1.0)
  composes four poles, `a-neg`, `a-rtn`, `b-neg` and `b-rtn`, so a two-hole lug
  seats across each pole of the SR-1 DC (0.1.3) and a ring lug on each stud.
  The 45-degree lug the guide names is not built; the straight one stands in.

### Changed
- Ground points drawn as two studs, or as one stud standing for a pair, are one
  pair host at the pitch of the two-hole lug their documents call for (#828,
  #830). **Breaking for anything holding the old placement ids**; each device
  takes one major:
  - the eleven Amphenol 300CB08 panels (300CB08, -C, -SC, the six nrg300CB08
    CTRL and SENS versions, nrgILS300CB08 and its -SC), 2.0.0: each of the three
    landings is `common/ground-stud-pair-5-8-1-4@1` at 15.875 (was two
    `common/ground-stud@1` 15.9 apart), ids `ground-bottom`, `ground-left`,
    `ground-right`;
  - Edgecore AIS800-64D and AIS800-64O, 4.0.0: `ground-screws`, one
    `common/ground-stud-pair-5-8-m6@1` (was `ground-screw-1` and `-2`, 16.2
    apart). The 5/8 in. is inferred from the lug the guide names, and a gap
    says so. The earth symbol above the plate is drawn;
  - Nokia 7360 FX-16 (nfxs-d-ba), 1.0.0: `ground-left` and `ground-right` are
    `common/ground-stud-pair-1-1-4@1`; FX-8 (nfxs-e-bb) and FX-4 (nfxs-f-bb),
    1.0.0: `ground` is `common/ground-stud-pair-3-4-1-4@1`, stood on end;
  - Nokia Lightspan MF-8 (lmfs-f), 1.0.0: `ground-studs`, one
    `common/ground-stud-pair-5-8-m6@1` at 15.875 (was `ground-stud-1` and `-2`,
    16.3 apart): the manual's 16 mm (0.63 in.) is 5/8 in. rounded. Its ESD
    point moves out of `grounding` into its own group, `esd` (#866).
- Casa C40G (0.5.16): no change to the terminal. Its `ground-stud-count` gap
  records that the guide's lug points at 5/8 in. and at horizontal or vertical
  mounting, and why the pair waits.
