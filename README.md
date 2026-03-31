# LS563 Linked Data Project — Verger Ewé Dataset

**Ayodele Odiduro | University of Alabama MLIS | LS563 Linked Data**

---

## Dataset Description

This dataset transforms a subset of Pierre Fatumbi Verger's ethnobotanical corpus — specifically the accepted specimen records from the Tulane University Herbarium — into linked RDF data using the Iroko Framework and Darwin Core.

**Source material:** Pierre Fatumbi Verger, *Ewé: The Use of Plants in Yoruba Society* (Editora Schwarcz, 1995). Verger documented sacred and medicinal plant use across Yoruba, Lucumí, and Afro-Caribbean communities, recording vernacular names across multiple languages and traditions alongside botanical identifications.

**Scope:** 13 accepted plant records drawn from the Tulane Herbarium collection, each representing a species documented by Verger with ritual, medicinal, and ethnobotanical significance in Afro-Atlantic religious communities.

**Record structure:** Each plant record includes:
- Scientific name (Darwin Core `dwc:scientificName`)
- Vernacular names across Yoruba, Lucumí (Cuban), Spanish, English, Haitian Creole, and Portuguese with appropriate language tags (`@yo`, `@x-lucumi`, `@es`, `@en`, `@ht`, `@pt`)
- Ritual use classification (Iroko Framework)
- Medicinal use classification (Iroko Framework)
- Access tier governance (Iroko Framework)
- Name collision flags for species sharing vernacular names across the corpus

---

## Ontologies and Controlled Vocabularies

### Primary Ontology: Iroko Framework (iroko-ewe module)
- **Namespace:** `https://ontology.irokosociety.org/iroko#`
- **DOI:** [10.5281/zenodo.18826673](https://doi.org/10.5281/zenodo.18826673)
- **Published at:** [ontology.irokosociety.org](https://ontology.irokosociety.org)

The Iroko Framework is a modular semantic vocabulary system for the ethical description and governance of Afro-Atlantic sacred knowledge systems. The `iroko-ewe` module specifically addresses ethnobotanical and plant-based ritual knowledge.

**Iroko classes and properties used:**
- `iroko:EwePlantRecord` — root class for plant records
- `iroko:accessLevel` — governs record visibility (public, community, initiated, elder)
- `iroko:ritualUse` — classifies ritual function (healing, protection, offering, purification, cosmological, boundary)
- `iroko:medicinalUse` — classifies medicinal application
- `iroko:nameCollision` — boolean flag for species sharing vernacular names with other records
- `iroko:collisionNote` — prose description of name collision context
- `iroko:ritualNote` — etymological or contextual notes on vernacular names

**Access level concepts used:**
- `iroko:access-public-unrestricted` — available to all researchers
- `iroko:access-community-only` — available to tradition community members
- `iroko:access-initiated-only` — requires initiatory standing
- `iroko:access-initiated-elder` — elder-level initiatory access required
- `iroko:access-public-no-amplification` — publicly known but not to be amplified

### Darwin Core
- **Namespace:** `http://rs.tdwg.org/dwc/terms/`
- Used for: `dwc:scientificName`, `dwc:taxonomicStatus`

### SKOS (Simple Knowledge Organization System)
- **Namespace:** `http://www.w3.org/2004/02/skos/core#`
- Used for: `skos:prefLabel` (primary Cuban Spanish name), `skos:altLabel` (all vernacular names with language tags)

### Dublin Core Terms
- **Namespace:** `http://purl.org/dc/terms/`
- Used for: `dcterms:identifier`

### XML Schema Datatypes
- **Namespace:** `http://www.w3.org/2001/XMLSchema#`
- Used for: `xsd:boolean` (name collision flags), `xsd:string` (identifier literals)

---

## Linking Strategy

### Internal linking (Iroko namespace)
Each plant record is identified by a persistent URI in the Iroko data namespace:
```
https://ontology.irokosociety.org/data/ewe/Plant0010
```
All class assignments (`rdf:type iroko:EwePlantRecord`) and property values link to terms defined in the published Iroko Framework vocabulary. The vocabulary terms are resolvable URIs — they resolve to human-readable documentation at `ontology.irokosociety.org`.

### External linking (Darwin Core)
Scientific names use Darwin Core properties to align with biodiversity informatics standards, enabling the dataset to interoperate with GBIF, Catalogue of Life, and other biodiversity linked data systems.

### Multilingual name linking (SKOS)
Vernacular names are recorded as SKOS labels with BCP 47 language tags:
- `@yo` — Yoruba
- `@x-lucumi` — Lucumí (private use subtag for Cuban Yoruba-derived liturgical language)
- `@es` — Spanish (Cuban and broader Caribbean vernacular)
- `@en` — English
- `@ht` — Haitian Creole
- `@pt` — Portuguese

The use of `@x-lucumi` rather than subsuming Lucumí under `@yo` reflects a core design decision of the Iroko Framework: Lucumí is an autonomous linguistic system with distinct orthographic conventions, a collapsed tonal system, and Spanish-influenced lexical patterns. Subordinating it to Standard Yoruba would misrepresent both languages.

### Access governance linking
Each record links to an access concept in the Iroko Framework that governs how the record should be treated in any downstream application. This is the central innovation of the dataset relative to standard Darwin Core botanical records — the access tier is a first-class triple, not metadata.

---

## Sample Triples

**Plant record with access governance and multilingual names (PRODIGIOSA, Bryophyllum pinnatum):**

```turtle
<https://ontology.irokosociety.org/data/ewe/Plant0016>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Bryophyllum pinnatum" ;
    dwc:taxonomicStatus  "accepted"@en ;
    skos:prefLabel       "PRODIGIOSA"@es ;
    skos:altLabel        "LIFE EVERLASTING"@en ;
    skos:altLabel        "Siempreviva"@es ;
    skos:altLabel        "Abàmọdá"@yo ;
    skos:altLabel        "Ewe dun dun"@x-lucumi ;
    skos:altLabel        "Zèb maltèt"@ht ;
    iroko:accessLevel    iroko:access-public-unrestricted ;
    iroko:ritualUse      iroko:ritual-protection-boundary ;
    iroko:medicinalUse   iroko:medicinal-general-tonic ;
    iroko:nameCollision  "false"^^xsd:boolean ;
    dcterms:identifier   "Plant0016"^^xsd:string .
```

**Name collision record (NARANJA AGRIA, Citrus aurantium):**

```turtle
<https://ontology.irokosociety.org/data/ewe/Plant0023>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Citrus aurantium" ;
    skos:prefLabel       "NARANJA AGRIA"@es ;
    skos:altLabel        "sour orange"@en ;
    skos:altLabel        "Òròmbó"@yo ;
    skos:altLabel        "Korosan"@x-lucumi ;
    iroko:nameCollision  "true"^^xsd:boolean ;
    iroko:collisionNote  "Name \"Òròmbó\" shared with other Citrus species"@en ;
    iroko:accessLevel    iroko:access-initiated-only .
```

**Access-restricted record (BONIATO, Ipomoea batatas):**

```turtle
<https://ontology.irokosociety.org/data/ewe/Plant0029>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Ipomoea batatas" ;
    skos:prefLabel       "BONIATO"@es ;
    skos:altLabel        "SWEET POTATOE"@en ;
    skos:altLabel        "Ọ̀dúnkùn"@yo ;
    skos:altLabel        "Oduko"@x-lucumi ;
    iroko:accessLevel    iroko:access-initiated-only ;
    iroko:ritualUse      iroko:ritual-purification-cleansing ;
    iroko:nameCollision  "false"^^xsd:boolean .
```

---

## Files in This Repository

| File | Description |
|---|---|
| `Verger_Ewe_Dataset_v4.ttl` | RDF dataset in Turtle format — 13 plant records, 1,195 triples |
| `Verger_Ewe_Dataset_v3.xlsx` | Original Darwin Core two-sheet workbook (Accepted_Records and Synonym_Records) |
| `Verger_Ewe_RDF_Diagram.png` | RDF graph diagram showing class structure and property relationships |
| `Verger_Ewe_Mapping_Table.xlsx` | Darwin Core → Iroko Framework mapping table with linking rationale |
| `README.md` | This file |

---

## Corrections from Part 3 Submission

**v4 corrects two issues identified in instructor feedback:**

1. **xsd:boolean values** — All boolean literals corrected from `"Yes"`/`"No"` to `"true"`/`"false"` per the W3C XML Schema specification for `xsd:boolean`.

2. **Missing language tags and datatypes** — Applied throughout:
   - `dwc:taxonomicStatus` values now carry `@en`
   - `dcterms:identifier` string literals now carry `^^xsd:string`
   - `iroko:ritualNote` and `iroko:collisionNote` now carry `@en`
   - `skos:prefLabel` values now carry `@es` (Cuban Spanish primary names)
   - `skos:altLabel` values now carry language tags: `@yo`, `@x-lucumi`, `@es`, `@en`, `@ht`, `@pt` — determined by linguistic pattern analysis across the multilingual corpus

---

*Dataset developed as part of LS563 Linked Data, University of Alabama MLIS Program.*
*Iroko Framework published under CC0. Dataset © 2026 Ayodele Odiduro / Iroko Historical Society.*
