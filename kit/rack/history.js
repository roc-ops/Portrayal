// UNDO AND REDO AS SNAPSHOTS: each step keeps the rack before and
// after it whole. Racks are never mutated, so a snapshot costs a reference,
// not a copy. Past the cap the oldest step is forgotten.

export function createHistory({cap = 100} = {}) {
  let past = [], future = [];
  return {
    record(before, after, summary, origin = 'ui') {
      past.push({before, after, summary, origin});
      if (past.length > cap) past.shift();
      future = [];
    },
    undo() { const s = past.pop(); if (s) future.push(s); return s ?? null; },
    redo() { const s = future.pop(); if (s) past.push(s); return s ?? null; },
    clear() { past = []; future = []; },
    get canUndo() { return past.length > 0; },
    get canRedo() { return future.length > 0; },
    get undoSummary() { return past.at(-1)?.summary ?? ''; },
    get redoSummary() { return future.at(-1)?.summary ?? ''; },
  };
}
