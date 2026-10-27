import * as path from 'path';
import { BDECrawler } from './crawler';

async function main() {
  const crawler = new BDECrawler();
  const outputPath =
    process.env.BDE_TAXONOMIES_OUTPUT_PATH ||
    path.join(__dirname, '..', 'data', 'taxonomies.json');

  try {
    console.log('Starting BDE Taxonomies Scraper...\n');
    await crawler.init();

    const data = await crawler.scrape();

    console.log(
      `\nScraping complete! Found ${data.metadata.totalCount} taxonomies and ${data.reportingModules.length} reporting modules.`
    );
    if (data.metadata.filesWithUpdates) {
      console.log(`${data.metadata.filesWithUpdates} item(s) with updated files since last check.`);
    }
    await crawler.saveData(data, outputPath);

    console.log('\n--- Sample Data ---');
    if (data.taxonomies.length > 0) {
      console.log(JSON.stringify(data.taxonomies[0], null, 2));
    }
  } catch (error) {
    console.error('Error during scraping:', error);
    process.exit(1);
  } finally {
    await crawler.close();
  }
}

main();
