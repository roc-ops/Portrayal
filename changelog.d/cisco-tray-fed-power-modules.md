### Changed
- The five Cisco ASR 9000 power modules that are fed through a power tray carry an `unmated` sentence that says where their cables land
  (`cisco/a9k-pwr-2kw-dc@1`, `cisco/a9k-pwr-3kw-ac@1` and `cisco/a9k-power-module-v2@1`, each 1.0.2 to 1.0.3, and
  `cisco/pwr-4p4kw-dc-v3@1` and `cisco/pwr-6kw-ac-v3@1`, each 1.0.0 to 1.0.1). Each module is drawn from the front of its tray. The DC
  source and return cables land on lugs over the terminal studs of the power tray, and the AC power cord plugs into a receptacle at the
  rear of the AC power tray. No tray is drawn, so none of the five presents an interface, a slot or a mate, and each sentence cites the
  pages of the Cisco hardware installation guide it rests on.
- The seven chassis that seat them (`cisco/asr-9006` and `cisco/asr-9904`, 3.3.1 to 3.3.2; `cisco/asr-9010`, 1.2.1 to 1.2.2;
  `cisco/asr-9906` and `cisco/asr-9910`, 2.0.1 to 2.0.2; `cisco/asr-9912` and `cisco/asr-9922`, 2.3.1 to 2.3.2) take a patch each, with
  their locks and the drawing version line of their exported device types (18 files in NetBox and Nautobot); the five modules' module
  types carry the new contract version (10 files). No port, interface or id moves, and nothing is drawn differently.
- Five rows of the port-usable records file are gone and its `cap:` is 170.
