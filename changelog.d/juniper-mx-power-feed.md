### Changed
- Eight Juniper MX routers now say what feeds each build, so a tool filtering by feed no longer reads it from a
  configuration's name. The value comes from the supply the build seats and the hardware guide's input table for that
  supply. `power` is stated on the chassis of the MX80 (`ac`, the supply takes 90 to 264 VAC), the MX104 (`dc`, the supply
  takes 24, -48 or -60 VDC) and the MX10003 (`ac`, 90 to 140 and 180 to 264 VAC). The MX10004, MX10008 and MX10016 state
  `ac` and `hvdc` on the chassis, because the JNP10K-PWR-AC2 they seat takes 180 to 305 VAC or 190 to 410 VDC. The MX204
  states it on each build (`ac` on `ac`, `dc` on `dc`). The MX304 states `ac` on the chassis and differs on two builds:
  `dc` on `dc`, and `ac` with `hvdc` on `hvac-dc`, whose supply takes 200 to 277 VAC or 240 to 380 VDC. Nothing is renamed
  or removed and no port or bay changes. The eight devices (`juniper/mx80` 4.0.2 to 4.0.3, `juniper/mx104` 5.1.0 to 5.1.1,
  `juniper/mx204` 4.1.0 to 4.1.1, `juniper/mx304` 4.1.1 to 4.1.2, `juniper/mx10003` 0.2.21 to 0.2.22, `juniper/mx10004`
  4.0.2 to 4.0.3, `juniper/mx10008` 4.0.1 to 4.0.2 and `juniper/mx10016` 4.0.1 to 4.0.2) each take a patch, with their
  locks, and the `power` of each build in their `configs` file and in the `options` of `devices.json`. The lint baseline no
  longer records the missing feed (L119) of these eight devices. This closes no row of the port records.
