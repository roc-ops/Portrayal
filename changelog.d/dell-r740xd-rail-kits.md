### Added
- Three rail kits of the Dell PowerEdge R740 and R740xd: `dell/b6-sliding-rail-kit@1` (ReadyRails
  sliding, drop-in), `dell/b13-sliding-rail-kit@1` (stab-in/drop-in sliding) and
  `dell/b4-static-rail-kit@1` (ReadyRails static, for four-post and for two-post racks, flush or
  centre), with their rails `dell/b6-sliding-rail@1`, `dell/b13-sliding-rail@1` and
  `dell/b4-static-rail@1` and the optional cable management arm `dell/cable-management-arm-14g@1`.
  Each kit states the rack depth range of its rail per hole type (square, round, threaded) and
  its rail depth with and without the arm, from the Dell Rail Sizing and Rack Compatibility
  Matrix (Version 4.7, December 2023). The R740/R740xd Technical Guide (July 2019) prints older
  figures for the same rails, and the kits' provenance names where it differs. The strain-relief
  bar is a stated gap: no source page says it is offered for these systems. The rail and arm sizes
  are placeholders and each kit says so.

### Changed
- `dell/r740xd` version 30.0.2 lists the three rail kits as optional. It states no `chassis.ears`:
  its drawn front face already holds the ears and the VGA, power button, USB and health lamp they
  carry, so a viewer that asks for ears draws none over them, and no source page gives where the
  ears bolt. The default faces do not change.
