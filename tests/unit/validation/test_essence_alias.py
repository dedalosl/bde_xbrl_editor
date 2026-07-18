"""Unit tests for essence-alias validation cancellation."""

from __future__ import annotations

import threading
from types import SimpleNamespace
from typing import cast

from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.essence_alias import EssenceAliasValidator


def test_taxonomy_validation_stops_when_cancelled() -> None:
    cancel_event = threading.Event()
    cancel_event.set()
    taxonomy = cast(
        TaxonomyStructure,
        SimpleNamespace(definition={"elr": [object()]}),
    )

    findings = EssenceAliasValidator(cancel_event=cancel_event).validate_taxonomy(
        taxonomy
    )

    assert findings == []
