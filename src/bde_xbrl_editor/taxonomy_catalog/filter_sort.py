"""Client-side filter and sort for taxonomy catalog entries."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy_catalog.models import FilterStatus, SortOption, Taxonomy


def filter_taxonomies(
    taxonomies: tuple[Taxonomy, ...],
    *,
    search: str,
    status: FilterStatus,
    category: str,
) -> tuple[Taxonomy, ...]:
    result: list[Taxonomy] = []
    query = search.strip().lower()
    for tax in taxonomies:
        if status != "all" and tax.status != status:
            continue
        if category and tax.category != category:
            continue
        if query:
            matches_reporting = any(
                query in f.label.lower() or query in f.url.lower()
                for f in tax.reporting_files
            )
            if not (
                query in tax.name.lower()
                or query in tax.category.lower()
                or query in tax.subcategory.lower()
                or query in tax.comments.lower()
                or query in tax.owner.lower()
                or matches_reporting
            ):
                continue
        result.append(tax)
    return tuple(result)


def unique_categories(taxonomies: tuple[Taxonomy, ...]) -> tuple[str, ...]:
    categories = {tax.category for tax in taxonomies if tax.category}
    return tuple(sorted(categories))


def sort_taxonomies(
    taxonomies: tuple[Taxonomy, ...],
    sort: SortOption,
) -> tuple[Taxonomy, ...]:
    items = list(taxonomies)

    def date_key(tax: Taxonomy) -> str:
        return tax.date or ""

    if sort == "date-desc":
        items.sort(key=date_key, reverse=True)
    elif sort == "date-asc":
        items.sort(key=date_key)
    elif sort == "name-asc":
        items.sort(key=lambda t: t.name.lower())
    elif sort == "name-desc":
        items.sort(key=lambda t: t.name.lower(), reverse=True)
    return tuple(items)
