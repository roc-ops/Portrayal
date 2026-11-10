### Added
- The ALARM connector of the Juniper MX104 is a placed part: `std/vga@1`, the library's female HD-15 receptacle, which presents
  the registered `hd15` key, with `generic/hd15-plug@1` as the cable end that mates it. The hardware guide calls the port a
  15-pin D-type connector that takes a DE-15 alarm cable, and the front photograph shows three rows of five sockets in a metal
  shell with a dark insulator and a threaded hole either side. The two holes are drawn as dark discs. The connector's position
  is read off the photograph and is an estimate.
- `std/vga@1` gains an `insulator` field (1.1.0 to 1.2.0), the colour of the insulator and its outline in the face drawing. The default is the
  blue a VGA receptacle carries, so no existing drawing changes; the MX104 sets a dark grey. The part's 3D relief follows the field.

### Changed
- The MX104 takes a major (5.1.3 to 6.0.0): its `alarm` cutout, which was 19.4 x 10.8 as read off the photograph, takes the
  placed connector's own size of 20.47 x 11.4, and a cutout and the part in it must agree. The id `alarm` and every other id are
  kept, and one id is added (the placed connector). The twelve devices that place `std/vga@1` take a patch each, with their
  locks and the `Drawing version` line of their exported device types.
