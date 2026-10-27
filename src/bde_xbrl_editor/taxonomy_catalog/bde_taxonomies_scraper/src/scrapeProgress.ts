/**
 * Weighted scrape progress for terminal output.
 * Phases sum to 100; sub-steps advance within each phase.
 */

export type ScrapePhaseId =
  | 'reporting_modules'
  | 'taxonomy_related'
  | 'taxonomies'
  | 'entry_points'
  | 'general_documents'
  | 'finalize';

const PHASE_WEIGHTS: Record<ScrapePhaseId, number> = {
  reporting_modules: 42,
  taxonomy_related: 5,
  taxonomies: 33,
  entry_points: 12,
  general_documents: 6,
  finalize: 2,
};

const PHASE_ORDER: ScrapePhaseId[] = [
  'reporting_modules',
  'taxonomy_related',
  'taxonomies',
  'entry_points',
  'general_documents',
  'finalize',
];

const PHASE_LABELS: Record<ScrapePhaseId, string> = {
  reporting_modules: 'Reporting modules',
  taxonomy_related: 'Taxonomy related links',
  taxonomies: 'Taxonomies',
  entry_points: 'Entry point metadata',
  general_documents: 'General documents',
  finalize: 'Saving results',
};

function phaseStartPercent(phase: ScrapePhaseId): number {
  let sum = 0;
  for (const id of PHASE_ORDER) {
    if (id === phase) return sum;
    sum += PHASE_WEIGHTS[id];
  }
  return sum;
}

export class ScrapeProgress {
  private lastPrinted = -1;
  private phase: ScrapePhaseId | null = null;
  private phaseDetail = '';

  startPhase(phase: ScrapePhaseId, detail?: string): void {
    this.phase = phase;
    this.phaseDetail = detail ?? '';
    const label = PHASE_LABELS[phase];
    console.log(
      `\n▶ ${label}${detail ? ` — ${detail}` : ''} (from ~${phaseStartPercent(phase)}%)`
    );
    this.emit(phaseStartPercent(phase));
  }

  endPhase(phase: ScrapePhaseId): void {
    const end =
      phaseStartPercent(phase) + PHASE_WEIGHTS[phase];
    console.log(`✓ ${PHASE_LABELS[phase]} done (~${end}%)`);
    this.emit(end);
    if (this.phase === phase) {
      this.phase = null;
      this.phaseDetail = '';
    }
  }

  /** Advance within the current phase (0–1). */
  setPhaseProgress(fraction: number, detail?: string): void {
    if (!this.phase) return;
    const clamped = Math.min(1, Math.max(0, fraction));
    if (detail !== undefined) this.phaseDetail = detail;
    const percent =
      phaseStartPercent(this.phase) +
      PHASE_WEIGHTS[this.phase] * clamped;
    this.emit(percent);
  }

  log(detail: string): void {
    this.phaseDetail = detail;
    if (this.phase) {
      const base = phaseStartPercent(this.phase);
      console.log(`  … ${PHASE_LABELS[this.phase]}: ${detail}`);
      this.emit(base + PHASE_WEIGHTS[this.phase] * 0.5);
    } else {
      console.log(`  … ${detail}`);
    }
  }

  private emit(percent: number): void {
    const rounded = Math.min(100, Math.max(0, Math.round(percent)));
    if (rounded === this.lastPrinted) return;
    this.lastPrinted = rounded;
    const phaseLabel = this.phase ? PHASE_LABELS[this.phase] : 'Scrape';
    const detail = this.phaseDetail ? ` — ${this.phaseDetail}` : '';
    process.stdout.write(`\r[${rounded}%] ${phaseLabel}${detail}   `);
    if (rounded >= 100) {
      process.stdout.write('\n');
    }
  }
}

export const scrapeProgress = new ScrapeProgress();
