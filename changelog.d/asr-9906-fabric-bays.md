### Changed
- The ASR 9906 (`cisco/asr-9906` 2.1.0) has five fabric card bays on its rear face, `fc-0` to `fc-4`, each taking the
  A99-SFC3-T (`cisco/a99-sfc3-t@2`), and the base configuration seats a card in each. Cisco's ASR 9000 Overview and
  Reference Guide counts five fabric cards for this chassis and says the switch fabric with five is 6+1 redundant; the
  IOS XR data sheet's System requirements table pairs the A99-SFC3-T with the ASR 9906; the chassis' rear stencil master
  draws the five-slot cage and prints FC0 to FC4. The bay positions are read off that master (no Cisco figure
  dimensions the cage) and the rest of the rear is still not drawn. The card's first major was drawn 43.7 mm wide, the
  slot envelope of its own stencil master, which does not stand five times on the cage's 38.36 mm pitch; `a99-sfc3-t@2`
  carries the 38.27 mm plate both masters agree on, and `@1` is kept, `superseded-by` the `@2`, so a saved rack that
  names it still resolves. One more of the ASR 9000 parts that no chassis accepted is now seated. The chassis' DCIM device types gain five module bays and the `Drawing version` line, and the card's module type shows `Contract version 2.0.0`.
