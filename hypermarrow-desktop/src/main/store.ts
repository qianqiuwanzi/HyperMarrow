import Store from 'electron-store';
export const store = new Store<any>({
  name: 'hypermarrow-config', encryptionKey: 'hypermarrow-v2-secure-store',
  defaults: {
    auth: null, license: null,
    settings: { autoLaunch: true, minimizeToTray: true, language: 'zh-CN', theme: 'auto', serverUrl: 'https://hm.qianshi.cool' },
  },
});
export function getAuthToken(): string | null { return store.get('auth.token', null); }
export function isLoggedIn(): boolean { const a = store.get('auth'); return !!(a && Date.now() / 1000 < a.expiresAt); }
export function clearAuth(): void { store.set('auth', null); }
export function getServerUrl(): string { return store.get('settings.serverUrl'); }
