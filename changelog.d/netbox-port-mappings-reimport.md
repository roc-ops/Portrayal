### Changed
- `library/README.md` records what a running NetBox 4.7 did with a module-type export file that carries `port-mappings`: a copy of the file, with its model name
  changed, imported as a new type with one template mapping per row; an instance of that type got the same number of instance-level mappings; and importing the
  file again over an existing type was refused and changed nothing. Whether NetBox 4.5.x ignores the key or refuses the file is still untried.
