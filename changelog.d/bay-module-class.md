### Changed
- A device bay may state the class of module it takes as its `interface`, a key registered in the connector
  registry, with no `accepts` list and no `default` where the library holds no module for it. Lint L6 no longer asks
  such a bay for a default while no part mates the key, and asks again the day one does. The device type's export
  lists the bay with its name and position and a description of what it takes, and no port. The guard that held every
  bay's `interface` back now holds a stronger fact: a bay that states one takes no part beyond its own list. It closes
  no records row.
