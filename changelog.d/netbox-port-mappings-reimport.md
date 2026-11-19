### Changed
- `library/README.md` records what two runs on a running NetBox 4.7 did with a module-type export file that carries `port-mappings`.
  A copy of the file, with its model name changed, imported as a new type with one template mapping per row.
  An instance of that type got the same number of instance-level mappings.
  Importing the file again over an existing type was refused and changed nothing.
  Installing a module of such a type creates its instance mappings, and the fibre map is then refused.
  Nautobot is unchanged.
  Whether NetBox 4.5.x ignores the key or refuses the file is still untried.
