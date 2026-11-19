### Added
- **The StarTech.com RK1219WALLOH hinged open wall frame as a rack product,
  `startech/rk1219walloh`** (#1116). A 12U `wall-frame` with 19 in rails and square
  holes for #10-32 cage nuts, a mounting depth of 502 mm, an outer box of
  555 x 647 x 602 mm, 22.73 kg and a static load of 63.37 kg, read from the
  maker's specification sheet and quick-start guide. The sheet labels its three
  sizes length, width and height without axes; length is read as front to back,
  and the product says so in a `gaps` entry. The frame lists its front rail
  alone, as the library does for every wall frame: the guide's two rear vertical
  rails, the four wall anchor points 16 in apart, the hinge and the swing are in
  the description and in `gaps` entries, because the rack product has no key for
  them. Its NetBox and Nautobot rack types are exported; the mounting depth is not
  in those exports. The product ships as an npm package,
  `@portrayal/racks-startech-rk1219walloh`.
