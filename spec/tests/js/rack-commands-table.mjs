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

// Spec rack-agent-commands §5.5: an agent reads only these words, so they name
// no function and no page of any one site.
test('no description an agent reads names a function or a site page', () => {
  const said = [];
  const walk = (schema, at) => {
    for (const [k, s] of Object.entries(schema.properties || {})) { said.push([`${at}${k}`, s.description]); walk(s, `${at}${k}.`); }
  };
  for (const [op, def] of Object.entries(COMMANDS)) {
    if (def.system) continue;
    said.push([op, def.description]);
    walk(def.args, `${op}: `);
  }
  for (const [where, text] of said) {
    assert.doesNotMatch(text, /\w\(\)/, `${where} names a function`);
    assert.doesNotMatch(text, /Explorer|portrayal\.dev|Rack Builder/, `${where} names a site page`);
  }
});

test('the commands an agent uses to change one part are in the table', () => {
  for (const op of ['fit', 'field']) assert.ok(COMMANDS[op], op);
  assert.ok(COMMANDS['cable.update'].args.properties.a && COMMANDS['cable.update'].args.properties.b);
});
