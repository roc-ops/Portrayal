### Added
- Six Perle IOLAN SCG L console servers: `perle/iolan-scg18-r-la`, `perle/iolan-scg18-r-le`, `perle/iolan-scg34-r-la`,
  `perle/iolan-scg34-r-le`, `perle/iolan-scg50-r-la` and `perle/iolan-scg50-r-le`. Each is the R chassis of its size
  with the 4G LTE radio. Its front adds a Micro-SIM slot and two SMA antenna jacks, WWAN 1 and WWAN 2.
- The -LA devices carry the radio for the Americas and the -LE devices the radio for Europe. They differ in their part
  numbers and bands only.
- Two new parts: `perle/scg-sim-slot`, the Micro-SIM slot, and `generic/sim-card-3ff`, the card that mates it. The slot
  has its own registered connector key, `sim-card-3ff`.
- The antenna jacks use the existing `common/sma-jack`. The SIM slot is read off the maker's drawing. The jacks are
  estimated from two photographs, so their positions are good to about 2 mm.
- Not drawn yet: the printed marks, the front labels and the DC builds with their terminal blocks.
