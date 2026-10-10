### Changed
- The two-position RELAY header on the ten AurCore AIS switches (`aurcore/ais2001`,
  `ais2001p`, `ais2002`, `ais2002p`, `ais2003`, `ais2003p`, `ais2004`, `ais2004p`, `ais4001`,
  `ais4001p`) is `common/terminal-header-508-2@2`, placed turned 90 at the same centre.
  Its two contacts now run parallel to the five of the power header, with the keyed side
  toward the RELAY legend, as the vendor's video and product images show. A seated
  `generic/terminal-508-2-plug@1` turns with it and overhangs the RELAY legend, as the
  five-position plug overhangs POWER. `@2` is 12.16 wide, the Phoenix Contact MSTBA 2,5/
  2-G-5,08 (1757242) width, with the contacts and the `mate` point (6.08, 6.05) 1.0 further
  in. Each of the ten devices takes a major, 0.1.x to 1.0.0. The header is still drawn 12.1
  high, which counts the solder pin; #873 asks whether it should be the installed 8.6 (#804).

### Removed
- `common/terminal-header-508-2@1`, which nothing places any more. Use
  `common/terminal-header-508-2@2` (#804). Superseded: `@2` was removed in turn
  (#873, below), and the major to pin today is `common/terminal-header-508-2@3`.
