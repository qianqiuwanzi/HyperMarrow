/**
 * HyperMarrow 智商藏不住 桌面客户端 — 主进程入口
 */
import { app, BrowserWindow, Menu, shell } from 'electron';
import * as path from 'path';

// 允许自签名证书（开发/测试用，正式证书部署后可移除此行）
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
import { initTray, updateTrayStatus } from './tray';
import { initAutoLaunch } from './auto-launch';
import { initUpdater, checkForUpdates } from './updater';
import { registerProtocol } from './protocol';
import { registerIpcHandlers } from './ipc-handlers';
import { store } from './store';

const isDev = !app.isPackaged;
const RENDERER_DIR = isDev
  ? path.join(__dirname, '..', 'src', 'renderer')
  : path.join(__dirname, '..', '..', 'src', 'renderer');

let mainWindow: BrowserWindow | null = null;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) { app.quit(); } else {
  app.on('second-instance', () => {
    if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); mainWindow.show(); }
  });
}

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 960, height: 680, minWidth: 800, minHeight: 600,
    title: '智商藏不住', show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: false,
    },
  });
  win.loadFile(path.join(RENDERER_DIR, 'index.html'));
  win.once('ready-to-show', () => win.show());
  win.on('close', (event) => {
    if (store.get('settings.minimizeToTray', true)) { event.preventDefault(); win.hide(); }
  });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  return win;
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  registerProtocol(); registerIpcHandlers();
  mainWindow = createMainWindow();
  initTray(mainWindow);
  await initAutoLaunch(); initUpdater(mainWindow);
  setTimeout(() => checkForUpdates(false), 5000);
  setInterval(() => checkForUpdates(false), 6 * 60 * 60 * 1000);
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) mainWindow = createMainWindow(); else mainWindow?.show(); });
});
app.on('window-all-closed', () => {});

export function getMainWindow(): BrowserWindow | null { return mainWindow; }
export function showMainWindow(): void {
  if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); mainWindow.show(); }
}
