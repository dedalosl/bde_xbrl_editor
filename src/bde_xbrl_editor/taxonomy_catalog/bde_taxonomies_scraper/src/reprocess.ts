import * as fs from 'fs';
import * as path from 'path';
import { attachReportingFiles } from './attachReportingFiles';
import {
  fetchIndexGeneralDocuments,
  mergeAndApplyGeneralDocuments,
} from './generalDocuments';
import {
  enrichTaxonomyRelatedLinks,
  TAXONOMY_INDEX_URLS,
} from './taxonomyRelatedLinks';
import {
  FileMetadataHistory,
  isDownloadableUrl,
  loadMetadataHistory,
  saveMetadataHistory,
} from './fileMetadata';
import { TaxonomyData } from './types';

const defaultDataPath =
  process.env.BDE_TAXONOMIES_OUTPUT_PATH ||
  path.join(__dirname, '..', 'data', 'taxonomies.json');
const METADATA_HISTORY_PATH =
  process.env.BDE_TAXONOMIES_METADATA_HISTORY_PATH ||
  path.join(path.dirname(defaultDataPath), 'file-metadata-history.json');

/**
 * Re-runs module matching and general-document extraction on existing scrape output
 * without launching the browser. Run: npm run reprocess
 */
async function main() {
  const dataPath = defaultDataPath;
  const raw = fs.readFileSync(dataPath, 'utf-8');
  const data = JSON.parse(raw) as TaxonomyData;

  if (!data.reportingModules?.length) {
    console.error('No reportingModules in taxonomies.json — run full scrape first.');
    process.exit(1);
  }

  const history = loadMetadataHistory(METADATA_HISTORY_PATH, fs);

  attachReportingFiles(data.taxonomies, data.reportingModules);
  const indexGeneralDocuments = await fetchIndexGeneralDocuments(history);
  data.generalDocuments = mergeAndApplyGeneralDocuments(
    data.taxonomies,
    data.reportingModules,
    indexGeneralDocuments
  );
  console.log(
    `Index general documents: ${indexGeneralDocuments.length}, total: ${data.generalDocuments.length}`
  );

  const relatedLinks = data.taxonomyRelatedLinks ?? [];
  if (relatedLinks.length === 0) {
    console.warn(
      'No taxonomyRelatedLinks in taxonomies.json — run full scrape to populate from index page(s):'
    );
    TAXONOMY_INDEX_URLS.forEach((url) => console.warn(`  ${url}`));
  } else {
    data.taxonomyRelatedLinks = await enrichTaxonomyRelatedLinks(relatedLinks, history);
    console.log(
      `Re-enriched ${data.taxonomyRelatedLinks.length} taxonomy related link(s).`
    );
  }

  data.metadata.lastRun = new Date().toISOString();
  const updateCounts = countUpdates(data);
  data.metadata.taxonomiesWithUpdates = updateCounts.taxonomies;
  data.metadata.entryPointsWithUpdates = updateCounts.entryPoints;
  data.metadata.filesWithUpdates = updateCounts.files;

  saveMetadataHistory(METADATA_HISTORY_PATH, history, fs, path);

  fs.writeFileSync(dataPath, JSON.stringify(data, null, 2), 'utf-8');
  console.log(
    `Reprocessed ${data.taxonomies.length} taxonomies, ${data.generalDocuments.length} general document(s).`
  );
}

function countUpdates(data: TaxonomyData): {
  taxonomies: number;
  entryPoints: number;
  files: number;
} {
  const taxonomiesWithUpdates = data.taxonomies.filter(
    (taxonomy) => taxonomy.hasEntryPointUpdates || taxonomy.hasReportingFileUpdates
  ).length;
  const updatedEntryPointUrls = new Set<string>();
  const updatedFileUrls = new Set<string>();
  for (const taxonomy of data.taxonomies) {
    for (const file of taxonomy.entryPoints) {
      if (file.isUpdatedSinceLastCheck) updatedEntryPointUrls.add(file.url);
    }
    for (const file of taxonomy.reportingFiles ?? []) {
      if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
    }
  }
  for (const module of data.reportingModules) {
    for (const file of module.files) {
      if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
    }
  }
  for (const file of data.generalDocuments ?? []) {
    if (file.isUpdatedSinceLastCheck) updatedFileUrls.add(file.url);
  }
  for (const file of data.taxonomyRelatedLinks ?? []) {
    if (isDownloadableUrl(file.url) && file.isUpdatedSinceLastCheck) {
      updatedFileUrls.add(file.url);
    }
  }
  return {
    taxonomies: taxonomiesWithUpdates,
    entryPoints: updatedEntryPointUrls.size,
    files: updatedFileUrls.size,
  };
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
