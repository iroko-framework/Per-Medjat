# Featured Work Selector

Generates `Per-Medjat/library/featured-work.json` for the Medjat Library page.

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
