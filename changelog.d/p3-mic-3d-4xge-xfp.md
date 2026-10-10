### Changed
- `juniper/mic-3d-4xge-xfp@4`: the four ports are named for the module
  reference's pic/port numbering (Figure 31: [0/2]0, [0/2]1, [1/3]0, [1/3]1),
  `port-0-0`, `port-0-1`, `port-1-0`, `port-1-1`, as `mic-3d-2xge-xfp` names its
  two; 3.x named them `port-0-0` to `port-0-3`. Each port gains its LINK lamp,
  `led-link-<pic>-<port>`, with the reference's states (off, green on link)
  (#887). `@3` is retired with `superseded-by` and stays accepted by
  `juniper/mpc2e-3d@3` (3.1.0), which now accepts `@4` too.
- `juniper/mx2010` 2.0.0: its vendor-photo configuration seats the new MIC in
  LC0 and LC6. **Breaking for DCIM data already imported**: the third and fourth
  port of each of those MICs is renamed. `mx2008`, `mx2020`, `mx240`, `mx480`
  and `mx960` take a patch for the carrier change.
