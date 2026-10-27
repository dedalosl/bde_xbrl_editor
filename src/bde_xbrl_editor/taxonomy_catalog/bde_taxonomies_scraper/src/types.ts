export interface FileResourceMetadata {
  lastModified?: string | null;
  contentLength?: number | null;
  etag?: string | null;
  isUpdatedSinceLastCheck?: boolean;
}

export interface EntryPoint extends FileResourceMetadata {
  name: string;
  url: string;
}

export interface ModuleFile extends FileResourceMetadata {
  label: string;
  url: string;
  fileType?: string;
}

export interface Taxonomy {
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
  entryPoints: EntryPoint[];
  reportingFiles?: ModuleFile[];
  reportingModuleUrl?: string;
  sourceUrl: string;
  scrapedAt: string;
  hasEntryPointUpdates?: boolean;
  hasReportingFileUpdates?: boolean;
}

export interface ReportingModule {
  id: string;
  name: string;
  category: string;
  section?: string;
  files: ModuleFile[];
  sourceUrl: string;
  scrapedAt: string;
  hasUpdates?: boolean;
}

export interface TaxonomyMetadata {
  lastRun: string;
  totalCount: number;
  reportingModuleCount?: number;
  taxonomiesWithUpdates?: number;
  entryPointsWithUpdates?: number;
  filesWithUpdates?: number;
}

export interface TaxonomyData {
  metadata: TaxonomyMetadata;
  taxonomies: Taxonomy[];
  reportingModules: ReportingModule[];
  generalDocuments?: ModuleFile[];
  taxonomyRelatedLinks?: ModuleFile[];
}
