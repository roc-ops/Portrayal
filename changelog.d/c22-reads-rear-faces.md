### Changed
- The part-conformance check of a drawn port (C22) reads the back of a part seated in a bay. That back is drawn on the host's other
  panel as a projection of the seated part: it carries an address and no `ref`, so the check looked for a published slot of that
  address on the host, which a seated part's back never has. It now reads what the part's rear face composes at that id, which is
  what the rack kit lists as the rear's ports. The five FS FHD enclosures and the Fibrain XPU no longer report their rear LC, SC
  and MPO adapters as ports with no interface, 392 causes in the scan of their configurations. Nothing in the library, its exports
  or any lock changes.
- Six rows of the port-usable records file are gone and its `cap:` is 187.
