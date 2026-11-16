### Added
- **Three 12U wall cabinets as rack products, `eaton/srw12u`,
  `ubiquiti/uacc-rack-12u-wall-450-g` and `ubiquiti/uacc-rack-12u-wall-450-p`**
  (#1119). Each is a `wall-cabinet` with 19 in rails and square holes, and states
  its front rail alone. The SRW12U is 600 x 637 x 450 mm, 22 kg, takes equipment
  up to 419 mm deep and carries 90.7 kg; its clear opening of 450.85 mm is read
  from the maker's drawing. The two Ubiquiti cabinets, glass door and perforated
  door, are 550 x 635 x 450 mm, take devices up to 325 mm deep, carry 50 kg and
  weigh 19 kg and 17.8 kg. The hole spacing and the unit numbering are stand-ins
  that each product's `gaps` names, and so is the Ubiquiti rail width. The
  SRW12U's data sheet and its drawing differ on its width and depth by 3 and 5
  mm; the dimensioned drawing is written. The doors, side panels, fans, cable openings,
  casters and wall plate are in each description and in a `gaps` entry: the rack
  product has no key for an enclosure or a base. Each rack type is exported for
  NetBox and Nautobot. Each product ships as an npm package,
  `@portrayal/racks-<maker>-<name>`.
