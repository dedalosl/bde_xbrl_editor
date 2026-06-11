import { Page } from 'playwright';
import {
  enrichFilesWithMetadata,
  FileMetadataHistory,
  inferFileType,
  isDownloadableUrl,
} from './fileMetadata';
import {
  MODULE_BFS_LOG_EVERY_N_PAGES,
  MODULE_BFS_MAX_DEPTH,
  MODULE_BFS_MAX_PAGES,
  PAGE_GOTO_TIMEOUT_MS,
  PAGE_GOTO_WAIT_UNTIL,
} from './scrapeConfig';
import { scrapeProgress } from './scrapeProgress';
import { ModuleFile, ReportingModule } from './types';

const BDE_BASE_URL = 'https://www.bde.es';

export const ENTITY_INDEX_PAGES: { category: string; url: string }[] = [
  {
    category: 'Entidades de crédito',
    url: `${BDE_BASE_URL}/wbe/es/punto-informacion/contenidos/informacion-financiera-a-remitir-entidades-supervisadas/entidades-credito/`,
  },
];

interface DiscoveredLink {
  url: string;
  text: string;
}

function normalizeUrl(href: string, baseUrl: string): string {
  try {
    const absolute = href.startsWith('http') ? href : new URL(href, baseUrl).href;
    const parsed = new URL(absolute);
    parsed.hash = '';
    let path = parsed.pathname;
    if (path.endsWith('/index.html')) {
      path = path.replace(/index\.html$/, '');
    }
    parsed.pathname = path;
    return parsed.href.replace(/\/$/, '') || parsed.href;
  } catch {
    return href;
  }
}

function isModuleCandidateUrl(url: string, indexRoot: string): boolean {
  if (!url.startsWith(BDE_BASE_URL)) return false;
  if (!url.includes(indexRoot)) return false;
  if (url.includes('/taxonomias/')) return false;
  if (isDownloadableUrl(url)) return false;
  if (url.includes('descarga') || url.includes('archivo')) return false;
  if (/\.(jsp|aspx)(\?|$)/i.test(url)) return false;
  return true;
}

export async function discoverModulePageUrls(
  page: Page,
  indexUrl: string
): Promise<DiscoveredLink[]> {
  const indexRoot = new URL(indexUrl).pathname.replace(/\/$/, '');
  const visited = new Set<string>();
  const moduleCandidates = new Map<string, DiscoveredLink>();
  const queue: { url: string; depth: number }[] = [{ url: indexUrl, depth: 0 }];
  const maxDepth = MODULE_BFS_MAX_DEPTH;
  const maxPages = MODULE_BFS_MAX_PAGES;

  while (queue.length > 0 && visited.size < maxPages) {
    const { url, depth } = queue.shift()!;
    const normalized = normalizeUrl(url, indexUrl);
    if (visited.has(normalized) || depth > maxDepth) continue;
    visited.add(normalized);

    try {
      if (
        visited.size > 0 &&
        visited.size % MODULE_BFS_LOG_EVERY_N_PAGES === 0
      ) {
        scrapeProgress.log(
          `BFS ${visited.size}/${maxPages} pages, queue ${queue.length}`
        );
        scrapeProgress.setPhaseProgress(
          Math.min(0.35, visited.size / maxPages),
          `discovering pages (${visited.size}/${maxPages})`
        );
      }

      await page.goto(normalized.endsWith('/') ? normalized : `${normalized}/`, {
        waitUntil: PAGE_GOTO_WAIT_UNTIL,
        timeout: PAGE_GOTO_TIMEOUT_MS,
      });
      await page.waitForTimeout(300);

      const pageData = await page.evaluate(
        ({ indexRootPath }) => {
          const fileLinks: { label: string; url: string }[] = [];
          const childLinks: { href: string; text: string }[] = [];
          const pageUrl = window.location.href;

          const resolveUrl = (href: string) => {
            try {
              return new URL(href, pageUrl).href;
            } catch {
              return href;
            }
          };

          const labelFromUrl = (url: string) => {
            try {
              const name = decodeURIComponent(new URL(url).pathname.split('/').pop() || '');
              return name.replace(/\.(pdf|xlsx?|xls|zip)$/i, '').replace(/[_-]+/g, ' ');
            } catch {
              return url;
            }
          };

          document.querySelectorAll('a[href]').forEach((anchor) => {
            const href = anchor.getAttribute('href') || '';
            if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

            const absolute = resolveUrl(href);
            const text = (anchor.textContent || '').replace(/\s+/g, ' ').trim();

            if (/\.(pdf|xlsx?|xls|zip)(\?|$)/i.test(absolute)) {
              fileLinks.push({
                label: text || labelFromUrl(absolute),
                url: absolute,
              });
            } else if (
              absolute.includes(indexRootPath) &&
              !absolute.includes('/taxonomias/') &&
              !/\.(pdf|xlsx?|xls|zip)(\?|$)/i.test(absolute)
            ) {
              childLinks.push({ href: absolute, text: text || absolute });
            }
          });

          const h1 = document.querySelector('h1')?.textContent?.trim() || '';
          return { fileLinks, childLinks, h1, pageUrl };
        },
        { indexRootPath: indexRoot }
      );

      if (pageData.fileLinks.length > 0) {
        const pageUrl = normalizeUrl(pageData.pageUrl, indexUrl);
        const indexNormalized = normalizeUrl(indexUrl, indexUrl);
        if (pageUrl !== indexNormalized && !moduleCandidates.has(pageUrl)) {
          moduleCandidates.set(pageUrl, {
            url: pageUrl,
            text: pageData.h1 || pageData.fileLinks[0]?.label || pageUrl,
          });
        }
      }

      if (depth < maxDepth) {
        for (const link of pageData.childLinks) {
          const childUrl = normalizeUrl(link.href, indexUrl);
          if (isModuleCandidateUrl(childUrl, indexRoot) && !visited.has(childUrl)) {
            queue.push({ url: childUrl, depth: depth + 1 });
          }
        }
      }
    } catch (err) {
      console.warn(`  Skipping ${normalized}: ${err}`);
    }
  }

  return Array.from(moduleCandidates.values());
}

export async function scrapeModuleDetail(
  page: Page,
  moduleUrl: string,
  title: string,
  category: string
): Promise<ReportingModule | null> {
  try {
    await page.goto(moduleUrl.endsWith('/') ? moduleUrl : `${moduleUrl}/`, {
      waitUntil: PAGE_GOTO_WAIT_UNTIL,
      timeout: PAGE_GOTO_TIMEOUT_MS,
    });
    await page.waitForTimeout(300);

    const scraped = await page.evaluate(() => {
      const name = document.querySelector('h1')?.textContent?.trim() || '';
      const files: { label: string; url: string }[] = [];
      const seen = new Set<string>();
      const pageUrl = window.location.href;

      const resolveUrl = (href: string) => {
        try {
          return new URL(href, pageUrl).href;
        } catch {
          return href;
        }
      };

      const labelFromUrl = (url: string) => {
        try {
          const fileName = decodeURIComponent(new URL(url).pathname.split('/').pop() || '');
          return fileName.replace(/\.(pdf|xlsx?|xls|zip)$/i, '').replace(/[_-]+/g, ' ');
        } catch {
          return url;
        }
      };

      document.querySelectorAll('a[href]').forEach((anchor) => {
        const href = anchor.getAttribute('href') || '';
        if (!href || href.startsWith('#')) return;

        const absolute = resolveUrl(href);
        if (!/\.(pdf|xlsx?|xls|zip)(\?|$)/i.test(absolute)) return;
        if (seen.has(absolute)) return;
        seen.add(absolute);

        const label = (anchor.textContent || '').replace(/\s+/g, ' ').trim();
        files.push({ label: label || labelFromUrl(absolute), url: absolute });
      });

      let section = '';
      const skipBreadcrumb = new Set(['Inicio', 'Punto de Información', 'Volver', name]);
      const breadcrumbItems = document.querySelectorAll(
        '[class*="breadcrumb"] a, nav[aria-label="Breadcrumb"] a'
      );
      const crumbs: string[] = [];
      breadcrumbItems.forEach((item) => {
        const text = item.textContent?.trim() || '';
        if (text && !skipBreadcrumb.has(text)) {
          crumbs.push(text);
        }
      });
      if (crumbs.length > 0) {
        section = crumbs[crumbs.length - 1];
      }

      return { name, files, section, sourceUrl: window.location.href };
    });

    if (scraped.files.length === 0) return null;

    const id = (scraped.name || title)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '');

    const files: ModuleFile[] = scraped.files.map((f) => ({
      label: f.label,
      url: f.url,
      fileType: inferFileType(f.url, f.label),
    }));

    return {
      id,
      name: scraped.name || title,
      category,
      section: scraped.section || undefined,
      files,
      sourceUrl: scraped.sourceUrl,
      scrapedAt: new Date().toISOString(),
    };
  } catch (error) {
    console.error(`Error scraping module ${moduleUrl}:`, error);
    return null;
  }
}

export async function scrapeReportingModules(
  page: Page,
  history: FileMetadataHistory
): Promise<ReportingModule[]> {
  const modules: ReportingModule[] = [];
  const seenIds = new Set<string>();
  let modulesProcessed = 0;
  let modulesTotalEstimate = 0;

  for (const { category, url } of ENTITY_INDEX_PAGES) {
    console.log(`\nDiscovering reporting modules from ${category}...`);
    const discovered = await discoverModulePageUrls(page, url);
    modulesTotalEstimate += discovered.length;
    console.log(`Found ${discovered.length} module pages for ${category}`);
    scrapeProgress.setPhaseProgress(0.4, `${discovered.length} module pages found`);

    for (const link of discovered) {
      const module = await scrapeModuleDetail(page, link.url, link.text, category);
      if (!module || seenIds.has(module.id)) continue;

      modulesProcessed += 1;
      const fraction =
        modulesTotalEstimate > 0
          ? 0.4 + (0.55 * modulesProcessed) / modulesTotalEstimate
          : 0.5;
      scrapeProgress.setPhaseProgress(
        fraction,
        `metadata ${modulesProcessed}/${modulesTotalEstimate}: ${module.name}`
      );
      console.log(`  Enriching ${module.files.length} file(s) for: ${module.name}`);

      module.files = await enrichFilesWithMetadata(module.files, history, {
        onProgress: (done, total) => {
          if (total > 5 && done % 10 === 0) {
            scrapeProgress.log(`${module.name}: ${done}/${total} files`);
          }
        },
      });
      module.hasUpdates = module.files.some((f) => f.isUpdatedSinceLastCheck);
      seenIds.add(module.id);
      modules.push(module);
      console.log(`    - ${module.name}${module.hasUpdates ? ' (updated files)' : ''}`);
    }
  }

  return modules;
}
