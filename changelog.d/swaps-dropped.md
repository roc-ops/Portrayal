### Added
- **The kit says which swaps a load left out** (#1752). A link or a saved
  selection that names a part the library no longer holds used to seat the
  slot's default and say nothing. `shell.applySwaps` now answers
  `{ignored, dropped}`: one row of `{path, ref, why}` for each ignored entry
  that names a part, where `why` is `gone` (the ref is not in the library,
  with `replacedBy` when a published part stands in for it, as `supersedes`
  lists), `under` (it sat under a dropped part, with `carrier`) or `refused`
  (the part is there but the slot does not exist or does not take it). The
  shell emits a `dropped` event with the rows, the explorer's boot warns in a
  sentence, and `kit/redirects.js` exports `droppedSwaps` and `droppedText` for
  a page that loads swaps itself. Nothing is followed or seated: a page that
  ignores the answer and the event behaves as before.
