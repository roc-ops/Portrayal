# The section fixture

A small library root for the tests of a housing whose end is a stepped profile
(docs/modelling-a-device.md, "A housing with a stepped end"): one device,
`fixture/stepped`. It is a test fixture and no hardware: every number in it is
chosen so that a test can check it, and nothing here is built into `library/dist`
or exported.

The box is 600 long, 288 high and 281 deep and mounts on a strand. Its
`chassis.section` is twelve points: an upper casting from 14 to 250 across the
depth and 132 tall, a flange the full 281 across and 23 tall, and a lower casting
from 28 to 253 and 133 tall. The upper casting is not centred, so the left face,
which is the right face's mirror, is not a copy of it. Each face is drawn with
plain rectangles that fill what the face shows; the end faces use three, one for
each step.

Five placements of a component already in the library (`std/db9@1`) stand on it for
the placement tests and the pictures: two on the front (one over the lower casting,
one on the flange), two on the top (one on the upper casting, one on the rear
flange) and one on the right end. Each lies wholly on one level, so lint is quiet.
