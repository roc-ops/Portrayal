### Added
- **A console server's serial lines export as console server ports.** A device
  placement that says `role: console-server` over `media: rj45-serial` is written
  to the NetBox and Nautobot device type's `console-server-ports`, named by its
  placement id and typed `rj-45`, and is not also written as an interface. A
  placement with `role: console` is still the box's own console port. No device
  in the library says `console-server` yet, so no existing export changes.
