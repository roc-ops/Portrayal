---
name: portrayal-vendor-intake
description: Use when preparing a new vendor or product line for Portrayal modelling - finding and staging datasheets, hardware guides, module references, rail and mounting-kit guides and photographs, then converting the PDFs with docling. Ends where portrayal-model-device begins, with a verified, converted corpus.
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

**An intake that starts from one URL is still an intake of the line.** Asked to
stage a single datasheet, find the product page it hangs from and take
everything that page publishes: the datasheet's siblings are usually one click
away and the install guide, not the datasheet, is the geometry source.

**Read the SKUs off the vendor's variant selector, not off a datasheet.** A
datasheet lists the variants its author was thinking of. The Amphenol 300CB08
datasheet names nine part numbers; the product page sells twelve, and the three
it omits have a datasheet of their own. Where a page offers two option groups
(fuse positions x input style), choosing one changes what the other offers, so
walk them breadth-first and read each SKU from its own variant page.

**Then cross-check against the ordering guide, in both directions.** Part
numbers in the guide with no page, and pages with no entry in the guide, both go
in COVERAGE.md by name. Neither list is the truth; the difference between them
is the finding.

## What to hunt, and what each source is for

| artefact | what it uniquely provides | typical count per line |
|---|---|---|
| **hardware install guide** (one per chassis family) | THE geometry source: chassis dimensions, FRU dimension tables when you are lucky, faceplate figures with callouts, slot numbering, power tables, grounding/clearance requirements | 10-30 |
| **module / interface-module reference** (one per line, if it exists) | the card catalogue: every orderable module, its weight, the chassis-support and module-compatibility tables, port-numbering figures. This ONE document is what let the MX module catalogue be built as data. It is NOT the power source - see below | 0-1 |
| **datasheet** (one per family) | overall dimensions, RU, weight, port counts, the box's own power figure | 5-20 |
| **studio photographs** (vendor image library / DAM) | colour, finish, construction, per-axis measurable elevations when straight-on | 2-3 per SKU |
| **community elevations** (NetBox devicetype-library) | fills DAM holes; already cropped to the rack face | varies |
| **document renders** (inside the guides) | when a vendor runs no public DAM (Dell), the manuals' rendered front/rear views per configuration ARE the elevation source - they arrive free at conversion time, so a thin photos/ folder does not mean thin photo coverage | many |
| **EOL doc archives** | vendors consolidate retired-product docs into zips; the only source for the oldest hardware | 0-1 zip |
| **the component maker's own datasheet** | when the field-replaceable part is bought in (a breaker, a fuse holder, a connector), the box vendor publishes a part number and nothing else; the outline drawing, terminal dimensions and sometimes a STEP model are on the maker's site | 1-3 per part family |
| **the vendor's cross-reference sheet** | a one-page "which breaker fits which panel" chart is this kind of line's compatibility matrix, and it is what reveals there are two part families, not one | 0-1 |
| **rail or mounting-kit installation guide** (one per kit) | the kit itself: its parts, how it assembles, its rack-depth range per hole type, rack types (4-post, 2-post, centre mount), travel for a slide, a factory preset | 1-5 |
| **rail sizing matrix** | which kit fits which chassis, and the depth range per chassis group; a matrix often gives one rail a different minimum on different chassis, which is a device-level override | 0-1 |
| **accessory table** (in the datasheet, ordering guide or HIG) | the kit SKUs, whether each ships in the box or is sold separately, normal or reversed mounting, and the cable management arm and strain-relief bar | 1 per family |
| **rack-mounting figures** (in the HIG) | the named ear positions (flush, recessed, mid-mount) and the one the box ships in; the reviewer checks the default against this figure | 1-4 per HIG |

**The four mounting sources are staged with the rest, each as a rule with
its check.** `chassis.ears` and `chassis.kits` are written right after the
panel (docs/rack-mounting-design.md), and they are read from these four.

- **A rail or mounting-kit guide is staged for every kit the accessory table
  names,** even when the faceplate is all you came for: it is a separate
  download, and one not fetched at intake is not fetched later. Check: every
  kit SKU in the accessory table has a guide in the corpus, or a named miss
  in COVERAGE.md.
- **Every edition of a rail document is staged, with its date.** Ranges
  change between editions, and review holds a kit to the newest source and
  names the one that lost. Check: `SOURCES.md` gives a date or a revision
  for each, and two editions of one document are both there.
- **A sizing matrix is staged whenever the line has one.** It is what gives
  one rail a different range on another chassis, which becomes an override on
  the device. Check: the matrix is in the corpus, or COVERAGE.md says the
  vendor publishes none and where you looked.
- **A rail document is a document.** It is converted with the rest and passes
  the same proof of conversion. Check: its range table reads correctly in the
  converted text, beside the page it came from.
- **A guide shared across a line is staged once.** Check: COVERAGE.md lists it
  against every model it covers, under the rail guide column.
- **The rack-mounting figures are found before modelling starts.** They name
  the ear positions and show the one the box ships in. Check: the page of
  each figure is noted against its model, or the miss is.

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

Amphenol Network Solutions (formerly Telect):

    product page       https://amphenol-ns.com/Product/<slug>            (plain HTML; one URL per variant under it)
    category listing   https://amphenol-ns.com/Our-Products/Product-Catalogue/rvdsfcatid/<n>/rvdsfpvn/<page>
    datasheet          https://amphenol-ns.com/Assets/P_DS_<part>.pdf    (a habit, not a rule: DS_P_<part>.pdf also occurs)
    install guide      https://amphenol-ns.com/Assets/P_IG_<part>.pdf
    ordering guide     https://amphenol-ns.com/Assets/P_OG_Power.pdf     (one per product area)
    gallery photos     https://amphenol-ns.com/DesktopModules/Revindex.Dnn.RevindexStorefront/Portals/0/Gallery/<uuid>.jpg   (600 px at most, angled)

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
- **The page can link an older document than the pattern URL serves.** One
  product page linked a 2020 install guide while the 2023 revision answered at
  the vendor's usual `P_IG_<part>.pdf` name, linked from nowhere. After
  crawling the links, probe the pattern anyway, and compare footers when both
  answer.
- **Cut the page before "related products".** A storefront page's gallery
  markup also carries the photos of whatever is "frequently purchased with"
  it; a regex over the whole page files a rack under a breaker panel.
- **De-duplicate photos by bytes, per product.** Variant pages re-serve the
  same shot under a new UUID, and half of what remains is the thumbnail of the
  other half. Report the count after de-duplication and say what the largest
  size is: a folder of 40 files can hold no measurable elevation at all.
- **A 403 to a command-line client is not absence either.** Some manufacturer
  sites refuse anything that is not a browser. Fetch through a browser session
  and say so in SOURCES.md, so the next person does not record a miss.
- **Note what robots.txt says about the asset path** and keep to the links the
  product pages publish, fetched once. A pattern probe is a handful of
  requests, not a crawl.
- **Save the pages you parsed.** The crawler, the saved HTML and the parsed
  manifest live beside the intake, and the crawler skips files already on
  disk. Fixing a parsing mistake is then a re-read, not a second visit.
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
artefact kind (guide, module reference, datasheet, photos, rail guide) — with each cell
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
- **Name converted output `<vendor>--<stem>`.** Converted figure sets from
  every vendor share one directory, and stems like `151881` or `Drawing_307491`
  mean nothing there and will collide.
- **Third-party documents get their own folder** (`third-party/`) and their
  own rows in SOURCES.md, so a breaker maker's datasheet is never cited as the
  panel vendor's.
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
   `extract.py` exits 1 when any file it was given FAILed (it still carries
   on past the failure), so the marker is trustworthy. Before that it
   printed `FAIL` and exited 0; for a log from an older run, grep `^FAIL`.
4. *Optional, only if you convert on another machine* (the maintainer runs
   docling on a separate GPU box; converting locally works, more slowly):
   `nohup ... &` survives the ssh dropping,
   but the launching ssh may hang holding stdout - launch, kill the ssh,
   verify by reconnecting and checking the process and the log.
5. Finish with one `--reclassify` pass over everything: banner/icon
   detection uses a cross-document hash pool that only exists at the end.
   Pass every PDF of the corpus in that ONE invocation - the pool is built
   from the files named on the command line, so a per-file reclassify
   counts only that file's repeats and keeps a banner that shows up fewer
   than ten times per document (a two-page datasheet always). Run it only
   once every file has a `raw.json`: `--reclassify` CONVERTS any file
   without one, in that same process, which is rule 1 broken - clear or
   set aside the FAILs first. The knobs, each shaped by a publisher that
   broke the default:
   - `--icon-px N` - the icon size floor (default 200). Too high for small
     module front views; the CH3000 corpus needs 80.
   - `--banner-max-h N` - a picture at least N px tall is never a banner
     (default off). For page-width charts drawn in the header strip colours,
     which share its hash: CH3000 needs 200 (every true banner is under 130).
     It cannot be a default: the Cisco cityscape banner is 370 tall and the
     Juniper "IN THIS SECTION" boxes reach 640.
   - `--no-banner` - the banner rule off entirely, for a publisher whose
     every figure is drawn at page width.
   Record the exact sort command in the intake `SOURCES.md`, so the next
   reclassify repeats it.
6. **A PDF that is pure vector converts to nothing, and exits 0.** A customer
   drawing with no text layer and no embedded images yields an empty `doc.md`
   and no pictures. Check for empty output after the run and render those
   pages (`pdftoppm -r 200 -png`) into the same output folder; such a drawing
   is often the only source for its part.
7. Watch the run with a monitor that reports **failures and completion,
   not progress** - and also reports the runner dying, because silence
   looks identical to "still working."

## Prove the conversion before modelling starts

- **Caption baseline:** for each document, `grep -cE '^Figure [0-9]+:'` in
  `doc.md` versus the kept-figure count in `index.json`. "No figure for this
  part" means something very different at 62/62 than at 39/62. Store the
  baseline beside the intake (`figure-baseline.tsv`).
- **The caption pattern is per publisher.** `Figure 12:` is one vendor's
  habit; another writes `Fig. 2-7:`. Read one converted guide before trusting
  a zero. And a list of figures without dot leaders matches the same pattern
  as the captions it lists, so count the LAST occurrence of each caption, not
  the first.
- **When caption attachment is unreliable, baseline by page.** Docling can
  hang a caption on the page-header logo and leave the drawing beside it
  uncaptioned, or merge four views on one page into one picture. The honest
  question then is "does every captioned page carry a kept figure that is not
  the logo", answered from the PDF's own text per page, and the handoff says
  to find figures by page.
- **The banner rule eats banner-shaped products.** The front of a 1RU panel
  is a wide, short picture that recurs across documents, which is exactly what
  the rule looks for; it dropped the front views of five panels. Look at every
  wide reject, not a sample, and re-sort with `--banner-max-h` when product
  faces are among them. Record the flag in COVERAGE.md for the next re-sort.
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

## Power figures: which book, and which rung

Two traps, both of which have already cost a re-do across the Juniper corpus.

**The module reference is not where the watts are.** It is the obvious place to
look and it is often silent, while the FRU power tables sit in the CHASSIS
guides - MX2K-MPC8E, MX2K-MPC9E, MIC3-100G-DWDM and SCB-MX were all found there
after seven contracts had already recorded "NOT STATED for this model in the
module reference extraction." That sentence was true of the book it named and
false of the corpus, and it reads as the second. **Never scope an absence claim
to one document.** Either say which books were searched, or search the corpus
and say that. An absence claim is a fact about the world and needs the same
sourcing as a number - it is what tells the next person to stop looking.

**A vendor power figure is a ladder, not a scalar.** The same part is printed at
25 C, 40 C and 55 C, and the rungs differ by enough to matter:
MIC-3D-4COC3-1COC12 is 33.96 W at 25 C and 36.48 W at 55 C. Three guides print
the 25 C figure bare, with no temperature anywhere near it, so an extractor that
takes the first watts it sees reads seven percent low and looks right. **Take the
maximum rung and record the ambient in `provenance.power`** - lint L52 asks for
that record. Two more things the row itself says and the number does not: a card
figure marked *without MICs* is the one that composes (the MICs answer for
themselves), and a figure marked *with optics* already includes them.

When extracting power in bulk, require a row to identify its own subject: ONE
cell exactly a part number, and an explicit temperature. A looser rule put the
MPC7E's 545 W onto the MPC6E.

## Then

*Optional, maintainer-only.* The maintainer keeps a private knowledge base of
converted guides; a contributor without one skips this paragraph, and the
`doc.md` files in `working/images/` serve the same purpose by grep.
Ingest the `doc.md` corpus into the knowledge base (one bundle per line) so
modelling-time questions are searchable. Leave out documents that converted to
no text; they are drawings, and they belong to the figure sets. A vendor the
knowledge base has not seen before has to be registered there before its
documents can be found, and granting access to it is the knowledge base
owner's step, not the intake's. **The ingest is done when a search returns the
new documents**, not when the write succeeds: a server that was already running
keeps its old index and its old access rules until it restarts.

Then hand off to
**portrayal-model-device** - whose first instruction, "sort the sources," now
has a sorted staging area, a sources ledger, converted figures with captions,
a completeness baseline, and a parsed compatibility matrix to sort.
