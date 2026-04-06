from __future__ import annotations

import argparse
import json
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

from access import ACCESS_META, boundary_message, evaluate_assertion, field_access
from model import AssertionModel, PlantRecord, SectionModel

BASE = Path(__file__).resolve().parent
DEFAULT_TTL = BASE / 'Verger_Ewe_Dataset_v4.ttl'
DEFAULT_OUT = BASE / 'output'
DEFAULT_CONFIG = BASE / 'site_config.json'
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

RITUAL_LABELS = {
    'ritual-purification-cleansing': 'Purification & Cleansing',
    'ritual-protection-boundary': 'Protection & Boundary',
    'ritual-invocation-communication': 'Invocation & Communication',
    'ritual-healing-restoration': 'Healing & Restoration',
    'ritual-offering-devotion': 'Offering & Devotion',
    'ritual-rites-of-transition': 'Rites of Transition',
    'ritual-cosmological-symbolic': 'Cosmological / Symbolic',
}

MEDICINAL_LABELS = {
    'medicinal-digestive-support': 'Digestive Support',
    'medicinal-respiratory-support': 'Respiratory Support',
    'medicinal-skin-topical': 'Skin and Topical Use',
    'medicinal-general-tonic': 'General Tonic / Revitalizing',
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


def build_jsonld(record_uri: str, scientific_name: str, taxonomic_status: str, labels_by_lang: dict[str, list[str]], access_key: str, medicinal_label: str, ritual_label: str) -> dict[str, Any]:
    # JSON-LD intentionally includes only assertions visible in the public build.
    names = []
    for lang, values in labels_by_lang.items():
        if lang == 'x-lucumi':
            continue
        for value in values:
            names.append({'@value': value, '@language': lang})
    return {
        '@context': {
            'name': 'http://schema.org/name',
            'alternateName': 'http://schema.org/alternateName',
            'identifier': 'http://purl.org/dc/terms/identifier',
            'scientificName': str(DWC_SCIENTIFIC_NAME),
            'taxonomicStatus': str(DWC_TAXONOMIC_STATUS),
            'accessLevel': f'{IROKO}accessLevel',
            'medicinalUse': f'{IROKO}medicinalUse',
            'ritualUse': f'{IROKO}ritualUse',
        },
        '@id': record_uri,
        '@type': f'{IROKO}EwePlantRecord',
        'scientificName': scientific_name,
        'taxonomicStatus': taxonomic_status,
        'alternateName': names,
        'accessLevel': access_key,
        'medicinalUse': medicinal_label,
        'ritualUse': ritual_label,
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

        if not pref_label:
            pref_label = labels_by_lang.get('en', [scientific_name or identifier])[0]

        scientific_synonyms, other_regional_names = partition_regional_names(labels_by_lang.get('und', []), scientific_name)
        sections = build_sections(access_key, dict(labels_by_lang), scientific_synonyms, other_regional_names, ritual_note, collision_note)
        access_meta = ACCESS_META.get(access_key, ACCESS_META['access-initiated-only'])
        visible_chunks = visible_search_chunks(identifier, pref_label, scientific_name, taxonomic_status, dict(labels_by_lang), scientific_synonyms, other_regional_names)
        visible_search_text = ' '.join(visible_chunks).strip().casefold()
        visible_jsonld = build_jsonld(str(subject), scientific_name, taxonomic_status, dict(labels_by_lang), access_key, MEDICINAL_LABELS.get(medicinal_key, medicinal_key or 'Unmapped'), RITUAL_LABELS.get(ritual_key, ritual_key or 'Unmapped'))

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


def build_context(ttl_path: Path, records: list[PlantRecord], config: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        'site_title': config['site_title'],
        'site_subtitle': config['site_subtitle'],
        'org_name': config['org_name'],
        'dataset_filename': ttl_path.name,
        'dataset_version': ttl_path.stem,
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


def render_site(ttl_path: Path, out_dir: Path, config_path: Path) -> None:
    config = load_config(config_path)
    records = parse_graph(ttl_path, config)
    context = build_context(ttl_path, records, config)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'plant').mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE / 'assets', out_dir / 'assets', dirs_exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(BASE / 'templates')),
        autoescape=select_autoescape(['html', 'xml', 'json']),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    (out_dir / 'index.html').write_text(env.get_template('index.html').render(records=records, **context), encoding='utf-8')
    plant_template = env.get_template('plant.html')
    for i, record in enumerate(records):
        previous_record = records[i - 1] if i > 0 else None
        next_record = records[i + 1] if i < len(records) - 1 else None
        (out_dir / record.page_url).write_text(plant_template.render(record=record, previous_record=previous_record, next_record=next_record, **context), encoding='utf-8')

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
    (out_dir / 'search-index.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    render_special_files(out_dir, records, context)


def main() -> None:
    parser = argparse.ArgumentParser(description='Build Ewé public interface from TTL')
    parser.add_argument('--ttl', type=Path, default=DEFAULT_TTL, help='Path to TTL dataset')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT, help='Output directory')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG, help='Path to site config JSON')
    args = parser.parse_args()
    render_site(args.ttl.resolve(), args.out.resolve(), args.config.resolve())
    print(f'Built site to {args.out}')


if __name__ == '__main__':
    main()
