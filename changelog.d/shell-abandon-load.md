### Added
- **The shell can give up a load that never settles: `abandonLoad()` and the
  `loadstart` event** (#998, `kit/shell.js`). `abandonLoad()` moves the load
  counter of #929 on, so the load in flight ends as a superseded one does: it
  writes no state, mounts no drawing, emits no `load`, and its promise rejects
  with the error `isSuperseded` recognises. The request itself is not
  cancelled; its answer is dropped. `loadstart` is emitted by every load, a
  host's `loadDevice` or `loadStage`, the shell's own selects, `openModule`,
  the back button and the start-up load, with `{kind, device, config, view,
  module}`. A host starts a timer on it and calls `abandonLoad()` when the
  timer runs out.
