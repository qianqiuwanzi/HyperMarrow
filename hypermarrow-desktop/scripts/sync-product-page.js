/**
 * Postbuild: update product page with version + actual file size.
 * Called automatically after every pack:win / pack:mac / pack:all.
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const WORKSPACE = path.resolve(__dirname, '..', '..', '..');

// Read version
const versionFile = path.join(ROOT, 'VERSION');
const version = fs.readFileSync(versionFile, 'utf-8').trim();

// Find installer
const releaseDir = path.join(ROOT, 'hypermarrow-desktop', 'release');
const files = fs.readdirSync(releaseDir).filter(f => f.endsWith('.exe'));
if (files.length === 0) {
  console.log('[sync-product-page] No installer found, skipping');
  process.exit(0);
}

const exePath = path.join(releaseDir, files[0]);
const sizeMB = Math.round(fs.statSync(exePath).size / (1024 * 1024));

// Update product page (commercial is a sibling of ROOT in workspace)
const htmlPath = path.join(WORKSPACE, 'commercial', 'sales', 'index.html');
if (!fs.existsSync(htmlPath)) {
  console.log('[sync-product-page] Product page not found, skipping');
  process.exit(0);
}

let html = fs.readFileSync(htmlPath, 'utf-8');
html = html.replace(/版本 [\d.]+/, `版本 ${version}`);
html = html.replace(/· \d+ MB ·/, `· ${sizeMB} MB ·`);
fs.writeFileSync(htmlPath, html);

console.log(`[sync-product-page] Product page: v${version} / ${sizeMB}MB`);
