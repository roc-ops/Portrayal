### Changed
- The test suite's warm render server parses each library file once when it starts, not up to three times.
  Each worker's start-up falls from about 72 s to about 38 s.
  The parse is shared with the two per-file memos by the hash of the file's bytes, so renders and L62's vocabulary are unchanged.
