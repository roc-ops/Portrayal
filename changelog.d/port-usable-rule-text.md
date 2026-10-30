### Added
- **Lint L197: a decor `kind` does not name a connector**
  (`docs/lint-rules.md`). A device's `panel.decor` entry whose `kind` is on the
  list in `spec/schemas/connector-decor-names.yaml` (`console-opening`,
  `earth-hole`, `inlet-housing` and the rest) draws a port that nothing can
  plug into. It is a warning, the library's present findings are in
  `library/lint-baseline.json`, and the list is a floor of names, not a proof.
- **Gate 4b in the modelling guide**, and a `4b` row in the skill's gate table:
  after the build, the part-conformance scan's codes C19 to C22 are run over
  the devices a change touches, and every finding has a record. The gate covers
  those four codes and their records only.
- **The rule that every port is usable, in the contributor documents.** Anything
  that takes a cable, cord, plug, lug or pluggable is a connector part with a
  mate in the library, or says in a sentence why none can exist. It is written
  in `CONTRIBUTING.md` and the modelling guide (with a ground stud, its ring lug
  and the wire as the worked example), in the review standards, and the pull
  request template asks what mates each connector.
