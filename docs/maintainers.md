# Maintainer notes

Process that only the maintainer runs. A contributor does not need any of it:
open the pull request, and the maintainer merges it once the gates are green.

## How a merge happens, and why it is a train

```sh
python3 .github/merge-train.py <pr-number> [<pr-number> ...]
```

**The train checks what branch protection cannot.** Branch protection on `main`
requires a pull request with `lint` and `build` passing. It cannot say whether a
set of pull requests that are each green is green together. The train checks
that, at the one place every merge goes through, and prints the `gh pr merge`
lines to run ([`docs/merging.md`](merging.md) has the whole procedure).

The second of those is the one that matters and the one a green tick does not
give you. **A green run on a branch says the branch works; it does not say the
branch works with what has landed since.** #100 and #101 were each green and
each correct, and `main` went red the moment both were in, because neither had
ever been run against the other. The train answers that by merging the heads
onto `origin/main` in the order they will land and running the full gates once
on that tree, instead of requiring every branch to be brought up to date after
each merge (which `strict` does, and which makes the checks the bottleneck).

The train also refuses a pull request whose head has a check that failed, one
still running, or a `build` that was skipped, as a draft's is. A skipped check
reads as passing to branch protection (#867), so the train takes only `success`
for `lint` and `build`. A single-pull-request merge script did this job before
the train; it was retired in this change (see [`docs/merging.md`](merging.md)).

**Green is enough for a two-way door, and not for a one-way one.** Every pull
request states its merge danger; `CONTRIBUTING.md` lists what makes a change a
one-way door. A two-way door that is green and up to date is merged without
being read again. A one-way door is read first, by the maintainer, because a
revert will not undo it. A pull request that declares two-way while the diff
renames a component, removes an export or touches a workflow is treated as
one-way, and the declaration is corrected.

## Releasing the compiled library to npm

```sh
gh workflow run release.yml --ref main                  # a dry run
gh workflow run release.yml --ref main -f publish=true  # the release
```

`release.yml` builds the library and runs
`npm_packages.py --from-registry --publish`. The packager reads what npm holds
for every package and publishes only the ones whose bytes changed: updates to
packages npm holds first, then new packages, then the index. A run with nothing new publishes nothing, and a run that failed partway
is finished by running it again. Run the dry run first: its summary lists what
a release would send.

npm limits how many new packages an account creates: about 25, then none for
hours. It documents neither the number nor the window. The first release was
refused with `E429` on its 26th package, and a run two hours later on its
first. A release stops at once on a first publish refused this way and says how
many packages are left; run it again the next day. Updates are published before
any new package, so the quota never holds one back. The index goes last, so
nothing reads the packages from the CDN until every device is out. `E429` on a
package npm already holds is an ordinary rate limit, and the packager waits and
tries that package again.

**A package's first publish needs a token; every later one does not.** npm's
trusted publishing lets the workflow publish with no stored secret, but a
trusted publisher is configured on a package, and a package that has never been
published is not there to configure. A run against the registry prints a
`first publish:` line for each such package: all of them on the first release,
and afterwards one for each device added since the last.

Devices are added most weeks, so the token is kept and not made for each
release. What limits it is where it is stored and how long it lives:

- **It is a secret of the `npm` environment, not of the repository.** Only a
  job that names the environment can read it, the environment admits only
  `main`, and it can require the maintainer's approval before the job starts.
- **npm expires it.** A token that can publish lasts 90 days at most. When it
  has lapsed, a release publishes every update to a trusted package and stops
  at the first new package: no new package goes out, and nor does the index.
  Replace the token and run the release again.

Setting it up, once:

1. Create the environment: repository Settings, Environments, `npm`. Restrict
   its deployment branches to `main` and add the maintainer as a required
   reviewer.
2. On npmjs.com, under Access Tokens, generate a granular access token: read
   and write on the `@portrayal` scope, "bypass two-factor authentication"
   ticked, 90 days. Store it with `gh secret set NPM_TOKEN --env npm`.

After a release that published new packages, trust the workflow on each. It
takes npm 11.10 or later and an interactive `npm login`, since npm refuses a
token for this:

```sh
for p in <the names published as a first publish>; do
  npx -y npm@11 trust github "$p" --repository roc-ops/Portrayal \
    --file release.yml --environment npm --yes
  sleep 2
done
```

The names are the `published ... (first publish)` lines of the run summary.
Take them from every run of a release that failed and was run again: a package
sent before the failure is on npm by the next run, which no longer calls it a
first publish.

npm asks for the second factor once and then skips it for five minutes, which
at this pace is about 80 packages; run the loop again for the rest. A package
left untrusted keeps publishing through the token, so this can be done in
batches. What trusting buys is that an expired or revoked token stops only new
devices, and that each trusted publish carries a provenance attestation.

`@portrayal/components` 0.1.0 was published before the skins were split by
namespace into `@portrayal/components-<namespace>`. Nothing publishes it now
and no index names it. Mark it, once, from an interactive login:

```sh
npm deprecate @portrayal/components "split by namespace: see @portrayal/components-<namespace>"
```

`@portrayal/kit` is not part of this. It is published by hand from `kit/`.

**Do not bump the kit version in a pull request; add a changelog fragment. The
version is bumped when the kit is published.** To publish:

1. Set `version` in `kit/package.json`, and write the matching "New in X" note
   in `kit/README.md`, in one commit.
2. Run `python3 spec/tools/portrayal/kitrelease.py --publish`. It fails unless
   the README's newest "New in" note names the `package.json` version.
3. Run `npm publish` from `kit/`.

## Cutting a version: the changelog

Pull requests record their changes in `changelog.d/`, one file each, and do not
edit `CHANGELOG.md` (`changelog.d/README.md` says why). Until a version is cut
the unreleased record is the `## Unreleased` section of `CHANGELOG.md`
followed by those files. Cutting a version folds them in:

```sh
python3 spec/tools/portrayal/changelog.py --show       # read the result first
python3 spec/tools/portrayal/changelog.py --assemble   # write it, delete the fragments
```

`--assemble` puts each entry after the entries already under the same heading
in `## Unreleased`, adding the heading at the end of the section if it is not
there yet, and deletes each fragment file it folded, keeping
`changelog.d/README.md`. It refuses, and changes nothing, if any fragment does
not parse. Fragments fold in file-name order, so read the result and reorder
entries by hand where the order matters. Then rename `## Unreleased` to the
version and open a new empty `## Unreleased` above it, in the same pull
request. The npm release above does not read the changelog and does not need
this step.

`preflight.py` is expected to pass on the release branch. Its `changelog` check
takes the diff as a release when it deletes fragments, adds one `## <version>`
heading to `CHANGELOG.md` carrying every deleted entry, and leaves
`## Unreleased` empty. A branch that touches `library/`, `spec/` or `kit/` and
is neither that nor adds a fragment still fails.

**The strings that move at a release.** Four places name the version, and the
release pull request moves them together:

- `version` in `pyproject.toml`;
- `TOOL_VERSION` in `spec/tools/portrayal/render.py`. It is stamped into the
  metadata of every compiled face and into the `generator` of each elements
  file, so the next npm release run after it moves updates every device
  package;
- the mentions of the current release in `docs/format-stability.md`: the
  package row, the `contract` row and the `generator` example;
- the `CHANGELOG.md` heading.

`kit/package.json` is the version of `@portrayal/kit` and does not move with
them. A schema's `$id` moves only when the format does.
