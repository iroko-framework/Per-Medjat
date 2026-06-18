#!/usr/bin/env python3
"""Build static Medjat Library catalog data from the public Zotero group.

Zotero remains the editorial source. This script generates the public,
static data files consumed by /library/ so the browser does not fetch the
full Zotero library at page load.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ZOTERO_GROUP = "6479329"
ZOTERO_API = "https://api.zotero.org"
MEDJAT_ITEM_BASE = "https://medjat.irokosociety.org/id/library/"
MEDJAT_VIEW_BASE = "https://medjat.irokosociety.org/library/?item="
MEDJAT_COLLECTION_URI = "https://medjat.irokosociety.org/id/collection/medjat-library"
DATA_PUBLIC_BASE = "/data"
TRADITION_VOCAB_URL = "https://ontology.irokosociety.org/vocab/tradition-vocab.json"

TYPE_LABELS = {
    "book": "Book",
    "journalArticle": "Journal Article",
    "thesis": "Thesis / Dissertation",
    "bookSection": "Book Chapter",
    "report": "Report",
    "conferencePaper": "Conference Paper",
    "document": "Document",
    "manuscript": "Manuscript",
    "artwork": "Artwork",
    "film": "Film",
    "webpage": "Web Page",
    "encyclopediaArticle": "Encyclopedia Article",
    "dictionaryEntry": "Dictionary Entry",
    "interview": "Interview",
    "letter": "Letter",
    "map": "Map",
    "presentation": "Presentation",
}

SCHEMA_TYPES = {
    "book": "schema:Book",
    "journalArticle": "schema:ScholarlyArticle",
    "thesis": "schema:Thesis",
    "bookSection": "schema:Chapter",
    "report": "schema:Report",
    "conferencePaper": "schema:ScholarlyArticle",
    "webpage": "schema:WebPage",
}

ACCESS_LABELS = {
    "l0-public": "Public",
    "l1-community": "Community",
    "l2-initiated": "Initiated",
    "l3-restricted": "Restricted",
    "l4-oath-bound": "Oath-bound",
    "l5-no-access": "No access",
    "public": "Public",
    "community": "Community",
    "initiated": "Initiated",
    "restricted": "Restricted",
    "oath-bound": "Oath-bound",
    "no-access": "No access",
    "access-public-unrestricted": "Public",
    "access-community-only": "Community",
    "access-initiated-only": "Initiated",
    "access-no-access": "No access",
}

CUSTODY_LABELS = {
    "held-ihs": "IHS Holds",
    "digitally-held": "IHS Digital",
    "external-reference": "External Ref",
    "known-inaccessible": "Record Only",
    "metadata-only": "Metadata Only",
}

DEFAULT_RECORD_TYPE_TAGS = [
    "Monograph",
    "Ethnography",
    "Field Study",
    "Comparative Literature",
    "Primary Source",
    "Reference",
    "Dictionary",
    "Encyclopedia",
    "Anthology",
    "Dissertation",
    "Journal Article",
    "Book Chapter",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def quick_key(value: str) -> str:
    key = str(value or "").strip()
    key = re.sub(r"^(Iroko\s+)?(Class|Module|Concept):\s*", "", key, flags=re.I)
    key = re.sub(r"^iroko[:_-]", "", key, flags=re.I)
    key = re.sub(r"^(class|module|concept|paper|theme):", "", key, flags=re.I)
    if ":" in key:
        key = key.split(":")[-1]
    key = re.sub(r"([a-z])([A-Z])", r"\1-\2", key)
    key = re.sub(r"[_\s]+", "-", key).lower()
    key = unicodedata.normalize("NFD", key)
    key = "".join(ch for ch in key if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9-]", "", key)


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def split_list(value: str) -> list[str]:
    return [clean_text(v) for v in re.split(r"[;,]", str(value or "")) if clean_text(v)]


def unique(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def parse_extra(extra: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in str(extra or "").splitlines():
        match = re.match(r"^([^:]+):\s*(.+)$", line.strip())
        if match:
            raw_key = match.group(1).strip().lower()
            norm_key = re.sub(r"[\s_]+", "-", raw_key)
            value = match.group(2).strip()
            data[raw_key] = value
            data[norm_key] = value
    return data


def first_extra(extra: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = extra.get(key)
        if value:
            return value
    return default


def extra_values(extra: dict[str, str], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        values.extend(split_list(extra.get(key, "")))
    return values


def year_from_date(value: str) -> str:
    match = re.search(r"(1[4-9]\d{2}|20\d{2})", str(value or ""))
    return match.group(1) if match else ""


def shard_for_key(key: str) -> str:
    return (key or "XX")[:2].upper()


def zotero_request(url: str, api_key: str = ""):
    headers = {
        "Zotero-API-Version": "3",
        "User-Agent": "MedjatLibraryBuilder/1.0",
    }
    if api_key:
        headers["Zotero-API-Key"] = api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.load(response)
        return payload, response.headers


def fetch_zotero_items(group_id: str, api_key: str = "", limit: int | None = None) -> list[dict]:
    items: list[dict] = []
    start = 0
    total = None
    while True:
        batch_limit = 100
        if limit is not None:
            batch_limit = min(batch_limit, max(0, limit - len(items)))
            if batch_limit == 0:
                break
        query = urllib.parse.urlencode({"format": "json", "limit": batch_limit, "start": start})
        url = f"{ZOTERO_API}/groups/{group_id}/items/top?{query}"
        batch, headers = zotero_request(url, api_key)
        if total is None:
            total = int(headers.get("Total-Results", "0") or "0")
        items.extend(batch)
        print(f"Fetched {len(items)} of {total}")
        if not batch or len(items) >= total:
            break
        if limit is not None and len(items) >= limit:
            break
        start += len(batch)
        time.sleep(0.2)
    return items


def load_remote_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "MedjatLibraryBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def load_tradition_vocab(root: Path, explicit_path: str = "") -> dict:
    sources: list[tuple[str, object]] = []
    if explicit_path:
        sources.append(("path", Path(explicit_path)))
    sources.append(("path", root.parent / "iroko-framework" / "vocab" / "tradition-vocab.json"))
    sources.append(("url", TRADITION_VOCAB_URL))

    concepts = []
    for kind, source in sources:
        try:
            if kind == "path":
                path = Path(source)
                if path.exists():
                    concepts = read_json(path, [])
                    break
            else:
                concepts = load_remote_json(str(source))
                break
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            print(f"Tradition vocabulary source failed ({source}): {exc}")

    by_label: dict[str, dict] = {}
    by_local: dict[str, dict] = {}
    lookup: dict[str, str] = {}
    for concept in concepts:
        label = clean_text(concept.get("prefLabel", ""))
        if not label:
            continue
        entry = {
            "prefLabel": label,
            "uri": concept.get("anchorUrl") or concept.get("uri") or "",
            "localName": concept.get("localName") or "",
            "broader": concept.get("broader") or "",
            "altLabels": concept.get("altLabels") or [],
        }
        by_label[label] = entry
        if entry["localName"]:
            by_local[entry["localName"]] = entry
        lookup[label.casefold()] = label
        lookup[quick_key(label)] = label
        for alt in entry["altLabels"]:
            lookup[clean_text(alt).casefold()] = label
            lookup[quick_key(alt)] = label
    return {"by_label": by_label, "by_local": by_local, "lookup": lookup}


def resolve_tradition(name: str, vocab: dict) -> dict | None:
    cleaned = clean_text(name)
    if not cleaned:
        return None
    label = vocab["lookup"].get(cleaned.casefold(), cleaned)
    label = vocab["lookup"].get(quick_key(cleaned), label)
    concept = vocab["by_label"].get(label)
    if not concept:
        return None
    seen = set()
    while concept.get("broader") and concept.get("localName") not in seen:
        seen.add(concept.get("localName"))
        parent = vocab["by_local"].get(concept["broader"])
        if not parent:
            break
        concept = parent
    return concept


def creator_name(creator: dict) -> str:
    if creator.get("name"):
        return clean_text(creator["name"])
    last = clean_text(creator.get("lastName", ""))
    first = clean_text(creator.get("firstName", ""))
    if last and first:
        return f"{last}, {first}"
    return last or first


def role_label(role: str) -> str:
    return {
        "author": "author",
        "editor": "editor",
        "seriesEditor": "series editor",
        "translator": "translator",
        "contributor": "contributor",
    }.get(role or "author", role or "author")


def load_maps(root: Path) -> dict:
    mapping_dir = root / "mappings"
    return {
        "tags": read_json(mapping_dir / "tag-map.json", {}),
        "ifwk": read_json(mapping_dir / "ifwk-map.json", {}),
        "languages": read_json(mapping_dir / "language-map.json", {}),
        "authorities": read_json(mapping_dir / "authority-map.json", {}),
        "overrides": read_json(mapping_dir / "local-overrides.json", {}),
    }


def language_label(value: str, maps: dict) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        return ""
    languages = maps["languages"]
    return languages.get(cleaned, languages.get(cleaned.lower(), cleaned))


def label_access(value: str) -> str:
    return ACCESS_LABELS.get(quick_key(value), "Public")


def ifwk_label(kind: str, value: str, maps: dict) -> str:
    table = maps["ifwk"].get(kind, {})
    key = quick_key(value)
    item = table.get(key)
    if isinstance(item, dict):
        return item.get("label", "")
    if isinstance(item, str):
        return item
    return ""


def ifwk_uri(kind: str, label: str, maps: dict) -> str:
    table = maps["ifwk"].get(kind, {})
    key = quick_key(label)
    item = table.get(key)
    if isinstance(item, dict):
        return item.get("uri", "")
    return ""


def authority_uri(source: str, value: str, maps: dict) -> str:
    value = clean_text(value)
    if value.startswith("http://") or value.startswith("https://"):
        return value
    templates = maps["authorities"].get("uriTemplates", {})
    template = templates.get(source.lower())
    if template:
        return template.format(id=urllib.parse.quote(value, safe=":/#"))
    return value


def authority_mappings(extra: dict[str, str], maps: dict) -> list[dict]:
    keys = maps["authorities"].get("extraKeys", {})
    mappings = []
    for source, extra_keys in keys.items():
        for key in extra_keys:
            for raw in split_list(extra.get(key, "")):
                uri = authority_uri(source, raw, maps)
                mappings.append({"source": source, "label": raw, "uri": uri})
    return mappings


def classify_record(item: dict, vocab: dict, maps: dict) -> dict:
    data = item.get("data", {})
    tags = [clean_text(t if isinstance(t, str) else t.get("tag", "")) for t in data.get("tags", [])]
    tags = [t for t in tags if t]
    extra = parse_extra(data.get("extra", ""))

    record_type_tags = set(maps["tags"].get("recordTypeTags") or DEFAULT_RECORD_TYPE_TAGS)
    ignored_prefixes = tuple(maps["tags"].get("ignoredPrefixes") or ["medjat-search:"])

    traditions: list[str] = []
    tradition_links: dict[str, str] = {}
    themes: list[str] = []
    subjects: list[str] = []
    regions: list[str] = []
    languages: list[str] = []
    framework_modules: list[str] = []
    framework_classes: list[str] = []
    record_type_override = ""

    for tag in tags:
        lower = tag.lower()
        if lower.startswith(ignored_prefixes):
            continue
        handled = False
        for prefix in ("tradition:", "tradition: ", "Tradition: "):
            if tag.startswith(prefix):
                raw = tag.split(":", 1)[1].strip()
                concept = resolve_tradition(raw, vocab)
                label = concept["prefLabel"] if concept else raw
                traditions.append(label)
                if concept and concept.get("uri"):
                    tradition_links[label] = concept["uri"]
                handled = True
                break
        if handled:
            continue
        if lower.startswith("theme:") or tag.startswith("Theme: "):
            themes.append(tag.split(":", 1)[1].strip())
            continue
        if lower.startswith("record:"):
            record_type_override = tag.split(":", 1)[1].strip()
            continue
        if lower.startswith("region:"):
            regions.append(tag.split(":", 1)[1].strip())
            continue
        if lower.startswith("language:"):
            languages.append(language_label(tag.split(":", 1)[1].strip(), maps))
            continue
        if lower.startswith(("ifwk:", "iroko:")):
            module = ifwk_label("modules", tag, maps)
            klass = ifwk_label("classes", tag, maps)
            if module:
                framework_modules.append(module)
            elif klass:
                framework_classes.append(klass)
            else:
                themes.append(tag.split(":", 1)[1].replace("-", " ").strip())
            continue

        module = ifwk_label("modules", tag, maps)
        klass = ifwk_label("classes", tag, maps)
        concept = resolve_tradition(tag, vocab)
        if module:
            framework_modules.append(module)
        elif klass:
            framework_classes.append(klass)
        elif concept:
            traditions.append(concept["prefLabel"])
            if concept.get("uri"):
                tradition_links[concept["prefLabel"]] = concept["uri"]
        elif tag in record_type_tags:
            record_type_override = tag
        else:
            subjects.append(tag[8:] if tag.startswith("Entity: ") else tag)

    extra_modules = extra_values(extra, "iroko_modules", "iroko-modules", "iroko_module", "iroko-module")
    extra_classes = extra_values(
        extra,
        "iroko_class",
        "iroko-class",
        "iroko_classes",
        "iroko-classes",
        "iroko_concept",
        "iroko-concept",
        "iroko_concepts",
        "iroko-concepts",
        "iroko_connects",
        "iroko-connects",
    )
    for value in extra_modules:
        label = ifwk_label("modules", value, maps)
        if label:
            framework_modules.append(label)
        else:
            themes.append(value)
    for value in extra_classes:
        label = ifwk_label("classes", value, maps)
        if label:
            framework_classes.append(label)
        else:
            themes.append(value)
    regions.extend(extra_values(extra, "medjat-region", "medjat_region", "region"))
    languages.extend(
        language_label(value, maps)
        for value in extra_values(extra, "medjat-language", "medjat_language", "language", "lang")
    )

    if data.get("language"):
        languages.append(language_label(data["language"], maps))

    access_raw = first_extra(
        extra,
        "access_tier_default",
        "access-tier-default",
        "access_tier",
        "access-tier",
        "iroko-access",
        "iroko_access",
        default="",
    )
    if not access_raw:
        for tag in tags:
            if quick_key(tag) in ACCESS_LABELS:
                access_raw = tag
                break
    access_raw = access_raw or "L0-public"

    return {
        "tags": tags,
        "extra": extra,
        "traditions": unique(traditions),
        "traditionLinks": tradition_links,
        "themes": unique(themes),
        "subjects": unique(subjects),
        "region": unique(regions),
        "language": unique([v for v in languages if v]),
        "frameworkClasses": unique(framework_classes),
        "frameworkModules": unique(framework_modules),
        "recordTypeOverride": record_type_override,
        "accessTier": access_raw,
        "access": label_access(access_raw),
        "custody": first_extra(extra, "iroko-custody", "iroko_custody", default="metadata-only"),
        "authorityMappings": authority_mappings(extra, maps),
    }


def publication_line(data: dict, year: str) -> str:
    place = clean_text(data.get("place", ""))
    publisher = clean_text(data.get("publisher", "") or data.get("publicationTitle", "") or data.get("university", ""))
    return publication_line_from_parts(place, publisher, year)


def publication_line_from_parts(place: str, publisher: str, year: str) -> str:
    place = clean_text(place)
    publisher = clean_text(publisher)
    parts = []
    if place:
        parts.append(f"{place}:")
    if publisher:
        parts.append(f"{publisher},")
    if year:
        parts.append(f"{year}.")
    return " ".join(parts)


def build_marc_rows(
    data: dict,
    creators: list[dict],
    classes: dict,
    record_type_label: str,
    publisher: str = "",
    place: str = "",
) -> list[dict]:
    title = clean_text(data.get("title", ""))
    subtitle = clean_text(data.get("subtitle", ""))
    year = year_from_date(data.get("date", ""))
    pub_line = publication_line_from_parts(
        place or data.get("place", ""),
        publisher or data.get("publisher", "") or data.get("publicationTitle", "") or data.get("university", ""),
        year,
    )
    main = next((c for c in creators if c["role"] == "author"), creators[0] if creators else None)
    rows = []
    if main:
        rows.append({"field": "100", "label": "Author", "value": main["name"]})
    if title:
        rows.append({"field": "245", "label": "Title", "value": title + (f" : {subtitle}" if subtitle else "")})
    if data.get("edition"):
        rows.append({"field": "250", "label": "Edition", "value": clean_text(data.get("edition"))})
    if pub_line:
        rows.append({"field": "264", "label": "Published", "value": pub_line})
    pages = clean_text(data.get("numPages", "") or data.get("pages", ""))
    if pages:
        rows.append({"field": "300", "label": "Extent", "value": pages if "p" in pages.lower() else f"{pages} p."})
    if data.get("series"):
        rows.append({"field": "490", "label": "Series", "value": clean_text(data.get("series"))})
    if data.get("ISBN"):
        rows.append({"field": "020", "label": "ISBN", "value": clean_text(data.get("ISBN"))})
    if data.get("DOI"):
        rows.append({"field": "024", "label": "DOI", "value": clean_text(data.get("DOI"))})
    if data.get("language") or classes["language"]:
        rows.append({"field": "041", "label": "Language", "value": "; ".join(classes["language"])})
    for value in unique(classes["themes"] + classes["subjects"] + classes["traditions"]):
        rows.append({"field": "650", "label": "Subject", "value": value})
    for creator in creators:
        if main and creator is main:
            continue
        label = "Added entry"
        if creator["role"] == "editor":
            label = "Added entry - editor"
        elif creator["role"] != "author":
            label = f"Added entry - {creator['role']}"
        rows.append({"field": "700", "label": label, "value": creator["name"]})
    if record_type_label:
        rows.append({"field": "655", "label": "Genre/Form", "value": record_type_label})
    return rows


def normalize_item(item: dict, vocab: dict, maps: dict) -> tuple[dict, dict]:
    data = item.get("data", {})
    key = data.get("key") or item.get("key") or ""
    classes = classify_record(item, vocab, maps)
    extra = classes["extra"]
    creators = [
        {"role": role_label(c.get("creatorType", "author")), "name": creator_name(c)}
        for c in data.get("creators", [])
        if creator_name(c)
    ]
    creator_labels = [creator["name"] for creator in creators]
    year = year_from_date(data.get("date", "") or item.get("meta", {}).get("parsedDate", ""))
    item_type = clean_text(data.get("itemType", ""))
    record_type_label = classes["recordTypeOverride"] or TYPE_LABELS.get(item_type, item_type or "Record")
    title = clean_text(data.get("title", ""))
    subtitle = clean_text(data.get("subtitle", ""))
    publication_title = clean_text(data.get("publicationTitle", "") or first_extra(extra, "publication-title", "publication_title"))
    book_title = clean_text(data.get("bookTitle", "") or first_extra(extra, "book-title", "book_title"))
    journal_abbreviation = clean_text(
        data.get("journalAbbreviation", "") or first_extra(extra, "journal-abbreviation", "journal_abbreviation")
    )
    publisher_extra = first_extra(extra, "publisher", "publication-title", "publication_title")
    publisher = clean_text(data.get("publisher", "") or publisher_extra or data.get("publicationTitle", "") or data.get("university", ""))
    place = clean_text(
        data.get("place", "") or
        first_extra(extra, "place", "city", "publisher-place", "publisher_place", "publication-place", "publication_place", "medjat-place", "medjat_place")
    )
    doi = clean_text(data.get("DOI", ""))
    url = clean_text(data.get("url", ""))
    isbn = clean_text(data.get("ISBN", "") or first_extra(extra, "isbn"))
    uri = f"{MEDJAT_ITEM_BASE}{key}"
    view_url = f"{MEDJAT_VIEW_BASE}{key}"
    ttl_path = f"{DATA_PUBLIC_BASE}/rdf/{shard_for_key(key)}/{key}.ttl"
    record_path = f"{DATA_PUBLIC_BASE}/records/{shard_for_key(key)}/{key}.json"

    about = []
    for label in classes["frameworkModules"]:
        uri_value = ifwk_uri("modules", label, maps)
        about.append({"label": label, "type": "Iroko Framework module", "uri": uri_value})
    for label in classes["frameworkClasses"]:
        uri_value = ifwk_uri("classes", label, maps)
        about.append({"label": label, "type": "Iroko Framework class", "uri": uri_value})
    for label in classes["traditions"]:
        if label in classes["traditionLinks"]:
            about.append({"label": label, "type": "Tradition", "uri": classes["traditionLinks"][label]})

    same_as = []
    if doi:
        same_as.append(f"https://doi.org/{doi}")
    same_as.extend(m["uri"] for m in classes["authorityMappings"] if str(m.get("uri", "")).startswith("http"))
    same_as = unique(same_as)

    display = {
        "title": title,
        "subtitle": subtitle,
        "shortTitle": clean_text(data.get("shortTitle", "")),
        "creators": creators,
        "year": year,
        "date": clean_text(data.get("date", "")),
        "publisher": publisher,
        "publicationTitle": publication_title,
        "bookTitle": book_title,
        "journalAbbreviation": journal_abbreviation,
        "place": place,
        "edition": clean_text(data.get("edition", "")),
        "series": clean_text(data.get("series", "")),
        "seriesNumber": clean_text(data.get("seriesNumber", "")),
        "volume": clean_text(data.get("volume", "")),
        "issue": clean_text(data.get("issue", "")),
        "pages": clean_text(data.get("numPages", "") or data.get("pages", "")),
        "abstract": clean_text(data.get("abstractNote", "")),
        "doi": doi,
        "url": url,
        "isbn": isbn,
        "issn": clean_text(data.get("ISSN", "") or first_extra(extra, "issn")),
        "university": clean_text(data.get("university", "")),
        "language": clean_text(data.get("language", "")),
    }

    marc = build_marc_rows(data, creators, classes, record_type_label, publisher, place)
    index_record = {
        "key": key,
        "title": title,
        "subtitle": subtitle,
        "creators": creator_labels,
        "year": year,
        "date": year,
        "publisher": publisher,
        "publicationLine": publication_line_from_parts(place, publisher, year),
        "itemType": item_type,
        "recordTypeLabel": record_type_label,
        "traditions": classes["traditions"],
        "traditionLinks": classes["traditionLinks"],
        "themes": classes["themes"],
        "frameworkClasses": classes["frameworkClasses"],
        "frameworkModules": classes["frameworkModules"],
        "access": classes["access"],
        "accessTier": classes["accessTier"],
        "custody": classes["custody"],
        "language": classes["language"],
        "region": classes["region"],
        "doi": doi,
        "url": url,
        "searchText": clean_text(
            " ".join(
                [
                    title,
                    subtitle,
                    " ".join(creator_labels),
                    year,
                    publisher,
                    item_type,
                    record_type_label,
                    " ".join(classes["traditions"]),
                    " ".join(classes["themes"]),
                    " ".join(classes["frameworkClasses"]),
                    " ".join(classes["frameworkModules"]),
                    " ".join(classes["subjects"]),
                    " ".join(classes["language"]),
                    " ".join(classes["region"]),
                    " ".join(classes["tags"]),
                ]
            )
        ).lower(),
        "recordPath": record_path,
    }

    full_record = {
        "key": key,
        "uri": uri,
        "viewUrl": view_url,
        "zotero": {
            "group": ZOTERO_GROUP,
            "key": key,
            "version": data.get("version") or item.get("version"),
            "itemType": item_type,
            "alternate": item.get("links", {}).get("alternate", {}).get("href", ""),
            "dateAdded": data.get("dateAdded", ""),
            "dateModified": data.get("dateModified", ""),
        },
        "display": display,
        "publicTags": {
            "recordType": record_type_label,
            "traditions": classes["traditions"],
            "themes": classes["themes"],
            "region": classes["region"],
            "language": classes["language"],
            "access": classes["access"],
            "custody": classes["custody"],
            "subjects": classes["subjects"],
        },
        "ifwk": {
            "classes": classes["frameworkClasses"],
            "modules": classes["frameworkModules"],
        },
        "marc": marc,
        "linkedData": {
            "ttl": ttl_path,
            "aggregateTtl": f"{DATA_PUBLIC_BASE}/library.ttl",
            "sameAs": same_as,
            "about": about,
            "authorityMappings": classes["authorityMappings"],
        },
    }
    return index_record, full_record


def upsert_marc_row(rows: list[dict], field: str, label: str, value: str, after_fields: set[str] | None = None) -> None:
    value = clean_text(value)
    if not value:
        return
    for row in rows:
        if row.get("field") == field:
            row["label"] = label
            row["value"] = value
            return
    insert_at = len(rows)
    if after_fields:
        for idx, row in enumerate(rows):
            if row.get("field") in after_fields:
                insert_at = idx + 1
    rows.insert(insert_at, {"field": field, "label": label, "value": value})


def apply_record_override(index_record: dict, full_record: dict, override: dict) -> None:
    for section, values in override.items():
        if section in full_record and isinstance(full_record[section], dict) and isinstance(values, dict):
            full_record[section].update(values)
        elif section in index_record and not isinstance(values, dict):
            index_record[section] = values

    display = full_record.get("display", {})
    tags = full_record.get("publicTags", {})
    index_record.update(
        {
            "title": display.get("title", index_record.get("title", "")),
            "subtitle": display.get("subtitle", index_record.get("subtitle", "")),
            "creators": [c.get("name", "") for c in display.get("creators", []) if c.get("name")],
            "year": display.get("year", index_record.get("year", "")),
            "date": display.get("year", index_record.get("date", "")),
            "publisher": display.get("publisher", index_record.get("publisher", "")),
            "publicationLine": publication_line_from_parts(
                display.get("place", ""),
                display.get("publisher", "") or display.get("publicationTitle", "") or display.get("university", ""),
                display.get("year", ""),
            ),
            "doi": display.get("doi", index_record.get("doi", "")),
            "url": display.get("url", index_record.get("url", "")),
        }
    )
    search_parts = [
        index_record.get("title", ""),
        index_record.get("subtitle", ""),
        " ".join(index_record.get("creators", [])),
        index_record.get("year", ""),
        index_record.get("publisher", ""),
        index_record.get("itemType", ""),
        index_record.get("recordTypeLabel", ""),
        " ".join(index_record.get("traditions", [])),
        " ".join(index_record.get("themes", [])),
        " ".join(index_record.get("frameworkClasses", [])),
        " ".join(index_record.get("frameworkModules", [])),
        " ".join(tags.get("subjects", [])),
        " ".join(index_record.get("language", [])),
        " ".join(index_record.get("region", [])),
    ]
    index_record["searchText"] = clean_text(" ".join(search_parts)).lower()

    pub_line = index_record.get("publicationLine", "")
    upsert_marc_row(full_record["marc"], "264", "Published", pub_line, {"245", "250"})
    upsert_marc_row(full_record["marc"], "020", "ISBN", display.get("isbn", ""), {"490", "264"})
    upsert_marc_row(full_record["marc"], "024", "DOI", display.get("doi", ""), {"020"})


def build_facets(records: list[dict]) -> dict:
    facets = {
        "recordTypes": {},
        "traditions": {},
        "themes": {},
        "frameworkClasses": {},
        "frameworkModules": {},
        "access": {},
    }

    def bump(bucket: dict, key: str, label: str | None = None):
        if not key:
            return
        current = bucket.get(key)
        if isinstance(current, dict):
            current["count"] += 1
        elif current is None and label is not None:
            bucket[key] = {"label": label, "count": 1}
        elif current is None:
            bucket[key] = 1
        else:
            bucket[key] = current + 1

    for record in records:
        bump(facets["recordTypes"], record["itemType"] or "record", record["recordTypeLabel"])
        for field, bucket_name in [
            ("traditions", "traditions"),
            ("themes", "themes"),
            ("frameworkClasses", "frameworkClasses"),
            ("frameworkModules", "frameworkModules"),
        ]:
            values = record.get(field) or []
            if values:
                for value in values:
                    bump(facets[bucket_name], value)
            elif field in ("traditions", "themes"):
                bump(facets[bucket_name], "__untagged__", "Untagged")
        bump(facets["access"], record.get("access") or "Public")

    for bucket_name, bucket in facets.items():
        def sort_value(item):
            key, value = item
            count = value.get("count", 0) if isinstance(value, dict) else value
            label = value.get("label", key) if isinstance(value, dict) else key
            return (-count, str(label))

        facets[bucket_name] = dict(sorted(bucket.items(), key=sort_value))
    return facets


def ttl_literal(value: str) -> str:
    value = str(value or "")
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("\n", "\\n").replace("\r", "")
    return f'"{value}"'


def ttl_uri(value: str) -> str:
    return f"<{value}>"


def ttl_item(record: dict, include_prefixes: bool = False) -> str:
    display = record["display"]
    tags = record["publicTags"]
    schema_type = SCHEMA_TYPES.get(record["zotero"]["itemType"], "schema:CreativeWork")
    props: list[tuple[str, list[str], bool]] = [
        ("a", [schema_type], False),
        ("schema:name", [display["title"]], True),
        ("schema:url", [record["viewUrl"]], False),
        ("dcterms:isPartOf", [MEDJAT_COLLECTION_URI], False),
        ("dcterms:identifier", [f"zotero:{record['zotero']['group']}:{record['key']}"], True),
    ]
    if display.get("abstract"):
        props.append(("schema:description", [display["abstract"]], True))
    authors = [c["name"] for c in display.get("creators", []) if c.get("role") == "author"]
    creators = [c["name"] for c in display.get("creators", []) if c.get("role") != "author"]
    if authors:
        props.append(("schema:author", authors, True))
    if creators:
        props.append(("schema:creator", creators, True))
    if display.get("year"):
        props.append(("schema:datePublished", [display["year"]], True))
    if display.get("publisher"):
        props.append(("schema:publisher", [display["publisher"]], True))
    if display.get("doi"):
        props.append(("schema:sameAs", [f"https://doi.org/{display['doi']}"], False))
        props.append(("dcterms:identifier", [f"doi:{display['doi']}"], True))
    if display.get("isbn"):
        props.append(("dcterms:identifier", [f"isbn:{display['isbn']}"], True))
    if tags.get("language"):
        props.append(("dcterms:language", tags["language"], True))
    if tags.get("region"):
        props.append(("dcterms:spatial", tags["region"], True))
    subjects = unique(tags.get("themes", []) + tags.get("subjects", []) + tags.get("traditions", []))
    if subjects:
        props.append(("dcterms:subject", subjects, True))
    about_uris = [a["uri"] for a in record["linkedData"].get("about", []) if a.get("uri")]
    if about_uris:
        props.append(("schema:about", about_uris, False))
    authority_uris = [
        item["uri"]
        for item in record["linkedData"].get("authorityMappings", [])
        if str(item.get("uri", "")).startswith(("http://", "https://"))
    ]
    if authority_uris:
        props.append(("schema:sameAs", authority_uris, False))

    lines = []
    if include_prefixes:
        lines.extend(
            [
                "@prefix schema: <https://schema.org/> .",
                "@prefix dcterms: <http://purl.org/dc/terms/> .",
                "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
                "",
            ]
        )
    lines.append(f"{ttl_uri(record['uri'])}")
    rendered = []
    for pred, values, literal in props:
        rendered_values = [ttl_literal(v) if literal else ttl_uri(v) if str(v).startswith("http") else str(v) for v in values if v]
        if rendered_values:
            rendered.append((pred, rendered_values))
    for index, (pred, values) in enumerate(rendered):
        terminator = "." if index == len(rendered) - 1 else ";"
        lines.append(f"  {pred} {', '.join(values)} {terminator}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, index_records: list[dict], full_records: list[dict], generated_at: str) -> None:
    data_dir = root / "data"
    for path in [data_dir / "records", data_dir / "rdf", data_dir / "marc"]:
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    write_json(data_dir / "library.index.json", index_records)
    write_json(data_dir / "library.facets.json", build_facets(index_records))
    manifest = {
        "generatedAt": generated_at,
        "count": len(index_records),
        "index": f"{DATA_PUBLIC_BASE}/library.index.json",
        "facets": f"{DATA_PUBLIC_BASE}/library.facets.json",
        "ttl": f"{DATA_PUBLIC_BASE}/library.ttl",
        "records": [
            {
                "key": record["key"],
                "json": f"{DATA_PUBLIC_BASE}/records/{shard_for_key(record['key'])}/{record['key']}.json",
                "ttl": f"{DATA_PUBLIC_BASE}/rdf/{shard_for_key(record['key'])}/{record['key']}.ttl",
            }
            for record in index_records
        ],
    }
    write_json(data_dir / "library.json", manifest)
    write_json(
        data_dir / "marc" / "library.marc.json",
        {
            "generatedAt": generated_at,
            "count": len(full_records),
            "records": [{"key": record["key"], "marc": record["marc"]} for record in full_records],
        },
    )

    aggregate_ttl = [
        "@prefix schema: <https://schema.org/> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        f"{ttl_uri(MEDJAT_COLLECTION_URI)}",
        '  a schema:Collection ;',
        '  schema:name "Medjat Library" ;',
        f"  schema:url {ttl_uri('https://medjat.irokosociety.org/library/')} .",
        "",
    ]

    for record in full_records:
        key = record["key"]
        record_path = data_dir / "records" / shard_for_key(key) / f"{key}.json"
        ttl_path = data_dir / "rdf" / shard_for_key(key) / f"{key}.ttl"
        write_json(record_path, record)
        item_ttl = ttl_item(record, include_prefixes=True)
        write_text(ttl_path, item_ttl)
        aggregate_ttl.append(ttl_item(record, include_prefixes=False))

    write_text(data_dir / "library.ttl", "\n".join(aggregate_ttl))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static Medjat Library catalog data.")
    parser.add_argument("--zotero-group", default=ZOTERO_GROUP)
    parser.add_argument("--api-key", default=os.environ.get("ZOTERO_API_KEY", ""))
    parser.add_argument("--limit", type=int, default=None, help="Limit Zotero records for a test build.")
    parser.add_argument("--tradition-vocab", default="", help="Optional local tradition-vocab.json path.")
    args = parser.parse_args()

    root = repo_root()
    maps = load_maps(root)
    vocab = load_tradition_vocab(root, args.tradition_vocab)
    raw_items = fetch_zotero_items(args.zotero_group, args.api_key, args.limit)
    generated_at = utc_now()

    index_records = []
    full_records = []
    overrides = maps["overrides"].get("records", {})
    for item in raw_items:
        item_type = (item.get("data", {}).get("itemType") or "").lower()
        if item_type in {"attachment", "note"}:
            continue
        index_record, full_record = normalize_item(item, vocab, maps)
        override = overrides.get(index_record["key"], {})
        if override:
            apply_record_override(index_record, full_record, override)
        if index_record["title"]:
            index_records.append(index_record)
            full_records.append(full_record)

    index_records.sort(key=lambda r: ((r["creators"][0] if r["creators"] else r["title"]).casefold(), r["title"].casefold()))
    full_by_key = {record["key"]: record for record in full_records}
    full_records = [full_by_key[record["key"]] for record in index_records]
    write_outputs(root, index_records, full_records, generated_at)
    print(f"Built {len(index_records)} public library records into {root / 'data'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
