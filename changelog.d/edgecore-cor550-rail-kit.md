### Added
- `edgecore/cor550-rack-kit@1`, the rack mounting kit of the Edgecore COR550, and its two
  parts, `edgecore/cor550-rack-bracket@1` and `edgecore/cor550-rack-rail@1`. It is a
  telescoping kit of one four-post configuration with a `preset` of 630 and no `depth`: the
  quick start guide prints only the rear slide plate's 630 mm mark and no range, so the kit's
  `gaps` say the range is unknown. Both parts are plain placeholder plates with estimated sizes.

### Changed
- `edgecore/cor550` version 4.0.0 states its ears and its kit: `chassis.kits` lists the rack
  mounting kit as in-box, and `chassis.ears` gives the bracket's colour and its 0.25 mm lift.
  The four placed `common/rack-ear@1` ears (`ear-left`, `ear-right`, `rear-ear-left`,
  `rear-ear-right`) are gone, so a viewer that asks for ears draws the generic bracket out to
  the rack face instead of a 14 mm one-unit part. A rack file or a page that names one of those
  four paths no longer finds it. The default faces do not change.
