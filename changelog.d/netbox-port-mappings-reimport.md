### Changed
- `library/README.md` records what a running NetBox 4.7 does with a module-type export file that carries `port-mappings`: it imports as a new type with one
  template mapping per row, an instance of that type gets the same number of instance-level mappings, and importing the file again over an existing type is
  refused and changes nothing. Whether NetBox 4.5.x ignores the key or refuses the file is still untried.
