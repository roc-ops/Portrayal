### Changed
- **UfiSpace S9600-30DX, S9600-32X and S9600-72XC: the fronthaul timing
  standards are read as timing** (#112). Each datasheet's introduction states
  IEEE 802.1CM fronthaul and ITU-T G.8273.2 T-BC Class C, which the manifests
  filed under `compliance-programme`; they now close the device's `timing`
  value, so the `timing` fact in `comparable-facts.json` carries them and a
  comparison of timing support can see them. `compliance-programme` stays an
  unclaimed key on the S9500-30XS, where it holds a programme ("OCP Accepted
  and TIP DCSG compliant") and not a standard. Each of the three devices takes
  a patch version and a new lock; their exported device types' attribute
  comment lines move. No records row is closed and no drawing changes.
