# LS563 Linked Data Project — Verger Ewé Dataset

**Délé Fágbèmí Ọ̀. | University of Alabama MLIS | LS563 Linked Data**

---

## Dataset Description

A subset of Pierre Fatumbi Verger's ethnobotanical corpus transformed into linked RDF data. Source: *Ewé: The Use of Plants in Yoruba Society* (1995). The dataset covers 13 accepted plant records from the Tulane University Herbarium, each documenting a species with ritual and medicinal significance in Afro-Atlantic religious communities. Records include scientific names, multilingual vernacular names (Yoruba, Lucumí, Spanish, English, Haitian Creole, Portuguese), ritual and medicinal use classifications, and access tier governance.

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

---

## Sample Triples

```turtle
<https://ontology.irokosociety.org/data/ewe/Plant0016>
    rdf:type             iroko:EwePlantRecord ;
    dwc:scientificName   "Bryophyllum pinnatum" ;
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
    dwc:scientificName   "Citrus aurantium" ;
    skos:prefLabel       "NARANJA AGRIA"@es ;
    skos:altLabel        "Òròmbó"@yo ;
    skos:altLabel        "Korosan"@x-lucumi ;
    iroko:nameCollision  "true"^^xsd:boolean ;
    iroko:collisionNote  "Name \"Òròmbó\" shared with other Citrus species"@en ;
    iroko:accessLevel    iroko:access-initiated-only .
```

---

## Files

| File | Description |
|---|---|
| `Verger_Ewe_Dataset_v4.ttl` | RDF dataset — 13 records, 1,195 triples |
| `Verger_Ewe_Dataset_v3.xlsx` | Original Darwin Core workbook |
| `Verger_Ewe_RDF_Diagram.png` | RDF graph diagram |
| `Verger_Ewe_Mapping_Table.xlsx` | Mapping table |

*v4 corrects Part 3 feedback: boolean values changed from "Yes"/"No" to "true"/"false" per xsd:boolean specification; language tags and datatypes added throughout.*
