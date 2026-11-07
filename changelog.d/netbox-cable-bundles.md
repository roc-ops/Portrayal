### Added
- **An export option "NetBox 4.6 or later" writes NetBox's own cable bundles**
  (#945, `kit/rack/dcim-rules.js`). `dcim.netbox` (`"4.6"` or later; off when
  blank, older or left out) makes the NetBox files carry a bundles file, imported
  before the cables file, and a `bundle` column in the cables file with the same
  name. A bundle is named `<site> <rack> <bundle name>`, since a rack's "Bundle 1"
  repeats from rack to rack and NetBox's bundle name is unique across the whole
  instance (`name`, 100 characters, `dcim/models/cables.py` at NetBox v4.7.2).
  The files are then `4-bundles.csv` and `5-cables.csv`, and the README has a
  step for each; a cable's description still names its bundle first. With no
  site the files are as with the option off and a note says why. A name over
  100 characters, or one that two bundles of a rack share, is left out and said,
  never cut. The kit cannot see a bundle the instance already has, and the
  README says so: NetBox refuses the whole bundles file if any bundle in it
  already exists, so remove those rows first (or skip the file on a re-import);
  the cables still join those bundles by name. **With the option off, every file is what it was.** Nautobot
  has no bundle object and is unchanged. `cableImportRows` takes `dcim` and
  returns `bundleFile`; `netboxFiles(dcim)` gives the file names; `kitReadme`
  reads the option from its `dcim`.
