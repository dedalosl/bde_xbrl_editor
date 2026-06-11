import { Page } from 'playwright';
import {
  enrichFilesWithMetadata,
  FileMetadataHistory,
  inferFileType,
} from './fileMetadata';
import { FETCH_HTML_TIMEOUT_MS, PAGE_GOTO_TIMEOUT_MS, PAGE_GOTO_WAIT_UNTIL } from './scrapeConfig';
import { scrapeProgress } from './scrapeProgress';
import { ENTITY_INDEX_PAGES } from './reportingModules';
import { ModuleFile, ReportingModule, Taxonomy } from './types';

const GENERAL_LABEL_PATTERNS: RegExp[] = [
  /\bsif\b/i,
  /i\.e\.\s*1996/i,
  /i\.e\.\s*2008/i,
  /i\.e\.\s*2014/i,
  /\bexb\b/i,
  /instrucci[oó]n\s+t[eé]cnica/i,
  /manual\s+de\s+usuario/i,
  /normas\s+para\s+la\s+presentaci[oó]n/i,
  /presentaci[oó]n\s+y\s+transmisi[oó]n\s+telem[aá]tica/i,
  /est[aá]ndar\s+xbrl/i,
  /documentaci[oó]n\s+financiera\s+de\s+acuerdo/i,
];

const INDEX_TITLE_SKIP = /compartir|twitter|linkedin|youtube|flickr|instagram|bluesky/i;

/** Minimum module pages a file URL must appear on to be treated as cross-cutting. */
const MIN_CROSS_MODULE_REPEAT = 3;

export function isGeneralDocumentByLabel(label: string): boolean {
  return GENERAL_LABEL_PATTERNS.some((pattern) => pattern.test(label));
}

export function fileKey(file: Pick<ModuleFile, 'url'>): string {
  return file.url.trim().toLowerCase();
}

function pickRicherFile(a: ModuleFile, b: ModuleFile): ModuleFile {
  if ((a.lastModified && !b.lastModified) || (a.contentLength && !b.contentLength)) {
    return a;
  }
  return b.label.length >= b.label.length ? a : b;
}

function dedupeGeneralDocuments(files: ModuleFile[]): ModuleFile[] {
  const byUrl = new Map<string, ModuleFile>();
  for (const file of files) {
    const key = fileKey(file);
    const existing = byUrl.get(key);
    byUrl.set(key, existing ? pickRicherFile(existing, file) : { ...file });
  }
  return Array.from(byUrl.values()).sort((a, b) =>
    a.label.localeCompare(b.label, 'es')
  );
}

/** Parse cross-cutting download links from an entity index HTML page. */
export function parseIndexGeneralDocumentLinks(
  html: string,
  baseUrl: string
): { label: string; url: string }[] {
  const results: { label: string; url: string }[] = [];
  const seen = new Set<string>();
  const anchorRe =
    /<a[^>]*href="([^"]+\.(?:pdf|xlsx?|xls|zip)(?:\?[^"]*)?)"[^>]*title="([^"]+)"[^>]*>/gi;

  let match: RegExpExecArray | null;
  while ((match = anchorRe.exec(html)) !== null) {
    const href = match[1];
    const title = match[2].replace(/\s+/g, ' ').trim();
    if (!title || INDEX_TITLE_SKIP.test(title)) continue;

    let url: string;
    try {
      url = new URL(href, baseUrl).href;
    } catch {
      continue;
    }

    const key = url.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);

    const inDownloadBlock = htmlIncludesDownloadBlock(html, match.index);
    if (!inDownloadBlock && !isGeneralDocumentByLabel(title)) {
      continue;
    }

    results.push({ label: title, url });
  }

  return results;
}

function htmlIncludesDownloadBlock(html: string, anchorIndex: number): boolean {
  const windowStart = Math.max(0, anchorIndex - 400);
  const snippet = html.slice(windowStart, anchorIndex);
  return snippet.includes('link-download__item');
}

export function detectGeneralDocuments(
  modules: ReportingModule[],
  _taxonomies: Taxonomy[]
): ModuleFile[] {
  const urlStats = new Map<string, { file: ModuleFile; moduleIds: Set<string> }>();

  for (const module of modules) {
    for (const file of module.files) {
      const key = fileKey(file);
      const existing = urlStats.get(key);
      if (existing) {
        existing.moduleIds.add(module.id);
        existing.file = pickRicherFile(existing.file, file);
      } else {
        urlStats.set(key, { file: { ...file }, moduleIds: new Set([module.id]) });
      }
    }
  }

  const generalByUrl = new Map<string, ModuleFile>();

  for (const { file, moduleIds } of urlStats.values()) {
    if (isGeneralDocumentByLabel(file.label) || moduleIds.size >= MIN_CROSS_MODULE_REPEAT) {
      generalByUrl.set(fileKey(file), file);
    }
  }

  return Array.from(generalByUrl.values()).sort((a, b) =>
    a.label.localeCompare(b.label, 'es')
  );
}

export function stripGeneralDocuments(
  taxonomies: Taxonomy[],
  modules: ReportingModule[],
  generalUrls: Set<string>
): void {
  if (generalUrls.size === 0) return;

  for (const taxonomy of taxonomies) {
    if (!taxonomy.reportingFiles?.length) continue;
    taxonomy.reportingFiles = taxonomy.reportingFiles.filter(
      (f) => !generalUrls.has(fileKey(f))
    );
    taxonomy.hasReportingFileUpdates = taxonomy.reportingFiles.some(
      (f) => f.isUpdatedSinceLastCheck
    );
    if (taxonomy.reportingFiles.length === 0) {
      taxonomy.reportingModuleUrl = undefined;
    }
  }

  for (const module of modules) {
    module.files = module.files.filter((f) => !generalUrls.has(fileKey(f)));
    module.hasUpdates = module.files.some((f) => f.isUpdatedSinceLastCheck);
  }
}

async function fetchHtmlWithTimeout(url: string): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_HTML_TIMEOUT_MS);
  try {
    const response = await fetch(url.endsWith('/') ? url : `${url}/`, {
      signal: controller.signal,
    });
    if (!response.ok) {
      console.warn(`Could not fetch ${url}: HTTP ${response.status}`);
      return null;
    }
    return await response.text();
  } catch (error) {
    console.warn(`Could not fetch ${url}: ${error}`);
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function enrichGeneralDocuments(
  files: ModuleFile[],
  history: FileMetadataHistory
): Promise<ModuleFile[]> {
  const enriched = await enrichFilesWithMetadata(
    files.map((file) => ({
      label: file.label,
      url: file.url,
      fileType: file.fileType,
    })),
    history,
    {
      onProgress: (done, total) => {
        scrapeProgress.setPhaseProgress(
          done / total,
          `general docs ${done}/${total}`
        );
      },
    }
  );

  return enriched.map((withMeta) => ({
    label: withMeta.label,
    url: withMeta.url,
    fileType: withMeta.fileType ?? inferFileType(withMeta.url, withMeta.label),
    lastModified: withMeta.lastModified,
    contentLength: withMeta.contentLength,
    etag: withMeta.etag,
    isUpdatedSinceLastCheck: withMeta.isUpdatedSinceLastCheck,
  }));
}

/** Fetch general-document links from configured entity index pages (no browser). */
export async function fetchIndexGeneralDocuments(
  history: FileMetadataHistory
): Promise<ModuleFile[]> {
  const collected: ModuleFile[] = [];

  for (const { url } of ENTITY_INDEX_PAGES) {
    const response = await fetch(url.endsWith('/') ? url : `${url}/`);
    if (!response.ok) {
      console.warn(`Could not fetch general documents index ${url}: ${response.status}`);
      continue;
    }
    const html = await response.text();
    const raw = parseIndexGeneralDocumentLinks(html, url);
    for (const link of raw) {
      collected.push({
        label: link.label,
        url: link.url,
        fileType: inferFileType(link.url, link.label),
      });
    }
  }

  return enrichGeneralDocuments(dedupeGeneralDocuments(collected), history);
}

/** Scrape general-document links from entity index pages with Playwright. */
export async function scrapeIndexGeneralDocuments(
  page: Page,
  baseUrl: string,
  history: FileMetadataHistory
): Promise<ModuleFile[]> {
  const collected: ModuleFile[] = [];

  for (const { url } of ENTITY_INDEX_PAGES) {
    await page.goto(url.endsWith('/') ? url : `${url}/`, { waitUntil: 'domcontentloaded' });
    const html = await page.content();
    const raw = parseIndexGeneralDocumentLinks(html, baseUrl);
    for (const link of raw) {
      collected.push({
        label: link.label,
        url: link.url,
        fileType: inferFileType(link.url, link.label),
      });
    }
  }

  return enrichGeneralDocuments(dedupeGeneralDocuments(collected), history);
}

export function mergeAndApplyGeneralDocuments(
  taxonomies: Taxonomy[],
  modules: ReportingModule[],
  extraDocuments: ModuleFile[] = []
): ModuleFile[] {
  const detected = detectGeneralDocuments(modules, taxonomies);
  const generalDocuments = dedupeGeneralDocuments([...detected, ...extraDocuments]);
  const generalUrls = new Set(generalDocuments.map(fileKey));
  stripGeneralDocuments(taxonomies, modules, generalUrls);
  return generalDocuments;
}

export function applyGeneralDocuments(
  taxonomies: Taxonomy[],
  modules: ReportingModule[]
): ModuleFile[] {
  return mergeAndApplyGeneralDocuments(taxonomies, modules);
}
