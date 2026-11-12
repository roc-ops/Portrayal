### Added
- CI's `lint` job checks every device lock a pull request changed against the lock on the
  branch it merges into. A lock that moved without the version bump the move needs now
  fails there, naming the device. Before, a branch that ran `devicelock.py --update` without
  raising `version:` passed, because the lock then agreed with the device. A new device and a
  removed device pass. `devicelock.py --base <commit>` runs the same check by hand.

### Changed
- The `preflight.py` `devicelock` check no longer calls its base half stricter than CI. CI
  runs that half now.
