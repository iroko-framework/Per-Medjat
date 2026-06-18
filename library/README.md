# Medjat Library

The main public catalog now uses prebuilt static data from `../data/`.

Run the catalog build from the repository root:

```powershell
python scripts\build_library.py
```

The build pulls top-level public Zotero records, normalizes them, and generates:

- `data/library.index.json`
- `data/library.facets.json`
- `data/records/{prefix}/{key}.json`
- `data/library.ttl`
- `data/rdf/{prefix}/{key}.ttl`
- `data/marc/library.marc.json`

The public `/library/` page loads only the lightweight index and facet files at startup. Full record JSON is fetched only when a visitor opens catalog details, linked data, or visits `/library/?item=KEY`.

Each card can generate a per-record RIS download from the full record JSON, so citation exports include available creator, title, publication, place, publisher, date, identifier, URL, abstract, language, and keyword fields without adding that weight to the search index.

## Featured Work Selector

The featured work file is a one-off page feature and is not part of the main scalable catalog build.

It generates `Per-Medjat/library/featured-work.json` for the Medjat Library page.

Run:

```powershell
python featured_work_selector.py
```

Optional, for private Zotero attachment downloads:

```powershell
$env:ZOTERO_API_KEY="your-key"
python featured_work_selector.py
```

Cover priority:

1. Zotero child image attachment tagged or named `featured-cover`, `cover`, or `front`
2. First Zotero child image attachment
3. Open Library cover by ISBN
4. Text fallback on the public page

The public site reads only `featured-work.json` and local/static image paths. It does not call Zotero for attachment files at page load.
