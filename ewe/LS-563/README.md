# LS563 Linked Data Project — Verger Ewé Dataset

**Délé Fágbèmí Ọ̀. | University of Alabama MLIS | LS563 Linked Data**

**Live pilot data:** [medjat.irokosociety.org/ewe/](https://medjat.irokosociety.org/ewe/)

---

## Dataset Description

A subset of Pierre Fatumbi Verger's ethnobotanical corpus transformed into linked RDF data, supplemented by Dalia Quiros-Moran's work for Spanish and Cuban vernacular names. Sources: Verger, *Ewé: The Use of Plants in Yoruba Society* (1995); Quiros-Moran, *Guide to Afro-Cuban Herbalism* (2009). The dataset covers 50 accepted plant records, each documenting a species with ritual and medicinal significance in Afro-Atlantic religious communities. Records include scientific names, multilingual vernacular names (Yoruba, Lucumí, Spanish, English, Haitian Creole), ritual and medicinal use classifications, and access tier governance.


---

## Ontologies and Controlled Vocabularies

**Iroko Framework — iroko-ewe module**
Namespace: `https://ontology.irokosociety.org/iroko#`
DOI: [10.5281/zenodo.18826673](https://doi.org/10.5281/zenodo.18826673)

Classes and properties used: `iroko:EwePlantRecord`, `iroko:accessLevel`, `iroko:ritualUse`, `iroko:medicinalUse`, `iroko:nameCollision`, `iroko:collisionNote`, `iroko:ritualNote`

**Darwin Core** (`http://rs.tdwg.org/dwc/terms/`)
Used for: `dwc:scientificName`, `dwc:taxonomicStatus`

**SKOS** (`http://www.w3.org/2004/02/skos/core#`)
Used for: `skos:prefLabel` (primary Cuban Spanish name), `skos:altLabel` (vernacular names with language tags)

**Dublin Core Terms** (`http://purl.org/dc/terms/`)
Used for: `dcterms:identifier`

**XML Schema** (`http://www.w3.org/2001/XMLSchema#`)
Used for: `xsd:boolean`, `xsd:string`

---

## Linking Strategy

Each plant record has a persistent URI in the Iroko data namespace (`https://ontology.irokosociety.org/data/ewe/Plant####`). Class assignments and property values link to terms defined in the published Iroko Framework vocabulary. Darwin Core properties align the dataset with biodiversity informatics standards (GBIF, Catalogue of Life).

Vernacular names use SKOS labels with BCP 47 language tags: `@yo` (Yoruba), `@x-lucumi` (Lucumí — private use subtag preserving its autonomy from Standard Yoruba), `@es` (Spanish), `@en` (English), `@ht` (Haitian Creole), `@pt` (Portuguese).

Each record links to an Iroko access concept governing downstream use: `iroko:access-public-unrestricted`, `iroko:access-community-only`, `iroko:access-initiated-only`, `iroko:access-initiated-elder`, `iroko:access-public-no-amplification`.

Taxonomic synonyms are modeled as separate records in a companion Synonym_Records sheet, each with its own IHS-namespaced URI (`Plant####s#`), linked back to the accepted record via `dwc:acceptedNameUsageID`. This follows the Darwin Core multi-record name usage model as implemented by GBIF and Catalogue of Life.

---

## Sample Triples

```turtle
<https://ontology.irokosociety.org/data/ewe/Plant0016>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Bryophyllum pinnatum"^^xsd:string ;
    dwc:taxonomicStatus  "accepted"@en ;
    skos:prefLabel       "PRODIGIOSA"@es ;
    skos:altLabel        "LIFE EVERLASTING"@en ;
    skos:altLabel        "Abàmọdá"@yo ;
    skos:altLabel        "Ewe dun dun"@x-lucumi ;
    iroko:accessLevel    iroko:access-public-unrestricted ;
    iroko:ritualUse      iroko:ritual-protection-boundary ;
    iroko:nameCollision  "false"^^xsd:boolean ;
    dcterms:identifier   "Plant0016"^^xsd:string .

<https://ontology.irokosociety.org/data/ewe/Plant0023>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Citrus aurantium"^^xsd:string ;
    dwc:taxonomicStatus  "accepted"@en ;
    skos:prefLabel       "NARANJA AGRIA"@es ;
    skos:altLabel        "sour orange"@en ;
    skos:altLabel        "Òròmbó"@yo ;
    skos:altLabel        "Korosan"@x-lucumi ;
    iroko:nameCollision  "true"^^xsd:boolean ;
    iroko:collisionNote  "Name \"Òròmbó\" shared with other Citrus species"@en ;
    iroko:accessLevel    iroko:access-initiated-only .
```

*v4 corrects Part 3 feedback: boolean values changed from "Yes"/"No" to "true"/"false" per xsd:boolean specification; language tags and datatypes added throughout (`@en`, `@es`, `^^xsd:string`); `dwc:taxonomicStatus` added with `@en`; synonym records split to separate sheet following Darwin Core multi-record model.*

---

## Files

| File | Description |
|---|---|
| [Verger_Ewe_Dataset_v4.ttl](Verger_Ewe_Dataset_v4.ttl) | RDF dataset — 13 accepted records, corrected per Part 3 feedback |
| [Verger_Ewe_Mapping_Table_v4.xlsx](Verger_Ewe_Mapping_Table_v4.xlsx) | Darwin Core to Iroko Framework mapping table |
| [Verger_Ewe_RDF_Diagram_v4.png](Verger_Ewe_RDF_Diagram_v4.png) | RDF graph diagram showing class structure and property relationships |
| [Verger_Ewe_Dataset_v3.xlsx](Verger_Ewe_Dataset_v3.xlsx) | Source workbook — Accepted_Records and Synonym_Records sheets |

---

*Dataset developed as part of LS563 Linked Data, University of Alabama MLIS Program.*
*Iroko Framework published under CC0. Dataset © 2026 Délé Fágbèmí Ọ̀. / Iroko Historical Society.*
