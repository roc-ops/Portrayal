### Added
- `rack.json` gives each device that lists rail kits a `kit` key with the default kit's `ref`
  and `motion`, and the `depth` range or `preset` of its one configuration, so a rack tool
  need not open the device's `configs.json`. The default is the `in-box` kit, else the first
  listed. A preset with no range is published without a `depth` key. A device with no kit has
  no key. The key is optional and `format` stays 1.
