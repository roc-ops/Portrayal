# The plan-outline fixture

A small library root for the tests of a housing whose top view is not a rectangle:
one device, `fixture/rounded`. It is a test fixture and no hardware: every number in
it is chosen so that a test can check it, and nothing here is built into
`library/dist` or exported.

The box is 600 long, 288 high and 281 deep and mounts on a strand. Its end profile
is the one in the section fixture (an upper casting, a flange, a lower casting). Its
`chassis.plan-outline` is three bands that tile the height, each a polygon seen from
above in the top face's frame (x from the left, y down, the rear at the top):

- the flange band, 132 to 155 mm down: corners of 24 mm in four chords, a lobe 10 mm
  out on the right end and one 8 mm out on the rear long side, so it reaches the
  right and rear sides of the box through its lobes and the left and front sides
  through its straight runs;
- the upper casting band, 0 to 132 mm: corners of 12 mm in three chords, inset from
  every side;
- the lower casting band, 155 to 288 mm: corners of 9 mm in three chords, inset from
  every side and from the upper casting differently.

Nothing in it is symmetric in x or in y. The tests make each broken copy by editing
the document in memory.
