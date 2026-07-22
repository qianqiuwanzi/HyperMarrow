/**
 * Engine Module Downloader — downloads & installs AI engine modules on demand.
 *
 * Flow:
 *  1. Check if engine module sentinel file exists → already installed
 *  2. If not, download engine-{name}-{version}.zip from CDN with progress
 *  3. Extract into embedded Python site-packages via Python zipfile
 *  4. Write sentinel file marking installation complete
 *  5. Return success → caller restarts Python API process
 */
import * as path from 'path';
import * as fs from 'fs';
import * as https from 'https';
import { app, BrowserWindow } from 'electron';
import { spawnSync } from 'child_process';

// ── Engine module registry ──────────────────────────────────────────────────

interface EngineModule {
  name: string;
  version: string;
  description: string;
  sizeMB: number;
}

const CDN_BASE = 'https://cdn.qianshi.cool/download';

const ENGINE_MODULES: Record<string, EngineModule> = {
  vector: {
    name: 'vector',
    version: '2.1.1',
    description: '向量记忆引擎 — 语义搜索和智能记忆',
    sizeMB: 80,
  },
  neural: {
    name: 'neural',
    version: '2.1.1',
    description: '神经引擎 — 世界模型和深度学习',
    sizeMB: 120,
  },
};

// ── Path helpers ────────────────────────────────────────────────────────────

function getSitePackagesPath(): string {
  return path.join(process.resourcesPath, 'py310', 'Lib', 'site-packages');
}

function getPythonExePath(): string {
  return path.join(process.resourcesPath, 'py310', 'python.exe');
}

function getSentinelPath(moduleName: string): string {
  return path.join(getSitePackagesPath(), `.engine-${moduleName}`);
}

// ── Public API ──────────────────────────────────────────────────────────────

export function isEngineInstalled(moduleName: string): boolean {
  return fs.existsSync(getSentinelPath(moduleName));
}

export function getInstalledModules(): Record<string, { version: string; installedAt: string }> {
  const result: Record<string, { version: string; installedAt: string }> = {};
  for (const name of Object.keys(ENGINE_MODULES)) {
    const sp = getSentinelPath(name);
    if (fs.existsSync(sp)) {
      try {
        result[name] = JSON.parse(fs.readFileSync(sp, 'utf-8'));
      } catch {
        result[name] = { version: '2.1.1', installedAt: '' };
      }
    }
  }
  return result;
}

export function getModuleInfo(moduleName: string): EngineModule | undefined {
  return ENGINE_MODULES[moduleName];
}

export function getAvailableModules(): EngineModule[] {
  return Object.values(ENGINE_MODULES);
}

/**
 * Download and install an engine module.
 *
 * @param moduleName  'vector' | 'neural'
 * @param onProgress  callback with 0-100 percent
 * @returns true on success
 */
export async function installEngineModule(
  moduleName: string,
  onProgress?: (pct: number) => void,
): Promise<boolean> {
  const mod = ENGINE_MODULES[moduleName];
  if (!mod) {
    console.error(`[Engine] Unknown module: ${moduleName}`);
    return false;
  }

  // Already installed?
  if (isEngineInstalled(moduleName)) {
    console.log(`[Engine] ${moduleName} already installed`);
    if (onProgress) onProgress(100);
    return true;
  }

  const url = `${CDN_BASE}/engine-${moduleName}-${mod.version}.zip`;
  const tmpDir = app.getPath('temp');
  const zipPath = path.join(tmpDir, `hypermarrow-engine-${moduleName}-${Date.now()}.zip`);

  console.log(`[Engine] Downloading ${moduleName} from ${url}...`);

  // Step 1: Download
  try {
    await downloadFile(url, zipPath, (received, total) => {
      if (onProgress && total > 0) {
        // Download is 80% of total progress
        onProgress(Math.round((received / total) * 80));
      }
    });
  } catch (err: any) {
    console.error(`[Engine] Download failed: ${err.message}`);
    try { fs.unlinkSync(zipPath); } catch {}
    return false;
  }

  if (onProgress) onProgress(85);

  // Step 2: Extract into site-packages
  const sitePkg = getSitePackagesPath();
  const pythonExe = getPythonExePath();

  if (!fs.existsSync(pythonExe)) {
    console.error('[Engine] Embedded Python not found at', pythonExe);
    try { fs.unlinkSync(zipPath); } catch {}
    return false;
  }

  console.log(`[Engine] Extracting to ${sitePkg}...`);
  const extractScript = `
import zipfile, sys, os
zip_path = sys.argv[1]
target = sys.argv[2]
os.makedirs(target, exist_ok=True)
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(target)
print('extracted', z.namelist()[0] if z.namelist() else 'empty')
`;

  const result = spawnSync(pythonExe, ['-c', extractScript, zipPath, sitePkg], {
    timeout: 120000, // 2 min for extraction
    encoding: 'utf-8',
  });

  // Clean up zip
  try { fs.unlinkSync(zipPath); } catch {}

  if (result.status !== 0) {
    console.error(`[Engine] Extract failed: ${result.stderr}`);
    return false;
  }

  console.log(`[Engine] Extract OK: ${result.stdout?.trim()}`);

  if (onProgress) onProgress(95);

  // Step 3: Write sentinel
  fs.writeFileSync(
    getSentinelPath(moduleName),
    JSON.stringify({
      version: mod.version,
      installedAt: new Date().toISOString(),
    }),
    'utf-8',
  );

  if (onProgress) onProgress(100);
  console.log(`[Engine] Module '${moduleName}' installed successfully`);
  return true;
}

// ── Internal: file download with progress ──────────────────────────────────

function downloadFile(
  url: string,
  dest: string,
  onProgress: (received: number, total: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    // Ensure dest directory exists
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });

    const file = fs.createWriteStream(dest);
    let received = 0;

    const req = https.get(url, { timeout: 300000 }, (response) => {
      // Handle redirects
      if (response.statusCode && response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        file.close();
        fs.unlinkSync(dest);
        // Follow redirect
        https.get(response.headers.location, { timeout: 300000 }, (redirectRes) => {
          const total = parseInt(redirectRes.headers['content-length'] || '0', 10);
          redirectRes.on('data', (chunk: Buffer) => {
            received += chunk.length;
            onProgress(received, total);
          });
          redirectRes.pipe(file);
          file.on('finish', () => { file.close(); resolve(); });
          file.on('error', (err) => { try { fs.unlinkSync(dest); } catch {} reject(err); });
        }).on('error', (err) => { try { fs.unlinkSync(dest); } catch {} reject(err); });
        return;
      }

      const total = parseInt(response.headers['content-length'] || '0', 10);
      response.on('data', (chunk: Buffer) => {
        received += chunk.length;
        onProgress(received, total);
      });
      response.pipe(file);
      file.on('finish', () => { file.close(); resolve(); });
      file.on('error', (err) => { try { fs.unlinkSync(dest); } catch {} reject(err); });
    });

    req.on('error', (err) => { try { fs.unlinkSync(dest); } catch {} reject(err); });
    req.on('timeout', () => { req.destroy(); try { fs.unlinkSync(dest); } catch {} reject(new Error('Download timeout')); });
  });
}
