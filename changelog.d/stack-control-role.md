### Added
- **`stack-control`, a group role for the control and sync jacks of a stacked
  pair** (#1042, `spec/schemas/device.schema.json`,
  `spec/schemas/component.schema.json`). A consumer that picks service ports by
  `data-group-role="traffic"` counted a stack control jack as a service port; it
  carries a control signal from the CPU. The role joins the enum in both schemas,
  after `management`. The Explorer's tree ranks it with `management`; the DCIM
  export lists an Ethernet jack of the role as an interface and does not mark it
  management-only, and still lists a jack that carries no Ethernet as nothing. A
  reader that does not know the value should treat it as none of the others.
  `docs/format-stability.md` says what `group` does and does not promise.

### Changed
- **The CSR310's STACK-CTRL and STACK-SYNC jacks are in one group, `stack-signals`,
  role `stack-control`** (#1042, `edgecore/csr310`). STACK-CTRL was in `stacking`
  with role `traffic`, and STACK-SYNC in `timing` with role `management`. The
  two stacking QSFP28 cages stay in `stacking`, role `traffic`, and `timing`
  keeps the BITS, PPS/ToD and GNSS jacks. The DCIM export of the CSR310 is
  unchanged.
