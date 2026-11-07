### Added
- A connector key in `connectors.yaml`, `iec-c16`, naming the AC appliance inlet of the Juniper EX4400 1050 W and 1600 W supplies and never the C15 cord end that mates it. The guide types the inlet by its cord; C16 is the reading of the two supply contracts, and the note says so. No standard is held for it. No part presents it, so no slot is published.
- The family file of the part-conformance runner lists `iec-c16` under "power inlets (AC)", so `--by-family` places a cause on a part presenting it in that family.
