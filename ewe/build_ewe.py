from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

from access import ACCESS_META, ACCESS_ORDER, boundary_message, evaluate_assertion, field_access, max_access
from model import AssertionModel, PlantRecord, SectionModel

BASE = Path(__file__).resolve().parent
DEFAULT_TTL = BASE / 'Verger_Ewe_Dataset_v4.ttl'
# Fixed 2026-07-03: this used to default to 'output/', a stale directory that
# was not the live deploy target. '.' matches actual deploy practice -- the
# rendered site lives in ewe/ root alongside templates/, assets/, etc.
DEFAULT_OUT = BASE
DEFAULT_CONFIG = BASE / 'site_config.json'
# Medjat Ewé Acquire/Steward's system-of-record database (see
# Main-Vault/14_Per_Medjat/Ewe/ewe-acquire-steward-spec.md). Only records at
# status='approved' or 'published' are read from here; 'pilot', 'draft', and
# everything else are excluded, same as they would be from a TTL that only
# ever contained finished records.
# medjat-tools is the canonical repo for all Medjat tools (confirmed
# 2026-07-03) and is a sibling of Per-Medjat under the same parent directory
# on Délé's machine. This resolves correctly from that layout without a
# hardcoded home-directory guess.
DEFAULT_DB = BASE.parent.parent / 'medjat-tools' / 'medjat_ewe.sqlite3'
PUBLISHABLE_STATUSES = {'approved', 'published'}
# Verified 2026-07-03 against iroko-framework/vocab/iroko-core.ttl's
# iroko:AccessLevelScheme: access-no-access carries skos:notation 99 and is
# annotated "Operational or internal use only. Never exported to RDF." A
# record at this tier is excluded from the build entirely -- no HTML page,
# no JSON-LD, no search-index.json entry -- not merely field-redacted. Prior
# to 2026-07-03 this build only redacted individual fields and still leaked
# a no-access record's existence into search-index.json; that gap is closed
# here for both the TTL and SQLite code paths.
NEVER_EXPORT_ACCESS = {'access-no-access'}
IROKO = 'https://ontology.irokosociety.org/iroko#'
EWE_RECORD = URIRef(f'{IROKO}EwePlantRecord')
DWC_SCIENTIFIC_NAME = URIRef('http://rs.tdwg.org/dwc/terms/scientificName')
DWC_TAXONOMIC_STATUS = URIRef('http://rs.tdwg.org/dwc/terms/taxonomicStatus')

LANG_ORDER = ['en', 'yo', 'es', 'pt', 'fr', 'ht', 'x-lucumi']
LANG_LABELS = {
    'en': 'English',
    'yo': 'Yoruba',
    'es': 'Spanish / Cuban',
    'pt': 'Brazilian Portuguese',
    'fr': 'French',
    'ht': 'Haitian Creole',
    'x-lucumi': 'Lucumí / Liturgical',
    'und': 'Unresolved / Other',
}
PRIMARY_CARD_LANGS = ['en', 'yo', 'es']

UI_COPY = {
    'all_plants': {'en': 'All Plants', 'es': 'Todas las Plantas', 'fr': 'Toutes les Plantes', 'yo': 'Gbogbo Ewé', 'pt': 'Todas as Plantas'},
    'about_title': {'en': 'About the Ewé Database', 'es': 'Acerca de la Base de Datos Ewé', 'fr': 'À propos de la Base de Données Ewé', 'yo': 'Nípa Àkójọpọ̀ Ewé', 'pt': 'Sobre a Base de Dados Ewé'},
    'about_body': {
        'en': 'The Ewé Database provides a public interface for plant records structured using the Iroko Framework. Public botanical and vernacular knowledge remains discoverable, while governed assertions are displayed with explicit stewardship boundaries rather than silent omission.',
        'es': 'La Base de Datos Ewé ofrece una interfaz pública para registros botánicos estructurados mediante el Iroko Framework. El conocimiento botánico y vernáculo público sigue siendo visible, mientras que las afirmaciones gobernadas se muestran con límites explícitos de custodia en lugar de omisiones silenciosas.',
        'fr': 'La Base de Données Ewé fournit une interface publique pour des notices botaniques structurées à l’aide du cadre Iroko. Les connaissances botaniques et vernaculaires publiques restent visibles, tandis que les assertions gouvernées sont affichées avec des limites explicites de stewardship plutôt qu’avec des silences invisibles.',
        'yo': 'Àkójọpọ̀ Ewé pèsè ọ̀nà gbangba fún àwọn àkọsílẹ̀ ọgbìn tí a ṣètò pẹ̀lú Iroko Framework. Ìmọ̀ ewéko àti àwọn orúkọ tó yẹ kí gbogbo ènìyàn rí ṣì hàn, ṣùgbọ́n ohun tí a ń ṣàkóso ní àyè ìtọju hàn pẹ̀lú àlàyé kedere dípò kí wọ́n pàrọ́ mọ́ra.',
        'pt': 'A Base de Dados Ewé oferece uma interface pública para registros botânicos estruturados pelo Iroko Framework. O conhecimento botânico e vernacular público permanece visível, enquanto as afirmações governadas são mostradas com limites explícitos de custódia em vez de omissões silenciosas.',
    },
    'search_placeholder': {'en': 'Search by name, scientific name, or vernacular…', 'es': 'Buscar por nombre, nombre científico o vernáculo…', 'fr': 'Rechercher par nom, nom scientifique ou vernaculaire…', 'yo': 'Wá nínú àwọn orúkọ…', 'pt': 'Pesquisar por nome, nome científico ou vernáculo…'},
    'plants': {'en': 'plants', 'es': 'plantas', 'fr': 'plantes', 'yo': 'ewé', 'pt': 'plantas'},
    'all_access': {'en': 'All Access Tiers', 'es': 'Todos los Niveles de Acceso', 'fr': 'Tous les Niveaux d’Accès', 'yo': 'Gbogbo Ìpele Àyèwọlé', 'pt': 'Todos os Níveis de Acesso'},
    'classification': {'en': 'Classification', 'es': 'Clasificación', 'fr': 'Classification', 'yo': 'Ìpín', 'pt': 'Classificação'},
    'names_by_language': {'en': 'Names by Language', 'es': 'Nombres por Idioma', 'fr': 'Noms par Langue', 'yo': 'Àwọn Orúkọ nípa Èdè', 'pt': 'Nomes por Idioma'},
    'regional_names': {'en': 'Regional and Unresolved Names', 'es': 'Nombres Regionales y No Resueltos', 'fr': 'Noms Régionaux et Non Résolus', 'yo': 'Àwọn Orúkọ Ẹkùn àti Tí Kò Tíì Yanju', 'pt': 'Nomes Regionais e Não Resolvidos'},
    'sacred_knowledge': {'en': 'Sacred Knowledge', 'es': 'Conocimiento Sagrado', 'fr': 'Savoir Sacré', 'yo': 'Ìmọ̀ Mímọ́', 'pt': 'Conhecimento Sagrado'},
    'record_governance': {'en': 'Record Governance', 'es': 'Gobernanza del Registro', 'fr': 'Gouvernance de la Notice', 'yo': 'Ìṣàkóso Àkọsílẹ̀', 'pt': 'Governança do Registro'},
    'scientific_name': {'en': 'Scientific Name', 'es': 'Nombre Científico', 'fr': 'Nom Scientifique', 'yo': 'Orúkọ Sáyẹ́ǹsì', 'pt': 'Nome Científico'},
    'taxonomic_status': {'en': 'Taxonomic Status', 'es': 'Estado Taxonómico', 'fr': 'Statut Taxonomique', 'yo': 'Ìpo Sáyẹ́ǹsì', 'pt': 'Status Taxonômico'},
    'record_uri': {'en': 'Record URI', 'es': 'URI del Registro', 'fr': 'URI de la Notice', 'yo': 'URI Àkọsílẹ̀', 'pt': 'URI do Registro'},
    'html_page': {'en': 'Public HTML Page', 'es': 'Página HTML Pública', 'fr': 'Page HTML Publique', 'yo': 'Ojú-ìwé HTML Gbangba', 'pt': 'Página HTML Pública'},
    'vocabulary': {'en': 'Vocabulary', 'es': 'Vocabulario', 'fr': 'Vocabulaire', 'yo': 'Àwọn Ọ̀rọ̀', 'pt': 'Vocabulário'},
    'medicinal_use': {'en': 'Medicinal Use', 'es': 'Uso Medicinal', 'fr': 'Usage Médicinal', 'yo': 'Lílo Ìwòsàn', 'pt': 'Uso Medicinal'},
    'ritual_use': {'en': 'Ritual Use', 'es': 'Uso Ritual', 'fr': 'Usage Rituel', 'yo': 'Lílo Àṣà', 'pt': 'Uso Ritual'},
    'ritual_notes': {'en': 'Ritual Notes', 'es': 'Notas Rituales', 'fr': 'Notes Rituelles', 'yo': 'Àwọn Àkọsílẹ̀ Àṣà', 'pt': 'Notas Rituais'},
    'collision_note': {'en': 'Collision Note', 'es': 'Nota de Colisión', 'fr': 'Note de Collision', 'yo': 'Àkọsílẹ̀ Ìjàmbá Orúkọ', 'pt': 'Nota de Colisão'},
    'scientific_synonyms': {'en': 'Scientific Synonyms', 'es': 'Sinónimos Científicos', 'fr': 'Synonymes Scientifiques', 'yo': 'Àwọn Orúkọ Sáyẹ́ǹsì Míràn', 'pt': 'Sinônimos Científicos'},
    'other_regional_names': {'en': 'Other Regional Names', 'es': 'Otros Nombres Regionales', 'fr': 'Autres Noms Régionaux', 'yo': 'Àwọn Orúkọ Ẹkùn Míràn', 'pt': 'Outros Nomes Regionais'},
    'none_recorded': {'en': 'None recorded', 'es': 'Ninguno registrado', 'fr': 'Aucun enregistré', 'yo': 'Kò sí tí a kọ', 'pt': 'Nenhum registrado'},
    'no_public_search': {'en': 'Hidden from public search', 'es': 'Oculto de la búsqueda pública', 'fr': 'Masqué de la recherche publique', 'yo': 'Farapamọ́ kúrò nínú ìwádìí gbangba', 'pt': 'Oculto da busca pública'},
    'next': {'en': 'Next', 'es': 'Siguiente', 'fr': 'Suivant', 'yo': 'Tókàn', 'pt': 'Próximo'},
}

# Verified 2026-07-04 against iroko-framework/vocab/iroko-ewe.ttl's
# iroko:RitualUseScheme (17 concepts) and iroko:MedicinalUseScheme (12
# concepts) -- these two dicts previously held a hand-picked subset (7
# ritual, 4 medicinal) that undercounted the real controlled vocabulary.
# Kept in sync with medjat-tools/medjat_ewe_shared.py's RITUAL_USE_TYPES /
# MEDICINAL_USE_TYPES, which Ewé Steward's dropdown is built from -- if a
# use_type reaches this file that isn't a key here, the .get(key, key)
# fallback below prints the raw slug instead of a label, so any concept
# addition needs to land in both places.
RITUAL_LABELS = {
    'ritual-ancestor-veneration': 'Ancestor Veneration',
    'ritual-consecration': 'Consecration',
    'ritual-cosmological-symbolic': 'Cosmological / Symbolic',
    'ritual-death-rites': 'Death Rites',
    'ritual-divination-enhancement': 'Divination Enhancement',
    'ritual-domination-binding': 'Domination & Binding',
    'ritual-healing-restoration': 'Healing & Restoration',
    'ritual-house-blessing': 'House & Space Blessing',
    'ritual-invocation-communication': 'Invocation & Communication',
    'ritual-legal-justice': 'Legal & Justice',
    'ritual-love-attraction': 'Love & Attraction',
    'ritual-offering-devotion': 'Offering & Devotion',
    'ritual-prosperity-abundance': 'Prosperity & Abundance',
    'ritual-protection-boundary': 'Protection & Boundary',
    'ritual-purification-cleansing': 'Purification & Cleansing',
    'ritual-rites-of-transition': 'Rites of Transition',
    'ritual-road-opening': 'Road Opening',
}

MEDICINAL_LABELS = {
    'medicinal-anti-inflammatory': 'Anti-Inflammatory',
    'medicinal-digestive-support': 'Digestive Support',
    'medicinal-fever-reduction': 'Fever Reduction',
    'medicinal-maternal-postpartum': 'Maternal & Postpartum Care',
    'medicinal-pain-relief': 'Pain Relief',
    'medicinal-pediatric': 'Pediatric Use',
    'medicinal-reproductive-fertility': 'Reproductive & Fertility Support',
    'medicinal-respiratory-support': 'Respiratory Support',
    'medicinal-skin-topical': 'Skin and Topical Use',
    'medicinal-general-tonic': 'General Tonic / Revitalizing',
    'medicinal-spiritual-psychosomatic': 'Spiritual & Psychosomatic',
    'medicinal-wound-healing': 'Wound Healing',
}


def local_name(value: str) -> str:
    if '#' in value:
        return value.rsplit('#', 1)[-1]
    return value.rstrip('/').rsplit('/', 1)[-1]


def literal_text(obj: Any) -> str:
    return str(obj).strip()


def append_unique(bucket: list[str], value: str) -> None:
    if value and value not in bucket:
        bucket.append(value)


def normalized_ascii(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()


def sort_records(records: list[PlantRecord]) -> list[PlantRecord]:
    return sorted(records, key=lambda r: ((r.primary_yoruba or r.pref_label).casefold(), r.identifier))


def looks_like_scientific_name(value: str) -> bool:
    parts = [part for part in value.replace('.', '').split() if part]
    if len(parts) < 2:
        return False
    first, second = parts[0], parts[1]
    return first[:1].isupper() and second[:1].islower()


def partition_regional_names(values: list[str], scientific_name: str) -> tuple[list[str], list[str]]:
    sci, other = [], []
    scientific_key = scientific_name.casefold().strip()
    for value in values:
        v = value.strip()
        if not v or v.casefold() == scientific_key:
            continue
        if v.casefold().startswith(('syn.', 'synonym:')) or looks_like_scientific_name(v) or any(part in v.casefold() for part in [' var.', ' subsp.', ' spp', ' cf.']):
            sci.append(v.replace('syn.', '').replace('Syn.', '').replace('synonym:', '').strip())
        else:
            other.append(v)

    def dedupe(items: list[str]) -> list[str]:
        seen, cleaned = set(), []
        for item in items:
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                cleaned.append(item)
        return cleaned

    return dedupe(sci), dedupe(other)


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def build_card_names(labels_by_lang: dict[str, list[str]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for lang in PRIMARY_CARD_LANGS:
        values = labels_by_lang.get(lang, [])
        if values:
            rows.append((lang.upper(), values[0]))
    return rows


def make_assertion(field_name: str, display_label: str, value: str | None, record_access: str, lang: str | None = None, category: str | None = None, helper_text: str | None = None) -> AssertionModel:
    assertion_access = field_access(field_name=field_name, record_access=record_access, lang=lang)
    helper = helper_text or 'This assertion is governed by the public stewardship policy for this dataset.'
    decision = evaluate_assertion(assertion_access, helper)
    return AssertionModel(
        field_name=field_name,
        display_label=display_label,
        value=value,
        lang=lang,
        category=category,
        access_key=assertion_access,
        render_mode=decision.render_mode,
        badge_label=decision.badge_label,
        badge_class=decision.badge_class,
        helper_text=decision.helper_text,
    )


def build_sections(record_access: str, labels_by_lang: dict[str, list[str]], scientific_synonyms: list[str], other_regional_names: list[str], ritual_note: str | None, collision_note: str | None) -> dict[str, SectionModel]:
    names_section = SectionModel(key='names', title='Names by Language')
    for lang in LANG_ORDER:
        values = labels_by_lang.get(lang, [])
        if values:
            for value in values:
                names_section.assertions.append(
                    make_assertion(
                        field_name='lucumi_label' if lang == 'x-lucumi' else 'label',
                        display_label=LANG_LABELS.get(lang, lang),
                        value=value,
                        record_access=record_access,
                        lang=lang,
                        category='names',
                        helper_text='This name remains intentionally bounded in the public interface under the record stewardship policy.' if lang == 'x-lucumi' else 'Public linguistic and vernacular labels remain visible in the public interface.',
                    )
                )
        elif lang == 'pt':
            pass
        else:
            names_section.assertions.append(
                AssertionModel(field_name='placeholder', display_label=LANG_LABELS.get(lang, lang), value='None recorded', category='names')
            )

    regional_section = SectionModel(key='regional', title='Regional and Unresolved Names')
    for value in scientific_synonyms:
        regional_section.assertions.append(make_assertion('scientific_synonym', 'Scientific Synonym', value, record_access, category='regional'))
    for value in other_regional_names:
        regional_section.assertions.append(make_assertion('regional_name', 'Regional Name', value, record_access, category='regional'))

    sacred_section = SectionModel(key='sacred', title='Sacred Knowledge')
    if ritual_note:
        sacred_section.assertions.append(
            make_assertion(
                field_name='ritual_note',
                display_label='Ritual Note',
                value=ritual_note,
                record_access=record_access,
                category='sacred',
                helper_text='The ritual note exists in the ontology but remains bounded according to the record access tier.'
            )
        )
    if collision_note:
        sacred_section.assertions.append(
            make_assertion(
                field_name='collision_note',
                display_label='Collision Note',
                value=collision_note,
                record_access=record_access,
                category='sacred',
                helper_text='Collision analysis is displayed in accordance with the stewardship tier assigned to this record.'
            )
        )
    return {'names': names_section, 'regional': regional_section, 'sacred': sacred_section}


def visible_search_chunks(identifier: str, pref_label: str, scientific_name: str, taxonomic_status: str, labels_by_lang: dict[str, list[str]], scientific_synonyms: list[str], other_regional_names: list[str]) -> list[str]:
    chunks = [identifier, pref_label, scientific_name, taxonomic_status]
    for lang, values in labels_by_lang.items():
        if lang == 'x-lucumi':
            continue
        chunks.extend(values)
    chunks.extend(scientific_synonyms)
    chunks.extend(other_regional_names)
    return [chunk for chunk in chunks if chunk]


def build_jsonld(record_uri: str, scientific_name: str, taxonomic_status: str, labels_by_lang: dict[str, list[str]], access_key: str, medicinal_key: str, ritual_key: str) -> dict[str, Any]:
    # JSON-LD intentionally includes only assertions visible in the public build.
    # Free-text plant_uses.description / ritual notes / collision notes never
    # appear here, regardless of tier -- only the controlled-vocabulary
    # category and the access tier itself are exportable as linked data. See
    # the spec's "Ritual and Sensitive Data Handling" section.
    names = []
    for lang, values in labels_by_lang.items():
        if lang == 'x-lucumi':
            continue
        for value in values:
            names.append({'@value': value, '@language': lang})
    # Fixed 2026-07-03: accessLevel/medicinalUse/ritualUse used to be emitted
    # as bare strings or display labels. iroko:medicinalUse and
    # iroko:ritualUse are declared as owl:ObjectProperty in iroko-ewe.ttl,
    # meaning their range is a concept, not a display string -- emitting
    # labels made this JSON-LD look like linked data without actually being
    # dereferenceable. All three are now @id references into the ontology's
    # own vocabulary. See the spec's "Linked-Data Connections" section.
    return {
        '@context': {
            'name': 'http://schema.org/name',
            'alternateName': 'http://schema.org/alternateName',
            'identifier': 'http://purl.org/dc/terms/identifier',
            'scientificName': str(DWC_SCIENTIFIC_NAME),
            'taxonomicStatus': str(DWC_TAXONOMIC_STATUS),
            'accessLevel': {'@id': f'{IROKO}accessLevel', '@type': '@id'},
            'medicinalUse': {'@id': f'{IROKO}medicinalUse', '@type': '@id'},
            'ritualUse': {'@id': f'{IROKO}ritualUse', '@type': '@id'},
        },
        '@id': record_uri,
        '@type': f'{IROKO}EwePlantRecord',
        'scientificName': scientific_name,
        'taxonomicStatus': taxonomic_status,
        'alternateName': names,
        'accessLevel': f'{IROKO}{access_key}' if access_key else None,
        'medicinalUse': f'{IROKO}{medicinal_key}' if medicinal_key else None,
        'ritualUse': f'{IROKO}{ritual_key}' if ritual_key else None,
    }


def parse_graph(ttl_path: Path, config: dict[str, Any]) -> list[PlantRecord]:
    graph = Graph()
    graph.parse(ttl_path, format='turtle')
    public_base = config['public_base'].rstrip('/') + '/'
    records: list[PlantRecord] = []

    for subject in sorted(set(graph.subjects(RDF.type, EWE_RECORD)), key=str):
        labels_by_lang: dict[str, list[str]] = defaultdict(list)
        pref_label = ''
        scientific_name = ''
        taxonomic_status = ''
        identifier = local_name(str(subject))
        access_key = 'access-public-unrestricted'
        medicinal_key = ''
        ritual_key = ''
        name_collision = False
        collision_note = None
        ritual_note = None

        for obj in graph.objects(subject, DCTERMS.identifier):
            if isinstance(obj, Literal):
                text = literal_text(obj)
                if text.startswith('Plant'):
                    identifier = text

        for obj in graph.objects(subject, URIRef(f'{IROKO}accessLevel')):
            access_key = local_name(str(obj))
        for obj in graph.objects(subject, URIRef(f'{IROKO}medicinalUse')):
            medicinal_key = local_name(str(obj))
        for obj in graph.objects(subject, URIRef(f'{IROKO}ritualUse')):
            ritual_key = local_name(str(obj))
        for obj in graph.objects(subject, URIRef(f'{IROKO}nameCollision')):
            name_collision = str(obj).lower() == 'true'
        for obj in graph.objects(subject, URIRef(f'{IROKO}collisionNote')):
            collision_note = literal_text(obj)
        for obj in graph.objects(subject, URIRef(f'{IROKO}ritualNote')):
            ritual_note = literal_text(obj)
        for obj in graph.objects(subject, DWC_SCIENTIFIC_NAME):
            scientific_name = literal_text(obj)
        for obj in graph.objects(subject, DWC_TAXONOMIC_STATUS):
            taxonomic_status = literal_text(obj)
        for obj in graph.objects(subject, SKOS.prefLabel):
            lang = obj.language or 'und'
            text = literal_text(obj)
            if not pref_label:
                pref_label = text
            append_unique(labels_by_lang[lang], text)
        for obj in graph.objects(subject, SKOS.altLabel):
            lang = obj.language or 'und'
            append_unique(labels_by_lang[lang], literal_text(obj))

        if access_key in NEVER_EXPORT_ACCESS:
            # Whole-record exclusion, not field redaction: no page, no
            # JSON-LD, no search-index.json entry. See NEVER_EXPORT_ACCESS.
            continue

        if not pref_label:
            pref_label = labels_by_lang.get('en', [scientific_name or identifier])[0]

        scientific_synonyms, other_regional_names = partition_regional_names(labels_by_lang.get('und', []), scientific_name)
        sections = build_sections(access_key, dict(labels_by_lang), scientific_synonyms, other_regional_names, ritual_note, collision_note)
        access_meta = ACCESS_META.get(access_key, ACCESS_META['access-initiated-only'])
        visible_chunks = visible_search_chunks(identifier, pref_label, scientific_name, taxonomic_status, dict(labels_by_lang), scientific_synonyms, other_regional_names)
        visible_search_text = ' '.join(visible_chunks).strip().casefold()
        visible_jsonld = build_jsonld(str(subject), scientific_name, taxonomic_status, dict(labels_by_lang), access_key, medicinal_key, ritual_key)

        records.append(
            PlantRecord(
                identifier=identifier,
                record_uri=str(subject),
                page_url=f'plant/{quote(identifier)}.html',
                html_public_url=f'{public_base}{quote(identifier)}.html',
                scientific_name=scientific_name,
                taxonomic_status=taxonomic_status,
                pref_label=pref_label,
                labels_by_lang={k: v for k, v in labels_by_lang.items()},
                card_names=build_card_names(labels_by_lang),
                access_key=access_key,
                access_label=access_meta['label'],
                access_class=access_meta['class'],
                medicinal_key=medicinal_key,
                medicinal_label=MEDICINAL_LABELS.get(medicinal_key, medicinal_key or 'Unmapped'),
                ritual_key=ritual_key,
                ritual_label=RITUAL_LABELS.get(ritual_key, ritual_key or 'Unmapped'),
                name_collision=name_collision,
                search_text=visible_search_text,
                search_text_ascii=normalized_ascii(visible_search_text),
                scientific_synonyms=scientific_synonyms,
                other_regional_names=other_regional_names,
                sections=sections,
                visible_jsonld=visible_jsonld,
            )
        )
    return sort_records(records)


def build_sections_from_uses(record_access: str, labels_by_lang: dict[str, list[str]], scientific_synonyms: list[str], other_regional_names: list[str], uses: list[sqlite3.Row], collision_note: str | None) -> dict[str, SectionModel]:
    """SQLite-source equivalent of build_sections().

    Names and regional sections are unchanged in shape from the TTL path.
    The Sacred Knowledge section differs: plant_uses rows already carry their
    own access_tier, assigned by a human reviewer in Ewé Steward, so each use
    is evaluated at its own tier directly rather than inherited from a single
    record-wide tier via field_access(). This is a closer match to how
    iroko:accessLevel governs individual assertions in the ontology than the
    old flat-TTL shape (one accessLevel per record) could represent.
    """
    names_section = SectionModel(key='names', title='Names by Language')
    for lang in LANG_ORDER:
        values = labels_by_lang.get(lang, [])
        if values:
            for value in values:
                names_section.assertions.append(
                    make_assertion(
                        field_name='lucumi_label' if lang == 'x-lucumi' else 'label',
                        display_label=LANG_LABELS.get(lang, lang),
                        value=value,
                        record_access=record_access,
                        lang=lang,
                        category='names',
                        helper_text='This name remains intentionally bounded in the public interface under the record stewardship policy.' if lang == 'x-lucumi' else 'Public linguistic and vernacular labels remain visible in the public interface.',
                    )
                )
        elif lang == 'pt':
            pass
        else:
            names_section.assertions.append(
                AssertionModel(field_name='placeholder', display_label=LANG_LABELS.get(lang, lang), value='None recorded', category='names')
            )

    regional_section = SectionModel(key='regional', title='Regional and Unresolved Names')
    for value in scientific_synonyms:
        regional_section.assertions.append(make_assertion('scientific_synonym', 'Scientific Synonym', value, record_access, category='regional'))
    for value in other_regional_names:
        regional_section.assertions.append(make_assertion('regional_name', 'Regional Name', value, record_access, category='regional'))

    sacred_section = SectionModel(key='sacred', title='Sacred Knowledge')
    for use in uses:
        label = RITUAL_LABELS.get(use['use_type']) or MEDICINAL_LABELS.get(use['use_type']) or use['use_type']
        use_tier = use['access_tier'] or record_access
        decision = evaluate_assertion(
            use_tier,
            'This use entry is displayed in accordance with the access tier assigned to it in Ewé Steward, '
            f"sourced to: {use['source_citation']}",
        )
        sacred_section.assertions.append(
            AssertionModel(
                field_name=f"use_{use['use_category']}",
                display_label=label,
                value=use['description'],
                category='sacred',
                access_key=use_tier,
                render_mode=decision.render_mode,
                badge_label=decision.badge_label,
                badge_class=decision.badge_class,
                helper_text=decision.helper_text,
            )
        )
    if collision_note:
        sacred_section.assertions.append(
            make_assertion(
                field_name='collision_note',
                display_label='Collision Note',
                value=collision_note,
                record_access=record_access,
                category='sacred',
                helper_text='Collision analysis is displayed in accordance with the stewardship tier assigned to this record.'
            )
        )
    return {'names': names_section, 'regional': regional_section, 'sacred': sacred_section}


def parse_sqlite(db_path: Path, config: dict[str, Any]) -> list[PlantRecord]:
    """Read publishable Ewé records from medjat_ewe.sqlite3.

    Only plants.status in PUBLISHABLE_STATUSES are read. As of 2026-07-03 all
    50 records migrated from Verger_Ewe_Dataset_v4.ttl sit at status='pilot'
    (deliberately -- only their names are validated content; use/access/notes
    are placeholder pending real Steward review), so a build run against a
    freshly migrated database with no records yet approved will correctly
    produce zero plant pages. That is the intended, safe behavior: nothing
    publishes until a human approves it in Steward, matching the Acquire/
    Steward boundary and the "nothing writes until explicitly approved"
    pattern already established for Medjat Steward's Zotero push.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    public_base = config['public_base'].rstrip('/') + '/'
    records: list[PlantRecord] = []

    placeholders = ','.join('?' for _ in PUBLISHABLE_STATUSES)
    plants = conn.execute(
        f"SELECT * FROM plants WHERE status IN ({placeholders}) ORDER BY identifier",
        tuple(PUBLISHABLE_STATUSES),
    ).fetchall()

    for plant in plants:
        identifier = plant['identifier']
        scientific_name = plant['scientific_name'] or ''
        taxonomic_status = plant['taxonomic_status'] or ''
        record_uri = plant['record_uri'] or f'https://ontology.irokosociety.org/data/ewe/{identifier}'
        name_collision = bool(plant['name_collision'])
        collision_note = plant['collision_note']

        labels_by_lang: dict[str, list[str]] = defaultdict(list)
        pref_label = ''
        for name_row in conn.execute(
            "SELECT language, name_text, name_type FROM plant_names WHERE plant_id=? ORDER BY id", (plant['id'],)
        ):
            lang = name_row['language'] or 'und'
            append_unique(labels_by_lang[lang], name_row['name_text'])
            if name_row['name_type'] == 'pref_label' and not pref_label:
                pref_label = name_row['name_text']
        if not pref_label:
            pref_label = labels_by_lang.get('en', [scientific_name or identifier])[0]

        # is_pilot_data=1 rows are excluded from the public build unconditionally,
        # regardless of the parent record's status. Pilot/placeholder use rows
        # (see the 2026-07-03 migration) are not curated content and must never
        # reach a live page, even on a record that has since been approved on
        # the strength of a different, sourced use entry.
        uses = conn.execute(
            "SELECT * FROM plant_uses WHERE plant_id=? AND is_pilot_data=0 ORDER BY id", (plant['id'],)
        ).fetchall()
        ritual_uses = [u for u in uses if u['use_category'] == 'ritual']
        medicinal_uses = [u for u in uses if u['use_category'] == 'medicinal']
        # Primary use per category for card/filter display, mirroring the old
        # one-ritualUse/one-medicinalUse-per-record TTL shape. The full list
        # is still rendered in the Sacred Knowledge section via
        # build_sections_from_uses(), which is the real upgrade here -- the
        # new schema supports multiple sourced uses per plant.
        ritual_key = ritual_uses[0]['use_type'] if ritual_uses else ''
        medicinal_key = medicinal_uses[0]['use_type'] if medicinal_uses else ''

        record_access = max_access(*(u['access_tier'] for u in uses)) if uses else 'access-public-unrestricted'
        if record_access in NEVER_EXPORT_ACCESS:
            # Whole-record exclusion. See NEVER_EXPORT_ACCESS.
            continue

        scientific_synonyms, other_regional_names = partition_regional_names(labels_by_lang.get('und', []), scientific_name)
        sections = build_sections_from_uses(record_access, dict(labels_by_lang), scientific_synonyms, other_regional_names, uses, collision_note)
        access_meta = ACCESS_META.get(record_access, ACCESS_META['access-initiated-only'])
        visible_chunks = visible_search_chunks(identifier, pref_label, scientific_name, taxonomic_status, dict(labels_by_lang), scientific_synonyms, other_regional_names)
        visible_search_text = ' '.join(visible_chunks).strip().casefold()
        visible_jsonld = build_jsonld(record_uri, scientific_name, taxonomic_status, dict(labels_by_lang), record_access, medicinal_key, ritual_key)

        records.append(
            PlantRecord(
                identifier=identifier,
                record_uri=record_uri,
                page_url=f'plant/{quote(identifier)}.html',
                html_public_url=f'{public_base}{quote(identifier)}.html',
                scientific_name=scientific_name,
                taxonomic_status=taxonomic_status,
                pref_label=pref_label,
                labels_by_lang={k: v for k, v in labels_by_lang.items()},
                card_names=build_card_names(labels_by_lang),
                access_key=record_access,
                access_label=access_meta['label'],
                access_class=access_meta['class'],
                medicinal_key=medicinal_key,
                medicinal_label=MEDICINAL_LABELS.get(medicinal_key, medicinal_key or 'Unmapped'),
                ritual_key=ritual_key,
                ritual_label=RITUAL_LABELS.get(ritual_key, ritual_key or 'Unmapped'),
                name_collision=name_collision,
                search_text=visible_search_text,
                search_text_ascii=normalized_ascii(visible_search_text),
                scientific_synonyms=scientific_synonyms,
                other_regional_names=other_regional_names,
                sections=sections,
                visible_jsonld=visible_jsonld,
            )
        )

    conn.close()
    return sort_records(records)


def build_context(source_path: Path, records: list[PlantRecord], config: dict[str, Any]) -> dict[str, Any]:
    """source_path is whichever dataset was actually read: the TTL file, or
    medjat_ewe.sqlite3. Used only for the footer's 'Built from ...' credit."""
    now = datetime.now(timezone.utc)
    return {
        'site_title': config['site_title'],
        'site_subtitle': config['site_subtitle'],
        'org_name': config['org_name'],
        'dataset_filename': source_path.name,
        'dataset_version': source_path.stem,
        'record_count': len(records),
        'build_date': now.strftime('%Y-%m-%d'),
        'build_timestamp': now.isoformat(timespec='seconds'),
        'namespace_uri': config['namespace_uri'],
        'vocab_page': config['vocab_page'],
        'site_url': config['site_url'].rstrip('/'),
        'logo_path': config['logo_path'],
        'top_bar_framework_label': config.get('top_bar_framework_label', 'Framework ↗'),
        'external_site_label': config.get('external_site_label', 'irokosociety.org ↗'),
        'footer_tagline': config.get('footer_tagline', ''),
        'sources_line': config.get('sources_line', ''),
        'ui': UI_COPY,
        'lang_order': ['en', 'es', 'fr', 'yo', 'pt'],
        'lang_labels': LANG_LABELS,
        'ritual_filter_options': sorted({record.ritual_label for record in records}),
        'access_filter_options': [(key, meta['label']) for key, meta in ACCESS_META.items()],
        'boundary_message': boundary_message,
    }


def render_special_files(out_dir: Path, records: list[PlantRecord], context: dict[str, Any]) -> None:
    site_url = context['site_url']
    sitemap_entries = [f'  <url><loc>{site_url}/index.html</loc></url>']
    for record in records:
        sitemap_entries.append(f'  <url><loc>{site_url}/{record.page_url}</loc></url>')
    sitemap = "\n".join([
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
        *sitemap_entries,
        "</urlset>",
        "",
    ])
    (out_dir / 'sitemap.xml').write_text(sitemap, encoding='utf-8')
    (out_dir / 'robots.txt').write_text(
        f'User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n',
        encoding='utf-8',
    )
    (out_dir / '_headers').write_text(
        '/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n/search-index.json\n  Cache-Control: public, max-age=3600\n',
        encoding='utf-8',
    )
    (out_dir / '_redirects').write_text('/ /index.html 200\n', encoding='utf-8')


REQUIRED_META_MARKERS = [
    '<meta property="og:image" content="https://medjat.irokosociety.org/assets/og-pm-ewe.png">',
    '<meta property="og:image:width" content="1200">',
    '<meta property="og:image:height" content="630">',
    '<meta property="og:image:type" content="image/png">',
    '<meta name="twitter:image" content="https://medjat.irokosociety.org/assets/og-pm-ewe.png">',
    '<link rel="canonical"',
    "gtag('config', 'G-S7WFXNP22P');",
]


def validate_build(stage_dir: Path, records: list[PlantRecord]) -> list[str]:
    """Validation pass run before any file overwrites the live site.

    Catches: the class of Unicode-corruption bug found in templates/base.html
    on 2026-07-03 (a real '?' mojibake defect that had gone undetected
    because the site hadn't been rebuilt since it was introduced); missing
    required meta tags (the OG/GA audit that same day found these silently
    dropped for all 50 plant pages before the template-level fix); and
    broken internal links. Returns a list of problem strings; empty means
    clean.
    """
    problems: list[str] = []

    for page_path in [stage_dir / 'index.html', *[stage_dir / r.page_url for r in records]]:
        if not page_path.exists():
            problems.append(f'MISSING FILE: {page_path.relative_to(stage_dir)}')
            continue
        text = page_path.read_text(encoding='utf-8')

        if '�' in text:
            problems.append(f'{page_path.relative_to(stage_dir)}: contains U+FFFD (a real UTF-8 decode failure)')

        title_start = text.find('<title>')
        title_end = text.find('</title>')
        if title_start != -1 and title_end != -1:
            title_text = text[title_start + len('<title>'):title_end]
            if '?' in title_text and '·' not in title_text and page_path.name != 'index.html':
                problems.append(
                    f"{page_path.relative_to(stage_dir)}: <title> contains a bare '?' and no '·' separator "
                    f"-- looks like the 2026-07-03 mojibake bug. <title>{title_text}</title>"
                )

        for marker in REQUIRED_META_MARKERS:
            if marker not in text:
                problems.append(f'{page_path.relative_to(stage_dir)}: missing required marker: {marker}')

    # Internal links: every record's own page must exist (checked above via
    # the file-existence loop); additionally confirm search-index.json only
    # references pages that were actually generated.
    index_path = stage_dir / 'search-index.json'
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding='utf-8'))
        generated_urls = {r.page_url for r in records}
        for entry in payload:
            if entry['page_url'] not in generated_urls:
                problems.append(f"search-index.json references un-generated page: {entry['page_url']}")

    return problems


def render_site(out_dir: Path, config_path: Path, ttl_path: Path | None = None, db_path: Path | None = None) -> list[PlantRecord]:
    config = load_config(config_path)
    if db_path is not None:
        records = parse_sqlite(db_path, config)
        source_path = db_path
    else:
        ttl_path = ttl_path or DEFAULT_TTL
        records = parse_graph(ttl_path, config)
        source_path = ttl_path
    context = build_context(source_path, records, config)

    # Stage to a temporary directory first. Validate before touching the
    # real out_dir at all -- "confirm ... before any file overwrites the
    # live site," per the spec's Phase 4.
    with tempfile.TemporaryDirectory(prefix='build_ewe_stage_') as stage_str:
        stage_dir = Path(stage_str)
        (stage_dir / 'plant').mkdir(parents=True, exist_ok=True)
        shutil.copytree(BASE / 'assets', stage_dir / 'assets', dirs_exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(BASE / 'templates')),
            autoescape=select_autoescape(['html', 'xml', 'json']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        (stage_dir / 'index.html').write_text(env.get_template('index.html').render(records=records, **context), encoding='utf-8')
        plant_template = env.get_template('plant.html')
        for i, record in enumerate(records):
            previous_record = records[i - 1] if i > 0 else None
            next_record = records[i + 1] if i < len(records) - 1 else None
            (stage_dir / record.page_url).write_text(plant_template.render(record=record, previous_record=previous_record, next_record=next_record, **context), encoding='utf-8')

        payload = []
        for r in records:
            payload.append({
                'identifier': r.identifier,
                'pref_label': r.pref_label,
                'scientific_name': r.scientific_name,
                'page_url': r.page_url,
                'record_uri': r.record_uri,
                'html_public_url': r.html_public_url,
                'access': r.access_label,
                'access_key': r.access_key,
                'ritual_use': r.ritual_label,
                'medicinal_use': r.medicinal_label,
                'taxonomic_status': r.taxonomic_status,
                'labels_by_lang': {k: v for k, v in r.labels_by_lang.items() if k != 'x-lucumi'},
                'search_text': r.search_text,
                'search_text_ascii': r.search_text_ascii,
            })
        (stage_dir / 'search-index.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        render_special_files(stage_dir, records, context)

        problems = validate_build(stage_dir, records)
        if problems:
            print(f'VALIDATION FAILED -- {len(problems)} problem(s). Nothing was written to {out_dir}.', file=sys.stderr)
            for problem in problems:
                print(f'  - {problem}', file=sys.stderr)
            raise SystemExit(1)

        # Validation passed -- copy staged files over the real output.
        # index.html/search-index.json/robots.txt/etc. and plant/ are the
        # only things this script owns; nothing else in out_dir is touched.
        for item in stage_dir.iterdir():
            dest = out_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description='Build Ewé public interface from Medjat Ewé Steward (SQLite) or a TTL file')
    parser.add_argument('--source', choices=['sqlite', 'ttl'], default='sqlite', help='Data source (default: sqlite)')
    parser.add_argument('--ttl', type=Path, default=DEFAULT_TTL, help='Path to TTL dataset (used with --source ttl)')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB, help='Path to medjat_ewe.sqlite3 (used with --source sqlite)')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='Output directory (default: this script\'s own directory, matching live deploy practice)')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG, help='Path to site config JSON')
    args = parser.parse_args()

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.source == 'sqlite':
        if not args.db.exists():
            raise SystemExit(f'medjat_ewe.sqlite3 not found at {args.db}. Pass --db, or run --source ttl.')
        records = render_site(out_dir, args.config.resolve(), db_path=args.db.resolve())
    else:
        records = render_site(out_dir, args.config.resolve(), ttl_path=args.ttl.resolve())

    print(f'Built {len(records)} record(s) to {out_dir} (source: {args.source})')
    if args.source == 'sqlite' and not records:
        print(
            "0 records published. This is expected if no plants.status is 'approved' or "
            "'published' yet -- e.g. immediately after the 2026-07-03 pilot migration, "
            "before any record has been through Ewé Steward review. Run --source ttl to "
            "rebuild from the last-known TTL snapshot instead."
        )


if __name__ == '__main__':
    main()
