/** Playwright navigation — avoid networkidle (can hang on analytics / long-polling). */
export const PAGE_GOTO_TIMEOUT_MS = 45_000;
export const PAGE_GOTO_WAIT_UNTIL: 'domcontentloaded' = 'domcontentloaded';

/** HTTP metadata (HEAD / range GET). */
export const FILE_METADATA_TIMEOUT_MS = 10_000;
export const FILE_METADATA_MAX_REDIRECTS = 5;
export const FILE_METADATA_CONCURRENCY = 8;

/** Reporting-module BFS discovery. */
export const MODULE_BFS_MAX_PAGES = 100;
export const MODULE_BFS_MAX_DEPTH = 5;
export const MODULE_BFS_LOG_EVERY_N_PAGES = 10;

/** Plain fetch() for index HTML (reprocess / general docs). */
export const FETCH_HTML_TIMEOUT_MS = 20_000;
