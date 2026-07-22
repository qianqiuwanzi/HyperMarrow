/**
 * 智商藏不住 桌面客户端 — 主进程入口
 */
import { app, BrowserWindow, Menu, shell } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

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
let apiProcess: ChildProcess | null = null;

const API_PORT = 8741;

function findPython(): string {
  // Use embedded Python if available (bundled with installer)
  const embeddedPython = path.join(process.resourcesPath, 'py310', 'python.exe');
  if (fs.existsSync(embeddedPython)) {
    console.log('[API] Using embedded Python:', embeddedPython);
    return embeddedPython;
  }
  // Fallback: try system Python
  for (const cmd of ['python3', 'python']) {
    try {
      const result = require('child_process').spawnSync(cmd, ['--version'], { timeout: 3000 });
      if (result.status === 0) return cmd;
    } catch (e) { /* continue */ }
  }
  if (process.platform === 'win32') {
    for (const p of [
      'C:\\Program Files\\Python310\\python.exe',
      process.env.LOCALAPPDATA + '\\Programs\\Python\\Python310\\python.exe',
    ]) {
      if (fs.existsSync(p)) return p;
    }
  }
  return 'python';
}

function startMemoryAPI(): void {
  const python = findPython();

  // Determine start.py path — search upward from __dirname
  let startScript = '';
  // First check resourcesPath (packaged extraResources)
  if (fs.existsSync(path.join(process.resourcesPath, 'start.py'))) {
    startScript = path.join(process.resourcesPath, 'start.py');
  } else {
    // Search upward from __dirname for start.py
    let dir = __dirname;
    for (let i = 0; i < 10; i++) {
      const candidate = path.join(dir, 'start.py');
      if (fs.existsSync(candidate)) { startScript = candidate; break; }
      dir = path.dirname(dir);
    }
  }
  if (!startScript) {
    console.error(`[API] start.py not found from: ${__dirname}`);
    return;
  }

  const workspaceDir = path.dirname(startScript);
  console.log(`[API] Starting memory API from: ${startScript}`);
  console.log(`[API] Python: ${python}, Workspace: ${workspaceDir}`);

  try {
    apiProcess = spawn(python, [startScript, '--no-build', '--port', String(API_PORT)], {
      cwd: workspaceDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONNOUSERSITE: '1', APPDIR: process.resourcesPath },
    });

    apiProcess.stdout?.on('data', (data: Buffer) => {
      console.log(`[API] ${data.toString().trim()}`);
    });
    apiProcess.stderr?.on('data', (data: Buffer) => {
      console.error(`[API] ${data.toString().trim()}`);
    });
    apiProcess.on('error', (err: Error) => {
      console.error(`[API] Failed to start: ${err.message}`);
    });
    apiProcess.on('exit', (code: number | null) => {
      console.log(`[API] Process exited with code ${code}`);
      apiProcess = null;
    });
    apiProcess.stderr?.on('data', (data: Buffer) => {
      console.error(`[API] ${data.toString().trim()}`);
    });
  } catch (e: any) {
    console.error(`[API] Failed to spawn: ${e.message}`);
  }
}

function stopMemoryAPI(): void {
  if (apiProcess) {
    console.log('[API] Stopping memory API...');
    try {
      apiProcess.kill('SIGTERM');
      // Force kill after 3 seconds
      setTimeout(() => {
        if (apiProcess && !apiProcess.killed) {
          apiProcess.kill('SIGKILL');
        }
      }, 3000);
    } catch (e) { /* already dead */ }
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) { app.quit(); } else {
  app.on('second-instance', () => {
    showMainWindow();
  });
}

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200, height: 800, minWidth: 900, minHeight: 640,
    title: '智商藏不住', show: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: false,
    },
  });
  win.loadFile(path.join(RENDERER_DIR, 'index.html'));
  win.once('ready-to-show', () => win.show());
  win.on('close', (event) => {
    if (store.get('settings.minimizeToTray', true)) {
      event.preventDefault();
      win.hide();
    }
  });
  win.on('closed', () => {
    mainWindow = null;
  });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  return win;
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  registerProtocol(); registerIpcHandlers();

  // Auto-start memory API
  startMemoryAPI();

  mainWindow = createMainWindow();
  initTray(mainWindow);
  await initAutoLaunch(); initUpdater(mainWindow);
  setTimeout(() => checkForUpdates(false), 5000);
  setInterval(() => checkForUpdates(false), 6 * 60 * 60 * 1000);
  app.on('activate', () => { showMainWindow(); });
});

app.on('window-all-closed', () => {
  stopMemoryAPI();
  app.quit();
});

app.on('will-quit', () => {
  stopMemoryAPI();
});

export function getMainWindow(): BrowserWindow | null { return mainWindow; }
export function showMainWindow(): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
    mainWindow.show();
  } else {
    mainWindow = createMainWindow();
  }
}
export { stopMemoryAPI, startMemoryAPI };
