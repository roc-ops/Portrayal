### Added
- The Amphenol Network Solutions nrgILS300CB08 (`amphenol-ns/nrgils300cb08`),
  the load-shedding member of the 300CB08 family: the nrg300CB08-CTRL front
  on a chassis 42.4 deeper, read off its own bottom view, with the plain
  stud-and-screw rear and a new centre block,
  `amphenol-ns/nrg-ils-rear-block@1` (nrgNET IN and OUT as RJ45s, a probe
  jack, three unnamed headers), which the DCIM exporter skips as not a DCIM
  port. In the DCIM exports it has two management interfaces, `mgmt` and
  `lan` (1000base-t), and two `dc-terminal` power ports. No existing device
  or export changes.
