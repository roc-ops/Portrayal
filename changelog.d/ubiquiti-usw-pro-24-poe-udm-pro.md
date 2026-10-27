### Added
- The maker Ubiquiti (`ubiquiti` in `spec/schemas/vendors.yaml`, hardware) and its first two devices,
  both fixed 1RU rack models: `ubiquiti/usw-pro-24-poe` (USW-Pro-24-PoE, UniFi Switch Pro 24 PoE: 24
  Gigabit RJ45 ports, 16 PoE+ and 8 PoE++, and two 1/10G SFP+ ports) and `ubiquiti/udm-pro` (UDM-Pro,
  UniFi Dream Machine Pro: eight Gigabit LAN, one Gigabit WAN and two 10G SFP+ ports, with a 3.5 inch
  drive bay). Both carry a 1.3 inch touchscreen, an internal supply and the USP-RPS DC input. Neither
  has Etherlighting.
- `ubiquiti/lcm-touchscreen-1-3@1`, the 1.3 inch touchscreen on both models, and
  `ubiquiti/usp-rps-input@1`, their USP-RPS DC input, for the later Ubiquiti models.
- DCIM device types `USW-Pro-24-PoE` and `UDM-Pro` in the NetBox and Nautobot exports, 1U.
