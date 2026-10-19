### Added
- **A vendor role `reseller`, and reseller listings** (#936,
  `spec/schemas/vendors.yaml`, `docs/listing-a-nos.md`). A reseller sells another
  maker's hardware under its own part numbers, and lists it the way a NOS vendor
  does: `devices/<reseller>/<id>/listing.yaml` pointing at the maker's device.
  A reseller listing says `model` (the seller's part number), `aliases`,
  `portfolio` and `source`, and carries no `nos`, `nos-versions` or `interfaces`
  (L56 refuses them, and a NOS vendor's listing still needs `nos`, which the
  listing schema no longer requires by itself). The DCIM export names it
  `<seller display>/<part>`, with the comments a NOS listing gets less the NOS
  line. `role` in `vendors.yaml` may now be a list, so a vendor that makes
  hardware and resells (`[hardware, reseller]`) says both; every existing entry
  is a single word and is published unchanged. **A consumer of `vendors.json`
  can now meet `reseller`, and a list in `role`.** No vendor uses either yet, so
  `vendors.json`, `listings.json` and every export are as they were.
