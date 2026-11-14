### Added
- A rolled bracket (`chassis.ears.rolled`) may state `strip`, a row of round holes or slots along its bar,
  and `ear-slots`, the slots in each ear. The rack elevation draws them and `configs.json` publishes them.
  Both are optional: a device that states neither builds as before. A new key in the device format,
  so a saved device that states one is refused by an older schema (Refs #538).
