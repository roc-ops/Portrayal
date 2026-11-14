"""The frame fittings of the Chatsworth Motive double-sided managers.

The page 1 photograph shows two caps and two feet.
The page 3 render shows four caps, three feet, a flat plate, a cross tube and a rear beam.
The plan adds squares, a slot, screws, a base rail and rounded lower corners on the centre section.
Each device draws 142 items on the top, bottom, left and right faces.
Every figure is a row of one table with its picture, pixels, direction and scale, and the notes quote that table.
Each door plate hides the fittings on the front and rear faces.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WIDTHS = {"0": 150, "1": 200, "2": 250, "3": 300, "4": 380}
MODELS = [f"3262{n}-{c}" for n in "01234" for c in ("703", "e03")]
LIMIT = 25
# The values below are the one table of the frame figures, listed once. No figure is typed anywhere else in this module.
SCALES = json.loads(r"""[
{"id": "ph-down", "picture": "photograph", "dir": "down", "mm": 2133.6, "px": 813, "digits": 3, "shown": "2.624", "sentence": "Scale 1, photograph, read down: 2.624 mm per pixel, the nominal height 2133.6 mm over the left door's rows 72 to 885, 813 rows."},
{"id": "ph-across", "picture": "photograph", "dir": "across", "mm": 300.0, "px": 112, "digits": 3, "shown": "2.679", "sentence": "Scale 2, photograph, read across: 2.679 mm per pixel, the 12 in width 300 mm over the door's columns at half level, 112 columns."},
{"id": "ph-depth", "picture": "photograph", "dir": "across", "mm": 600.0, "px": 58, "digits": 1, "shown": "10.3", "sentence": "Scale 3, photograph, read across: 10.3 mm per pixel, the depth 600 mm over the left face's columns 97 to 155, 58 columns."},
{"id": "r-across", "picture": "render", "dir": "across", "mm": 198.0, "px": 39, "digits": 1, "shown": "5.1", "sentence": "Scale 4, render, read across: 5.1 mm per pixel, the centre section 198 mm over the plate's columns, 39 columns."},
{"id": "r-plate", "picture": "render", "dir": "across", "mm": 198.0, "px": 37, "digits": 2, "shown": "5.35", "sentence": "Scale 5, render, read across: 5.35 mm per pixel, the centre section 198 mm over the near plate's end columns 118 to 155, 37 columns."},
{"id": "r-axis", "picture": "render", "dir": "across", "mm": 300.0, "px": 67.8, "digits": 1, "shown": "4.4", "sentence": "Scale 6, render, read along the width axis: 4.4 mm per pixel, the door's width 300 mm over the cap centres, 67.8 pixels."},
{"id": "r-depth", "picture": "render", "dir": "across", "mm": 600.0, "px": 162, "digits": 1, "shown": "3.7", "sentence": "Scale 7, render, read along the depth axis: 3.7 mm per pixel, the depth 600 mm over the left rail, 162 pixels."},
{"id": "r-down", "picture": "render", "dir": "down", "mm": 2133.6, "px": 500, "digits": 3, "shown": "4.267", "sentence": "Scale 8, render, read down: 4.267 mm per pixel, the nominal height 2133.6 mm over the render's rows, 500 rows."},
{"id": "plan", "picture": "plan", "dir": "both", "mm": 198.0, "px": 266, "digits": 4, "shown": "0.7444", "sentence": "Scale 9, plan, read both: 0.7444 mm per pixel, the centre section 198 mm over its columns 552 to 818, 266 pixels."},
{"id": "p3-across", "picture": "elevation", "dir": "across", "mm": 198.0, "px": 84, "digits": 3, "shown": "2.357", "sentence": "Scale 10, elevation, read across: 2.357 mm per pixel, the centre section 198 mm over its columns 2188 to 2272, 84 columns."},
{"id": "p3-down", "picture": "elevation", "dir": "down", "mm": 2133.6, "px": 1553, "digits": 3, "shown": "1.374", "sentence": "Scale 11, elevation, read down: 1.374 mm per pixel, the nominal height 2133.6 mm over the manager's rows 515 to 2068, 1553 rows."},
{"id": "p3-mark", "picture": "elevation", "dir": "both", "mm": 14.1, "px": 9.5, "digits": 3, "shown": "1.484", "sentence": "Scale 12, elevation, read both: 1.484 mm per pixel, the plan's square 14.1 mm over the page 3 square's outline, 9.5 pixels."}
]""")
ROWS = json.loads(r"""[
{"id": "cap", "kind": "size", "picture": "photograph", "dims": [{"px": 28, "px_s": "28", "dir": "across", "scale": "ph-across", "scale_s": "2.679", "mm": 75.0, "name": "wide"}, {"px": 8, "px_s": "8", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": 21.0, "name": "tall"}], "fits": [["top", "end-cap-.*", 75.0, 37.5], ["left|right", "end-cap-.*", 37.5, 21.0]], "percent": null, "mm": [75.0, 21.0], "tol": 0.05, "sentences": ["A cap (page 1 photograph) is 28 columns across at 2.679 mm per pixel, so 75 wide.", "It is 8 rows down at 2.624 mm per pixel, so 21 tall.", "The cap and foot widths are read on the 12 in part and drawn on every width."]},
{"id": "cap-depth", "kind": "standin", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [37.5], "tol": 0.05, "sentences": ["A cap's depth is half its width, 37.5, a stand-in that no picture gives."]},
{"id": "foot", "kind": "size", "picture": "photograph", "dims": [{"px": 22, "px_s": "22", "dir": "across", "scale": "ph-across", "scale_s": "2.679", "mm": 58.9, "name": "wide"}, {"px": 5, "px_s": "5", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": 13.1, "name": "tall"}], "fits": [["bottom", "foot-.*", 58.9, 29.5], ["left|right", "foot-.*", 29.5, 13.1]], "percent": null, "mm": [58.9, 13.1], "tol": 0.05, "sentences": ["A foot (page 1 photograph) is 22 columns across at 2.679 mm per pixel, so 58.9 wide.", "It is 5 rows down at 2.624 mm per pixel, so 13.1 tall."]},
{"id": "foot-depth", "kind": "standin", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [29.5], "tol": 0.05, "sentences": ["A foot's depth is half its width, 29.5, a stand-in that no picture gives."]},
{"id": "render-foot", "kind": "info", "picture": "render", "dims": [{"px": 7, "px_s": "7", "dir": "across", "scale": "r-axis", "scale_s": "4.4", "mm": 30.8, "name": "wide"}], "fits": [], "percent": null, "mm": [30.8], "tol": 0.05, "sentences": ["A render foot (page 3 render) is 7 columns across at 4.4 mm per pixel, so 30.8 wide.", "The render's feet are narrower than the photograph's, and the photograph rules at its finer scale."]},
{"id": "rim-side", "kind": "size", "picture": "photograph", "dims": [{"px": 3, "px_s": "3", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": 7.9, "name": "tall"}], "fits": [["left|right", "base-rim", null, 7.9]], "percent": null, "mm": [7.9], "tol": 0.05, "sentences": ["The base rim (page 1 photograph) is 3 rows down at 2.624 mm per pixel, so 7.9 tall."]},
{"id": "rim-outline", "kind": "given", "picture": "", "dims": [], "fits": [["bottom", "base-rim", "W", "D"]], "percent": null, "mm": [], "tol": 0.05, "sentences": ["The bottom's base outline is the chassis width by its depth."]},
{"id": "hole", "kind": "size", "picture": "photograph", "dims": [{"px": 3, "px_s": "3", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": 7.9, "name": "across"}], "fits": [["bottom", "base-plate-hole-.*", 7.9, 7.9], ["left|right", "side-plate-hole-.*", 7.9, 7.9]], "percent": null, "mm": [7.9], "tol": 0.05, "sentences": ["A base-plate or side-plate hole (page 1 photograph) is 3 rows down at 2.624 mm per pixel, so 7.9 across."]},
{"id": "dot", "kind": "size", "picture": "photograph", "dims": [{"px": 2, "px_s": "2", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": 5.0, "name": "across"}], "fits": [["left|right", "side-plate-dot-.*", 5.0, 5.0]], "percent": null, "mm": [5.0], "tol": 0.3, "sentences": ["A side-plate dot (page 1 photograph) is 2 rows down at 2.624 mm per pixel, which gives 5.2 across, and 5 is drawn, within 0.3."]},
{"id": "rail", "kind": "size", "picture": "render", "dims": [{"px": 15.25, "px_s": "15.25", "dir": "down", "scale": "r-axis", "scale_s": "4.4", "mm": 70.5, "name": "wide"}], "fits": [["top", "top-rail-.*", 70.5, null], ["bottom", "base-rail-(left|right)", 70.5, null]], "percent": null, "mm": [70.5], "tol": 0.05, "sentences": ["A rail's width (page 3 render) is 15.25 rows down at 4.4 mm per pixel after the slant correction of 0.952, so 70.5 wide.", "The correction 0.952 is sin 29.1 plus sin 27.8, the angles read in the render.", "The base rails take the same width, because the door hides them in the render."]},
{"id": "tube", "kind": "size", "picture": "render", "dims": [{"px": 14.75, "px_s": "14.75", "dir": "down", "scale": "r-depth", "scale_s": "3.7", "mm": 54.6, "name": "deep"}], "fits": [["top", "cross-tube", "W", 54.6]], "percent": null, "mm": [54.6], "tol": 0.05, "sentences": ["The cross tube's depth (page 3 render) is 14.75 rows down at 3.7 mm per pixel, so 54.6 deep."]},
{"id": "tube-place", "kind": "percent", "picture": "render", "dims": [], "fits": [], "percent": 44.3, "mm": [], "tol": 0.05, "sentences": ["The cross tube's place (page 3 render) is 44.3 percent of the way from the front cap centres to the rear ones, 556.5 mm apart.", "It is the mean of four readings along the cap centres: 45.4, 43.7, 45.5 and 42.6."]},
{"id": "beam", "kind": "size", "picture": "render", "dims": [{"px": 7, "px_s": "7", "dir": "down", "scale": "r-depth", "scale_s": "3.7", "mm": 25.9, "name": "deep"}], "fits": [["top", "rear-beam", "W", 25.9]], "percent": null, "mm": [25.9], "tol": 0.05, "sentences": ["The rear beam's depth (page 3 render) is 7 rows down at 3.7 mm per pixel, so 25.9 deep."]},
{"id": "centre-section", "kind": "given", "picture": "", "dims": [], "fits": [["left|right", "centre-plate", 198.0, null]], "percent": null, "mm": [198.0], "tol": 0.05, "sentences": ["The centre plate is the centre section, 198 deep, between the two channels."]},
{"id": "corner", "kind": "size", "picture": "plan", "dims": [{"px": 17.5, "px_s": "17.5", "dir": "down", "scale": "plan", "scale_s": "0.7444", "mm": 13.0, "name": "radius"}], "fits": [], "percent": null, "mm": [13.0], "tol": 0.05, "sentences": ["A rounded lower corner's radius (page 2 plan) is 17.5 rows down at 0.7444 mm per pixel, so 13 radius."]},
{"id": "plate-foot", "kind": "multiple", "picture": "", "dims": [], "fits": [["left|right", "centre-plate-foot", 198.0, 39.0]], "percent": null, "mm": [39.0], "tol": 0.05, "sentences": ["The plate's rounded foot is three corner radii tall, 39."]},
{"id": "base-rail", "kind": "size", "picture": "plan", "dims": [{"px": 44, "px_s": "44", "dir": "down", "scale": "plan", "scale_s": "0.7444", "mm": 32.8, "name": "tall"}], "fits": [["left|right", "base-rail-(rear|front)", null, 32.8]], "percent": null, "mm": [32.8], "tol": 0.05, "sentences": ["A tall base rail (page 2 plan) is 44 rows down at 0.7444 mm per pixel, so 32.8 tall."]},
{"id": "round-hole", "kind": "size", "picture": "render", "dims": [{"px": 2.57, "px_s": "2.57", "dir": "across", "scale": "r-across", "scale_s": "5.1", "mm": 13.1, "name": "across"}], "fits": [["left", "centre-plate-hole-(top-[1-4]|bottom-[1-4]|row\\d-\\d)|centre-plate-dot-1", 13.1, 13.1], ["right", "centre-plate-hole-(top-[23]|bottom-[1-4]|row\\d-\\d)|centre-plate-dot-1", 13.1, 13.1]], "percent": null, "mm": [13.1], "tol": 0.05, "sentences": ["A round hole of the near plate (page 3 render) is 2.57 columns across at 5.1 mm per pixel, so 13.1 across.", "Its rows span 2.29 on average, 9.8 down, and the column reading is used."]},
{"id": "far-hole", "kind": "size", "picture": "render", "dims": [{"px": 3, "px_s": "3", "dir": "across", "scale": "r-across", "scale_s": "5.1", "mm": 15.3, "name": "across"}], "fits": [["right", "centre-plate-hole-top-1", 15.3, 15.3]], "percent": null, "mm": [15.3], "tol": 0.05, "sentences": ["The far plate's dark hole (page 3 render) is 3 columns across at 5.1 mm per pixel, so 15.3 across."]},
{"id": "slot", "kind": "size", "picture": "render", "dims": [{"px": 4, "px_s": "4", "dir": "across", "scale": "r-across", "scale_s": "5.1", "mm": 20.4, "name": "wide"}, {"px": 2, "px_s": "2", "dir": "down", "scale": "r-down", "scale_s": "4.267", "mm": 8.5, "name": "tall"}], "fits": [["left", "centre-plate-slot-[12]", 20.4, 8.5], ["right", "centre-plate-slot-([12]|head-[12])", 20.4, 8.5]], "percent": null, "mm": [20.4, 8.5], "tol": 0.05, "sentences": ["A slot (page 3 render) is 4 columns across at 5.1 mm per pixel, so 20.4 wide.", "It is 2 rows down at 4.267 mm per pixel, so 8.5 tall."]},
{"id": "mark", "kind": "size", "picture": "render", "dims": [{"px": 1.5, "px_s": "1.5", "dir": "across", "scale": "r-across", "scale_s": "5.1", "mm": 7.7, "name": "across"}], "fits": [["left|right", "centre-plate-mark-\\d", 7.7, 7.7]], "percent": null, "mm": [7.7], "tol": 0.05, "sentences": ["A faint mark (page 3 render) is 1.5 columns across at 5.1 mm per pixel, so 7.7 across."]},
{"id": "plan-square", "kind": "size", "picture": "plan", "dims": [{"px": 19, "px_s": "19", "dir": "across", "scale": "plan", "scale_s": "0.7444", "mm": 14.1, "name": "wide"}, {"px": 19, "px_s": "19", "dir": "down", "scale": "plan", "scale_s": "0.7444", "mm": 14.1, "name": "tall"}], "fits": [["left|right", "plan-square-\\d", 14.1, 14.1]], "percent": null, "mm": [14.1, 14.1], "tol": 0.05, "sentences": ["A plan square (page 2 plan) is 19 columns across at 0.7444 mm per pixel, so 14.1 wide.", "It is 19 rows down at 0.7444 mm per pixel, so 14.1 tall."]},
{"id": "plan-slot", "kind": "size", "picture": "plan", "dims": [{"px": 35, "px_s": "35", "dir": "across", "scale": "plan", "scale_s": "0.7444", "mm": 26.1, "name": "wide"}, {"px": 19, "px_s": "19", "dir": "down", "scale": "plan", "scale_s": "0.7444", "mm": 14.1, "name": "tall"}], "fits": [["left|right", "plan-slot", 26.1, 14.1]], "percent": null, "mm": [26.1, 14.1], "tol": 0.05, "sentences": ["The plan slot (page 2 plan) is 35 columns across at 0.7444 mm per pixel, so 26.1 wide.", "It is 19 rows down at 0.7444 mm per pixel, so 14.1 tall."]},
{"id": "plan-screw", "kind": "size", "picture": "plan", "dims": [{"px": 20, "px_s": "20", "dir": "across", "scale": "plan", "scale_s": "0.7444", "mm": 14.9, "name": "across"}], "fits": [["left|right", "plan-screw-\\d", 14.9, 14.9]], "percent": null, "mm": [14.9], "tol": 0.05, "sentences": ["A plan screw ring (page 2 plan) is 20 columns across at 0.7444 mm per pixel, so 14.9 across."]},
{"id": "p3-square", "kind": "size", "picture": "elevation", "dims": [{"px": 9.5, "px_s": "9.5", "dir": "across", "scale": "p3-mark", "scale_s": "1.484", "mm": 14.1, "name": "wide"}, {"px": 9.5, "px_s": "9.5", "dir": "down", "scale": "p3-mark", "scale_s": "1.484", "mm": 14.1, "name": "tall"}], "fits": [["left|right", "page3-square-.*", 14.1, 14.1]], "percent": null, "mm": [14.1, 14.1], "tol": 0.05, "sentences": ["A page 3 square (page 3 elevation) is 9.5 columns across at 1.484 mm per pixel, so 14.1 wide.", "It is 9.5 rows down at 1.484 mm per pixel, so 14.1 tall.", "It is drawn at the plan square's size, so the scale of the page 3 marks is a transfer from the plan."]},
{"id": "p3-triangle", "kind": "size", "picture": "elevation", "dims": [{"px": 11, "px_s": "11", "dir": "across", "scale": "p3-mark", "scale_s": "1.484", "mm": 16.3, "name": "wide"}, {"px": 8, "px_s": "8", "dir": "down", "scale": "p3-mark", "scale_s": "1.484", "mm": 11.9, "name": "tall"}], "fits": [["left|right", "page3-triangle", 16.3, 11.9]], "percent": null, "mm": [16.3, 11.9], "tol": 0.05, "sentences": ["The page 3 triangle (page 3 elevation) is 11 columns across at 1.484 mm per pixel, so 16.3 wide.", "It is 8 rows down at 1.484 mm per pixel, so 11.9 tall."]},
{"id": "p3-dot", "kind": "size", "picture": "elevation", "dims": [{"px": 5, "px_s": "5", "dir": "across", "scale": "p3-mark", "scale_s": "1.484", "mm": 7.4, "name": "across"}], "fits": [["left|right", "page3-dot", 7.4, 7.4]], "percent": null, "mm": [7.4], "tol": 0.05, "sentences": ["The page 3 dot (page 3 elevation) is 5 columns across at 1.484 mm per pixel, so 7.4 across."]},
{"id": "near-cols", "kind": "place", "picture": "render", "dims": [{"px": 37, "px_s": "37", "dir": "across", "scale": "r-plate", "scale_s": "5.35", "mm": 198.0, "name": "in all"}], "fits": [], "percent": null, "mm": [198.0], "tol": 0.05, "sentences": ["The near plate's hole columns (page 3 render) are 37 columns across at 5.35 mm per pixel, so 198 in all.", "The head holes, the foot holes, the foot slots and the fifth dot stand at the columns the render shows."]},
{"id": "near-rows", "kind": "place", "picture": "render", "dims": [{"px": null, "px_s": "", "dir": "down", "scale": "r-down", "scale_s": "4.267", "mm": null, "name": ""}], "fits": [], "percent": null, "mm": [null], "tol": 0.05, "sentences": ["The near plate's slot and dot rows (page 3 render) are read down at 4.267 mm per pixel.", "Each row is counted from the render's foot line under it."]},
{"id": "far-places", "kind": "place", "picture": "render", "dims": [{"px": null, "px_s": "", "dir": "across", "scale": "r-across", "scale_s": "5.1", "mm": null, "name": ""}, {"px": null, "px_s": "", "dir": "down", "scale": "r-down", "scale_s": "4.267", "mm": null, "name": ""}], "fits": [], "percent": null, "mm": [null, null], "tol": 0.05, "sentences": ["The far plate's mark places (page 3 render) are read across at 5.1 mm per pixel.", "They are read down at 4.267 mm per pixel.", "A column is counted from column 56 and a row from row 75, and each row is corrected by 0.49 per pixel along the axis."]},
{"id": "overlay", "kind": "place", "picture": "render", "dims": [{"px": null, "px_s": "", "dir": "across", "scale": "r-plate", "scale_s": "5.35", "mm": null, "name": ""}, {"px": null, "px_s": "", "dir": "down", "scale": "r-down", "scale_s": "4.267", "mm": null, "name": ""}], "fits": [], "percent": null, "mm": [null, null], "tol": 0.05, "sentences": ["The overlay marks (page 3 render) are read across at 5.35 mm per pixel.", "They are read down at 4.267 mm per pixel.", "An overlay of the render on the built plate gave two more rows of marks, near 200 mm and 861 mm, and a foot row."]},
{"id": "plan-places", "kind": "place", "picture": "plan", "dims": [{"px": null, "px_s": "", "dir": "across", "scale": "plan", "scale_s": "0.7444", "mm": null, "name": ""}, {"px": null, "px_s": "", "dir": "down", "scale": "plan", "scale_s": "0.7444", "mm": null, "name": ""}], "fits": [], "percent": null, "mm": [null, null], "tol": 0.05, "sentences": ["The plan's places (page 2 plan) are read across at 0.7444 mm per pixel.", "They are read down at 0.7444 mm per pixel.", "The plan gives four squares, a slot and four screws on the centre section."]},
{"id": "p3-places", "kind": "place", "picture": "elevation", "dims": [{"px": 84, "px_s": "84", "dir": "across", "scale": "p3-across", "scale_s": "2.357", "mm": 198.0, "name": "wide"}, {"px": 1553, "px_s": "1553", "dir": "down", "scale": "p3-down", "scale_s": "1.374", "mm": 2133.6, "name": "tall"}], "fits": [], "percent": null, "mm": [198.0, 2133.6], "tol": 0.05, "sentences": ["The page 3 marks' places (page 3 elevation) are 84 columns across at 2.357 mm per pixel, so 198 wide.", "They are 1553 rows down at 1.374 mm per pixel, so 2133.6 tall.", "Page 3 adds three pairs of squares, a triangle and a dot."]},
{"id": "side-places", "kind": "place", "picture": "photograph", "dims": [{"px": null, "px_s": "", "dir": "across", "scale": "ph-depth", "scale_s": "10.3", "mm": null, "name": ""}, {"px": null, "px_s": "", "dir": "down", "scale": "ph-down", "scale_s": "2.624", "mm": null, "name": ""}], "fits": [], "percent": null, "mm": [null, null], "tol": 0.05, "sentences": ["The side plate's mark places (page 1 photograph) are read across at 10.3 mm per pixel.", "They are read down at 2.624 mm per pixel.", "A mark stands along the depth at 20 plus its column less 99.5, times 10.3, and down at its row less 72, times 2.624.", "The side plate shows four marks near 505 mm, two dots near 1904 mm and one near 219 mm."]},
{"id": "side-estimates", "kind": "estimate", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [], "tol": 0.05, "sentences": ["The side plate's three holes stand at depths 20, 82 and 124, 100 down. Two dots stand at depths 82 and 144, 1010 down. All five are read by eye from the photograph."]},
{"id": "base-holes", "kind": "estimate", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [], "tol": 0.05, "sentences": ["The bottom's four plate holes stand 12 from the left edge and 40, 100, 145 and 285 from the rear door, read by eye."]},
{"id": "foot-hole-y", "kind": "estimate", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [], "tol": 0.05, "sentences": ["The foot holes' centres stand 60 above the plate's foot, an estimate."]},
{"id": "door-t", "kind": "given", "picture": "", "dims": [], "fits": [], "percent": null, "mm": [3.0], "tol": 0.05, "sentences": ["Each door is 3 thick, the door part's own figure, and the fittings stand inside it."]}
]""")
NOTES = json.loads(r"""{"top": "It draws four end caps, two rails, a cross tube and a beam across the rear. The cross tube stands 44 percent of the way from the front caps to the rear caps.", "bottom": "It draws the base plate with four holes, two rails and four feet.", "method": "The matrix figures are transcribed, not copied from a picture. The frame fittings are read from the pictures, and the `frame` entry lists them as a table. A row is one figure: its picture, the pixels it spans, the direction it is read in, the scale, the size drawn and the tolerance. The direction is down the rows or across the columns of that picture. The tolerance is how far the drawn size may differ from the pixels times the scale; it is 0.05 unless a row says otherwise. The scale list holds 12 scales, each the millimetres of a known part over the pixels it spans.", "central-track": "the data sheet and the installation drawing show an integral central track. No held page gives its width or how far it stands. The top and bottom faces draw it as a strip the full depth between the doors. The left and right faces draw the page 3 render's flat centre plate, 198 deep, in its place."}""")
COUNTS = json.loads(r"""{"views": {"top": 8, "bottom": 11, "left": 61, "right": 62}, "total": 142, "kinds": ["end-cap", "foot", "base-plate", "hole", "slot", "centre-plate", "rail", "cross-tube", "beam", "mounting-hole", "screw", "mark"]}""")
PINS = json.loads(r"""{"side": {"left": {"end-cap-rear": [21.8, 10.5], "end-cap-front": [578.2, 10.5], "base-rim": [300.0, 2129.6], "base-rail-rear": [100.5, 2109.3], "base-rail-front": [499.5, 2109.3], "foot-rear": [17.8, 2127.1], "foot-front": [582.2, 2127.1], "centre-plate": [300.0, 1060.3], "centre-plate-foot": [300.0, 2106.2], "centre-plate-hole-top-1": [366.9, 50.0], "centre-plate-hole-top-2": [314.9, 50.0], "centre-plate-hole-top-3": [266.2, 50.0], "centre-plate-hole-top-4": [209.1, 50.0], "centre-plate-hole-bottom-1": [372.2, 2073.7], "centre-plate-hole-bottom-2": [313.4, 2073.7], "centre-plate-hole-bottom-3": [262.6, 2073.7], "centre-plate-hole-bottom-4": [206.4, 2073.7], "centre-plate-slot-1": [334.8, 1986.2], "centre-plate-slot-2": [281.3, 1987.8], "centre-plate-dot-1": [222.5, 1982.2], "centre-plate-hole-row2-1": [356.2, 199.5], "centre-plate-hole-row3-1": [356.4, 860.8], "centre-plate-hole-row3-2": [224.8, 862.8], "centre-plate-mark-1": [336.5, 201.2], "centre-plate-mark-2": [280.8, 201.0], "centre-plate-mark-3": [244.5, 200.2], "centre-plate-mark-4": [222.3, 201.0], "centre-plate-mark-5": [336.6, 862.4], "centre-plate-mark-6": [244.3, 861.4], "centre-plate-mark-7": [244.0, 1983.3], "centre-plate-mark-8": [306.4, 1979.5], "centre-plate-mark-9": [359.6, 1984.2], "side-plate-hole-1": [20.1, 100.0], "side-plate-hole-2": [82.0, 100.0], "side-plate-hole-3": [124.0, 100.0], "side-plate-dot-1": [82.0, 1010.0], "side-plate-dot-2": [144.0, 1010.0], "side-plate-dot-3": [153.9, 480.2], "side-plate-dot-4": [148.8, 504.9], "side-plate-dot-5": [117.9, 518.2], "side-plate-dot-6": [173.5, 515.1], "side-plate-dot-7": [54.0, 1896.6], "side-plate-dot-8": [109.6, 1912.4], "side-plate-dot-9": [246.6, 219.1], "plan-square-1": [231.9, 2003.2], "plan-square-2": [254.2, 2003.2], "plan-square-3": [347.2, 2003.2], "plan-square-4": [368.9, 2003.2], "plan-slot": [300.4, 2003.2], "page3-square-head-1": [275.2, 456.8], "page3-square-head-2": [330.7, 456.8], "page3-square-mid-1": [275.2, 1040.6], "page3-square-mid-2": [330.7, 1040.6], "page3-square-foot-1": [275.2, 2029.1], "page3-square-foot-2": [330.7, 2029.1], "page3-triangle": [303.0, 414.6], "page3-dot": [229.3, 440.3], "plan-screw-1": [217.3, 2111.1], "plan-screw-2": [275.4, 2108.8], "plan-screw-3": [325.3, 2108.5], "plan-screw-4": [382.6, 2111.0]}, "right": {"end-cap-rear": [578.2, 10.5], "end-cap-front": [21.8, 10.5], "base-rim": [300.0, 2129.6], "base-rail-rear": [499.5, 2109.3], "base-rail-front": [100.5, 2109.3], "foot-rear": [582.2, 2127.1], "foot-front": [17.8, 2127.1], "centre-plate": [300.0, 1060.3], "centre-plate-foot": [300.0, 2106.2], "centre-plate-hole-top-1": [218.3, 47.9], "centre-plate-hole-top-2": [267.4, 112.0], "centre-plate-hole-top-3": [309.7, 134.3], "centre-plate-slot-head-1": [264.8, 130.8], "centre-plate-slot-head-2": [331.6, 133.2], "centre-plate-hole-bottom-1": [227.8, 2073.7], "centre-plate-hole-bottom-2": [286.7, 2073.7], "centre-plate-hole-bottom-3": [337.4, 2073.7], "centre-plate-hole-bottom-4": [393.7, 2073.7], "centre-plate-slot-1": [265.2, 1986.2], "centre-plate-slot-2": [318.7, 1987.8], "centre-plate-dot-1": [377.6, 1982.2], "centre-plate-hole-row2-1": [243.9, 199.5], "centre-plate-hole-row3-1": [243.8, 860.8], "centre-plate-hole-row3-2": [375.4, 862.8], "centre-plate-mark-1": [263.7, 201.2], "centre-plate-mark-2": [319.4, 201.0], "centre-plate-mark-3": [355.6, 200.2], "centre-plate-mark-4": [377.8, 201.0], "centre-plate-mark-5": [263.6, 862.4], "centre-plate-mark-6": [355.8, 861.4], "centre-plate-mark-7": [356.1, 1983.3], "centre-plate-mark-8": [293.8, 1979.5], "centre-plate-mark-9": [240.5, 1984.2], "side-plate-hole-1": [580.1, 100.0], "side-plate-hole-2": [518.1, 100.0], "side-plate-hole-3": [476.1, 100.0], "side-plate-dot-1": [518.0, 1010.0], "side-plate-dot-2": [456.0, 1010.0], "side-plate-dot-3": [446.1, 480.2], "side-plate-dot-4": [451.3, 504.9], "side-plate-dot-5": [482.2, 518.2], "side-plate-dot-6": [426.5, 515.1], "side-plate-dot-7": [546.0, 1896.6], "side-plate-dot-8": [490.4, 1912.4], "side-plate-dot-9": [353.4, 219.1], "plan-square-1": [368.1, 2003.2], "plan-square-2": [345.8, 2003.2], "plan-square-3": [252.8, 2003.2], "plan-square-4": [231.2, 2003.2], "plan-slot": [299.7, 2003.2], "page3-square-head-1": [324.8, 456.8], "page3-square-head-2": [269.4, 456.8], "page3-square-mid-1": [324.8, 1040.6], "page3-square-mid-2": [269.4, 1040.6], "page3-square-foot-1": [324.8, 2029.1], "page3-square-foot-2": [269.4, 2029.1], "page3-triangle": [296.9, 414.6], "page3-dot": [370.7, 440.3], "plan-screw-1": [382.6, 2111.1], "plan-screw-2": [324.6, 2108.8], "plan-screw-3": [274.6, 2108.5], "plan-screw-4": [217.3, 2111.0]}}, "top": {"150": {"top-rail-left": [35.2, 300.0], "top-rail-right": [114.8, 300.0], "cross-tube": [75.0, 331.7], "rear-beam": [75.0, 15.9], "end-cap-rear-left": [37.5, 21.8], "end-cap-rear-right": [112.5, 21.8], "end-cap-front-left": [37.5, 578.2], "end-cap-front-right": [112.5, 578.2]}, "200": {"top-rail-left": [35.2, 300.0], "top-rail-right": [164.8, 300.0], "cross-tube": [100.0, 331.7], "rear-beam": [100.0, 15.9], "end-cap-rear-left": [37.5, 21.8], "end-cap-rear-right": [162.5, 21.8], "end-cap-front-left": [37.5, 578.2], "end-cap-front-right": [162.5, 578.2]}, "250": {"top-rail-left": [35.2, 300.0], "top-rail-right": [214.8, 300.0], "cross-tube": [125.0, 331.7], "rear-beam": [125.0, 15.9], "end-cap-rear-left": [37.5, 21.8], "end-cap-rear-right": [212.5, 21.8], "end-cap-front-left": [37.5, 578.2], "end-cap-front-right": [212.5, 578.2]}, "300": {"top-rail-left": [35.2, 300.0], "top-rail-right": [264.8, 300.0], "cross-tube": [150.0, 331.7], "rear-beam": [150.0, 15.9], "end-cap-rear-left": [37.5, 21.8], "end-cap-rear-right": [262.5, 21.8], "end-cap-front-left": [37.5, 578.2], "end-cap-front-right": [262.5, 578.2]}, "380": {"top-rail-left": [35.2, 300.0], "top-rail-right": [344.8, 300.0], "cross-tube": [190.0, 331.7], "rear-beam": [190.0, 15.9], "end-cap-rear-left": [37.5, 21.8], "end-cap-rear-right": [342.5, 21.8], "end-cap-front-left": [37.5, 578.2], "end-cap-front-right": [342.5, 578.2]}}, "bottom": {"150": {"base-rim": [75.0, 300.0], "base-rail-left": [35.2, 292.0], "base-rail-right": [114.8, 292.0], "foot-rear-left": [29.4, 17.8], "foot-rear-right": [120.5, 17.8], "foot-front-left": [29.4, 582.2], "foot-front-right": [120.5, 582.2], "base-plate-hole-1": [12.1, 43.1], "base-plate-hole-2": [12.1, 103.0], "base-plate-hole-3": [12.1, 148.0], "base-plate-hole-4": [12.1, 288.1]}, "200": {"base-rim": [100.0, 300.0], "base-rail-left": [35.2, 292.0], "base-rail-right": [164.8, 292.0], "foot-rear-left": [29.4, 17.8], "foot-rear-right": [170.5, 17.8], "foot-front-left": [29.4, 582.2], "foot-front-right": [170.5, 582.2], "base-plate-hole-1": [12.1, 43.1], "base-plate-hole-2": [12.1, 103.0], "base-plate-hole-3": [12.1, 148.0], "base-plate-hole-4": [12.1, 288.1]}, "250": {"base-rim": [125.0, 300.0], "base-rail-left": [35.2, 292.0], "base-rail-right": [214.8, 292.0], "foot-rear-left": [29.4, 17.8], "foot-rear-right": [220.5, 17.8], "foot-front-left": [29.4, 582.2], "foot-front-right": [220.5, 582.2], "base-plate-hole-1": [12.1, 43.1], "base-plate-hole-2": [12.1, 103.0], "base-plate-hole-3": [12.1, 148.0], "base-plate-hole-4": [12.1, 288.1]}, "300": {"base-rim": [150.0, 300.0], "base-rail-left": [35.2, 292.0], "base-rail-right": [264.8, 292.0], "foot-rear-left": [29.4, 17.8], "foot-rear-right": [270.6, 17.8], "foot-front-left": [29.4, 582.2], "foot-front-right": [270.6, 582.2], "base-plate-hole-1": [12.1, 43.1], "base-plate-hole-2": [12.1, 103.0], "base-plate-hole-3": [12.1, 148.0], "base-plate-hole-4": [12.1, 288.1]}, "380": {"base-rim": [190.0, 300.0], "base-rail-left": [35.2, 292.0], "base-rail-right": [344.8, 292.0], "foot-rear-left": [29.4, 17.8], "foot-rear-right": [350.6, 17.8], "foot-front-left": [29.4, 582.2], "foot-front-right": [350.6, 582.2], "base-plate-hole-1": [12.1, 43.1], "base-plate-hole-2": [12.1, 103.0], "base-plate-hole-3": [12.1, 148.0], "base-plate-hole-4": [12.1, 288.1]}}}""")
DIM = re.compile(r"(\d[\d.]*) (columns|rows|pixels) (across|down) at ([\d.]+) mm per pixel")


def load(model):
    path = ROOT / "library" / "devices" / "chatsworth" / model / "device.yaml"
    return yaml.safe_load(path.read_text())


def decor(dev, view):
    return {d["id"]: d for d in dev["views"][view]["panel"]["decor"]}


def flat(text):
    return " ".join(text.split())


def note(model, key):
    return flat(load(model)["provenance"][key]["note"])


def centre(v):
    return [v["at"][0] + v["size"][0] / 2, v["at"][1] + v["size"][1] / 2]


def close(got, want):
    """Each figure is written to one decimal place, so a centre is within 0.16 of the computed one."""
    assert all(abs(a - b) <= 0.16 for a, b in zip(got, want)), (got, want)


def ref(token, dev):
    if token is None:
        return None
    if isinstance(token, str):
        return dev["chassis"][{"W": "width", "D": "depth", "H": "height"}[token]]
    return token


@pytest.mark.parametrize("model", MODELS)
def test_every_sized_row_matches_the_drawn_items(model):
    dev = load(model)
    assert dev["chassis"]["width"] == WIDTHS[model[4]]
    for row in ROWS:
        for views, pattern, w, h in row["fits"]:
            for view in views.split("|"):
                items = [v for k, v in decor(dev, view).items() if re.fullmatch(pattern, k)]
                assert items, (row["id"], view, pattern)
                for it in items:
                    for got, want in zip(it["size"], (ref(w, dev), ref(h, dev))):
                        assert want is None or abs(got - want) <= 0.051, (row["id"], it["id"], got, want)


@pytest.mark.parametrize("model", MODELS)
def test_each_view_carries_the_counted_number_of_frame_items(model):
    dev = load(model)
    kinds = set(COUNTS["kinds"])
    got = {view: len([v for v in decor(dev, view).values() if v["kind"] in kinds]) for view in ("top", "bottom", "left", "right")}
    assert got == COUNTS["views"]
    assert sum(got.values()) == COUNTS["total"]


@pytest.mark.parametrize("model", MODELS)
def test_every_frame_item_stands_where_the_table_places_it(model):
    dev = load(model)
    for view in ("left", "right"):
        d = decor(dev, view)
        for id_, want in PINS["side"][view].items():
            close(centre(d[id_]), want)
    for view in ("top", "bottom"):
        d = decor(dev, view)
        for id_, want in PINS[view][str(dev["chassis"]["width"])].items():
            close(centre(d[id_]), want)


@pytest.mark.parametrize("model", MODELS)
def test_the_cross_tube_stands_at_its_table_percent_of_the_way_from_the_front(model):
    dev = load(model)
    tube = decor(dev, "top")["cross-tube"]
    row = next(r for r in ROWS if r["id"] == "tube-place")
    front, rear = [v["at"][1] + v["size"][1] / 2 for v in (decor(dev, "top")["end-cap-front-left"], decor(dev, "top")["end-cap-rear-left"])]
    got = (front - (tube["at"][1] + tube["size"][1] / 2)) / (front - rear) * 100
    assert abs(got - row["percent"]) < 0.2, got
    assert "cross-tube-front" not in decor(dev, "top"), "the tube stands at mid-depth, not at the front end"


@pytest.mark.parametrize("model", MODELS)
def test_the_right_face_draws_the_far_plates_head_pattern_not_the_near_plates(model):
    d = decor(load(model), "right")
    assert [k for k in d if k.startswith("centre-plate-hole-top-")] == [f"centre-plate-hole-top-{i}" for i in (1, 2, 3)]
    left = decor(load(model), "left")
    assert not any(k.startswith("centre-plate-slot-head-") for k in left)
    assert "centre-plate-hole-top-4" in left and "centre-plate-hole-top-4" not in d
    assert sum(1 for k in d if k.startswith("centre-plate-slot-head-")) == 2


@pytest.mark.parametrize("model", MODELS)
def test_the_triangle_is_a_motif_of_one_triangular_cell(model):
    row = next(r for r in ROWS if r["id"] == "p3-triangle")
    for view in ("left", "right"):
        tri = decor(load(model), view)["page3-triangle"]
        assert tri["pattern"] == "motif" and tri["pattern-pitch"] == tri["size"]
        w, h = tri["size"]
        assert len(tri["pattern-cells"]) == 1 and len(tri["pattern-cells"][0]) == 3
        assert abs(w - row["dims"][0]["mm"]) <= 0.051 and abs(h - row["dims"][1]["mm"]) <= 0.051


@pytest.mark.parametrize("model", MODELS)
def test_every_new_item_is_estimated_and_front_and_rear_are_unchanged(model):
    dev = load(model)
    kinds = set(COUNTS["kinds"])
    for view in ("top", "bottom", "left", "right"):
        new = [v for v in decor(dev, view).values() if v["kind"] in kinds]
        assert new and all(v["confidence"] == "estimated" for v in new)
    for view in ("front", "rear"):
        assert "decor" not in dev["views"][view].get("panel", {})


@pytest.mark.parametrize("model", MODELS)
def test_every_figure_the_note_names_is_in_the_table_with_its_direction_and_scale(model):
    text = note(model, "frame")
    table = {(d["px_s"], d["dir"], d["scale_s"]) for r in ROWS for d in r["dims"] if d["px_s"]}
    named = {(px, direction, scale) for px, _unit, direction, scale in DIM.findall(text)}
    assert named, "the note names no figure"
    assert named == table, (sorted(named - table), sorted(table - named))
    for row in ROWS:
        for sentence in row["sentences"]:
            assert sentence in text, sentence


@pytest.mark.heavy
@pytest.mark.parametrize("model", MODELS)
def test_the_count_of_scales_in_the_notes_equals_the_count_in_the_table(model):
    used = {d["scale"] for r in ROWS for d in r["dims"]}
    assert used == {s["id"] for s in SCALES}, "every scale is used and every row's scale is listed"
    assert len({s["shown"] for s in SCALES}) == len(SCALES)
    for key in ("frame", "method"):
        text = note(model, key)
        count = re.search(r"(\d+) scales", text)
        assert count and int(count.group(1)) == len(SCALES), key
    text = note(model, "frame")
    quoted = set(re.findall(r"([\d.]+) mm per pixel", text))
    assert quoted == {s["shown"] for s in SCALES}
    for n, s in enumerate(SCALES, 1):
        assert s["sentence"] in text, s["sentence"]
        assert abs(s["mm"] / s["px"] - float(s["shown"])) <= 0.5 * 10 ** -s["digits"] + 1e-9, s["id"]


@pytest.mark.parametrize("model", MODELS)
def test_gaps_say_what_is_left_and_no_stale_gap_remains(model):
    gaps = {g["what"]: g for g in load(model)["gaps"]}
    for gone in ("end-caps", "feet", "side-plate-holes", "centre-plate"):
        assert gone not in gaps
    assert gaps["end-fittings-front"]["scope"] == ["front", "rear"]
    assert gaps["track-rungs"]["scope"] == ["left", "right"], "the render shows the rungs in the side channel"
    rungs = flat(gaps["track-rungs"]["note"])
    assert "The left and right faces draw the guides but not the rungs." in rungs
    assert "The door plates hide the track in the front and rear elevations." in rungs
    assert "door-hinge-tabs" in gaps and "door-hook" in gaps and "mid-panel" in gaps
    assert all(g["reason"] == "vendor-silent" for g in gaps.values())
    track = flat(gaps["central-track"]["note"])
    assert NOTES["central-track"] in track
    assert "it is drawn as a strip" not in track, "the side faces draw the flat centre plate, not a strip"


@pytest.mark.parametrize("model", MODELS)
def test_the_notes_say_what_is_drawn_and_none_says_the_centre_is_open(model):
    notes = load(model)["provenance"]
    spine = flat(notes["spine"]["note"])
    assert "none is fitted" not in spine and "centre is open" not in spine
    assert "That kit is a separate part and is not drawn." in spine
    side = flat(notes["left"]["note"])
    assert "across the centre" not in side
    assert "The flat centre plate of the page 3 render stands between the channels." in side
    flats = {k: flat(notes[k]["note"]) for k in ("top", "bottom", "right", "method")}
    assert NOTES["top"] in flats["top"] and NOTES["bottom"] in flats["bottom"] and NOTES["method"] in flats["method"]
    assert "the bottom end is the top end again" not in flats["bottom"]
    assert "pale" not in flats["top"], "the beam is named by its place, and the five black devices have none that is pale"
    assert "Nothing was copied from a picture" not in flats["method"]
    assert "except the centre plate's head" in flats["right"]
    assert "The render's far plate shows its own head pattern, drawn on this face." in flats["right"]


@pytest.mark.parametrize("model", MODELS)
def test_no_added_sentence_is_over_25_words_and_no_banned_phrase(model):
    dev = load(model)
    prov = dev["provenance"]
    texts = [prov[k]["note"] for k in ("frame", "top", "bottom", "right", "method", "spine", "left")]
    texts += [g["note"] for g in dev["gaps"] if g["what"] in ("end-fittings-front", "track-rungs", "central-track", "mid-panel")]
    banned = [" ".join(w) for w in (("shared", "frame"), ("frame", "for", "the", "family"), ("one", "method"), ("pale", "beam"))]
    for text in texts:
        flat_text = flat(text)
        assert not any(p in flat_text.lower() for p in banned)
    assert "four feet" not in flat(prov["frame"]["note"]), "the render shows three feet"
    generated = [prov["frame"]["note"]] + [g["note"] for g in dev["gaps"] if g["what"] in ("end-fittings-front", "track-rungs", "central-track")]
    generated += [NOTES["top"], NOTES["bottom"], NOTES["method"]]
    for text in generated:
        for s in re.split(r"(?<=[.!?])\s+", flat(text)):
            assert len(s.split()) <= LIMIT, s
