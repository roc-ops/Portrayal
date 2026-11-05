### Added
- **Two StarTech.com open frame racks as rack products, `startech/4postrack12a`
  and `startech/4postrack42`** (#1118, #1109). Both are four-post frames with
  19 in rails and square holes for cage nuts. The 12U one has a rear rail depth
  range of 97 to 913 mm, an outer box of 534 x 657 x 913 mm with its casters
  fitted, 15.60 kg and a static load of 270.07 kg. The 42U one has a range of
  558.8 to 1016.0 mm, an outer box of 600 x 2040 x 1130 mm, 38.51 kg, a static
  load of 600.10 kg and a rolling load of 360.06 kg. Neither maker page prints a
  step for the range, so it states none and the Rack Builder takes any depth in
  it. The 42U sizes are read from figures printed in feet to one decimal, and
  each product's `gaps` says so. The casters, and the 42U's leveling feet and
  floor-anchoring base plate, are in each description and in a `gaps` entry: the
  rack product has no key for a base yet. Each rack type is exported for NetBox
  and Nautobot; the depth range is not in those exports, and the rolling load
  reaches the Nautobot comment only. Each product ships as an npm package,
  `@portrayal/racks-startech-<name>`.
