# CLAUDE.md: Per-Medjat

Per Medjat, the IHS digital archive. Published at **medjat.irokosociety.org** (GitHub Pages, CNAME in repo root). This repo is the *published site*. The tooling that builds the catalog lives in a different repo; see Coupling below.

---

## The one rule that matters

**`library/data/` is generated. Do not hand-edit anything in it.**

A GitHub Action rebuilds that directory nightly and force-commits the result. Manual edits are overwritten without warning. Current state: **644 records**, 639 of them listed, last generated 2026-08-09T09:05Z.

To change what appears in the catalog, edit either the Zotero group library (the upstream source) or the mapping files in `library/mappings/`. Never the output.

---

## Layout

| Path | Contents | Generated? |
|---|---|---|
| `library/data/` | `library.json` (manifest), `library.index.json`, `library.facets.json`, `library.ttl`, `marc/library.marc.json`, `records/**` (644 JSON), `rdf/**` (644 TTL) | Yes, nightly |
| `library/mappings/` | `authority-map.json`, `ifwk-map.json`, `language-map.json`, `tag-map.json`, `local-overrides.json` | No, hand-maintained |
| `library/featured/`, `library/assets/`, `library/index.html` | Catalog front end | No |
| `ewe/` | Ewé botanical subsite; `build_ewe.py`, `access.py`, `model.py`, Verger dataset (LS-563) | Site is built from the scripts |
| `archives/`, `espiritismo/`, `entrusting/`, `hyatt/`, `research-portals/` | Section landing pages | No |
| `generate-og.py` | Open Graph card generation. `generate-og (old).py` is superseded; do not run it | No |

`records/` and `rdf/` are sharded by the first two characters of the Zotero item key (`records/24/24NCDVPQ.json`). Keep that convention if anything ever writes there.

---

## The nightly catalog build

`.github/workflows/nightly-build.yml`. Cron `22 8 * * *` (08:22 UTC, which is 2:22 AM CST and 3:22 AM CDT). Also runs on manual dispatch. Concurrency group `medjat-catalog-build`, queued rather than cancelled.

The build script **is not in this repo**. The workflow checks out `iroko-framework/medjat-tools` at `main` into `.build/medjat-tools` and runs `build_library/build_library.py` from there, with `PER_MEDJAT_ROOT` set to the workspace.

Sequence:

1. Checkout Per-Medjat (`GITHUB_TOKEN`)
2. Checkout medjat-tools at `main` (`MEDJAT_TOOLS_PAT`)
3. Python 3.11
4. Run `build_library.py` (`ZOTERO_API_KEY`)
5. Validate the generated catalog
6. Commit `library/data` as "Nightly catalog build YYYY-MM-DD HH:MM UTC" and push

### Required secrets

`MEDJAT_TOOLS_PAT` and `ZOTERO_API_KEY`. If the build fails with a checkout or auth error, an expired PAT is the first thing to check.

### Validation gate

Step 5 fails the build, before anything is committed, when:

- any of `library.json`, `library.index.json`, `library.facets.json`, `library.ttl`, or `marc/library.marc.json` is missing
- `count` is zero, or `count` does not equal `len(library.index.json)`
- the record count drops more than 25% from the previous commit, and the previous count was at least 20

That last check is a deliberate guard against a partial Zotero fetch silently emptying the public catalog. If a legitimate large deletion needs to publish, it has to be forced through manually rather than by weakening the gate.

---

## Diagnosing a failed nightly build

Work in this order. The failure is usually upstream of this repo.

1. **Read the Actions log first.** The validation step names the exact failure, and the count check prints both old and new numbers.
2. **Auth.** Expired `MEDJAT_TOOLS_PAT` breaks step 2; a bad `ZOTERO_API_KEY` breaks step 4.
3. **medjat-tools changed.** The workflow tracks `main`, deliberately, so that catalog rules do not revert after a tools update. That also means a commit in medjat-tools can break this build with no change here. Check that repo's recent history.
4. **Zotero.** A partial fetch shows up as the 25% drop guard firing.
5. **Mappings.** A malformed edit to `library/mappings/*.json` breaks the build with no upstream cause.

There is no test suite in either repo, so the validation step in this workflow is currently the only automated check standing between a bad build and the public catalog. Treat it as load-bearing.

---

## Coupling

- **medjat-tools** owns `build_library/build_library.py` and `framework_vocab.py`. It builds this repo. It is checked out at `main` during every nightly run.
- **iroko-framework** produces `vocab/tradition-vocab.json`, which feeds catalog vocabulary. A term rename there reaches this catalog.
- **Zotero group library** is the upstream record source. Medjat Steward is what enriches records before they arrive here.

Changing catalog behavior almost always means editing medjat-tools, not this repo.

---

## Notes

- `ewe/.github/workflows/deploy-github-pages.yml` sits in a subdirectory. GitHub only runs workflows from the repository root `.github/workflows/`, so that file is inert here. It is a leftover from when `ewe` was its own repo. Leave it or remove it, but do not expect it to run.
- `__pycache__` and a stray `_bash_write_test.txt`-style artifact pattern appear in these repos. Do not commit them.
- The long hex `.txt` file in the repo root is a domain or service verification token. Do not delete it.

---

## Working conventions

- Never use em dashes in any prose written into this repo.
- Do not use "diaspora" or "diasporic" in public copy. Use Afro-Atlantic, Atlantic world, or the specific geographic framing.
- Access posture: restricted by default for sacred Afro-Atlantic material. Universal transparency is not the value here. Any public-facing copy or new catalog facet has to respect the access tier model before it ships.
- Iroko terminology is exact. Do not substitute generalist synonyms.
