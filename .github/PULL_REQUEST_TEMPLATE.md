<!-- One device, component or change per pull request. The reviewer reads this
     before the diff, so say what is true after the change and how you know. -->

## What this changes

<!-- One or two sentences. For a device: vendor and model, which faces, which
     configurations. For a component: the part and what seats it. -->

## Sources

<!-- What the geometry and facts were read from: datasheet title, hardware
     guide and section, photograph of the unit, measurement on hardware.
     No vendor PDFs, CAD, stencils or photographs are committed; cite them. -->

## Maturity claimed, and why

<!-- draft / modelled / verified, and what earns it. `verified` means no
     `estimated` value anywhere in the assembly, including placed components. -->

## Compared against the reference

<!-- Put the render beside the reference at matched scale and say what it
     showed. "Front render over the datasheet elevation at 2.2 px/mm: port
     pitch and PSU cut-out agree; the status lamp sits 0.6 mm low and is
     recorded as estimated." -->

## Gates run locally

- [ ] `./build.sh --device <name>` lints clean for this device (or `./build.sh` for a component change)
- [ ] `python3 spec/tools/portrayal/devicelock.py --library library` run **against main's lock first**; every device it named took the bump it asked for; then `--update`
- [ ] `./publish.sh --no-images` and the regenerated `library/exports` committed
- [ ] `python3 -m pytest spec/tests -q -n auto` passes (build first; it skips without `dist/`)
- [ ] A change a consumer could notice has its entry in a new file under `changelog.d/`, not in `CHANGELOG.md`
- [ ] No vendor material committed: no PDF, CAD, stencil, or photograph; dumps sanitised

<!-- What the tests cost: quote what CI's "Test time" summary flagged, or say
     nothing was flagged. A new test of five seconds or more says why a lint
     rule or a cheaper fixture could not answer the same question. -->

## Merge danger

<!-- CONTRIBUTING.md, "Merge danger", lists what makes a one-way door. -->

**Door:** <!-- two-way, or one-way and why -->

**Blast radius:** <!-- who notices if this is wrong: one device, every device
     seating a part, DCIM data already imported, kit consumers, CI only -->

## Anything a reviewer should look at first

<!-- A judgement you made, a figure you are unsure of, a rule you waived. -->
