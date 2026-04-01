"""Access evaluation helpers for the Ewé public interface.

This module is intentionally reusable.

The important design choice in pass 4 is that the build pipeline no longer
 treats every RDF literal as equally public. Instead, each value is modeled as
 an assertion with its own render mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ACCESS_ORDER = {
    'access-public-unrestricted': 0,
    'access-public-no-amplification': 1,
    'access-community-only': 2,
    'access-initiated-only': 3,
    'access-initiated-elder': 4,
    'access-no-access': 5,
}

ACCESS_META: dict[str, dict[str, str]] = {
    'access-public-unrestricted': {
        'label': 'Public – Unrestricted',
        'class': 'access-public',
        'card_class': 'public',
        'boundary_copy': 'Public – Unrestricted',
        'stewardship_copy': 'Public – Unrestricted',
    },
    'access-public-no-amplification': {
        'label': 'Public – No Amplification',
        'class': 'access-public',
        'card_class': 'public',
        'boundary_copy': 'Public – No Amplification',
        'stewardship_copy': 'Public – No Amplification (Stewarded Knowledge)',
    },
    'access-community-only': {
        'label': 'Limited – Community Only',
        'class': 'access-community',
        'card_class': 'community',
        'boundary_copy': 'Limited – Community Only',
        'stewardship_copy': 'Limited – Community Only (Stewarded Knowledge)',
    },
    'access-initiated-only': {
        'label': 'Limited – Initiated Only',
        'class': 'access-initiated',
        'card_class': 'initiated',
        'boundary_copy': 'Limited – Initiated Only',
        'stewardship_copy': 'Limited – Initiated Only (Stewarded Knowledge)',
    },
    'access-initiated-elder': {
        'label': 'Limited – Elder Initiated',
        'class': 'access-initiated',
        'card_class': 'initiated',
        'boundary_copy': 'Limited – Elder Initiated',
        'stewardship_copy': 'Limited – Elder Initiated (Stewarded Knowledge)',
    },
    'access-no-access': {
        'label': 'Restricted – No Access',
        'class': 'access-none',
        'card_class': 'none',
        'boundary_copy': 'Restricted – No Access',
        'stewardship_copy': 'Restricted – No Access (Stewarded Knowledge)',
    },
}


@dataclass
class AccessDecision:
    access_key: str
    render_mode: str
    badge_label: str
    badge_class: str
    helper_text: str


def access_meta(access_key: str) -> dict[str, str]:
    """Return normalized metadata for an access tier."""
    return ACCESS_META.get(access_key, ACCESS_META['access-initiated-only'])


def max_access(*access_keys: str | None) -> str:
    """Return the most restrictive access key from a set of access keys."""
    keys = [key for key in access_keys if key]
    if not keys:
        return 'access-public-unrestricted'
    return max(keys, key=lambda key: ACCESS_ORDER.get(key, 99))


def boundary_message(access_key: str) -> str:
    return access_meta(access_key)['stewardship_copy']


def should_redact_public(assertion_access: str) -> bool:
    """Decide whether a value should be redacted in the public build."""
    return ACCESS_ORDER.get(assertion_access, 99) >= ACCESS_ORDER['access-community-only']


def evaluate_assertion(assertion_access: str, reason: str) -> AccessDecision:
    """Create a reusable access decision for a single assertion."""
    meta = access_meta(assertion_access)
    if should_redact_public(assertion_access):
        return AccessDecision(
            access_key=assertion_access,
            render_mode='redacted',
            badge_label=meta['stewardship_copy'],
            badge_class=meta['class'],
            helper_text=reason,
        )
    return AccessDecision(
        access_key=assertion_access,
        render_mode='visible',
        badge_label=meta['label'],
        badge_class=meta['class'],
        helper_text=reason,
    )


def field_access(field_name: str, record_access: str, lang: str | None = None) -> str:
    """Infer access for a field/assertion when the TTL lacks statement-level ACLs.

    Current assumptions:
    - Lucumí labels are always at least community-only in the public build.
    - Ritual notes inherit the record access tier.
    - Collision notes inherit the record access tier.
    - Scientific/taxonomic/basic vernacular assertions stay public unless a
      future dataset adds explicit assertion access.
    """
    if lang == 'x-lucumi' or field_name == 'lucumi_label':
        return max_access(record_access, 'access-community-only')
    if field_name in {'ritual_note', 'collision_note'}:
        return record_access
    return 'access-public-unrestricted'


def assertion_visible(assertion: Any) -> bool:
    return getattr(assertion, 'render_mode', '') == 'visible'


def assertion_redacted(assertion: Any) -> bool:
    return getattr(assertion, 'render_mode', '') == 'redacted'
