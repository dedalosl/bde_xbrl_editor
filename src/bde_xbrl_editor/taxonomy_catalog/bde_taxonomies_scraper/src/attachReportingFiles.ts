import { ModuleFile, ReportingModule, Taxonomy } from './types';

const HISTORIC_URL_PATTERN =
  /historico|no-vigente|no-vigentes|archivo|obsoleto|impresos-no-vigentes|versiones-anteriores/;
const VIGENTE_PATH_PATTERN =
  /informacion-a-remitir|base-consolidada|impresos-vigentes|informacion-tipos-interes/;

const GENERIC_TOKENS = new Set([
  'estados',
  'relativos',
  'informacion',
  'estadisticas',
  'estadisticos',
  'requerimientos',
  'union',
  'economica',
  'monetaria',
  'para',
  'sobre',
  'bce',
  'bde',
  'entidades',
  'credito',
  'remitir',
]);

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ');
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function isHistoricModuleUrl(url: string): boolean {
  return HISTORIC_URL_PATTERN.test(url.toLowerCase());
}

function isVigenteModuleUrl(url: string): boolean {
  const lower = url.toLowerCase();
  return VIGENTE_PATH_PATTERN.test(lower) && !isHistoricModuleUrl(lower);
}

function extractTaxonomyCode(taxonomy: Taxonomy): string | null {
  const match = taxonomy.name.match(/\(([A-Za-z0-9_.\-]+)\)/);
  return match ? match[1].toLowerCase() : null;
}

function taxonomyCodeMatchesUrl(code: string, url: string): boolean {
  const codeSlug = slugify(code);
  let pathSlug = slugify(url);
  try {
    pathSlug = slugify(new URL(url, 'https://www.bde.es').pathname);
  } catch {
    // use full url slug fallback
  }
  if (codeSlug.length >= 4 && pathSlug.includes(codeSlug)) return true;

  const compactCode = code.replace(/[^a-z0-9]/gi, '').toLowerCase();
  const compactUrl = url.replace(/[^a-z0-9]/gi, '').toLowerCase();
  return compactCode.length >= 6 && compactUrl.includes(compactCode);
}

function extractTaxonomyTokens(taxonomy: Taxonomy): string[] {
  const tokens = new Set<string>();
  const name = taxonomy.name;

  const paren = name.match(/\(([^)]+)\)/);
  if (paren) {
    paren[1]
      .split(/[\s_\-/]+/)
      .filter((t) => t.length >= 2)
      .forEach((t) => tokens.add(t.toLowerCase()));
  }

  const leading = name.match(/^([A-Za-z][A-Za-z0-9_-]*)/);
  if (leading && leading[1].length >= 3) {
    tokens.add(leading[1].toLowerCase());
  }

  name
    .split(/[\s(,]+/)
    .map((w) => w.replace(/[^a-z0-9_-]/gi, ''))
    .filter((w) => w.length >= 4 && !GENERIC_TOKENS.has(w.toLowerCase()))
    .forEach((w) => tokens.add(w.toLowerCase()));

  return Array.from(tokens);
}

function extractEntryPointPathHints(taxonomy: Taxonomy): string[] {
  const hints = new Set<string>();
  for (const ep of taxonomy.entryPoints) {
    const combined = `${ep.name} ${ep.url}`.toLowerCase();
    const mirYear = combined.match(/\/mir\/(\d{4})/);
    if (mirYear) {
      hints.add(`mir-${mirYear[1]}`);
      hints.add('mir');
    }
    const fws = combined.match(/\/fws\/([a-z0-9_-]+)/i);
    if (fws) hints.add(fws[1].toLowerCase());
    const finrep = combined.match(/finrep/i);
    if (finrep) hints.add('finrep');
    const solv = combined.match(/solv/i);
    if (solv) hints.add('solv');
  }
  return Array.from(hints);
}

function moduleSearchText(module: ReportingModule): string {
  return normalize(`${module.name} ${module.section || ''} ${module.sourceUrl} ${module.id}`);
}

function statusCompatible(taxonomy: Taxonomy, module: ReportingModule): boolean {
  const moduleUrl = module.sourceUrl.toLowerCase();
  const historic = isHistoricModuleUrl(moduleUrl);

  if (taxonomy.status === 'vigente' && historic) return false;
  if (taxonomy.status === 'no-vigente' && isVigenteModuleUrl(moduleUrl) && !historic) {
    return false;
  }
  return true;
}

function matchScore(taxonomy: Taxonomy, module: ReportingModule): number {
  if (!statusCompatible(taxonomy, module)) return 0;

  const tokens = extractTaxonomyTokens(taxonomy);
  const haystack = moduleSearchText(module);
  const moduleUrl = module.sourceUrl.toLowerCase();
  const moduleSlug = slugify(moduleUrl);
  let score = 0;

  const code = extractTaxonomyCode(taxonomy);
  if (code && taxonomyCodeMatchesUrl(code, module.sourceUrl)) {
    score += 30;
  }

  for (const hint of extractEntryPointPathHints(taxonomy)) {
    const hintSlug = slugify(hint);
    if (hintSlug.length >= 3 && moduleSlug.includes(hintSlug)) {
      score += 12;
    }
  }

  for (const token of tokens) {
    const normalized = normalize(token);
    if (normalized.length < 3 || GENERIC_TOKENS.has(normalized.replace(/\s/g, ''))) {
      continue;
    }

    if (haystack.includes(normalized)) {
      score += normalized.length >= 6 ? 8 : 5;
    }

    const acronym = normalized.replace(/[^a-z]/g, '');
    if (acronym.length >= 4 && haystack.replace(/\s/g, '').includes(acronym)) {
      score += 6;
    }

    const slugToken = acronym.replace(/[^a-z0-9]/g, '');
    if (slugToken.length >= 4 && moduleSlug.includes(slugToken)) {
      score += 10;
    }
  }

  if (taxonomy.category && module.category === taxonomy.category) {
    score += 1;
  }

  if (taxonomy.status === 'vigente' && isVigenteModuleUrl(moduleUrl)) {
    score += 6;
  }

  if (taxonomy.status === 'no-vigente' && isHistoricModuleUrl(moduleUrl)) {
    score += 8;
  }

  if (taxonomy.status === 'vigente' && isHistoricModuleUrl(moduleUrl)) {
    score -= 50;
  }

  return score;
}

const MIN_MATCH_SCORE = 6;

function preferModule(
  candidate: ReportingModule,
  current: ReportingModule,
  taxonomy: Taxonomy
): boolean {
  const candidateUrl = candidate.sourceUrl.toLowerCase();
  const currentUrl = current.sourceUrl.toLowerCase();
  const candidateHistoric = isHistoricModuleUrl(candidateUrl);
  const currentHistoric = isHistoricModuleUrl(currentUrl);

  if (taxonomy.status === 'vigente') {
    if (candidateHistoric !== currentHistoric) return !candidateHistoric;
  } else if (taxonomy.status === 'no-vigente') {
    if (candidateHistoric !== currentHistoric) return candidateHistoric;
  }

  if (candidate.files.length !== current.files.length) {
    return candidate.files.length > current.files.length;
  }
  return candidate.name.length < current.name.length;
}

export function attachReportingFiles(
  taxonomies: Taxonomy[],
  modules: ReportingModule[]
): void {
  for (const taxonomy of taxonomies) {
    taxonomy.reportingFiles = [];
    taxonomy.reportingModuleUrl = undefined;
    taxonomy.hasReportingFileUpdates = false;
  }

  for (const taxonomy of taxonomies) {
    let bestModule: ReportingModule | null = null;
    let bestScore = 0;

    for (const module of modules) {
      const score = matchScore(taxonomy, module);
      if (score < MIN_MATCH_SCORE) continue;
      if (
        !bestModule ||
        score > bestScore ||
        (score === bestScore && preferModule(module, bestModule, taxonomy))
      ) {
        bestModule = module;
        bestScore = score;
      }
    }

    if (!bestModule) continue;

    taxonomy.reportingFiles = [...bestModule.files];
    taxonomy.reportingModuleUrl = bestModule.sourceUrl;
    taxonomy.hasReportingFileUpdates = bestModule.files.some(
      (f) => f.isUpdatedSinceLastCheck
    );
  }

}
