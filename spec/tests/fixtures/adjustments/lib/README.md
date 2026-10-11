# The adjustments fixture

A small library root for the tests of adjustable positions
(docs/adjustable-positions-design.md): one device, `fixture/slider`, and the
four parts it places. It is a test fixture and no hardware: every number in it
is chosen so that a test can check it, and nothing here is built into
`library/dist` or exported.

The device is a frame 120 wide, 40 high and 200 deep, with three parts that
slide, one along each axis:

- **`panel-setback`, along z.** A panel slides along the depth, from 20 to 180
  mm behind the front, and is drawn at 60. The front view draws the panel as a
  well with a rail standing in it; the top and bottom views draw the panel and
  the rail as decor; each side view draws a stud that holds the panel to a
  fixed side plate.
- **`block-offset`, along x.** A block slides across the front, its left edge
  22 to 92 mm from the left of the frame, drawn at 30. The front, the rear and
  both plans show it.
- **`shelf-height`, along y.** A shelf stud slides up the front, its centre 5
  to 35 mm above the bottom, drawn at 20. The front, the rear and both sides
  show it.

The stud has a colour field, `finish`, so that a test can repaint a part that
has moved.
