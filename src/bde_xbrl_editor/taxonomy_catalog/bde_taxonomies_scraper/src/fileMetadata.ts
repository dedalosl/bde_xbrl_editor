import * as https from 'https';
import * as http from 'http';
import {
  FILE_METADATA_CONCURRENCY,
  FILE_METADATA_MAX_REDIRECTS,
  FILE_METADATA_TIMEOUT_MS,
} from './scrapeConfig';

export interface HttpFileMetadata {
  lastModified: string | null;
  contentLength: number | null;
  etag: string | null;
}

export interface FileMetadataHistory {
  files: Record<
    string,
    {
      lastModified: string | null;
      contentLength?: number | null;
      etag: string | null;
      checkedAt: string;
    }
  >;
}

const DOWNLOAD_EXTENSIONS = /\.(pdf|xlsx?|xls|zip|docx?|csv)(\?|$)/i;
const LAST_MODIFIED_DRIFT_TOLERANCE_MS = 2_000;

export function isDownloadableUrl(url: string): boolean {
  try {
    const pathname = new URL(url).pathname;
    return DOWNLOAD_EXTENSIONS.test(pathname);
  } catch {
    return DOWNLOAD_EXTENSIONS.test(url);
  }
}

export function inferFileType(url: string, label?: string): string | undefined {
  const source = `${url} ${label || ''}`.toLowerCase();
  if (source.includes('.pdf') || label?.toLowerCase().includes('pdf')) return 'pdf';
  if (source.includes('.xlsx') || source.includes('.xls')) return 'excel';
  if (source.includes('.zip')) return 'zip';
  if (source.includes('.doc')) return 'word';
  return undefined;
}

function requestMetadata(
  url: string,
  method: 'HEAD' | 'GET'
): Promise<{ statusCode: number; headers: http.IncomingHttpHeaders }> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === 'https:' ? https : http;

    const req = lib.request(
      url,
      {
        method,
        headers: method === 'GET' ? { Range: 'bytes=0-0' } : {},
        timeout: FILE_METADATA_TIMEOUT_MS,
      },
      (res) => {
        res.resume();
        resolve({ statusCode: res.statusCode || 0, headers: res.headers });
      }
    );

    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timeout after ${FILE_METADATA_TIMEOUT_MS}ms`));
    });
    req.end();
  });
}

export async function fetchFileMetadata(
  url: string,
  redirectDepth = 0
): Promise<HttpFileMetadata> {
  if (redirectDepth > FILE_METADATA_MAX_REDIRECTS) {
    console.warn(`  Metadata redirect limit reached for ${url}`);
    return { lastModified: null, contentLength: null, etag: null };
  }

  try {
    let response = await requestMetadata(url, 'HEAD');

    if (response.statusCode === 405 || response.statusCode === 403 || response.statusCode === 501) {
      response = await requestMetadata(url, 'GET');
    }

    if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
      const redirectUrl = new URL(response.headers.location, url).href;
      return fetchFileMetadata(redirectUrl, redirectDepth + 1);
    }

    const lastModified = response.headers['last-modified']
      ? String(response.headers['last-modified'])
      : null;
    const etag = response.headers.etag ? String(response.headers.etag) : null;
    const contentLengthHeader = response.headers['content-length'];
    const contentLength =
      contentLengthHeader !== undefined ? parseInt(String(contentLengthHeader), 10) : null;

    return {
      lastModified,
      contentLength: Number.isNaN(contentLength) ? null : contentLength,
      etag,
    };
  } catch (error) {
    console.warn(`  Could not fetch metadata for ${url}: ${error}`);
    return { lastModified: null, contentLength: null, etag: null };
  }
}

export function loadMetadataHistory(filePath: string, fs: typeof import('fs')): FileMetadataHistory {
  if (!fs.existsSync(filePath)) {
    return { files: {} };
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as FileMetadataHistory;
  } catch {
    return { files: {} };
  }
}

export function saveMetadataHistory(
  filePath: string,
  history: FileMetadataHistory,
  fs: typeof import('fs'),
  pathModule: typeof import('path')
): void {
  const dir = pathModule.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(filePath, JSON.stringify(history, null, 2), 'utf-8');
}

export function detectUpdate(
  url: string,
  current: HttpFileMetadata,
  history: FileMetadataHistory
): boolean {
  const previous = history.files[url];
  if (!previous) return false;

  if (
    current.contentLength != null &&
    previous.contentLength != null &&
    current.contentLength !== previous.contentLength
  ) {
    return true;
  }

  if (current.lastModified && previous.lastModified) {
    return lastModifiedChanged(current.lastModified, previous.lastModified);
  }

  if (current.etag && previous.etag) {
    return current.etag !== previous.etag;
  }

  return false;
}

function lastModifiedChanged(current: string, previous: string): boolean {
  if (current === previous) return false;

  const currentTime = Date.parse(current);
  const previousTime = Date.parse(previous);
  if (!Number.isNaN(currentTime) && !Number.isNaN(previousTime)) {
    return Math.abs(currentTime - previousTime) > LAST_MODIFIED_DRIFT_TOLERANCE_MS;
  }

  return current !== previous;
}

export async function enrichFileWithMetadata<T extends { url: string }>(
  file: T,
  history: FileMetadataHistory
): Promise<
  T & {
    lastModified: string | null;
    contentLength: number | null;
    etag: string | null;
    isUpdatedSinceLastCheck: boolean;
  }
> {
  const meta = await fetchFileMetadata(file.url);
  const isUpdatedSinceLastCheck = detectUpdate(file.url, meta, history);

  history.files[file.url] = {
    lastModified: meta.lastModified,
    contentLength: meta.contentLength,
    etag: meta.etag,
    checkedAt: new Date().toISOString(),
  };

  return {
    ...file,
    lastModified: meta.lastModified,
    contentLength: meta.contentLength,
    etag: meta.etag,
    isUpdatedSinceLastCheck,
  };
}

/** Run metadata enrichment with bounded concurrency and optional progress callback. */
export async function enrichFilesWithMetadata<T extends { url: string }>(
  files: T[],
  history: FileMetadataHistory,
  options?: {
    concurrency?: number;
    onProgress?: (completed: number, total: number) => void;
  }
): Promise<
  Array<
    T & {
      lastModified: string | null;
      contentLength: number | null;
      etag: string | null;
      isUpdatedSinceLastCheck: boolean;
    }
  >
> {
  if (files.length === 0) return [];

  const concurrency = options?.concurrency ?? FILE_METADATA_CONCURRENCY;
  const results: Array<
    T & {
      lastModified: string | null;
      contentLength: number | null;
      etag: string | null;
      isUpdatedSinceLastCheck: boolean;
    }
  > = new Array(files.length);
  let nextIndex = 0;
  let completed = 0;

  async function worker(): Promise<void> {
    while (true) {
      const index = nextIndex++;
      if (index >= files.length) return;
      results[index] = await enrichFileWithMetadata(files[index], history);
      completed += 1;
      options?.onProgress?.(completed, files.length);
    }
  }

  const workers = Array.from(
    { length: Math.min(concurrency, files.length) },
    () => worker()
  );
  await Promise.all(workers);
  return results;
}
