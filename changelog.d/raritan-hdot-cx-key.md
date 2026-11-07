### Added
- The connector key `raritan-hdot-cx`, the HDOT Cx outlet of a Raritan PX4 PDU, a hybrid of the IEC C13 and C19 outlets that takes a
  C14 or a C20 plug (Raritan PX4 Rack PDUs data sheet). Server Technology's outlet of the same name keeps its own key,
  `servertech-hdot-cx`: no document says the two are one connector.

### Changed
- `raritan/px4-cx-outlet@1` (1.0.0 to 1.1.0) presents `raritan-hdot-cx` and carries a mate point at the centre of its recess, an
  estimate. `generic/c14-plug@1` and `generic/c20-plug@1` (1.3.0 to 1.4.0) name the key among the outlets they enter, so a C14 or a
  C20 cord end can be laid to a PX4 Cx outlet. No device seats either plug, so no device takes a bump for them.
- The Raritan PX4-132AWA-E7M26V2 and PX4-5551WA-E7M26V2 (0.1.0 to 0.1.1) take a patch, because they place the Cx outlet, with their
  lock and the drawing version line of their exported device types. Their outlets still export as `other` labelled `Cx locking`,
  and no port, interface or id moves. This closes no row of the port records.
