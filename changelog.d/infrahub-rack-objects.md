### Added
- **A rack-side writer for Infrahub objects** (`kit/rack/infrahub.js`). From a rack and its
  devices it writes the rack's site, the rack and one device per placed item as object
  documents, with the notes and the devices left out, and a README text that says what is
  not confirmed. Interfaces, modules and cables are not written yet. The file format has
  not been loaded into an Infrahub instance, and nothing is published with the other exports.
