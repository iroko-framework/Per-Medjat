# Research Portals Build Spec

Proposal to replace the hand-authored `research-portals/index.html` card markup with a
generated page driven by a single data file. Written 2026-08-07, at 26 portals. Not yet
implemented.

## The problem this solves

Every portal currently exists three times in one file:

1. The `<a class="portal-card">` block, roughly eighteen lines of markup.
2. A `ListItem` entry in the `application/ld+json` `ItemList` in `<head>`.
3. A hardcoded total in `#searchCount` ("26 portals").

These three copies have no mechanical relationship. Adding the five francophone portals on
2026-08-07 updated the cards and the count but silently left the JSON-LD at 21 items, which
is precisely the failure this spec anticipates: the desync is invisible in the browser,
survives review, and degrades only the structured data that search engines consume. It was
caught by a script written after the fact, not by anything in the workflow.

Three further couplings are unenforced today. Every `data-category` value must have a
matching `.filter-pill` in `#categoryFilter`, or cards become unreachable through the UI.
Every `data-access` value must have a matching `<option>` in `#accessFilter`. And the
`?category=` links in the Start Here section must name categories that actually exist. A
typo in any of these produces a filter that returns nothing, with no error.

The page has been edited ten times since creation. It is not volatile, but each edit is
manual markup surgery across three locations, and the cost of that grows linearly while the
benefit of consistency grows with the card count.

## Design decision: build-time render, not runtime fetch

The repository contains two established build patterns, and they point in different
directions.

`library/` uses **runtime fetch**: `build_library.py` in the external `medjat-tools` repo
emits JSON into `library/data/`, and the page fetches it on load. This suits the catalog,
which holds hundreds of records, changes nightly, and is searched rather than browsed.

`ewe/` uses **build-time render**: `build_ewe.py` reads a TTL or SQLite source and renders
Jinja2 templates into static HTML committed to the repo.

Research Portals should follow the `ewe/` pattern. The reasoning is not primarily about
scale, though 26 records is far below the threshold where runtime fetching pays for itself.
It is that this page is a discovery surface. The card descriptions are substantive prose
about scope, language, and access conditions, and that prose is the page's value to a search
engine and to a reader who arrives from one. Moving it behind a `fetch()` would strip the
crawlable text out of the document and make the JSON-LD describe content that is not in the
HTML. The page would also lose its no-JavaScript fallback, which currently degrades to a
plain readable list.

Build-time rendering keeps every guarantee the page has now and adds a single source of
truth.

## Data file

`research-portals/portals.json`, an array of objects in display order. Order in the file is
order on the page and position in the JSON-LD; no separate sort key.

```json
{
  "name": "Persée",
  "url": "https://www.persee.fr/",
  "eyebrow": "Journal backfiles",
  "institution": "Persée · ENS de Lyon, CNRS, Ministère de l'Enseignement supérieur",
  "description": "Retrospective digitization of French scholarly journals ...",
  "best_for": "Pre-1990 French journal runs and colonial-era ethnographic articles.",
  "languages": "Primarily French.",
  "materials": "Digitized articles, full issues, and page images with OCR.",
  "coverage": "French scholarly journals, 19th century onward",
  "last_verified": "2026-08",
  "category": "digital-library",
  "access": "access-open",
  "access_note": null,
  "search_terms": "persee digitized backfiles french journals ..."
}
```

Notes on specific fields. `description` permits inline `<em>` for journal titles, which the
current cards already use, so the template must not autoescape this field; every other field
is escaped. `last_verified` is stored as `YYYY-MM` and rendered as "August 2026", which
removes the drift where some cards say July and others August with no way to sort them.
`access_note` is the optional suffix after the badge label, as in "paywalled, openly indexed"
on the Cairn card; `null` renders the bare label. `coverage` is stored without the "Coverage:"
prefix and without the trailing verification clause, both of which the template supplies.

A sibling `portals-config.json` holds the two controlled vocabularies, so that categories and
access tiers are declared once and drive both the data validation and the filter UI:

```json
{
  "categories": [
    { "id": "digital-library", "label": "Digital Libraries & Repositories" },
    { "id": "theses",          "label": "Theses & Dissertations" }
  ],
  "access_levels": [
    { "id": "access-open",    "label": "Open digital access" },
    { "id": "access-partial", "label": "Partial digital access" }
  ],
  "start_here": [
    { "category": "theses", "kicker": "Theses", "title": "Theses and dissertations" }
  ]
}
```

## Templates

`research-portals/templates/index.html`, a Jinja2 template holding everything the current
page holds except the generated regions. The inline `<style>` and `<script>` blocks move into
the template verbatim; the filter JavaScript needs no changes, since it reads the same
`data-` attributes it reads today.

Five regions become loops rather than literals:

| Region | Source |
| --- | --- |
| `itemListElement` in the JSON-LD | `portals.json`, enumerated |
| `#searchCount` text | `portals.json` length |
| `.start-grid` cards | `config.start_here` |
| `#categoryFilter` pills | `config.categories` |
| `#accessFilter` options | `config.access_levels` |
| `#portalGrid` cards | `portals.json` |

The Start Here grid is currently `grid-template-columns: repeat(5, ...)`, hardcoded to five
cards. Either the template emits the column count from `config.start_here | length`, or the
CSS moves to `repeat(auto-fit, minmax(...))`. The latter is preferable and is a small
independent improvement.

## Build script

`research-portals/build_portals.py`, following `build_ewe.py`'s conventions: `BASE =
Path(__file__).resolve().parent`, `argparse` for paths, render to a staging directory and
move into place only on success, so a failed build never leaves a half-written page.

Dependency is Jinja2 alone, already required by `ewe/requirements.txt`. No rdflib, no network
access, no API keys. The build is deterministic and offline, which matters for the validation
step below.

Validation runs before render and exits non-zero on any failure:

- every `category` and `access` value appears in `portals-config.json`
- every `config.start_here[].category` resolves to a declared category
- no duplicate `url` values
- required fields non-empty; `url` is absolute and https
- `last_verified` matches `YYYY-MM`

A `--check` flag renders to a temporary directory and diffs against the committed
`index.html`, exiting non-zero if they differ. This is what makes the generated file
trustworthy in review: it proves the committed HTML is what the data produces.

## Migration

The one-time extraction is mechanical and should be scripted rather than retyped. Parse the
current 26 cards with a throwaway script, emit `portals.json`, render, and diff the result
against the current `index.html`. Iterate on the template until the diff is empty except for
intended normalizations, namely the July-to-August `last_verified` values and any whitespace.
An empty diff is the acceptance criterion; it demonstrates the generator reproduces the page
exactly and that the migration introduced no content changes.

## Deployment

No GitHub Action. The nightly workflow exists because Zotero changes without anyone touching
the repo; portals change only when Délé edits them, so a scheduled build would be a scheduled
no-op.

The generated `index.html` is committed, consistent with `ewe/`, which commits its rendered
output. GitHub Pages serves the file directly and nothing changes about hosting.

Two manual steps stay manual and should be noted in `research-portals/README.md`: bump
`<lastmod>` for the portals URL in `sitemap.xml`, and re-run `generate-og.py` if the OG card
text changes, which it rarely does since that text is static and carries no count.

Optionally, a pre-commit hook or a lightweight CI job runs `build_portals.py --check` so a
hand-edit to the generated HTML fails loudly rather than being silently overwritten by the
next build.

## Cost and honest counterargument

The implementation is roughly a day: an afternoon for script and template, an afternoon for
migration and diff-matching.

The counterargument deserves stating. Ten edits in the page's lifetime is not a heavy
maintenance burden, and the generator introduces a build step where none existed, meaning a
future editor must have Python and Jinja2 available to change a typo in a description. That
is a real regression in the page's approachability.

The case for building it anyway rests on the JSON-LD desync being a class of error that
manual editing cannot reliably prevent, and on the observation that structured data failures
are silent. If the page had only cards, hand-authoring at this scale would be entirely
defensible. It is the second and third copies of the data that make the generator worth its
cost, and those copies do not go away as the directory grows.
