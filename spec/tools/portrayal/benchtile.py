"""Cut a face into windows a detector can see, whatever shape the face is.

WHY THIS IS ITS OWN FILE. The training set and the harness must cut a panel the
same way or the score is of a different task, and they were two copies of one
function kept in step by a test. One place, imported twice.

WHY IT CUTS BOTH AXES. The first version cut only in x, because every device in
front of it was a 1RU ribbon - 1455 x 145 px, seven windows, and each window
holds about ten cages. Handed a chassis router it silently returned ONE window:
the MX2020's face is 440 x 2000 mm, so the panel came back whole, 440 x 2000
px, which is the same 10:1 problem the cutting exists to solve, turned on its
side. Twenty-one of the seventy-nine modelled devices are under 4:1 and twelve
are taller than they are wide, so this was never a future problem.

    juniper/mx2020    440 x 2000 mm     0.22:1
    cisco/asr-9922    447 x 1956        0.23:1
    cisco/asr-9006    444 x  444        1.00:1

THE WINDOW IS SIZED FROM THE FACE'S SHORT SIDE, which is the dimension that
says how big the features are: a 1RU's ports span its height, a chassis
router's slots span its width. `aspect` then lays the window along the long
side.

A FACE THAT IS ALREADY SQUARE HAS NO LONG SIDE TO LAY IT ALONG, and taking the
short side there returns the whole face again - the same degeneracy, milder.
Thirteen of the twenty-one are in that band, including a 444 x 444 mm ASR-9006,
so it is not a corner. There the window is half the short side, which is the
smallest cut that still gives a window of the right shape.
"""


MIN_SIDE = 128


def tiles(w, h, aspect=2.0, overlap=0.25, min_side=MIN_SIDE):
    """Windows covering a w x h face, each about `aspect` to one.

    Returns (x, y, tw, th) in face pixels, left to right then top to bottom.
    Neighbours overlap by `overlap` of a window so a cage on a seam is whole in
    at least one of them, and the last window of a row or column is pulled back
    inside the face rather than hanging off the end.

    `min_side` stops the square case cutting a face that was already legible:
    cutting exists to keep features readable once a window is enlarged, and a
    200 x 145 face read whole at 2x is 400 x 290, which is fine. Halving it
    into six 144 x 72 windows splits the very features it was meant to show.
    """
    short = max(1, min(w, h))
    if w >= h * aspect:                      # a ribbon: lay the window along x
        tw, th = round(short * aspect), short
    elif h >= w * aspect:                    # a column: lay it along y
        tw, th = short, max(1, round(short / aspect))
    elif short >= 2 * min_side:              # square enough to have no long side
        th = max(1, round(short / 2))
        tw = round(th * aspect)
    else:                                    # square AND already legible whole
        tw, th = w, h
    tw, th = max(1, min(w, tw)), max(1, min(h, th))

    def starts(total, size):
        if size >= total:
            return [0]
        step = max(1, int(round(size * (1 - overlap))))
        out, x = [], 0
        while x + size < total:
            out.append(x)
            x += step
        out.append(total - size)
        return out

    return [(x, y, tw, th) for y in starts(h, th) for x in starts(w, tw)]
