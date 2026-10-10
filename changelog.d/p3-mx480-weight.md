### Fixed
- `juniper/mx480` 5.0.1: the weight comes from the hardware guide's Table 88,
  29.7 kg for the chassis with midplane, fan tray, air filter and cable
  management brackets and 100.26 kg for the maximum configuration
  (`weight-base-kg`, `weight-max-kg`). The "up to 163.5 kg" it carried was the
  guide's rack text, 163.5 lb (74.2 kg), read as kilograms; the false
  `weight-and-max-config` gap is gone (#886).
