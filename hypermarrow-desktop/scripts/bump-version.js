/**
 * Auto-bump patch version and sync to all files before each build.
 * Called by npm prebuild hook — never skipped.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const VERSION_FILE = path.join(ROOT, 'VERSION');

// 1. Read current version
let version = fs.existsSync(VERSION_FILE)
  ? fs.readFileSync(VERSION_FILE, 'utf-8').trim()
  : '0.0.0';

// 2. Bump with rollover: each segment 0-9, overflow carries left
const parts = version.split('.').map(Number);
parts[2] += 1;                     // bump patch
if (parts[2] > 9) { parts[2] = 0; parts[1] += 1; }  // 2.0.9 → 2.1.0
if (parts[1] > 9) { parts[1] = 0; parts[0] += 1; }  // 2.9.9 → 3.0.0
const newVersion = parts.join('.');

// 3. Write back
fs.writeFileSync(VERSION_FILE, newVersion + '\n');
console.log(`[bump-version] ${version} → ${newVersion}`);

// 4. Sync to package.json
const pkgPath = path.join(ROOT, 'hypermarrow-desktop', 'package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
pkg.version = newVersion;
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n');

// 5. Sync to config.py
const cfgPath = path.join(ROOT, 'openclaw-memory-system', 'memory_core', 'config.py');
let cfg = fs.readFileSync(cfgPath, 'utf-8');
cfg = cfg.replace(/__version__\s*=\s*"[^"]+"/, `__version__ = "${newVersion}"`);
fs.writeFileSync(cfgPath, cfg);

// 6. Sync to engine-downloader.ts
const engPath = path.join(ROOT, 'hypermarrow-desktop', 'src', 'main', 'engine-downloader.ts');
let eng = fs.readFileSync(engPath, 'utf-8');
eng = eng.replace(/version:\s*'[^']+'/g, `version: '${newVersion}'`);
fs.writeFileSync(engPath, eng);

// 7. Export for use by postbuild
process.env.HM_VERSION = newVersion;
console.log(`[bump-version] All files synced to ${newVersion}`);
