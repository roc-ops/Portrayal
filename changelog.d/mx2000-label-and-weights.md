### Added
- `juniper/mx2008`, `mx2010` and `mx2020` state `weight-base-kg` and `weight-max-kg`
  from their hardware guides' physical-specification tables, with the table named
  in `weight-note`: 118.39 and 336.66 kg (AC chassis; the DC chassis is 301.55 kg),
  146.96 and 446.79 kg, and 177.1 and 622.1 kg. The three device types gain a
  weight in their DCIM exports (#996).

### Fixed
- The MX2008 front prints `CB-RE 0` and `CB-RE 1` over the two control boards, as
  its chassis does; the bays and descriptions keep the guide's name, RCB. The label
  strip above the line-card cage moves up 23.8 mm to the studio front photograph;
  the cage already sat where the photograph puts it, so it does not move. The
  MX2008 elevation image changes (#996).
