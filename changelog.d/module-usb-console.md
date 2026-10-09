### Fixed
- A card's USB jack is a console port only when its placement says so, as on a
  device. The module export filed every `std/usb-a` part as a `usb-a` console
  from the ref alone, and had no micro-USB or USB-C console row; it now asks
  the device path's own decision (`device_console_row`). The USB storage and
  service ports on 14 Cisco ASR 9000 RSP/RP cards, 10 Juniper RE/RCB cards and
  the Dell 16G rear I/O boards no longer export as consoles; the ten CommScope
  CH3000 modules gain their micro-USB console (`usb-micro-b`), and the Eaton
  G4 ENMC its USB-C console. **BREAKING for DCIM data already imported.**
