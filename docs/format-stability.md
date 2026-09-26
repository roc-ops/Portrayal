# Format stability: what can change, and what says so

Portrayal has four version numbers, and each answers a different question. This
page says what each one covers, what raises it, and what the project promises
about it while the package is at 0.x.

| Number | Where it appears | What it versions |
|---|---|---|
| `format` | every `device.yaml`, contract, overlay and lab (`format: 1`) | the **file format** a manifest is written in |
| schema `v1` | the schema `$id`s and titles in `spec/schemas/` | the same thing, named: schema v1 *is* format 1 |
| package | `version` in `pyproject.toml` (0.1.0) | the **tools**: the linter, the compiler, the indexers and the exporter |
| `contract` | `devices.json` (`contract: 1`) | the **published build** a consumer reads from `library/dist/`; `CHANGELOG.md` records each one |

Each device and component also carries its own semantic version and lock, which
records what changed in *that hardware's drawing*. That is a separate system,
and [DESIGN §9](../spec/DESIGN.md) covers it: art is a patch, an addition is a
minor, and geometry or ids are a major.

## What is a breaking change

**To the format** (which raises `format`, and the schema label with it):
- a key is removed or renamed;
- a key's meaning changes, for example a unit, a frame or what a value refers to;
- validation starts rejecting a file that used to be valid.

Adding an **optional** key does not raise `format`. A file written without it
stays valid, and a reader that ignores it is unaffected.

**To the published build** (which raises `contract`): the same rule applied to
the files under `library/dist/`. A field a consumer reads is removed or renamed,
or its meaning changes. A new field does not raise it.

The two move independently. A format change can leave the build's shape alone,
and a change to the build can happen without any change to the files authors
write.

## What is promised before 1.0

The package is at 0.x, and at 0.x the promise is deliberately small:

- **The tools read the current format only.** When `format` goes up, files are
  migrated in the same change. Older files are not read side by side.
- **Every breaking change is announced.** A `format` or `contract` change is
  listed in `CHANGELOG.md`, with what to change in a file or a consumer to move
  across.
- **The version says so.** A change that raises `format` or `contract` also
  raises the package's minor version, so 0.1 to 0.2 is where to look.

## What 1.0 will promise

From 1.0, a change that raises `format` or `contract` is a major version of
the package. The **previous** format stays readable, and the previous
`contract` stays documented, for one release after the change, so a consumer
has a release in which to move.
