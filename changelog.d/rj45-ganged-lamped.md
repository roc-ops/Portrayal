### Added
- **`common/rj45-ganged-lamped@1`: a ganged RJ-45 cell with two integrated
  corner lamps and no Ethernet claim** (#370). It is `std/rj45-ganged@2` plus the
  `led-a` and `led-b` lamps exactly where `common/rj45-ganged-eth@1` puts them,
  and carries no `media`. A timing, BITS or ToD jack whose housing has the two
  lamps takes it; the placement's role, media and group say what the jack is for.
  L76 accepts a timing jack on it and sends an Ethernet jack on it to
  `common/rj45-ganged-eth@1`; the DCIM export does not type it as Ethernet.

### Fixed
- **`edgecore/csr440` (1.1.2 to 2.0.0): the BITS jack draws its two lamps without
  saying Ethernet** (#370). `bits` moves from `common/rj45-ganged-eth@1` to
  `common/rj45-ganged-lamped@1`, and its L76 waiver is retired. The drawing and the
  port's type are unchanged. The lock asks for a major because a part swap with
  unchanged ids reads as a moved slot.
