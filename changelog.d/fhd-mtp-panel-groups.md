### Changed
- The ports on the four FHD MTP adapter panels (the 12-adapter MTP panels in Type A and Type B, the
  12-adapter MTP-16 panel and the 8-adapter MTP panel), front and rear contract each, now join a port
  group, so an adapter on a panel seated in an enclosure says what it is for. Each face has one group,
  `adapters`, with the role `traffic` and the media `fiber`. The FS datasheet prints the fibre mode, the
  adapter count and the key arrangement of these panels and no data rate, so no group states a speed;
  the key arrangement stays in `optical.polarity`. Part ids, positions and drawn geometry are unchanged;
  each contract takes a minor and the seven FHD enclosures that can seat them a patch.
