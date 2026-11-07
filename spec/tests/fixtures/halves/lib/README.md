# The halves fixture

A small library root for the tests of a box that opens in two halves
(docs/modelling-a-device.md, "A box that opens"): one device, `fixture/clam`,
and the one card its bays accept. It is a test fixture and no hardware: every
number in it is chosen so that a test can check it, and nothing here is built
into `library/dist` or exported.

The box is 200 wide, 100 high and 120 deep. Its base stands 50 from the back to
the seam (`outer: rear`) and its lid 70 from the seam to its own outer face, so
the two sum to the depth. The lid is hinged on its top edge and opens to 110
degrees. The `open` view draws the two halves one above the other: the lid
region holds one bay and the base region holds two.
