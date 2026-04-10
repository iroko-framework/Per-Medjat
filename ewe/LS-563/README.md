# LS563 Linked Data Project — Verger Ewé Dataset

**Délé Fágbèmí Ọ̀.** | **University of Alabama - MLIS** | **LS563 Linked Data**

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

**What gets a URI and why:**
Each accepted plant record receives a persistent URI in the Iroko data namespace (https://ontology.irokosociety.org/data/ewe/Plant####). Records are assigned URIs rather than treated as blank nodes or literals because each record is a governed entity with its own identity, access tier, and long-term resolvability. A URI-identified record can be linked to by other systems, resolved independently, and governed by the Iroko Framework's access tier architecture in a machine-actionable way.

Governance concepts (access level, ritual use, and medicinal use) are also modeled as URIs referencing controlled terms in the Iroko Framework vocabulary rather than as string literals. This means any system consuming the data can resolve the term, apply the governance logic, and interoperate with the vocabulary. A literal like "initiated only" carries no machine-actionable semantics; a URI reference to iroko:access-initiated-only does.

**What gets linked to external vocabularies and why:**
Scientific names use dwc:scientificName and taxonomic status uses dwc:taxonomicStatus from Darwin Core, aligning the dataset with GBIF and Catalogue of Life standards. This enables interoperability with biodiversity informatics systems without custom crosswalks and situates the dataset within an established botanical linked data ecosystem.
Vernacular name labels use SKOS (skos:prefLabel and skos:altLabel) because SKOS is the standard vocabulary for concept labeling across multiple languages and is widely supported in linked data applications.

**What remains a literal and why:**
Vernacular names are modeled as typed literals with BCP 47 language tags rather than as URI-identified entities because they are assertions about a record, not independent entities. Their meaning is inseparable from linguistic context. The same string can refer to different plants across traditions, so language tagging rather than URI identification is the appropriate model.

@x-lucumi is used as a private use BCP 47 subtag for Lucumí rather than subsuming it under @yo (Standard Yoruba). Lucumí is an autonomous liturgical language with a collapsed tonal system and Spanish-influenced lexicon developed across centuries of Afro-Cuban religious practice. Subsuming it under Standard Yoruba would misrepresent both languages and obscure a meaningful distinction the data is specifically designed to preserve.

Free-text fields such as iroko:collisionNote and iroko:ritualNote remain string literals tagged @en because they are explanatory prose, not governed concepts, and do not require URI identification.

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
| [Verger_Ewe_Dataset_v4.ttl](Verger_Ewe_Dataset_v4.ttl) | RDF dataset — 50 accepted records, corrected per Part 3 feedback |
| [Verger_Ewe_Mapping_Table_v4.xlsx](Verger_Ewe_Mapping_Table_v4.xlsx) | Darwin Core to Iroko Framework mapping table |
| [Verger_Ewe_RDF_Diagram_v4.png](Verger_Ewe_RDF_Diagram_v4.png) | RDF graph diagram showing class structure and property relationships |
| [Verger_Ewe_Dataset_v3.xlsx](Verger_Ewe_Dataset_v3.xlsx) | Source workbook — Accepted_Records and Synonym_Records sheets |

---

*Dataset developed as part of LS563 Linked Data, University of Alabama MLIS Program.*
*Iroko Framework published under CC0. Dataset © 2026 Délé Fágbèmí Ọ̀. / Iroko Historical Society.*
