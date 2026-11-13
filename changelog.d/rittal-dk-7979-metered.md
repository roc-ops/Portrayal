### Added
- Seven Rittal DK 7979 metered PDUs: the .210, .230, .235, .236, .238, .240
  and .242. Each is a 0U strip with a fixed 16 A cord, unswitched outlets and
  the PDU controller. The controller carries a display, two Ethernet jacks, a
  CAN bus jack and an RS232 jack. It also has a USB-A port, a digital input and
  an alarm relay output. The new parts are `rittal/pdu-controller@1`,
  `rittal/pdu-cover-plate@1`, `rittal/pdu-digital-input@1` and
  `rittal/pdu-alarm-relay@1`. The phase plates are drawn as frames round each
  outlet block. The connector registry gains the key `pdu-io-header` for the
  two small headers. The library gains seven device rows and no existing row
  changes.
