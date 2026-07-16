import { ipcMain, shell } from 'electron';
import { store, getAuthToken, isLoggedIn, clearAuth, getServerUrl } from './store';
import { updateTrayStatus } from './tray';
import { showMainWindow, getMainWindow } from './index';
import { checkForUpdates } from './updater';
import { setAutoLaunch, isAutoLaunchEnabled } from './auto-launch';
import { checkOfflineStatus } from './offline';

async function apiRequest(method: string, path: string, body?: unknown, useAuth = true) {
  const url = `${getServerUrl()}${path}`;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (useAuth) { const t = getAuthToken(); if (t) headers['Authorization'] = `Bearer ${t}`; }
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30000);
    const opts: RequestInit = { method, headers, signal: controller.signal };
    if (body && method !== 'GET') opts.body = JSON.stringify(body);
    const resp = await fetch(url, opts);
    clearTimeout(timer);
    const data = await resp.json().catch(() => null);
    return { ok: resp.ok, status: resp.status, data };
  } catch (err: any) {
    console.error(`[API] ${method} ${url} → ${err.name}: ${err.message}`);
    return { ok: false, status: 0, data: { detail: err.name === 'TimeoutError' || err.name === 'AbortError' ? '请求超时' : `网络错误: ${err.message}` } };
  }
}

export function registerIpcHandlers(): void {
  ipcMain.handle('api:get', (_e, p: string) => apiRequest('GET', p));
  ipcMain.handle('api:post', (_e, p: string, b: unknown) => apiRequest('POST', p, b));
  ipcMain.handle('api:put', (_e, p: string, b: unknown) => apiRequest('PUT', p, b));
  ipcMain.handle('api:delete', (_e, p: string) => apiRequest('DELETE', p));
  ipcMain.handle('auth:get-token', () => getAuthToken());
  ipcMain.handle('auth:is-logged-in', () => isLoggedIn());
  ipcMain.handle('auth:clear', () => { clearAuth(); store.set('license', null); updateTrayStatus('none', -1); });
  ipcMain.handle('license:get-cached', () => store.get('license'));
  ipcMain.handle('license:update', (_e, d: any) => {
    store.set('license', d);
    const s = d?.status || 'none'; const r = d?.remainingDays || -1;
    updateTrayStatus(s === 'active' ? (r > 7 ? 'active' : 'warning') : s === 'expired' ? 'expired' : 'none', r);
    return true;
  });
  ipcMain.handle('window:show', () => showMainWindow());
  ipcMain.handle('window:hide', () => getMainWindow()?.hide());
  ipcMain.handle('system:open-external', (_e, url: string) => shell.openExternal(url));
  ipcMain.handle('system:open-html', (_e, html: string) => {
    const tmp = require('path').join(require('os').tmpdir(), `hypermarrow_pay_${Date.now()}.html`);
    require('fs').writeFileSync(tmp, html, 'utf-8');
    shell.openExternal(`file://${tmp}`);
    return true;
  });
  ipcMain.handle('system:get-auto-launch', () => isAutoLaunchEnabled());
  ipcMain.handle('system:set-auto-launch', (_e, v: boolean) => { setAutoLaunch(v); return true; });
  ipcMain.handle('system:check-updates', () => { checkForUpdates(true); return true; });
  ipcMain.handle('store:get', (_e, k: string, d?: unknown) => store.get(k as any, d as any));
  ipcMain.handle('store:set', (_e, k: string, v: unknown) => { store.set(k as any, v); return true; });
  ipcMain.handle('system:get-platform', () => process.platform);
  ipcMain.handle('system:get-device-info', () => ({ platform: process.platform, arch: process.arch, version: require('electron').app.getVersion() }));
  ipcMain.handle('license:offline-status', () => checkOfflineStatus());
}
