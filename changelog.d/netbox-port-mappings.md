### Added
- **NetBox module types state their front-to-rear binding as `port-mappings`.**
  NetBox 4.6 and later keep the binding in the module type
  (`PortTemplateMapping`), so each of the 63 module types with front ports
  (the FS and Fibrain panels and cassettes, the Smartoptics passive modules)
  now carries one `{front_port, front_port_position, rear_port,
  rear_port_position}` entry for every row of its fibre map, in the map's
  order, after its `front-ports`. An import of the type is then
  self-contained: no second step applies the fibre map. `ratio` and `band`
  have no field in a mapping and stay in the fibre map, which remains the full
  record. The Nautobot module types are unchanged, and so is every port name.
  **A type that carries `port-mappings` needs NetBox 4.6 or later to import
  its mappings**; the module types already needed 4.5.7 for nested bay tokens.
