### Changed
- The ports on seven CommScope back plates of the CH3000 chassis (the BP-A5, BP-A10, BP-F2, BP-F2-AL and
  BP-F4 plates, the BD31A8-100-H10F transmitter plate and the BP3400C quad receiver plate) now join port
  groups, so a port on a plate seated in the chassis says what it is for. The optical connectors, the SFP
  cages and the F-type jacks are `traffic`, in one group per connector family. The one optional SFP data
  port of the BP3400C, which carries the receivers' management data, is its own `management` group. The
  data sheets print no rate that one speed value states, so no group states a speed. Part ids, positions
  and drawn geometry are unchanged. Each contract takes a minor and the CH3000 chassis, which seats them,
  a patch. It closes no conformance record.
