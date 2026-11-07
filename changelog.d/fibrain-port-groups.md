### Changed
- The ports on the 53 Fibrain components that carry any (the LC duplex adapter, the six and twelve
  way LC and SC adapter holders and their rear faces, and the RJ45 connection modules XE, XQ and XR
  in their Cat.5, Cat.6 and Cat.6A forms) now join port groups, so a port on a holder seated in a
  panel says what it is for. Each holder groups its adapters as `traffic` with media `fiber`, its
  rear face groups the same adapters as a group of their own, each module groups its RJ45 jack as
  `traffic` with media `rj45`, and the adapter groups its two LC bores. No group states a speed:
  the Fibrain data sheets print a category and a fibre type for these passive ports and no rate.
  Part ids, positions and drawn geometry are unchanged; each component takes a minor and the two
  Fibrain devices that seat them a patch. This finishes the Fibrain namespace: every Fibrain
  component that composes a port part declares groups.
