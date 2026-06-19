# Medjat Library

The main public catalog uses prebuilt static data from `/library/data/`.

Run the catalog builder from the `medjat-tools` repository:

```powershell
$env:PER_MEDJAT_ROOT="C:\path\to\Per-Medjat"
python build_library\build_library.py
```

The build pulls top-level public Zotero records, normalizes them, and generates:

- `library/data/library.index.json`
- `library/data/library.facets.json`
- `library/data/records/{prefix}/{key}.json`
- `library/data/library.ttl`
- `library/data/rdf/{prefix}/{key}.ttl`
- `library/data/marc/library.marc.json`

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
