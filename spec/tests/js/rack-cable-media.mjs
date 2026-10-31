import test from 'node:test';
import assert from 'node:assert/strict';
import * as C from '../../../kit/rack/cable-rules.js';
import {mediaOfEnd} from '../../tools/dev/part_conformance.mjs';

const end = (item, path, view = 'front') => ({item, path, view});

test('the media enum is the eight data media, then power and ground (#1045), then stack, usb and console, each with a label and a kind', () => {
  assert.deepEqual(C.MEDIA, ['os2', 'om3', 'om4', 'om5', 'cat6', 'cat6a', 'dac', 'aoc', 'power', 'ground', 'stack', 'usb', 'console']);
  assert.deepEqual([C.mediaKind('power'), C.mediaKind('ground')], [{family: 'power', mode: null}, {family: 'ground', mode: null}]);
  assert.deepEqual(['stack', 'usb', 'console'].map(C.mediaKind),
    [{family: 'stack', mode: null}, {family: 'usb', mode: null}, {family: 'console', mode: null}]);
  assert.deepEqual(['stack', 'usb', 'console'].map(m => C.MEDIA_LABELS[m]), ['Stack cable', 'USB cable', 'Console cable']);
  for (const m of C.MEDIA) { assert.ok(C.MEDIA_LABELS[m], m); assert.ok(C.mediaKind(m).family, m); }
  assert.deepEqual(C.mediaKind('os2'), {family: 'fiber', mode: 'single-mode'});
  assert.deepEqual(C.mediaKind('om5'), {family: 'fiber', mode: 'multimode'});
  assert.deepEqual(C.mediaKind('cat6'), {family: 'copper', mode: null});
  assert.deepEqual(C.mediaKind(''), {family: null, mode: null});
  assert.deepEqual(C.mediaKind('os1'), {family: null, mode: null}, 'a media from a newer file is kept, not known');
});

test('connectorOf reads the seated part first, then the port', () => {
  assert.deepEqual(C.connectorOf({attrs: {face: 'lc-duplex', media: 'fiber'}}), {family: 'fiber', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {media: 'sfp', mode: 'single-mode'}}), {family: 'fiber', mode: 'single-mode'});
  assert.deepEqual(C.connectorOf({attrs: {media: 'fiber', mode: 'multi-mode'}}), {family: 'fiber', mode: 'multimode'});
  assert.deepEqual(C.connectorOf({attrs: {'cable-kind': 'dac'}}), {family: 'dac', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {'cable-kind': 'aec'}}), {family: 'dac', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {'cable-kind': 'aoc'}}), {family: 'aoc', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {face: 'cable'}}), {family: 'dac', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {face: 'rj45', media: 'copper'}}), {family: 'copper', mode: null});
  assert.deepEqual(C.connectorOf({attrs: {connector: 'rj45', media: 'rj45'}}), {family: 'copper', mode: null}, 'an RJ45 plug');
  assert.deepEqual(C.connectorOf({attrs: {connector: 'lc', media: 'fiber'}}), {family: 'fiber', mode: null}, 'an LC plug');
  assert.deepEqual(C.connectorOf({attrs: {}, portMedia: 'rj45'}), {family: null, mode: null},
    'a seated part that says nothing is unknown, whatever its cage is');
  assert.deepEqual(C.connectorOf({portMedia: 'rj45', iface: 'rj45'}), {family: 'copper', mode: null});
  assert.deepEqual(C.connectorOf({portMedia: 'rj45-serial'}), {family: 'copper', mode: null});
  assert.deepEqual(C.connectorOf({iface: 'lc-duplex'}), {family: 'fiber', mode: null});
  assert.deepEqual(C.connectorOf({portMedia: 'qsfp28', iface: 'qsfp'}), {family: null, mode: null});
  assert.deepEqual(C.connectorOf(), {family: null, mode: null});
});

test('proposeMedia follows the rulings: sm -> os2, mm -> om4, unstated fiber -> os2, copper -> cat6a, DAC -> dac, unknown -> blank', () => {
  const sm = {family: 'fiber', mode: 'single-mode'}, mm = {family: 'fiber', mode: 'multimode'};
  const fiber = {family: 'fiber', mode: null}, cu = {family: 'copper', mode: null};
  const none = {family: null, mode: null};
  assert.equal(C.proposeMedia(sm, sm), 'os2');
  assert.equal(C.proposeMedia(mm, mm), 'om4');
  assert.equal(C.proposeMedia(fiber, fiber), 'os2');
  assert.equal(C.proposeMedia(fiber, mm), 'om4', 'the end that states a mode decides between fibers');
  assert.equal(C.proposeMedia(cu, cu), 'cat6a');
  assert.equal(C.proposeMedia({family: 'dac', mode: null}, none), 'dac');
  assert.equal(C.proposeMedia(none, {family: 'aoc', mode: null}), 'aoc');
  assert.equal(C.proposeMedia(none, cu), 'cat6a', 'the first end that knows decides');
  assert.equal(C.proposeMedia(cu, mm), 'cat6a');
  assert.equal(C.proposeMedia(none, none), '');
  assert.equal(C.proposeMedia(null, undefined), '');
});

test('a mismatch is a list of warnings, never a refusal', () => {
  const sm = {family: 'fiber', mode: 'single-mode'}, mm = {family: 'fiber', mode: 'multimode'};
  const fiber = {family: 'fiber', mode: null}, cu = {family: 'copper', mode: null};
  const none = {family: null, mode: null};
  assert.deepEqual(C.mismatch('os2', sm, fiber), []);
  assert.deepEqual(C.mismatch('', none, none), []);
  assert.deepEqual(C.mismatch('cat6a', cu, none), [], 'an unknown end is not a mismatch');
  assert.deepEqual(C.mismatch('os2', fiber, cu),
    ['The ends differ: A is fiber, B is copper.', 'OS2 single-mode fiber does not suit end B, which is copper.']);
  assert.deepEqual(C.mismatch('os2', sm, mm), ['The ends differ: A is single-mode, B is multimode.']);
  assert.deepEqual(C.mismatch('cat6', fiber, fiber),
    ['Cat 6 copper does not suit end A, which is fiber.', 'Cat 6 copper does not suit end B, which is fiber.']);
  assert.deepEqual(C.mismatch('dac', {family: 'dac', mode: null}, {family: 'aoc', mode: null}),
    ['The ends differ: A is a DAC, B is an AOC.', 'DAC (twinax) does not suit end B, which is an AOC.']);
  assert.deepEqual(C.mismatch('os1', fiber, cu), ['The ends differ: A is fiber, B is copper.'],
    'an unknown media has no family to disagree with');
});

test('plugFor chooses by the slot\'s interface, and only a plug the slot accepts', () => {
  assert.equal(C.plugFor({interface: 'rj45', accepts: ['generic/rj45-plug@1']}), 'generic/rj45-plug@1');
  assert.equal(C.plugFor({interface: 'lc', accepts: ['common/lc-dust-cap@1', 'generic/lc-plug@2']}), 'generic/lc-plug@2');
  assert.equal(C.plugFor({interface: 'lc-duplex', accepts: ['generic/lc-duplex-plug@2']}), 'generic/lc-duplex-plug@2');
  assert.equal(C.plugFor({interface: 'qsfp', accepts: ['generic/qsfp-lc@2', 'generic/qsfp-cable@1']}), null, 'a cage takes an optic, not a plug');
  assert.equal(C.plugFor({interface: 'mpo', accepts: ['generic/mpo12-plug@1']}), null, 'no known plug: not an error');
  assert.equal(C.plugFor({interface: 'rj45', accepts: []}), null);
  assert.equal(C.plugFor(null), null);
});

test('plugSeats seats the port\'s own plug, or one in each bore of what the port holds', () => {
  const jack = {id: 'mgmt-eth', interface: 'rj45', accepts: ['generic/rj45-plug@1']};
  const cage = {id: 'port-1', interface: 'qsfp', accepts: ['generic/qsfp-lc@2']};
  const bore = (id) => ({id, interface: 'lc', accepts: ['common/lc-dust-cap@1', 'generic/lc-plug@2']});
  const slots = [jack, cage, bore('port-1-occupant/tx'), bore('port-1-occupant/rx'),
                 {id: 'port-1-occupant/tx-occupant/boot', interface: 'lc', accepts: ['generic/lc-plug@2']},
                 bore('port-10-occupant/tx'),
                 {id: 'bay-1/module/lc1', interface: 'lc-duplex', accepts: ['generic/lc-duplex-plug@2'], bores: ['1', '2']},
                 bore('bay-1/module/lc1/1'), bore('bay-1/module/lc1/2')];
  assert.deepEqual(C.plugSeats('mgmt-eth', slots), {'mgmt-eth': 'generic/rj45-plug@1'});
  assert.deepEqual(C.plugSeats('port-1', slots),
    {'port-1-occupant/tx': 'generic/lc-plug@2', 'port-1-occupant/rx': 'generic/lc-plug@2'},
    'the optic\'s two bores, not port-10\'s and not a slot further down');
  assert.deepEqual(C.plugSeats('bay-1/module/lc1', slots), {'bay-1/module/lc1': 'generic/lc-duplex-plug@2'},
    'a duplex adapter takes one duplex plug, not one per bore');
  assert.deepEqual(C.plugSeats('port-2', slots), {}, 'an empty cage gets nothing');
  assert.deepEqual(C.plugSeats('port-1', slots, {'port-1-occupant/tx': 'common/lc-dust-cap@1'}),
    {'port-1-occupant/rx': 'generic/lc-plug@2'}, 'a bore the user capped is the user\'s');
  assert.deepEqual(C.plugSeats('mgmt-eth', slots, {'mgmt-eth': null}), {}, 'a jack the user emptied stays empty');
  assert.deepEqual(C.plugSeats('bay-1/module/lc1', slots, {'bay-1/module/lc1/2': 'common/lc-dust-cap@1'}), {},
    'an adapter with a bore the user filled is left alone');
});

test('mergeSeats lays the item\'s own swaps over the plugs and changes neither', () => {
  const swaps = {'port-1': 'generic/qsfp-lc@2', 'mgmt-eth': null};
  const plugs = {'port-1-occupant/tx': 'generic/lc-plug@2', 'mgmt-eth': 'generic/rj45-plug@1'};
  assert.deepEqual(C.mergeSeats(swaps, plugs),
    {'port-1': 'generic/qsfp-lc@2', 'mgmt-eth': null, 'port-1-occupant/tx': 'generic/lc-plug@2'});
  assert.deepEqual(swaps, {'port-1': 'generic/qsfp-lc@2', 'mgmt-eth': null});
  assert.deepEqual(C.mergeSeats(undefined, undefined), {});
});

test('looseReason says why an end does not land, or null when it does', () => {
  const ok = {item: true, drawing: true, port: true, cage: false, occupied: false, holder: null};
  assert.equal(C.looseReason(end('i2', 'mgmt-eth'), ok), null);
  assert.equal(C.looseReason(end('i2', 'port-1'), {...ok, cage: true, occupied: true}), null);
  assert.equal(C.looseReason(end('i2', 'port-2'), {...ok, cage: true}), 'port-2 holds no optic');
  assert.equal(C.looseReason(end('i1', 'slot-2/module/p2'),
    {...ok, port: false, holder: {path: 'slot-2', part: 'A9K-24X10GE'}}), 'slot-2 holds A9K-24X10GE, which has no port p2');
  assert.equal(C.looseReason(end('i1', 'slot-2/module/p2'), {...ok, port: false, holder: {path: 'slot-2', part: null}}),
    'slot-2 is empty');
  assert.equal(C.looseReason(end('i2', 'port-99'), {...ok, port: false}), 'port-99 is not on this panel');
  assert.equal(C.looseReason(end('i2', 'port-1'), {item: true, drawing: false}), 'this panel has no drawing');
  assert.equal(C.looseReason(end('i9', 'port-1'), {item: false}), 'the device was removed');
  assert.equal(C.looseReason(end('i9', 'port-1'), undefined), 'the device was removed');
  assert.equal(C.holderPath('slot-2/module/p2'), 'slot-2');
  assert.equal(C.holderPath('slot-1/module/ppm-1/module/x0'), 'slot-1/module/ppm-1');
  assert.equal(C.holderPath('port-1'), null);
});

test('countsBy and matches drive the list\'s two filters', () => {
  const cables = [{media: 'os2', purpose: 'uplink'}, {media: 'cat6a', purpose: 'management'},
                  {media: 'os2', purpose: ''}];
  assert.deepEqual([...C.countsBy(cables, 'media')], [['os2', 2], ['cat6a', 1]]);
  assert.deepEqual([...C.countsBy(cables, 'purpose')], [['uplink', 1], ['management', 1], ['', 1]]);
  assert.deepEqual([...C.countsBy(undefined, 'media')], []);
  const n = on => cables.filter(c => C.matches(c, on)).length;
  assert.equal(n({purpose: null, media: null}), 3);
  assert.equal(n({purpose: null, media: 'os2'}), 2);
  assert.equal(n({purpose: 'uplink', media: 'os2'}), 1);
  assert.equal(n({purpose: '', media: null}), 1, 'the empty purpose is a value of its own');
  assert.equal(n(), 3);
});

// ── stack, usb and console ──────────────────────────────────────────────
const STACK = {family: 'stack', mode: null}, USB = {family: 'usb', mode: null}, CONSOLE = {family: 'console', mode: null};

test('a stack cable between two slots of one stacking interface is proposed stack and raises no mismatch', () => {
  for (const iface of ['flexstack', 'stackwise-480', 'ex4200-vcp']) {
    const e = C.connectorOf({iface});
    assert.deepEqual(e, STACK, iface);
    assert.equal(C.proposeMedia(e, e), 'stack', iface);
    assert.deepEqual(C.mismatch('stack', e, e), [], iface);
  }
  // a plug the end seats states the same key (`media` or `connector`), and an end that states none stays unknown
  assert.deepEqual(C.connectorOf({attrs: {media: 'flexstack'}}), STACK);
  assert.deepEqual(C.connectorOf({attrs: {connector: 'stackwise-480'}}), STACK);
  assert.deepEqual(C.connectorOf({attrs: {media: 'something-else'}}), {family: null, mode: null});
  // a stack cable does not suit a copper end, and the sentence says what the end is
  assert.deepEqual(C.mismatch('stack', STACK, {family: 'copper', mode: null}),
    ['The ends differ: A is stacking, B is copper.', 'Stack cable does not suit end B, which is copper.']);
  assert.deepEqual(C.mismatch('cat6a', STACK, STACK),
    ['Cat 6A copper does not suit end A, which is stacking.', 'Cat 6A copper does not suit end B, which is stacking.']);
});

// THE RULE THAT TELLS A USB END FROM A CONSOLE END. A USB receptacle serves a data link and a console alike,
// and its interface cannot tell them apart. The port's `role` can, so: an end is a console end when its
// `role` is `console` (whatever its connector); else it is a USB end when its interface, its port media or the
// seated plug's media is one of the four USB keys; a console port whose role is not passed stays what it was.
test('a USB end and a console end are told apart by the port\'s role, and the interface decides only what the role leaves', () => {
  for (const iface of ['usb-a', 'micro-usb-b', 'mini-usb-b', 'usb-c']) {
    assert.deepEqual(C.connectorOf({iface}), USB, iface);
    assert.deepEqual(C.connectorOf({portMedia: iface}), USB, `port media ${iface}`);
    assert.deepEqual(C.connectorOf({iface, role: 'console'}), CONSOLE, `${iface} with the console role`);
    assert.deepEqual(C.connectorOf({iface, role: 'data'}), USB, `${iface} with another role`);
    assert.deepEqual(C.connectorOf({attrs: {media: iface}}), USB, `a ${iface} plug`);
    assert.deepEqual(C.connectorOf({attrs: {media: iface}, role: 'console'}), CONSOLE, `a ${iface} plug on a console port`);
  }
  // the role wins over a connector that is not USB too: an RJ45 console is a console
  assert.deepEqual(C.connectorOf({portMedia: 'rj45-serial', iface: 'rj45', role: 'console'}), CONSOLE);
  assert.deepEqual(C.connectorOf({attrs: {role: 'console'}}), CONSOLE, 'a seated part that states the role');
  // and without it nothing changes: an RJ45 serial port with no role passed is copper, as it was
  assert.deepEqual(C.connectorOf({portMedia: 'rj45-serial'}), {family: 'copper', mode: null});
  assert.deepEqual(C.connectorOf({iface: 'rj45', role: ''}), {family: 'copper', mode: null});
  assert.equal(C.proposeMedia(USB, USB), 'usb');
  assert.equal(C.proposeMedia(CONSOLE, CONSOLE), 'console');
  assert.equal(C.proposeMedia(CONSOLE, USB), 'console', 'the first end that knows decides');
  assert.deepEqual(C.mismatch('usb', USB, USB), []);
  assert.deepEqual(C.mismatch('console', CONSOLE, CONSOLE), []);
  assert.deepEqual(C.mismatch('usb', USB, CONSOLE),
    ['The ends differ: A is USB, B is console.', 'USB cable does not suit end B, which is console.']);
});

test('mediaOfEnd offers stack, usb and console as connectorOf reads the end, and the media it offered before otherwise', () => {
  assert.equal(mediaOfEnd({kind: 'data', media: 'flexstack'}, null), 'stack');
  assert.equal(mediaOfEnd({kind: 'data', media: 'x', iface: 'ex4200-vcp'}, null), 'stack');
  assert.equal(mediaOfEnd({kind: 'data', media: 'usb-a'}, null), 'usb');
  assert.equal(mediaOfEnd({kind: 'data', media: 'mini-usb-b'}, null), 'usb');
  assert.equal(mediaOfEnd({kind: 'data', media: 'mini-usb-b', role: 'console'}, null), 'console');
  assert.equal(mediaOfEnd({kind: 'data', media: 'rj45-serial', role: 'console'}, null), 'console');
  // nothing that was offered before moves
  assert.equal(mediaOfEnd({kind: 'power'}, null), 'power');
  assert.equal(mediaOfEnd({kind: 'ground'}, null), 'ground');
  assert.equal(mediaOfEnd({kind: 'data', media: 'rj45'}, null), 'cat6');
  assert.equal(mediaOfEnd({kind: 'data', media: 'rj45-serial'}, null), 'cat6');
  assert.equal(mediaOfEnd({kind: 'data', media: 'lc'}, null), 'os2');
  assert.equal(mediaOfEnd({kind: 'data', media: 'qsfp28'}, {kind: 'dac'}), 'dac');
  assert.equal(mediaOfEnd({kind: 'data', media: 'qsfp28'}, {kind: 'optic'}), 'os2');
  assert.equal(mediaOfEnd({kind: 'data', media: 'sma'}, null), '');
});
