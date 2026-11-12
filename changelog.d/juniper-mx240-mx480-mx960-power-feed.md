### Changed
- Three more Juniper MX routers now say what feeds each build, so a tool filtering by feed no longer reads it from a
  configuration's name. The value comes from the supply the build seats and the input table the hardware guide prints for
  that supply. The MX240 states `dc` on its chassis, because its `base` and `dc` builds seat the DC supply, and `ac` on its
  `ac` build, whose supply takes 100 to 240 VAC. The MX480 states `ac` on its chassis and `dc` on its `dc` build, whose
  supply takes -40.5 to -72 VDC. The MX960 states `ac` on its chassis: every build seats the AC supply, which takes 200 to
  240 VAC. No guide prints a second input for any of these supplies, so no build lists both. Nothing is renamed or removed
  and no port or bay changes. The three devices (`juniper/mx240` 6.6.0 to 6.6.1, `juniper/mx480` 7.5.0 to 7.5.1 and
  `juniper/mx960` 6.2.0 to 6.2.1) each take a patch, with their locks, and the `power` of each build in their `configs`
  file and in the `options` of `devices.json`. The lint baseline no longer records the missing feed (L119) of these three
  devices. This closes no row of the port records.
