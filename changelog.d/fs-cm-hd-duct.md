### Added
- Six FS ABS high-density finger ducts, built hollow from their datasheet drawings, the
  only pictures FS publishes of them: `fs/cmh-uhd-sfdabs1u`, `fs/cmh-uhd-sfdabs2u` and
  `fs/cmh-uhd-sfdabs3u` (175 mm deep), `fs/cmh-hd-sfdabs3u` and `fs/cmh-hd-sfdabs4u`
  (112 mm deep), each a back plate with pass-through windows, two walls of ten T-shaped
  fingers and a hinged cover the explorer can pull; and `fs/cmh-bs-dfdabs2u`, a 2U
  dual-sided duct with a channel, fingers and a pullable cover on each side of a shared
  spine. Each states its cable capacity, `full-depth: false` and a vendor-silent weight.
  Where the drawing dimensions a cover taller than the rack unit, the device is that
  tall: `fs/cmh-uhd-sfdabs1u` 1.0.0 is 52 mm high over its 44 mm ears and
  `fs/cmh-bs-dfdabs2u` 1.0.0 is 93.5 mm over its 87 mm ears, the covers overhanging the
  units above and below; `ru` stays 1 and 2.
  The HD and UHD lines share one finger part each, `fs/cmh-hd-sfdabs-finger@1` and
  `fs/cmh-uhd-sfdabs-finger@1`; the other new parts are per model.
