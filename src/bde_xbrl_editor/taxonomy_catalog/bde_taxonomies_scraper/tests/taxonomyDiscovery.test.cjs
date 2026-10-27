const assert = require('node:assert/strict');
const { test } = require('node:test');
const { BDECrawler } = require('../src/crawler');

test('discovers the monthly taxonomy without truncating its long title', async () => {
  const baseUrl = 'https://www.bde.es';
  const categoryPath = '/wbe/es/punto-informacion/contenidos/informacion-financiera-a-remitir-entidades-supervisadas/entidades-credito/taxonomias/vigentes/entidades-credito-establecimientos-financieros/';
  const title = 'Información para el Banco de España - Estados financieros reservados mensuales (reservados_m_2026_03)';
  const detailPath = `${categoryPath}informacion-para-el-banco-de-espana---estados-financieros-reservados-mensuales-reservados_m_2026_03.html`;
  const anchor = (href, textContent) => ({ getAttribute: () => href, textContent });
  const visited = [];
  let currentUrl;
  const crawler = new BDECrawler();
  crawler.page = {
    goto: async (url) => { currentUrl = url; },
    waitForTimeout: async () => {},
    evaluate: async (callback, argument) => {
      const previousDocument = global.document;
      global.document = {
        querySelectorAll: () => currentUrl === baseUrl + categoryPath
          ? [anchor(detailPath, title), anchor(detailPath, 'Siguiente')]
          : [anchor(categoryPath, 'Category')],
      };
      try {
        return callback(argument);
      } finally {
        global.document = previousDocument;
      }
    },
  };
  crawler.scrapeTaxonomyDetail = async (url, name, status) => {
    visited.push({ url, name, status });
    return { id: 'monthly', name, sourceUrl: url };
  };

  const taxonomies = await crawler.scrapeSection('vigente', {});

  assert.equal(title.length, 101);
  assert.deepEqual(visited, [{ url: baseUrl + detailPath, name: title, status: 'vigente' }]);
  assert.equal(taxonomies.length, 1);
});
