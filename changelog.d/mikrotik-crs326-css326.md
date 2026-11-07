### Added
- MikroTik is a maker in the vendor registry (`mikrotik`, displayed MikroTik, role `both`: SwOS and RouterOS).
- `mikrotik/crs326-24g-2s-plus-rm`: the MikroTik CRS326-24G-2S+RM, a 1U Cloud Router Switch with 24
  10/100/1000 ports, two SFP+ cages and an RJ45 console, front and rear, from MikroTik's dimensions drawing.
  Its DC jack is a placed `common/dc-barrel` (`dc-in`) and exports a power port; no supply or fan is built in.
- `mikrotik/css326-24g-2s-plus-rm`: the MikroTik CSS326-24G-2S+RM, the SwOS-only Cloud Smart Switch of the same
  chassis, without the console jack. The `+` in a MikroTik model is `-plus` in its device name.
- `expand.py`: a layout block takes `attrs-by-n`, extra attrs for the port with that number (a passive-PoE-in jack
  among plain ones).

### Changed
- `dc-barrel` is placed on six devices, and the CSS326-24G-2S+RM quick guide is the one document that states a barrel
  size; the registry note and the DC design document say so.
