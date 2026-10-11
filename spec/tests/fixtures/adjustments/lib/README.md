# The adjustments fixture

A small library root for the tests of adjustable positions
(docs/adjustable-positions-design.md): one device, `fixture/slider`, and the
four parts it places. It is a test fixture and no hardware: every number in it
is chosen so that a test can check it, and nothing here is built into
`library/dist` or exported.

The device is a frame 120 wide, 40 high and 200 deep. A panel slides along its
depth, from 20 to 180 mm behind the front, and is drawn at 60. The front view
draws the panel as a well with a rail standing in it; the top and bottom views
draw the panel and the rail as decor; each side view draws a stud that holds
the panel to a fixed side plate.
