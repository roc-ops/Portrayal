### Fixed
- **A rack's first read is faster, and no route changes** (#1038). The run-outs
  past a ring (#1026) were tried at every lead end that had any way round; they
  are now tried only where a way round is round a body that is no tray's floor,
  which is every end where one was ever taken. Every route, length and finding
  is the one it was. A first read of 300 cables took about 13 per cent less in
  a measurement on a shared machine, and the speed budgets are tighter.
