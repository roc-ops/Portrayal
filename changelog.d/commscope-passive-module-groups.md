### Changed
- The optical ports on the 27 CommScope passive modules of the CH3000 chassis (the NP and OP filters,
  multiplexers, demultiplexers and splitters) now join a port group, so a port on a module seated in the
  chassis says what it is for. Each module has one group, `ports`, with the role `traffic` and the media
  `fiber`; a test port is a member of it. The CommScope data sheets print each module's ports and no data
  rate, so no group states a speed. Part ids, positions and drawn geometry are unchanged. Each contract
  takes a minor and the CH3000 chassis, which seats them, a patch. It closes no conformance record.
