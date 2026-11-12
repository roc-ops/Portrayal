# The fins fixture

A small library root for the tests of a housing whose casting carries ribs
(docs/modelling-a-device.md, "A housing with a stepped end"): two devices, `fixture/finned`
and `fixture/finned-outside`. They are test fixtures and no hardware: every number in them is
chosen so that a test can check it, and nothing here is built into `library/dist` or exported.

`finned` is the box of the section fixture (600 long, 288 high, 281 deep, the same twelve-point
end profile) with a field of ribs on its top edge and one on its bottom edge. The top field
runs from 20 to 587 along the length, the ribs stand 29 tall, each 7 thick with a 7 gap: 41
ribs. The bottom field has the same span and pitch, stands 48 at its two ends and 32 in the
middle (three steps), and is 41 ribs as well. Parts stand on the front, the rear and the right
end, each below the ribs.

`finned-outside` is a plain 60 by 40 by 50 casting whose ribs stand out of its edges instead
of cutting into it: seven ribs out of the top in two heights (20 and 12) and seven out of the
bottom 10 tall. It is the fixture for what a viewer, a face and a fit do with ribs that leave
the box.
