### Fixed
- A card's USB jack is a console port only when its placement says so, as on a
  device. The module export filed every `std/usb-a` part as a `usb-a` console
  from the ref alone, and had no micro-USB or USB-C console row; it now asks
  the device path's own decision (`device_console_row`): a USB-A or USB-C jack
  needs `role: console`, and a micro-USB jack is a console when its id, role or
  function says so. The USB storage and service ports on 14 Cisco ASR 9000
  RSP/RP cards, 10 Juniper RE/RCB cards and the two Dell 16G rear I/O boards no
  longer export as consoles; eight CommScope CH3000 modules gain their
  micro-USB console (`usb-micro-b`), and the Eaton G4 ENMC its USB-C console.
  **BREAKING for DCIM data already imported.**
- The CommScope CX3003C and CX3033N (1.0.1; CH3000 3.2.4) no longer call their
  micro-USB a console: both datasheets reserve it, with the RS-232 jack beside
  it, for factory use, so it exports nothing.
