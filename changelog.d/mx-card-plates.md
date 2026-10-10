### Changed
- The MX240, MX480 and MX960 card is one part, drawn once: the 22 horizontal
  MX card contracts (`juniper/scb-mx`, `dpc-r-4xge-xfp`, `dpce-20ge-2xge`,
  `dpce-2xge-xfp`, `dpce-40ge-tx`, `dpce-q-20ge-sfp`, `dpce-r-40ge-sfp`,
  `mpc-3d-16xge-sfpp`, `mpc10e-10c-mrate`, `mpc10e-15c-mrate`, `mpc1e-3d`,
  `mpc2e-3d`, `mpc3e-3d`, `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`,
  `mpc5e-100g10g`, `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate`, `ms-dpc`,
  `ms-mpc`, `mx-dpc-blank`) are @2 at 413.5 x 29.5, the ejector-lever
  envelope of Juniper's Visio stencil, with a 396.0 plate centred in it,
  measured off the MX240, MX480 and MX960 front photographs (#261). Their art
  is re-enveloped, not redrawn. The levers, the model name and the OK/FAIL
  status group are re-placed from the photographs, and the MIC windows of
  `mpc1e-3d`, `mpc2e-3d` and `mpc3e-3d` from the MX2010 photograph's ratios.
  On the 13 layout-derived cards, the port layout moves 8.4 mm right to clear
  the lever. `mx-dpc-blank@2` draws the blank's own short knobs and its 0/1
  mark instead of card levers.
- `juniper/mx240` 3.0.0 and `juniper/mx480` 3.0.0: every card slot is the
  card's 413.5 x 29.5 envelope at x 28.5, centred on the measured plate, with
  a 396.0 x 29.5 `opening`. The slot pitch is 31.0 on the MX240 (was 30.45) and
  31.3 on the MX480 (was 31.86; the photograph reads 31.2-31.5). The grey
  slot-number tab strip the plates no longer cover is chassis decor, with the
  slot numbers on their tabs. The MX480's front scale note is corrected: the
  photograph is isotropic to 0.8%, not 5.1% anisotropic.
- `juniper/mx960` 2.0.0: its fourteen slots seat the same horizontal cards at
  `rotate: 90`, footprint 29.5 x 413.5 with a 29.5 x 396.0 `opening`, on a 31.0
  pitch (was 30.1). The SCB slots take `juniper/scb-mx@2`, so an MX960 SCB now
  offers the RE-S-2000 as well as the RE-S-1300. The MX960 device type's `Accepts:`
  descriptions name the horizontal cards. Each module type's export comments
  now name one fewer author.

### Removed
- The MX960 vertical card twins, each replaced by the horizontal card at
  `rotate: 90`: `juniper/dpc-r-4xge-xfp-v@1` by `juniper/dpc-r-4xge-xfp@2`,
  `juniper/dpce-r-40ge-sfp-v@2` by `juniper/dpce-r-40ge-sfp@2`,
  `juniper/scb-mx960-v@1` by `juniper/scb-mx@2`, and
  `juniper/<base>-v960@1` by `juniper/<base>@2` for `dpce-20ge-2xge`,
  `dpce-2xge-xfp`, `dpce-40ge-tx`, `dpce-q-20ge-sfp`, `mpc-3d-16xge-sfpp`,
  `mpc10e-10c-mrate`, `mpc10e-15c-mrate`, `mpc1e-3d`, `mpc2e-3d`, `mpc3e-3d`,
  `mpc4e-3d-2cge-8xge`, `mpc4e-3d-32xge-sfpp`, `mpc5e-100g10g`,
  `mpc5e-40g10g`, `mpc7e-10g`, `mpc7e-mrate`, `ms-dpc` and `ms-mpc` (#261).
  Superseded for five of them: `juniper/dpc-r-4xge-xfp@2` and
  `juniper/scb-mx@2` were removed in turn for `@3` (#891, below), and
  `mpc1e-3d@2`, `mpc2e-3d@2` and `mpc3e-3d@2` are kept only as deprecated
  majors whose replacement is `@3` (#448). Those five `@3` are the majors
  to pin today.
- `juniper/re-s-1300-v@1`, which only `scb-mx960-v` seated, is replaced by
  `juniper/re-s-1300@1` in `juniper/scb-mx@2`. Superseded: both were removed
  in turn (#891, below), and today it is `juniper/re-s-1300@2` in
  `juniper/scb-mx@3`.
- `juniper/mx960-blank-v@1` is replaced by `juniper/mx960-blank@1`, drawn
  horizontally with the MX960 blank's own knobs. Its DCIM module type is
  renamed from `mx960-blank-v` to `mx960-blank`, so the export files
  `mx960-blank-v.yaml` are replaced by `mx960-blank.yaml`. **BREAKING for DCIM
  data already imported.** Superseded: the module type was renamed again, and
  today it is `DPC-SCB-BLANK`, in `DPC-SCB-BLANK.yaml` (#899, under Changed).
- The 22 horizontal card majors at @1, each replaced by its @2 above. The
  major to pin today is `@3` for `dpc-r-4xge-xfp`, `scb-mx`, `mpc1e-3d`,
  `mpc2e-3d` and `mpc3e-3d`, and `@2` for the other seventeen.
