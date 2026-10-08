// spec/tests/js/rack-commands-table.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {COMMANDS} from '../../../kit/rack/commands.js';

// An agent reads this table to know what it may send (spec §2.1).
test('every command and every argument is described, briefly', () => {
  for (const [op, def] of Object.entries(COMMANDS)) {
    assert.ok(def.description && def.description.length <= 500, `${op}: description`);
    assert.equal(typeof def.run, 'function', `${op}: run`);
    const walk = (schema, at) => {
      for (const [k, s] of Object.entries(schema.properties || {})) {
        assert.ok(s.description && s.description.length <= 150, `${op}: ${at}${k} needs a description under 150 characters`);
        walk(s, `${at}${k}.`);
      }
    };
    walk(def.args, '');
  }
});

test('every command takes the optional rack argument', () => {
  for (const [op, def] of Object.entries(COMMANDS)) assert.ok(def.args.properties.rack, op);
});
