/**
 * Release script: copy installer + latest.yml to commercial/sales.
 * Called by npm run release. Uses absolute paths — never fails silently.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');
const version = fs.readFileSync(path.join(ROOT, 'VERSION'), 'utf-8').trim();

const releaseDir = path.join(ROOT, 'hypermarrow-desktop', 'release');
const salesDir = path.join(WORKSPACE, 'commercial', 'sales');

// Ensure sales dir exists
fs.mkdirSync(salesDir, { recursive: true });

// Copy installer
const exeName = `智商藏不住-Setup-${version}-win-x64.exe`;
const srcExe = path.join(releaseDir, exeName);
const dstExe = path.join(salesDir, 'hm-setup.exe');
fs.copyFileSync(srcExe, dstExe);
console.log(`[release] Copied ${exeName} → commercial/sales/hm-setup.exe (${(fs.statSync(dstExe).size / 1024 / 1024).toFixed(0)}MB)`);

// Copy latest.yml
const srcYml = path.join(releaseDir, 'latest.yml');
const dstYml = path.join(salesDir, 'latest.yml');
fs.copyFileSync(srcYml, dstYml);
console.log('[release] Copied latest.yml → commercial/sales/');
