import { Browser, Page, chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import {
  enrichFilesWithMetadata,
  FileMetadataHistory,
  isDownloadableUrl,
  loadMetadataHistory,
  saveMetadataHistory,
} from './fileMetadata';
import { PAGE_GOTO_TIMEOUT_MS, PAGE_GOTO_WAIT_UNTIL } from './scrapeConfig';
import { scrapeProgress } from './scrapeProgress';
import { attachReportingFiles } from './attachReportingFiles';
import {
  mergeAndApplyGeneralDocuments,
  scrapeIndexGeneralDocuments,
} from './generalDocuments';
import { scrapeReportingModules } from './reportingModules';
import { scrapeAndEnrichTaxonomyRelatedLinks } from './taxonomyRelatedLinks';
import { EntryPoint, Taxonomy, TaxonomyData } from './types';

const METADATA_HISTORY_PATH = path.join(__dirname, '..', 'data', 'file-metadata-history.json');

const BDE_BASE_URL = 'https://www.bde.es';
const BDE_TAXONOMIES_URL = `${BDE_BASE_URL}/wbe/es/punto-informacion/contenidos/informacion-financiera-a-remitir-entidades-supervisadas/entidades-credito/taxonomias/`;

function getStatusPath(status: 'vigente' | 'no-vigente'): string {
  return status === 'vigente' ? 'vigentes' : 'no-vigentes';
}

interface LinkResult {
  href: string;
  text: string;
}

interface TaxonomyResult {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  status: 'vigente' | 'no-vigente';
  owner: string;
  date: string;
  specVersion: string;
  comments: string;
  urlBase: string;
  entryPoints: { name: string; url: string }[];
  sourceUrl: string;
  scrapedAt: string;
}

export class BDECrawler {
  private browser: Browser | null = null;
  private page: Page | null = null;

  async init(): Promise<void> {
    this.browser = await chromium.launch({ headless: true });
    this.page = await this.browser.newPage();
    this.page.setDefaultNavigationTimeout(PAGE_GOTO_TIMEOUT_MS);
    this.page.setDefaultTimeout(PAGE_GOTO_TIMEOUT_MS);
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
    }
  }

  async scrape(): Promise<TaxonomyData> {
    if (!this.page) {
      throw new Error('Browser not initialized. Call init() first.');
    }

    const history = loadMetadataHistory(METADATA_HISTORY_PATH, fs);

    scrapeProgress.startPhase('reporting_modules');
    const reportingModules = await scrapeReportingModules(this.page, history);
    scrapeProgress.endPhase('reporting_modules');

    scrapeProgress.startPhase('taxonomy_related');
    console.log('Navigating to BDE taxonomies page...');
    await this.page.goto(BDE_TAXONOMIES_URL, {
      waitUntil: PAGE_GOTO_WAIT_UNTIL,
      timeout: PAGE_GOTO_TIMEOUT_MS,
    });

    const taxonomyRelatedLinks = await scrapeAndEnrichTaxonomyRelatedLinks(
      this.page,
      BDE_BASE_URL,
      history
    );
    console.log(`Found ${taxonomyRelatedLinks.length} taxonomy related link(s)`);
    scrapeProgress.endPhase('taxonomy_related');

    const taxonomies: Taxonomy[] = [];

    scrapeProgress.startPhase('taxonomies', 'vigentes');
    console.log('Scraping vigentes taxonomies...');
    const vigentesTaxonomies = await this.scrapeSection('vigente', history, 0, 0.5);
    taxonomies.push(...vigentesTaxonomies);

    scrapeProgress.log('no vigentes');
    console.log('Scraping no vigentes taxonomies...');
    const noVigentesTaxonomies = await this.scrapeSection(
      'no-vigente',
      history,
      0.5,
      1
    );
    taxonomies.push(...noVigentesTaxonomies);
    scrapeProgress.endPhase('taxonomies');

    scrapeProgress.startPhase('entry_points');
    console.log('\nChecking entry point file metadata...');
    await this.enrichTaxonomyEntryPoints(taxonomies, history);
    scrapeProgress.endPhase('entry_points');

    attachReportingFiles(taxonomies, reportingModules);

    scrapeProgress.startPhase('general_documents');
    const indexGeneralDocuments = await scrapeIndexGeneralDocuments(
      this.page,
      BDE_BASE_URL,
      history
    );
    const generalDocuments = mergeAndApplyGeneralDocuments(
      taxonomies,
      reportingModules,
      indexGeneralDocuments
    );
    console.log(
      `General documents: ${generalDocuments.length} (${indexGeneralDocuments.length} from entity index)`
    );
    scrapeProgress.endPhase('general_documents');

    scrapeProgress.startPhase('finalize');
    saveMetadataHistory(METADATA_HISTORY_PATH, history, fs, path);
    scrapeProgress.endPhase('finalize');

    const taxonomiesWithUpdates = taxonomies.filter(
      (taxonomy) => taxonomy.hasEntryPointUpdates || taxonomy.hasReportingFileUpdates
    ).length;
    const updatedEntryPointUrls = new Set<string>();
    const updatedFileUrls = new Set<string>();
    for (const taxonomy of taxonomies) {
      for (const file of taxonomy.entryPoints) {
        if (file.isUpdatedSinceLastCheck) updatedEntryPointUrls.add(file.url);
      }
      for (const file of taxonomy.reportingFiles ?? []) {
        if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
      }
    }
    for (const module of reportingModules) {
      for (const file of module.files) {
        if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
      }
    }
    for (const file of generalDocuments ?? []) {
      if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
    }
    for (const file of taxonomyRelatedLinks) {
      if (isDownloadableUrl(file.url) && file.isUpdatedSinceLastCheck) {
        updatedFileUrls.add(file.url);
      }
    }

    const filesWithUpdates = updatedFileUrls.size;
    const entryPointsWithUpdates = updatedEntryPointUrls.size;

    const data: TaxonomyData = {
      metadata: {
        lastRun: new Date().toISOString(),
        totalCount: taxonomies.length,
        reportingModuleCount: reportingModules.length,
        taxonomiesWithUpdates,
        entryPointsWithUpdates,
        filesWithUpdates,
      },
      taxonomies,
      reportingModules,
      generalDocuments,
      taxonomyRelatedLinks,
    };

    return data;
  }

  private async enrichTaxonomyEntryPoints(
    taxonomies: Taxonomy[],
    history: FileMetadataHistory
  ): Promise<void> {
    const allEntryPoints: { taxonomy: Taxonomy; index: number; ep: EntryPoint }[] = [];
    for (const taxonomy of taxonomies) {
      taxonomy.entryPoints.forEach((ep, index) => {
        allEntryPoints.push({ taxonomy, index, ep });
      });
    }

    if (allEntryPoints.length === 0) return;

    const enriched = await enrichFilesWithMetadata(
      allEntryPoints.map(({ ep }) => ({ name: ep.name, url: ep.url })),
      history,
      {
        onProgress: (done, total) => {
          scrapeProgress.setPhaseProgress(
            done / total,
            `entry points ${done}/${total}`
          );
        },
      }
    );

    for (let i = 0; i < allEntryPoints.length; i++) {
      const { taxonomy, index } = allEntryPoints[i];
      const withMeta = enriched[i];
      taxonomy.entryPoints[index] = {
        name: withMeta.name,
        url: withMeta.url,
        lastModified: withMeta.lastModified,
        contentLength: withMeta.contentLength,
        etag: withMeta.etag,
        isUpdatedSinceLastCheck: withMeta.isUpdatedSinceLastCheck,
      };
    }

    for (const taxonomy of taxonomies) {
      taxonomy.hasEntryPointUpdates = taxonomy.entryPoints.some(
        (ep) => ep.isUpdatedSinceLastCheck
      );
    }
  }

  private async scrapeSection(
    status: 'vigente' | 'no-vigente',
    _history: FileMetadataHistory,
    progressStart = 0,
    progressEnd = 1
  ): Promise<Taxonomy[]> {
    if (!this.page) return [];

    const taxonomies: Taxonomy[] = [];

    try {
      await this.page.goto(BDE_TAXONOMIES_URL, {
        waitUntil: PAGE_GOTO_WAIT_UNTIL,
        timeout: PAGE_GOTO_TIMEOUT_MS,
      });

      // Get the category page URLs from the main page
      const statusPath = getStatusPath(status);
      const categoryLinks = await this.page.evaluate((params: { baseUrl: string; statusPath: string }) => {
        const allLinks = document.querySelectorAll('a');
        const results: string[] = [];

        allLinks.forEach((link) => {
          const href = link.getAttribute('href') || '';

          // Find category links (e.g., /taxonomias/vigenteS/entidades-credito/)
          // They end with '/' and don't include '.html'
          if (href.includes(`/taxonomias/${params.statusPath}/`) &&
              !href.includes('.html') &&
              href.endsWith('/')) {
            results.push(href.startsWith('http') ? href : params.baseUrl + href);
          }
        });

        return results;
      }, { baseUrl: BDE_BASE_URL, statusPath }) as string[];

      console.log(`Found ${categoryLinks.length} category pages for ${status}`);

      let categoryIndex = 0;
      const categoryCount = Math.max(categoryLinks.length, 1);

      // For each category page, get the actual taxonomy links
      for (const categoryUrl of categoryLinks) {
        categoryIndex += 1;
        const sectionFraction =
          progressStart +
          (progressEnd - progressStart) *
            ((categoryIndex - 1) / categoryCount);
        scrapeProgress.setPhaseProgress(
          sectionFraction,
          `${status} categories ${categoryIndex}/${categoryCount}`
        );

        try {
          await this.page.goto(categoryUrl, {
            waitUntil: PAGE_GOTO_WAIT_UNTIL,
            timeout: PAGE_GOTO_TIMEOUT_MS,
          });

          await this.page.waitForTimeout(300);

          const links: LinkResult[] = await this.page.evaluate((baseUrl) => {
            const results: { href: string; text: string }[] = [];
            const allLinks = document.querySelectorAll('a');

            allLinks.forEach((link) => {
              const href = link.getAttribute('href') || '';
              const text = link.textContent?.trim() || '';

              // Get actual taxonomy detail pages (with .html)
              // They have: punto-informacion, taxonomia, .html, and don't have 'descarga' or 'archivo'
              const isTaxonomyPage =
                href.includes('/punto-informacion/') &&
                href.includes('/taxonomias/') &&
                href.includes('.html') &&
                !href.includes('descarga') &&
                !href.includes('archivo') &&
                !href.includes('manual') &&
                !href.includes('pdf') &&
                !href.includes('zip');

              const isValidText = text &&
                text.length > 3 &&
                text.length < 100 &&
                !text.includes('Volver') &&
                !text.includes('Ir a') &&
                !text.includes('Inicio') &&
                !text.includes('Ampliar') &&
                !text.includes('Archivo') &&
                !text.includes('Siguiente') &&
                !text.includes('Anterior');

              if (isTaxonomyPage && isValidText) {
                results.push({
                  href: href.startsWith('http') ? href : baseUrl + href,
                  text: text.substring(0, 100)
                });
              }
            });

            return results;
          }, BDE_BASE_URL);

          // Remove duplicates
          const uniqueLinks = links.filter((link, index, self) =>
            index === self.findIndex((l) => l.href === link.href)
          );

          console.log(`  Found ${uniqueLinks.length} taxonomies on ${new URL(categoryUrl).pathname}`);

          let linkIndex = 0;
          const linkCount = Math.max(uniqueLinks.length, 1);
          for (const link of uniqueLinks) {
            linkIndex += 1;
            const categorySlice = 1 / categoryCount;
            const linkFraction =
              progressStart +
              (progressEnd - progressStart) *
                ((categoryIndex - 1 + linkIndex / linkCount) / categoryCount);
            scrapeProgress.setPhaseProgress(
              linkFraction,
              `${status} ${linkIndex}/${uniqueLinks.length}`
            );

            try {
              const taxonomy = await this.scrapeTaxonomyDetail(
                link.href,
                link.text,
                status
              );
              if (taxonomy) {
                const exists = taxonomies.some((t) => t.id === taxonomy.id);
                if (!exists) {
                  taxonomies.push(taxonomy);
                  console.log(`    - Scraped: ${taxonomy.name}`);
                }
              }
            } catch (err) {
              console.error(`    - Error: ${err}`);
            }
          }
        } catch (err) {
          console.error(`Error fetching category ${categoryUrl}:`, err);
        }
      }
    } catch (error) {
      console.error(`Error scraping ${status} section:`, error);
    }

    return taxonomies;
  }

  private async scrapeTaxonomyDetail(url: string, title: string, status: 'vigente' | 'no-vigente'): Promise<Taxonomy | null> {
    if (!this.page) return null;

    try {
      await this.page.goto(url, {
        waitUntil: PAGE_GOTO_WAIT_UNTIL,
        timeout: PAGE_GOTO_TIMEOUT_MS,
      });
      await this.page.waitForTimeout(200);

      const taxonomy = await this.page.evaluate((params: { taxTitle: string; taxStatus: string; baseUrl: string }) => {
        const result: TaxonomyResult = {
          id: '',
          name: params.taxTitle,
          category: '',
          subcategory: '',
          status: params.taxStatus as 'vigente' | 'no-vigente',
          owner: '',
          date: '',
          specVersion: '',
          comments: '',
          urlBase: '',
          entryPoints: [],
          sourceUrl: window.location.href,
          scrapedAt: new Date().toISOString(),
        };

        // Get category from breadcrumb navigation
        const breadcrumbItems = document.querySelectorAll('[class*="breadcrumb"] a, nav[aria-label="Breadcrumb"] a');
        breadcrumbItems.forEach((item) => {
          const text = item.textContent?.trim() || '';
          if (text.includes('Entidades de crédito')) {
            result.category = 'Entidades de crédito';
          } else if (text.includes('Establecimientos financieros')) {
            result.category = 'Establecimientos financieros de crédito';
          } else if (text.includes('Instituciones financieras')) {
            result.category = 'Instituciones financieras monetarias';
          }
        });

        if (!result.category) {
          const h1 = document.querySelector('h1');
          if (h1) {
            const h1Text = h1.textContent || '';
            if (h1Text.includes('Entidades de crédito')) {
              result.category = 'Entidades de crédito';
            } else if (h1Text.includes('Establecimientos')) {
              result.category = 'Establecimientos financieros de crédito';
            }
          }
        }

        // Get subcategory from page structure
        const mainContent = document.body.innerText;
        const subCatMatch = mainContent.match(/(Entidades de crédito y establecimientos financieros de crédito|Entidades de crédito|Establecimientos financieros de crédito|Instituciones financieras monetarias)/);
        if (subCatMatch) {
          result.subcategory = subCatMatch[1];
        }

        // Extract Propietario
        const ownerMatch = mainContent.match(/Propietario\s*[:-]?\s*([^\n\r]+)/i);
        if (ownerMatch) {
          result.owner = ownerMatch[1].trim();
        }

        // Extract Fecha
        const dateMatch = mainContent.match(/Fecha\s*\(aaaa-mm-dd\)\s*[:-]?\s*(\d{4}-\d{2}-\d{2})/i);
        if (dateMatch) {
          result.date = dateMatch[1].trim();
        }

        // Extract Versión de la especificación
        const specMatch = mainContent.match(/Versión de la especificación\s*[:-]?\s*([^\n\r]+)/i);
        if (specMatch) {
          result.specVersion = specMatch[1].trim();
        }

        // Extract Comentarios
        const commentsMatch = mainContent.match(/Comentarios\s*[:-]?\s*([^\n\r]+(?:\n[^\n\r]+)*?)(?=\n\n|\n[A-Z])/i);
        if (commentsMatch) {
          result.comments = commentsMatch[1].trim();
        }

        // Extract URLBase
        const urlBaseMatch = mainContent.match(/URLBase\s*[:-]?\s*(https?:\/\/[^\s\n\r]+)/i);
        if (urlBaseMatch) {
          result.urlBase = urlBaseMatch[1].trim();
        }

        function addEntryPoint(link: HTMLAnchorElement) {
          const epUrl = link.getAttribute('href') || '';
          const epName = link.textContent?.trim() || '';
          if (epUrl && (epUrl.startsWith('http') || epUrl.startsWith('/'))) {
            result.entryPoints.push({
              name: epName || epUrl,
              url: epUrl.startsWith('http') ? epUrl : params.baseUrl + epUrl,
            });
          }
        }

        // Extract Puntos de entrada
        const headers = document.querySelectorAll('h3, h4, h5');
        headers.forEach((header) => {
          if (header.textContent?.includes('Puntos de entrada') || header.textContent?.includes('Punto de entrada')) {
            let container: Element | null = header.nextElementSibling;
            if (container && container.tagName !== 'UL' && container.tagName !== 'OL') {
              const list = container.querySelector('ul, ol');
              if (list) container = list;
            }
            if (container) {
              const entryLinks = container.querySelectorAll('a');
              entryLinks.forEach((link) => {
                addEntryPoint(link as HTMLAnchorElement);
              });
            }

            let sibling = header.nextElementSibling;
            while (sibling && !['H3', 'H4', 'H5'].includes(sibling.tagName)) {
              sibling.querySelectorAll('a').forEach((link) => {
                const href = link.getAttribute('href') || '';
                if (href.endsWith('.xsd') || link.textContent?.includes('.xsd')) {
                  addEntryPoint(link as HTMLAnchorElement);
                }
              });
              sibling = sibling.nextElementSibling;
            }
          }
        });

        result.entryPoints = result.entryPoints.filter((entryPoint, index, self) =>
          index === self.findIndex((candidate) => candidate.url === entryPoint.url)
        );

        // Generate ID from name
        result.id = params.taxTitle.toLowerCase()
          .replace(/[^a-z0-9]+/g, '_')
          .replace(/^_|_$/g, '');

        return result;
      }, { taxTitle: title, taxStatus: status, baseUrl: BDE_BASE_URL });

      return taxonomy;
    } catch (error) {
      console.error(`Error fetching taxonomy detail from ${url}:`, error);
      return null;
    }
  }

  async saveData(data: TaxonomyData, outputPath: string): Promise<void> {
    const dir = path.dirname(outputPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), 'utf-8');
    console.log(`Data saved to ${outputPath}`);
  }
}
