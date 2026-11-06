### Changed
- The Mini-USB Type-B console of twelve Juniper switches is the placed `std/mini-usb@1` (interface
  `mini-usb-b`, whose plug is `generic/mini-usb-b-plug@1`) where it was panel art: the EX2200-C-12P
  and -12T, the EX2300-24P, -24T, -48P, -48T, -C-12P and -C-12T, and the EX3400-24P, -24T, -48P and
  -48T. Each places it as `console-usb` with the console role, centred where the art was, and says in
  a gap, `mini-usb-console-shell`, that the drawn shell is the registry's and not the maker's; the
  EX3400's old `mini-usb-console-port` gap is gone. Each takes a minor with its lock, and each of its
  exported device types gains a `Console (mini-USB)` console port of type `usb-mini-b` beside its
  RJ-45 console; no port or interface that was exported is renamed or retyped, and a DCIM that
  imported a device type keeps its old console list until it is re-imported.
- The USB-A receptacles of the EX2200-C-12P and -12T, EX2300-24MP, -48MP, -C-12P and -C-12T and the
  MikroTik CCR2116-12G-4S+ and CRS418-8P-8G-2S+RM were already placed parts; the box drawn round each
  is named `port-shell` (Juniper) or `bezel` (MikroTik) instead of `usb-shell` or `usb-bezel`, so
  lint L197 no longer reads it as a port drawn as art. The EX2300-24MP, -48MP and the two MikroTik
  devices take a patch with the lock and the drawing version line of their exported device types;
  nothing is drawn differently. L197 no longer warns on any of the sixteen devices for a console or
  a USB receptacle (30 entries).
