# LLM Wiki Schema

This document defines the structure, conventions, and workflows for the LLM Wiki. It serves as the operational guide for the LLM agent maintaining this knowledge base.

## 1. Architecture

The wiki consists of three layers:

1.  **Raw Sources**: The source of truth (e.g., code, documentation, user-provided files). These are immutable.
2.  **The Wiki**: The LLM-maintained layer of markdown files (summaries, entity pages, concept pages, index, log).
3.  **The Schema**: This document, which governs the maintenance and integrity of the wiki.

## 2. Operations

### Ingest
When a new source is provided:
1.  **Read**: Analyze the source document(s) thoroughly.
2.  **Synthesize**: Extract key information, entities, and concepts.
3.  **Update Wiki**:
    - Create new pages for new entities or concepts.
    - Update existing pages if the new source adds information or contradicts previous data.
    - Update `index.md` to reflect changes.
    - Append a new entry to `log.md`.
4.  **Cross-reference**: Ensure links between relevant pages are established or updated.

### Query
When a user asks a question:
1.  **Search**: Consult `index.md` and search the wiki for relevant pages.
2.  **Analyze**: Read the identified pages to gather context.
3.  **Synthesize**: Provide a comprehensive answer with citations to the wiki pages used.
4.  **Reflect**: If the query leads to new insights or discovery, create a new wiki page or update an existing one to capture the knowledge.

### Lint
Periodically, perform a health check:
1.  **Consistency Check**: Look for contradictions between wiki pages.
2.  **Completeness Check**: Identify orphan pages (no inbound links) or missing links between related topics.
3.  **Staleness Check**: Flag information that may have been superseded by newer sources.
4.s **Report**: Suggest fixes or document findings in `log.md`.

## 3. Indexing and Logging

### `index.md` (Content Catalog)
- Organized by categories (e.g., Concepts, Entities, Sources).
- Each entry includes a link to the page and a brief summary.
- Updated during every Ingest and Lint operation.

### `log.md` (Chronological Record)
- An append-only record of all significant actions (Ingest, Query, Lint).
- Format: `## [YYYY-MM-DD] action | Title/Description`
- Provides a timeline of the wiki's evolution.

## 4. Writing Conventions

- **File Naming**: Use kebab-case for all filenames (e.g., `xbrl-overview.md`).
- **Format**: All pages must be in valid Markdown.
- **Tone**: Informative, concise, and objective.
- **Citations**: When referencing other wiki pages, use standard Markdown links `[Page Title](path/to/page.md)`.
- **Frontmatter**: For complex pages, use YAML frontmatter to track metadata (e.g., `source-count`, `last-updated`).

## 5. Core Principles

- **Persistence**: The wiki is a compounding asset. Information should be integrated, not just summarized.
- **Integrity**: Always prioritize accuracy and consistency. If a new source contradicts the wiki, flag it and discuss with the user.
- **Structure**: Maintain a logical and discoverable organization.
