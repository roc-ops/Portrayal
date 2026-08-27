---
name: portrayal-vendor-intake
description: Use when preparing a new vendor or product line for Portrayal modelling - finding and staging datasheets, hardware guides, module references and photographs, then converting the PDFs with docling. Ends where portrayal-model-device begins, with a verified, converted corpus.
---

# Preparing a vendor intake for Portrayal

The modelling skill starts at "sort the sources you have." This skill is
everything before that moment: deciding what to hunt, finding it, staging it
where it survives, converting it, and proving the conversion is complete.

The difference it makes is measured. The ASR 9000 intake was assembled ad hoc
and the models built from it needed a long tail of corrections - a size filter
silently dropped every datasheet faceplate, ground pads went unmodelled across
seven chassis, dimensions were declared "not stated anywhere" that were in the
intake all along. The MX intake followed the process below and 15 chassis plus
a ~100-module catalogue went through review with the defect classes already
fenced. Same modeller, same gates - different preparation.

**Definition of done:** a staged corpus under `working/intake/<vendor>/<line>/`
with a `SOURCES.md` naming every artefact and its URL, a **`COVERAGE.md`
declaring what was found AND what was not** (see below - an intake that ends
in silence about its gaps is not done), converted figure sets under
`working/images/<stem>/`, a per-document caption baseline proving the
conversion is complete, and (for modular platforms) the support tables parsed
into a machine-readable matrix. Only then does modelling start.

## Stage 0 - enumerate the line before hunting anything

List every model FIRST, from the vendor's product-line page plus their EOL /
end-of-support page. EOL hardware is still racked everywhere and its
documentation is still (mostly) online; the MX set shipped seven EOL chassis
and reviewers asked for them by name. For switch lines, enumerate to the SKU
(EX4400-24P and EX4400-48P are different faceplates; MX240 and MX480 share
cards but not chassis). The list is the checklist everything below runs
against - without it, "done" means "what I happened to find."

## What to hunt, and what each source is for

| artefact | what it uniquely provides | typical count per line |
|---|---|---|
| **hardware install guide** (one per chassis family) | THE geometry source: chassis dimensions, FRU dimension tables when you are lucky, faceplate figures with callouts, slot numbering, power tables, grounding/clearance requirements | 10-30 |
| **module / interface-module reference** (one per line, if it exists) | the card catalogue: every orderable module, per-model power and weight, the chassis-support and module-compatibility tables, port-numbering figures. This ONE document is what let the MX module catalogue be built as data | 0-1 |
| **datasheet** (one per family) | overall dimensions, RU, weight, port counts, the box's own power figure | 5-20 |
| **studio photographs** (vendor image library / DAM) | colour, finish, construction, per-axis measurable elevations when straight-on | 2-3 per SKU |
| **community elevations** (NetBox devicetype-library) | fills DAM holes; already cropped to the rack face | varies |
| **document renders** (inside the guides) | when a vendor runs no public DAM (Dell), the manuals' rendered front/rear views per configuration ARE the elevation source - they arrive free at conversion time, so a thin photos/ folder does not mean thin photo coverage | many |
| **EOL doc archives** | vendors consolidate retired-product docs into zips; the only source for the oldest hardware | 0-1 zip |

## Finding them: probe, don't browse

Clicking through a documentation portal for 30 models wastes hours and misses
things. The vendor's URL patterns are regular; **write a probe script** that
candidates every (model x artefact-kind x naming-variant) URL and checks them
in parallel, then reads the hits. The MX/EX/QFX hunt probed ~1,150 URLs in
minutes and the misses were as informative as the hits. Keep the probe script
and its raw hit JSON beside the intake.

Verified patterns (Juniper; add other vendors' here as they are learned):

    hardware guide     https://www.juniper.net/documentation/us/en/hardware/<family>/<family>.pdf
    hardware guide EOL .../documentation/en_US/release-independent/junos/information-products/pathway-pages/<line>-series/<fam>/<model>.pdf
    oldest EOL         .../release-independent/downloads/<line>-series/<line>-series-doc-archives.zip
    datasheet          https://www.juniper.net/content/dam/www/assets/datasheets/us/en/<category>/<name>-datasheet.pdf
    studio photos      https://www.juniper.net/content/dam/www/assets/images/us/en/image-library/<line>-series/<KEY>/<KEY>-{front,rear,frontwtop}-high.jpg
    doc figures        https://www.juniper.net/documentation/us/en/hardware/<family>/images/g<NNNNNN>.png
    NetBox             https://raw.githubusercontent.com/netbox-community/devicetype-library/master/elevation-images/<Vendor>/<vendor>-<sku>.{front,rear}.png

Probe craft, learned the hard way:

- **A 200 with an HTML content-type is a miss** dressed as a hit (portals
  serve pretty 404s). Check content-type, not just status.
- **A redirect is information, not a failure.** Juniper's current-product
  datasheets 301 to HPE PSNow (`hpe.com/psnow/doc/<id>`); resolving the
  redirect target gives the authoritative ID even when the target host is
  unreachable from your sandbox. Record the IDs; fetch by browser if needed.
- **Photo folders may be per-SKU where docs are per-family** (EX/QFX DAM is
  keyed `ex4100-48p`, MX was keyed `mx480`). Probe both shapes.
- **A miss at one pattern is not absence.** EOL guides moved twice at Juniper;
  the oldest live only inside an archive zip whose existence a redirect to an
  "archives" page revealed. Follow the redirect chain before writing
  "no guide exists."
- `-front-high` / `-rear-high` DAM shots are straight-on studio elevations
  (1500-2100 px, port numerals legible); `-frontwtop-` is angled. Both are
  worth keeping; only the former is measurable.
- **General image search is a modelling-time tool, not a staging-time one.**
  Bulk image-search results are angled marketing shots, reseller composites
  and watermarked stock - unmeasurable, uncitable ("found on an image
  search" is not a provenance token) and often showing a different
  configuration than labelled. At modelling time, a targeted search answers
  a specific question ("does this SKU's 24-bay front carry the LCD?"), and
  a vendor's press/media kit is the official middle ground when a face
  needs colour or finish the document renders cannot give.

## The coverage report: say what you did NOT find

The intake's most important output after the corpus itself is **`COVERAGE.md`**:
the expected-artefact grid — every enumerated model crossed with every
artefact kind (guide, module reference, datasheet, photos) — with each cell
marked found / missing / not-applicable. Three rules make it honest:

- **A probe miss is a claim about your URL patterns, not about the world.**
  Every model on the enumerated list HAS a manual and a datasheet somewhere;
  "missing" means "not found by these methods", and the report says which
  methods were tried. The Dell intake wrote off an entire host as empty when
  the host was merely rejecting the probe's user agent — and separately
  listed models as undocumented that did not exist, because the model list
  itself had been enumerated from memory instead of the vendor's own pages.
  Both failure shapes belong in the report explicitly: *is this cell empty
  because the artefact is hidden, or because the model is imaginary?*
  Verify the enumeration against the vendor before trusting any zero.
- **End with a handoff list, not a shrug.** The report's final section is
  addressed to a human: "these artefacts exist but need a login / a support
  portal / a browser" (vendor support accounts, HPE PSNow, JS-only portals),
  with the exact URLs or IDs a person can chase. Someone on the team may
  have credentials the automation does not. "I'm done and we have part of
  it" is a failure mode; "here is the corpus, here are the seven holes and
  where a human can fill them" is the deliverable.
- **Gate the conversion on the report.** Before docling runs, whoever owns
  the intake reads COVERAGE.md and decides: fill the holes first, or accept
  them in writing. Holes accepted at intake become `gaps:` entries at
  modelling time — the chain of custody for what the library does not know.

## Staging: where it lives and how it is recorded

- Everything goes in the **MAIN checkout** `working/intake/<vendor>/<line>/`
  (`pdf/`, `datasheets/`, `photos/`), never in a worktree. `working/` is
  gitignored, and gitignored files in a worktree DIE with the worktree -
  the MX staging was lost exactly this way once and rebuilt from URLs.
- Write **`SOURCES.md`** as you stage: every file, its exact URL, image
  dimensions and view style for photos, and a "gaps to hunt" list. When the
  staging was rebuilt after the worktree loss, SOURCES.md was the only reason
  it took an hour instead of a day.
- Reference material is **never committed and never published**. Transcribe
  facts into contracts; the PDFs and photos stay in `working/`.

## Converting: docling, one process per file

`spec/tools/intake/extract.py` converts a PDF into `working/images/<stem>/`:
`doc.md` (full text), `fig-*.png` (EVERY picture), `raw.json` (no judgement),
`index.json` (kept figures + rejected-with-reason). Two stages on purpose:
conversion is expensive, classification is free, so save everything and sort
afterwards - retuning a filter is then a one-second re-read instead of an
hour of reconversion. Dependencies: `spec/tools/intake/requirements.txt`
(docling + pillow; GPU optional but several times faster).

The rules that two OOM kills and one lost evening bought:

1. **One fresh python process per PDF.** Docling holds a whole document in
   memory AND accumulates across documents in one process. A 963-page guide
   hit 52 GB and was killed; a chunked run in one process died ~2,900
   cumulative pages in. A loop that spawns `python extract.py <one-file>`
   per file is immune.
2. **Split anything over ~600 pages** into 300-page chunks first
   (`<stem>-p0001-0300.pdf` naming); reassembly is just the shared stem.
3. **Echo an EXIT marker per file** (`PERFILE-EXIT(<file>)=$?`). Over ssh,
   `cmd | tee log` eats exit codes and a dead run looks like a quiet one.
4. If converting on a remote box: `nohup ... &` survives the ssh dropping,
   but the launching ssh may hang holding stdout - launch, kill the ssh,
   verify by reconnecting and checking the process and the log.
5. Finish with one `--reclassify` pass over everything: banner/icon
   detection uses a cross-document hash pool that only exists at the end.
6. Watch the run with a monitor that reports **failures and completion,
   not progress** - and also reports the runner dying, because silence
   looks identical to "still working."

## Prove the conversion before modelling starts

- **Caption baseline:** for each document, `grep -cE '^Figure [0-9]+:'` in
  `doc.md` versus the kept-figure count in `index.json`. "No figure for this
  part" means something very different at 62/62 than at 39/62. Store the
  baseline beside the intake (`figure-baseline.tsv`).
- **Look at a sample of the rejects.** A size filter is shaped like the last
  vendor you looked at; the one that dropped every Cisco datasheet faceplate
  made "vendor published no pictures" out of "filter ate them."
- **Count the kept figures, report the kept count.** The raw picture count
  on disk flatters you by 2x (icons, banners); say which number any claim is.

## While the tables are fresh: parse the matrix

For a modular platform, the module reference's support tables ARE the
`accepts:` lists. Parse them into TSV/JSON **before** modelling - models x
chassis, module x carrier compatibility, per-model power - and hand-correct
the rows the PDF table-wrapping mangles (verify against the per-model
sections). The MX module catalogue shipped wired-by-vendor-table instead of
wired-by-what-was-photographed because this happened first. Docling wraps
model numbers with stray spaces (`MPC4E-3 D- 32XGE- SFPP`); normalise by
stripping whitespace, and treat a release number in a cell as "supported",
`-` as not.

## Then

Ingest the `doc.md` corpus into the knowledge base (one bundle per line) so
modelling-time questions are searchable, and hand off to
**portrayal-model-device** - whose first instruction, "sort the sources," now
has a sorted staging area, a sources ledger, converted figures with captions,
a completeness baseline, and a parsed compatibility matrix to sort.
