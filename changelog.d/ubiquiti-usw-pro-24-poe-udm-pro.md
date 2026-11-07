### Added
- The maker Ubiquiti (`ubiquiti` in `spec/schemas/vendors.yaml`, hardware) and its first two devices,
  both fixed 1RU rack models: `ubiquiti/usw-pro-24-poe` (USW-Pro-24-PoE, UniFi Switch Pro 24 PoE: 24
  Gigabit RJ45 ports, 16 PoE+ and 8 PoE++, and two 1/10G SFP+ ports) and `ubiquiti/udm-pro` (UDM-Pro,
  UniFi Dream Machine Pro: eight Gigabit LAN, one Gigabit WAN and two 10G SFP+ ports, with a 3.5 inch
  drive bay). Both carry a 1.3 inch touchscreen, an internal supply and the USP-RPS DC input. Neither
  has Etherlighting.
- `ubiquiti/lcm-touchscreen-1-3@1` (1.1.0), the 1.3 inch touchscreen on both models, drawn as a lit
  panel, and `ubiquiti/usp-rps-input@1` (1.1.0), their USP-RPS DC input, for the later Ubiquiti
  models. Both models share one chassis grey and draw their vent slots as plain bars.
- The USP-RPS input presents a registered connector key, `ubiquiti-usp-rps` in
  `spec/schemas/connectors.yaml`, and `ubiquiti/usp-rps-plug@1` (1.0.0) is the plug that mates it,
  estimated and marked as needing a drawing. This closes the two blocking findings of the connector
  scan on the new devices.
- DCIM device types `USW-Pro-24-PoE` and `UDM-Pro` in the NetBox and Nautobot exports, 1U.
