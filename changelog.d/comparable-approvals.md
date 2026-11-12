### Added
- **Comparable fact: `approvals`** (#112, `spec/tools/portrayal/comparable.py`).
  `comparable-facts.json` gains one fact, `approvals`, read from `certifications`
  (33 devices from Arista, Cisco, CyberPower, Eaton, Edgecore and Ubiquiti) and
  `other-approvals` (2 UfiSpace devices), 35 devices in all, so the marks a box
  carries line up under one heading. The values are safety marks, EMC marks and
  country approvals as the maker prints them, often several in one string; each is
  kept whole and is not split, and the fact's published note says so. No device
  carries both keys. The neighbouring spellings (`certification`,
  `product-compliance`, `psu-approvals`, `regulatory`, `regulatory-model`,
  `compliance-programme`) are other claims and are not sources, and `encryption`
  is left as it was. Nothing is renamed, no device file changes and no export
  moves; the unclaimed-spelling census loses two spellings. This closes no
  record. A fact name, once published, is a key to add to and not to rename.
