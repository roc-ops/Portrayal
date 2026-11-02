### Changed
- The part-conformance check no longer reports two places that are offered by design. A device whose only power end is a fixed
  cord (a part with a plug of its own whose `unmated` sentence says it is no connector) is not reported as powered with no power
  end offered (C19). An inlet inside a placed part that composes just that one connector part is found offered when the
  placement publishes a slot of the inlet's interface at the placement's own path (C20), where the check looked only at the
  inlet's path. The three Smartoptics devices that place the 550 W supply and the three FS fan devices no longer report them.
  Nothing in the library, its exports or any lock changes.
- Four rows of the port-usable records file are gone and its `cap:` is 183.
