### Changed
- The part-conformance check no longer reports a configuration as powered with no power end offered (C19) when every bay that
  takes a supply is open and no supply is drawn, as a spare chassis ships. Such a configuration has no supply to offer a power end,
  and the supplies ordered for it are judged on their own parts. A bay that takes no supply, a supply bay that is seated or
  seated by default, a supply that is drawn, and a chassis with no bay are reported as before.
  Nothing in the library, its exports or any lock changes.
- Thirty-four rows of the port-usable records file are gone: the device rows whose only finding was a configuration with every supply bay open.
