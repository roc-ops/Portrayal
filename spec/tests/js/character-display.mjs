// What the kit can ask a compiled display, and what it must NOT be handed.
//
// `statesOfEl` and `messagesOfEl` read two attributes on purpose. states.js
// drops a data-states whose tokens are not lowercase `[a-z0-9-]`, which is right
// for a lamp - several contracts put a sentence where the state names go - and
// fatal for a display, whose whole vocabulary is uppercase words. This pins the
// separation: a display's readings come back from messagesOfEl and nothing
// reaches statesOfEl, in both directions.
//
// jsdom is not a dependency, so the element is the smallest one these two
// functions use: a `dataset`.
const el = dataset => ({dataset});

const m = await import('../../../kit/states.js');

const matrix = el({class: 'display', characters: '4',
                   messages: 'INIT BOOT IMEM PSEQ PST1'});
const digit = el({class: 'display', characters: '1', states: '0 1 2 blank'});
const lamp = el({class: 'led', states: 'off on'});
const bare = el({});

console.log(JSON.stringify({
  readings: m.messagesOfEl(matrix),
  cells: m.charactersOfEl(matrix),
  // a display's readings are not states, and its states are not readings
  matrixStates: m.statesOfEl(matrix),
  digitStates: m.statesOfEl(digit),
  digitReadings: m.messagesOfEl(digit),
  digitCells: m.charactersOfEl(digit),
  // a lamp answers neither display question
  lampReadings: m.messagesOfEl(lamp),
  lampCells: m.charactersOfEl(lamp),
  // and nothing throws on an element carrying nothing at all
  bareReadings: m.messagesOfEl(bare),
  bareCells: m.charactersOfEl(bare),
  nullCells: m.charactersOfEl(null),
  // a capacity that is not a positive integer is not a capacity
  junk: ['0', '-3', 'four', ''].map(v => m.charactersOfEl(el({characters: v}))),
}));
