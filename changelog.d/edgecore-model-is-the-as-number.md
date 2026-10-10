### Changed
- Four Edgecore devices now record the AS number as `model` and the catalogue
  name as a `kind: marketing` alias, as the rest of the line does (#916):
  `edgecore/dcs500` is `AS7816-64X` (alias `DCS500`), `edgecore/dcs510` is
  `AS9716-32D` (alias `DCS510`), `edgecore/cor550` is `AS7926-40XKFB` (alias
  `COR550`) and `edgecore/cor580` is `AS9926-24D` (alias `COR580`). Each data
  sheet's ordering table names the base model by the AS number. Device slugs
  are unchanged. No DCIM export is renamed: device types are named by SKU, and
  those of these four boxes and of the Arrcus, DriveNets, IP Infusion and SONiC
  listings of them keep their file names and `model`; their comments now list
  the catalogue name under "Also sold or listed as". The AIS800 line keeps
  `AIS800-*` as its model: its current data sheets and quick starts print no
  AS number, and `AS9817-64O` is recorded as a superseded name.
