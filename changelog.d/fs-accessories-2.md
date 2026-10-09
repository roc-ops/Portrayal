### Added
- FS.com rack fans: FANP3U3F (3U panel, three fans behind stamped guards, a
  rocker switch, front-to-back airflow) and the FANS1U2F and FANS1U4F 1U fan
  trays, each with the new `fs/fan-temp-controller@1` (two-digit display,
  LOAD and SET lamps, four keys). All three take power through the new
  `fs/fan-cord-5-15p@1`, which exports as a `nema-5-15p` power port.
- FS.com cantilever shelves FS-CFS-1U, IWEP1U350 and IWEP1U550 as sheet bodies:
  a vented floor, side walls to their profile, a rear lip on the IWEP, and the
  built-in ears drawn on the full rack-width face. Each states its usable
  surface and static load in `attrs.physical`.
- FS.com DIN rail brackets DINRAIL2U and DINRAIL4U: two side brackets with
  built-in ears, a rail panel and a 400 mm TS35 x 7.5 rail
  (`fs/din-rail-ts35-400@1`), with the rail's profile, length, height and
  setback range in `attrs.physical`.
