### Changed
- The ASR 9000 4th-generation -SE line cards are seated. `cisco/a9k-16x100ge-se` (1.1.0, A9K-16X100GE-SE) is
  accepted by the line-card bays of `cisco/asr-9006` (3.3.0), `cisco/asr-9010` (1.2.0), `cisco/asr-9904`
  (3.3.0), `cisco/asr-9906` (1.3.0), `cisco/asr-9910` (1.3.0), `cisco/asr-9912` (2.2.0) and `cisco/asr-9922`
  (2.2.0), 56 bays. `cisco/a99-32x100ge-se` (1.2.0, A99-32X100GE-SE) is accepted by the same chassis except
  the 9006 and 9010, 44 bays. Both are placed as an inference: no held Cisco document names either part number
  beside a chassis, so each is seated where its -TR sibling's data sheet row puts the -TR, and the contracts
  and chassis say so. The `unplaced` sentences are gone. Every bay, default and configuration is unchanged, and
  the cards' power stays unpublished. The DCIM device types of the seven chassis differ only in the `Accepts:`
  text of their line-card module bays and the description sentence the exporter writes.
