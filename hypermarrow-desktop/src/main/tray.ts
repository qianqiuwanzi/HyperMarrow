import { Tray, Menu, nativeImage, BrowserWindow, app } from 'electron';
import * as path from 'path';
import { store } from './store';
import { showMainWindow } from './index';
import { checkForUpdates } from './updater';
let tray: Tray | null = null;

function trayIcon(): Electron.NativeImage {
  // Use product icon for tray — in packaged app it's at resources/icon.png
  const isDev = !app.isPackaged;
  const iconPath = isDev
    ? path.join(__dirname, '..', '..', 'build', 'icon.png')
    : path.join(process.resourcesPath, 'icon.png');
  try {
    const img = nativeImage.createFromPath(iconPath);
    return img.resize({ width: 16, height: 16 });
  } catch(e) {
    // Fallback: colored circle
    const s = 16, c = Buffer.alloc(s * s * 4);
    for (let y=0;y<s;y++) for (let x=0;x<s;x++) { const i=(y*s+x)*4; if(Math.sqrt((x-8)**2+(y-8)**2)<=6) {c[i]=102;c[i+1]=126;c[i+2]=234;c[i+3]=255;} }
    return nativeImage.createFromBuffer(c,{width:s,height:s});
  }
}

function buildMenu(): Menu {
  return Menu.buildFromTemplate([
    {label:'打开主面板',click:()=>showMainWindow()},{type:'separator'},
    {label:'检查更新',click:()=>checkForUpdates(true)},{type:'separator'},
    {label:'退出',click:()=>{store.set('settings.minimizeToTray',false);app.quit();}},
  ]);
}
export function initTray(mw: BrowserWindow): void {
  if(tray)return;
  tray=new Tray(trayIcon());
  tray.setToolTip('智商藏不住');
  tray.setContextMenu(buildMenu());
  tray.on('click',()=>showMainWindow());
}
export function updateTrayStatus(status: 'active'|'warning'|'expired'|'none', days: number): void {
  if(!tray)return;
  const labels: Record<string,string> = { active:`剩余 ${days} 天`, warning:`仅剩 ${days} 天`, expired:'已过期', none:'未激活' };
  tray.setToolTip(`智商藏不住 · ${labels[status]||labels.none}`);
  tray.setContextMenu(Menu.buildFromTemplate([
    {label:'打开主面板',click:()=>showMainWindow()},{type:'separator'},
    {label:(status==='active'?'✅':status==='warning'?'⚠️':status==='expired'?'❌':'⚪')+` License · ${labels[status]}`,enabled:false},
    {type:'separator'},{label:'检查更新',click:()=>checkForUpdates(true)},{type:'separator'},
    {label:'退出',click:()=>{store.set('settings.minimizeToTray',false);app.quit();}},
  ]));
}
