# Maintainer notes

Process that only the maintainer runs. A contributor does not need any of it:
open the pull request, and the maintainer merges it once the gates are green.

## How a merge happens, and why it is a script

```sh
.github/merge-if-green.sh <pr-number>
```

**The script checks what branch protection checks.** While the repository was
private, required status checks and rulesets were unavailable (a paid feature
for a private repository), so GitHub could not refuse a bad merge, and the
script was the stand-in: it checks the two things branch protection would have
checked, at the one place every merge goes through. Now that the repository is
public, #155 turns branch protection on for `main`. Until it has, the script is
still the only check.

The second of those two is the one that matters and the one a green tick does
not give you. **A green run on a branch says the branch works; it does not say
the branch works with what has landed since.** #100 and #101 were each green
and each correct, and `main` went red the moment both were in, because neither
had ever been run against the other. That is what `strict` means in branch
protection, and the script checks it by refusing to merge a branch that is
behind its base.

Use it rather than `gh pr merge` until branch protection is on. Before then,
nothing enforces it, and that is exactly how it gets skipped.

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
