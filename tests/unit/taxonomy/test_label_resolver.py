"""Unit tests for LabelResolver — precedence, priority, prohibited arcs, fallback, never-raises."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy.constants import LABEL_ROLE, TERSE_LABEL_ROLE
from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.models import Label, QName

NS = "http://test.example/ns"
NS2 = "http://other.example/ns"


def make_label(text: str, lang: str, role: str = LABEL_ROLE, source: str = "standard", priority: int = 0) -> Label:
    return Label(text=text, language=lang, role=role, source=source, priority=priority)


def make_resolver(
    standard: dict | None = None,
    generic: dict | None = None,
    lang_pref: list[str] | None = None,
) -> LabelResolver:
    return LabelResolver.build(
        standard or {},
        generic or {},
        lang_pref or ["es", "en"],
    )


class TestLanguageFallback:
    def test_returns_preferred_language(self):
        q = QName(NS, "Assets")
        resolver = make_resolver(
            standard={q: [make_label("Activos", "es"), make_label("Assets", "en")]}
        )
        assert resolver.resolve(q) == "Activos"

    def test_falls_back_to_english(self):
        q = QName(NS, "Assets")
        resolver = make_resolver(
            standard={q: [make_label("Assets", "en")]},
            lang_pref=["es", "en"],
        )
        assert resolver.resolve(q) == "Assets"

    def test_falls_back_to_qname_string(self):
        q = QName(NS, "Assets")
        resolver = make_resolver()
        result = resolver.resolve(q)
        assert "Assets" in result or NS in result

    def test_fallback_to_qname_is_non_empty(self):
        q = QName(NS, "NoLabels")
        resolver = make_resolver()
        assert len(resolver.resolve(q)) > 0


class TestStandardVsGenericPrecedence:
    def test_standard_wins_over_generic_at_same_priority(self):
        q = QName(NS, "Concept")
        resolver = make_resolver(
            standard={q: [make_label("Standard Label", "en", priority=0)]},
            generic={q: [make_label("Generic Label", "en", priority=0)]},
        )
        assert resolver.resolve(q, language_preference=["en"]) == "Standard Label"

    def test_higher_priority_generic_wins_over_lower_standard(self):
        q = QName(NS, "Concept")
        resolver = make_resolver(
            standard={q: [make_label("Standard Label", "en", priority=0)]},
            generic={q: [make_label("Generic Label", "en", priority=5, source="generic")]},
        )
        assert resolver.resolve(q, language_preference=["en"]) == "Generic Label"


class TestRoleFallback:
    def test_resolves_terse_label(self):
        q = QName(NS, "Assets")
        resolver = make_resolver(
            standard={q: [make_label("Activos (abrev)", "es", role=TERSE_LABEL_ROLE)]}
        )
        assert resolver.resolve(q, role=TERSE_LABEL_ROLE) == "Activos (abrev)"

    def test_falls_back_to_standard_role_when_role_missing(self):
        q = QName(NS, "Assets")
        resolver = make_resolver(
            standard={q: [make_label("Activos", "es", role=LABEL_ROLE)]}
        )
        # Ask for terse, fall back to standard
        result = resolver.resolve(q, role=TERSE_LABEL_ROLE)
        assert result == "Activos"


class TestNeverRaises:
    def test_resolve_unknown_qname_does_not_raise(self):
        resolver = make_resolver()
        result = resolver.resolve(QName("http://unknown", "Whatever"))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_all_labels_unknown_returns_empty(self):
        resolver = make_resolver()
        result = resolver.get_all_labels(QName("http://unknown", "Nothing"))
        assert result == []

    def test_fuzz_random_qnames_never_raises(self):
        """Fuzz-style: random QNames not in taxonomy always return non-empty string."""
        import random
        import string
        resolver = make_resolver()
        for _ in range(50):
            ns = "http://" + "".join(random.choices(string.ascii_lowercase, k=10)) + ".example"
            local = "".join(random.choices(string.ascii_letters, k=8))
            q = QName(ns, local)
            result = resolver.resolve(q)
            assert isinstance(result, str)
            assert len(result) > 0


class TestGetAllLabels:
    def test_returns_all_labels(self):
        q = QName(NS, "Assets")
        labels = [
            make_label("Activos", "es"),
            make_label("Assets", "en"),
            make_label("Activos (res.)", "es", role=TERSE_LABEL_ROLE),
        ]
        resolver = make_resolver(standard={q: labels})
        result = resolver.get_all_labels(q)
        assert len(result) == 3
