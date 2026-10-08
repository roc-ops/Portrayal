// THE HEADLESS RACK EDITOR: a document, its history, and the one
// way in for edits. The page draws what it is told by `change`; an agent drives
// the same object. Selection is the page's, not this.

import {apply as applyCommands, COMMANDS} from './commands.js';
import {settleManagers} from './managers.js';
import {createHistory} from './history.js';

// What a command that is not a step owns is kept across an undo or redo: Undo
// never takes the DCIM settings back. Routed lengths are measured
// again by the next render, so they need nothing here.
const keepDcim = (rack, from) => {
  const {dcim: _old, ...bare} = rack;
  return 'dcim' in from ? {...bare, dcim: from.dcim} : bare;
};

export function createRackEditor({doc, chassisOf, cap = 100}) {
  const ctx = {chassisOf};
  const history = createHistory({cap});
  const listeners = new Set();
  let current = doc;
  const rack = () => current.racks[0];
  const put = next => { current = {...current, racks: [next, ...current.racks.slice(1)]}; };
  // A LISTENER THAT THROWS is its own fault: the edit has landed, so apply
  // still answers, and the listeners after it still hear of it.
  const emit = ev => {
    for (const fn of [...listeners]) {
      try { fn(ev); } catch (e) { console.error(e); }
    }
  };
  const list = cmds => (Array.isArray(cmds) ? cmds : [cmds]);

  function apply(cmds, {origin = 'ui'} = {}) {
    const commands = list(cmds), before = rack();
    // A SYSTEM COMMAND is the page's own (routed lengths it measured): an agent
    // or a control that sends one is refused like any other bad command.
    if (origin !== 'system') {
      const index = commands.findIndex(c => typeof c?.op === 'string' && Object.hasOwn(COMMANDS, c.op) && COMMANDS[c.op].system);
      if (index >= 0) return {error: `${commands[index].op} is the page's own command.`, index};
    }
    const res = applyCommands(before, commands, ctx);
    if (res.error || res.noop) return res;
    put(res.rack);
    if (res.step) history.record(before, res.rack, res.summary, origin);
    emit({cause: 'apply', origin, step: res.step, commands, summary: res.summary, findings: res.findings, before, after: res.rack});
    return res;
  }

  function travel(cause) {
    const s = cause === 'undo' ? history.undo() : history.redo();
    if (!s) return null;
    const before = rack(), after = keepDcim(cause === 'undo' ? s.before : s.after, before);
    put(after);
    emit({cause, origin: s.origin, step: true, commands: [], summary: s.summary, findings: [], before, after});
    return {summary: s.summary};
  }

  return {
    getDoc: () => current,
    rack,
    loadDoc(next) {
      const findings = [];
      const racks = next.racks.map(r => {
        const s = settleManagers(r, chassisOf);
        findings.push(...s.notices.map(text => ({kind: 'note', text})));
        return s.rack;
      });
      current = {...next, racks};
      history.clear();
      emit({cause: 'load', origin: 'ui', step: false, commands: [], summary: '', findings, before: null, after: rack()});
      return {findings};
    },
    apply,
    preview: cmds => applyCommands(rack(), list(cmds), ctx),
    undo: () => travel('undo'),
    redo: () => travel('redo'),
    // For the probe hook only (?probe=1): a whole rack put in as one step.
    replaceRack(next, summary = 'Changed the rack.', origin = 'probe') {
      const before = rack();
      put(next);
      history.record(before, next, summary, origin);
      emit({cause: 'apply', origin, step: true, commands: [], summary, findings: [], before, after: next});
    },
    get canUndo() { return history.canUndo; },
    get canRedo() { return history.canRedo; },
    get undoSummary() { return history.undoSummary; },
    get redoSummary() { return history.redoSummary; },
    on(type, fn) {
      if (type !== 'change') throw new Error(`There is no event called ${type}.`);
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}
