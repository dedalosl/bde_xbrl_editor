import { Page } from 'playwright';
import {
  enrichFilesWithMetadata,
  FileMetadataHistory,
  inferFileType,
  isDownloadableUrl,
} from './fileMetadata';
import { PAGE_GOTO_TIMEOUT_MS, PAGE_GOTO_WAIT_UNTIL } from './scrapeConfig';
import { scrapeProgress } from './scrapeProgress';
import { ModuleFile } from './types';

export const TAXONOMY_INDEX_URLS = [
  'https://www.bde.es/wbe/es/punto-informacion/contenidos/informacion-financiera-a-remitir-entidades-supervisadas/entidades-credito/taxonomias/',
] as const;

interface RawRelatedLink {
  label: string;
  url: string;
}

/**
 * Finds the "Información relacionada" block on a taxonomies index page and returns its links.
 */
export async function scrapeTaxonomyRelatedLinks(
  page: Page,
  pageUrl: string,
  baseUrl: string
): Promise<RawRelatedLink[]> {
  await page.goto(pageUrl, {
    waitUntil: PAGE_GOTO_WAIT_UNTIL,
    timeout: PAGE_GOTO_TIMEOUT_MS,
  });

  const raw = (await page.evaluate((origin) => {
    const normalize = (href: string): string | null => {
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return null;
      try {
        return new URL(href, origin).href;
      } catch {
        return null;
      }
    };

    const headingPattern = /informaci[oó]n\s+relacionada/i;
    const headings = Array.from(
      document.querySelectorAll('h2, h3, h4, h5, h6, [class*="title"], strong')
    );

    let sectionRoot: Element | null = null;
    for (const heading of headings) {
      const text = heading.textContent?.trim() || '';
      if (!headingPattern.test(text)) continue;

      let sibling: Element | null = heading.nextElementSibling;
      while (sibling) {
        if (sibling.matches('ul, ol, div, section, nav')) {
          sectionRoot = sibling;
          break;
        }
        const list = sibling.querySelector('ul, ol');
        if (list) {
          sectionRoot = list;
          break;
        }
        sibling = sibling.nextElementSibling;
      }
      if (sectionRoot) break;
    }

    if (!sectionRoot) return [] as { label: string; url: string }[];

    const links = sectionRoot.querySelectorAll('a[href]');
    const results: { label: string; url: string }[] = [];
    const seen = new Set<string>();

    links.forEach((anchor) => {
      const href = anchor.getAttribute('href') || '';
      const url = normalize(href);
      const label = anchor.textContent?.replace(/\s+/g, ' ').trim() || '';
      if (!url || !label || seen.has(url)) return;
      seen.add(url);
      results.push({ label, url });
    });

    return results;
  }, baseUrl)) as RawRelatedLink[];

  return raw;
}

function toModuleFile(link: RawRelatedLink): ModuleFile {
  return {
    label: link.label,
    url: link.url,
    fileType: inferFileType(link.url, link.label),
  };
}

function dedupeByUrl(links: ModuleFile[]): ModuleFile[] {
  const byUrl = new Map<string, ModuleFile>();
  for (const link of links) {
    const key = link.url.trim().toLowerCase();
    const existing = byUrl.get(key);
    if (!existing || link.label.length > existing.label.length) {
      byUrl.set(key, link);
    }
  }
  return Array.from(byUrl.values()).sort((a, b) =>
    a.label.localeCompare(b.label, 'es')
  );
}

export async function enrichTaxonomyRelatedLinks(
  links: ModuleFile[],
  history: FileMetadataHistory
): Promise<ModuleFile[]> {
  const downloadableLinks = links.filter((link) => isDownloadableUrl(link.url));
  const enriched = await enrichFilesWithMetadata(
    downloadableLinks.map((link) => ({
      label: link.label,
      url: link.url,
      fileType: link.fileType,
    })),
    history,
    {
      onProgress: (done, total) => {
        scrapeProgress.setPhaseProgress(
          0.5 + (0.45 * done) / total,
          `related links ${done}/${total}`
        );
      },
    }
  );
  const enrichedByUrl = new Map(enriched.map((link) => [link.url, link]));

  return links.map((link) => {
    const withMeta = enrichedByUrl.get(link.url);
    if (!withMeta) {
      return {
        label: link.label,
        url: link.url,
        fileType: link.fileType ?? inferFileType(link.url, link.label),
        isUpdatedSinceLastCheck: false,
      };
    }
    return {
      label: withMeta.label,
      url: withMeta.url,
      fileType: withMeta.fileType ?? inferFileType(withMeta.url, withMeta.label),
      lastModified: withMeta.lastModified,
      contentLength: withMeta.contentLength,
      etag: withMeta.etag,
      isUpdatedSinceLastCheck: withMeta.isUpdatedSinceLastCheck,
    };
  });
}

/** Scrape all configured taxonomy index pages and enrich file metadata. */
export async function scrapeAndEnrichTaxonomyRelatedLinks(
  page: Page,
  baseUrl: string,
  history: FileMetadataHistory
): Promise<ModuleFile[]> {
  const collected: ModuleFile[] = [];

  for (const indexUrl of TAXONOMY_INDEX_URLS) {
    console.log(`Scraping taxonomy related links from ${indexUrl}...`);
    const raw = await scrapeTaxonomyRelatedLinks(page, indexUrl, baseUrl);
    collected.push(...raw.map(toModuleFile));
  }

  return enrichTaxonomyRelatedLinks(dedupeByUrl(collected), history);
}
