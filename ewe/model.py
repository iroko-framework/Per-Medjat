"""Dataclasses for the pass-4 Ewé build pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AssertionModel:
    """A single renderable assertion."""

    field_name: str
    value: str | None
    display_label: str
    lang: str | None = None
    category: str | None = None
    access_key: str = 'access-public-unrestricted'
    render_mode: str = 'visible'
    badge_label: str = 'Public – Unrestricted'
    badge_class: str = 'access-public'
    helper_text: str = ''


@dataclass
class SectionModel:
    """A section rendered on a plant page."""

    key: str
    title: str
    assertions: list[AssertionModel] = field(default_factory=list)
    empty_message: str = 'None recorded'

    @property
    def visible_assertions(self) -> list[AssertionModel]:
        return [item for item in self.assertions if item.render_mode == 'visible']

    @property
    def redacted_assertions(self) -> list[AssertionModel]:
        return [item for item in self.assertions if item.render_mode == 'redacted']

    @property
    def has_any_content(self) -> bool:
        return bool(self.assertions)


@dataclass
class PlantRecord:
    identifier: str
    record_uri: str
    page_url: str
    html_public_url: str
    scientific_name: str
    taxonomic_status: str
    pref_label: str
    labels_by_lang: dict[str, list[str]]
    card_names: list[tuple[str, str]]
    access_key: str
    access_label: str
    access_class: str
    medicinal_key: str
    medicinal_label: str
    ritual_key: str
    ritual_label: str
    name_collision: bool
    search_text: str
    search_text_ascii: str
    scientific_synonyms: list[str]
    other_regional_names: list[str]
    sections: dict[str, SectionModel]
    visible_jsonld: dict[str, Any]

    @property
    def primary_yoruba(self) -> str | None:
        values = self.labels_by_lang.get('yo', [])
        return values[0] if values else None

    @property
    def primary_english(self) -> str | None:
        values = self.labels_by_lang.get('en', [])
        return values[0] if values else None

    @property
    def primary_spanish(self) -> str | None:
        values = self.labels_by_lang.get('es', [])
        return values[0] if values else None
