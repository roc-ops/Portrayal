### Added
- The rack kit checks a cable whose ends are DC ports or poles, as warnings that
  refuse nothing. `mismatch` says them first, polarity first (`A is BATT where
  B is RTN: the feed is crossed.`), then the voltage (sign and range), the
  conductors and gauge against the end's poles and awg, A and B kept to their
  sides, and the protector against the load and the cable's ampacity. Each is
  said only where both sides state what it reads; what is missing is a note, and
  only three are: a pole whose role is `unstated`, a port with no voltage and a
  cable with no DC feed type. Polarity is compared by position (conductor `k`
  on pole `k`) with the pairs of `spec/schemas/dc.yaml`, which the kit now
  holds as `DC_MATCHES` and `DC_ROLES`; no feed is called crossed on an
  `unstated` pole.
- A consumer finds them in the cable's `mismatch` of `inspect`, in
  `suggestMedia`, and in the `findings` of `cable.add` and `cable.update`.
  `mismatch` takes an optional fourth argument `{type}` and `inspect` reads the
  cable types table from the new optional `ctx.cableTypes`; without either, the
  checks that need no type are said and the rest are not.
- A device whose DC supplies are all fed from outputs of one side is a finding:
  `inspect` of the device carries `feed_side`, `describe` counts it on its
  `Findings:` line, and `cable.add` or `cable.update` returns it when the cable
  makes it true.

### Changed
- `cable.add` says which DC port or pole each end landed on ("Added cable c1:
  end A on the DC port output-a1/output, end B on the BATT pole of
  psu-0/module/input."), `cable.update` adds the same for a moved end, and the
  `path` argument and the two descriptions name a DC port and a pole. A cable
  with no DC end keeps its summary and its findings.
- An end on a terminal that a supply, inlet or power part draws as an element
  and whose part declares no DC port is loose with "`terminal-48v` is drawn on
  `PWS-601S`, which declares no DC port" in place of "holds `PWS-601S`, which
  has no port `terminal-48v`". Every other loose sentence is unchanged.
