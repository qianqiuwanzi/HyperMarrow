import { contextBridge, ipcRenderer } from 'electron';
contextBridge.exposeInMainWorld('electronAPI', {
  api: { get: (p: string) => ipcRenderer.invoke('api:get', p), post: (p: string, b?: unknown) => ipcRenderer.invoke('api:post', p, b), put: (p: string, b?: unknown) => ipcRenderer.invoke('api:put', p, b), delete: (p: string) => ipcRenderer.invoke('api:delete', p) },
  auth: { getToken: () => ipcRenderer.invoke('auth:get-token'), isLoggedIn: () => ipcRenderer.invoke('auth:is-logged-in'), clear: () => ipcRenderer.invoke('auth:clear') },
  license: { getCached: () => ipcRenderer.invoke('license:get-cached'), update: (d: any) => ipcRenderer.invoke('license:update', d) },
  window: { show: () => ipcRenderer.invoke('window:show'), hide: () => ipcRenderer.invoke('window:hide') },
  system: { openExternal: (u: string) => ipcRenderer.invoke('system:open-external', u), openHtml: (h: string) => ipcRenderer.invoke('system:open-html', h), getAutoLaunch: () => ipcRenderer.invoke('system:get-auto-launch'), setAutoLaunch: (v: boolean) => ipcRenderer.invoke('system:set-auto-launch', v), checkUpdates: () => ipcRenderer.invoke('system:check-updates'), getPlatform: () => ipcRenderer.invoke('system:get-platform'), getDeviceInfo: () => ipcRenderer.invoke('system:get-device-info') },
  store: { get: (k: string, d?: unknown) => ipcRenderer.invoke('store:get', k, d), set: (k: string, v: unknown) => ipcRenderer.invoke('store:set', k, v) },
  on: (ch: string, cb: (...args: any[]) => void) => { if (['update:download-progress','payment:callback','license:activated'].includes(ch)) ipcRenderer.on(ch, (_e, ...args) => cb(...args)); },
});
