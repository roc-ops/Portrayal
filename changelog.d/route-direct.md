### Changed
- **Automatic routes and routed lengths change** (`@portrayal/kit` 0.12.0,
  #949; `docs/cable-lay-design.md` section 4.1, pulled forward from step 5).
  A cable whose two ends leave through the same manager on the same face runs
  along it, port to port, through the rings whose centres lie between its two
  ports, and no longer goes out to the side lane and back; with no ring
  between, through the ring nearest the middle of its two ports (of two as
  near, end a's side; the nearest one it passes through, when one does), so
  never direct. Any other automatic route takes the gutter both ports stand
  on, or, when they stand on opposite sides of the centre line, the side
  whose path is the shorter (end a's side on a tie, or when a port is not
  found); before, the side was end a's alone. On
  the owner's rack of #949 every one of its sixteen cords changes, from 0.67
  to 1.04 m by the lane to 0.43 to 0.50 m along the lacer (stock 1 or 1.5 m
  to 0.5 m); on a sample of 780 cables between six devices, a fifth to a
  quarter change, every one shorter. A saved rack's routed lengths and stock
  sizes are re-measured the next time a page measures them; an entered
  length and a route edited by hand are never touched.
- **Fewer doubles-back ring findings** (#949, #930's rule): a cable whose
  route reaches only a short way past a port, or any neighbour, into a ring
  just beyond it is held by the ring and not reported. Short means the ring's
  near face is no further past the nearer neighbour, along the run, than the
  ring's depth plus the cable's diameter; further is a hook-back and is still
  reported. Such a cable now passes the ring (`held: true` on `routePath`'s
  ring, `back: false` on its mark), is drawn through it, counts in its fill and
  its manager's capacity, and measures 8 to 13.5 mm longer. The rule is in
  `throughRings`, so hand routes and automatic ones agree. On a sample of 8850
  hand routes through one lacer ring each, 78 of 1520 findings went (5 %), 8
  of those routes moving a stock size; the automatic routes gave none before
  or after, and the owner's saved routes on the rack of #949 none either way.
