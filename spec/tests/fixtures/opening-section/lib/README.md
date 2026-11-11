# The opening stepped box fixture

A small library root for the tests of a stepped housing that opens in two halves
(docs/modelling-a-device.md, "A housing with a stepped end" and "A box that opens"):
one device, `fixture/stepped-open`. It is a test fixture and no hardware: every number
in it is chosen so that a test can check it, and nothing here is built into
`library/dist` or exported.

The box is the finned fixture of `fixtures/fins` (600 long, 288 high, 281 deep, an upper
casting 14 to 250, a flange 132 to 155 across the whole depth, a lower casting 28 to
253) with `halves` added: the base is the upper casting (`outer: top`, `stands: 144`,
so the seam is 144 down, inside the flange), the lid the lower one, hinged on the rear
and opened to 180 degrees. The `lid-open` view draws the two halves one above the other
with their regions and three bays.
