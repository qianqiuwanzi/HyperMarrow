import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';
import { store } from './store';
import { execSync } from 'child_process';
let checking = false;
export function initUpdater(mw: BrowserWindow): void {
  autoUpdater.setFeedURL({ provider: 'generic', url: `${store.get('settings.serverUrl')}/api/v2/client/updates` });
  autoUpdater.autoDownload = false;
  autoUpdater.on('update-available', (info) => {
    const force = (info as any).forceUpdate;
    dialog.showMessageBox(mw, { type: force ? 'warning' : 'info', title: force ? '需要更新' : '发现新版本', message: `HyperMarrow v${info.version} 已发布`, buttons: ['立即更新', '稍后提醒'], defaultId: 0, cancelId: 1 }).then(({ response }) => { if (response === 0) autoUpdater.downloadUpdate(); });
  });
  autoUpdater.on('download-progress', (p) => mw.webContents.send('update:download-progress', { percent: Math.round(p.percent) }));
  autoUpdater.on('update-downloaded', () => dialog.showMessageBox(mw, { type: 'info', title: '更新已下载', message: '是否立即重启安装？', buttons: ['立即重启', '稍后'], defaultId: 0 }).then(({ response }) => {
    if (response === 0) {
      // Disable minimize-to-tray so close actually quits the app
      store.set('settings.minimizeToTray', false);
      // Force-close all windows so app can exit
      BrowserWindow.getAllWindows().forEach(w => { try { w.destroy(); } catch(e) {} });
      // Now quitAndInstall can proceed — no more "无法关闭" from NSIS
      setImmediate(() => autoUpdater.quitAndInstall(false, true));
    }
  }));
  autoUpdater.on('error', (err) => console.error('[Updater]', err.message));
}
export async function checkForUpdates(userInitiated: boolean): Promise<void> {
  if (checking) return; checking = true;
  try { if (userInitiated) autoUpdater.autoDownload = true; await autoUpdater.checkForUpdates(); }
  catch (err) { console.error('[Updater] check failed:', err); } finally { checking = false; }
}
