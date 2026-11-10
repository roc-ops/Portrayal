### Changed
- The ports on two more modules now join a port group, so a port on one of them seated in a switch says what it is
  for. They are the Cisco C2960S-STACK FlexStack module of the Catalyst 2960-S (`c2960s-stack`), whose two stack
  ports STACK 1 and STACK 2 join a `stack-control` group, and the Digi CORE plug-in LTE modem (`core-lte-modem`),
  whose two SMA antenna jacks WWAN2 and WWAN1 join a `traffic` group. Both are counted from 1. Cisco's installation
  guide and Digi's product page print no data rate for these ports, so neither group states a speed. Part ids,
  positions and drawn geometry are unchanged; each contract takes a minor, and the seven devices that seat them
  (`ws-c2960s-24pd`, `ws-c2960s-24td`, `ws-c2960s-48fpd`, `ws-c2960s-48lpd`, `ws-c2960s-48td`, `connect-ez-16` and
  `connect-ez-32`) take a patch. No conformance row is closed or opened.
