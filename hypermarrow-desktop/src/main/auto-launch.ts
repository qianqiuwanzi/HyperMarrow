import { app } from 'electron';
import { store } from './store';
export async function initAutoLaunch(): Promise<void> {
  try { app.setLoginItemSettings({ openAtLogin: store.get('settings.autoLaunch', true), openAsHidden: true, path: app.getPath('exe') }); }
  catch (err) { console.error('[AutoLaunch] Failed:', err); }
}
export function setAutoLaunch(enabled: boolean): void { store.set('settings.autoLaunch', enabled); app.setLoginItemSettings({ openAtLogin: enabled, openAsHidden: true }); }
export function isAutoLaunchEnabled(): boolean { return store.get('settings.autoLaunch', true); }
