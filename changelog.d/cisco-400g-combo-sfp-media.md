### Fixed
- The four Cisco 400G Combo line cards (`cisco/a9k-4hg-flex-se`, `a9k-4hg-flex-tr`,
  `a99-4hg-flex-se` and `a99-4hg-flex-tr`) mark each SFP cage with its `media`, from the
  port numbers in Cisco's Ethernet Line Card Installation Guide: ports 0-5, 10-15, 20-25
  and 30-35 are `sfp-plus`, ports 6-9, 16-19, 26-29 and 36-39 are `sfp28`. Before, all 40
  drew as `data-media="sfp"`. The ASR 9010, 9906, 9910, 9912 and 9922 chassis take a patch
  bump, and their DCIM exports now list the SFP28 ports as SFP28.
