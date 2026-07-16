import { Tray, Menu, nativeImage, BrowserWindow, app } from 'electron';
import { store } from './store';
import { showMainWindow } from './index';
import { checkForUpdates } from './updater';
let tray: Tray | null = null;
function icon(status: string): Electron.NativeImage {
  const s = 16, c = Buffer.alloc(s * s * 4);
  const colors: Record<string, [number,number,number]> = { active: [39,174,96], warning: [241,196,15], expired: [231,76,60], none: [149,165,166] };
  const [r,g,b] = colors[status] || colors.none;
  for (let y=0;y<s;y++) for (let x=0;x<s;x++) { const i=(y*s+x)*4; if(Math.sqrt((x-8)**2+(y-8)**2)<=6) {c[i]=r;c[i+1]=g;c[i+2]=b;c[i+3]=255;} }
  return nativeImage.createFromBuffer(c,{width:s,height:s});
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
  tray=new Tray(icon('none'));
  tray.setToolTip('智商藏不住');
  tray.setContextMenu(buildMenu());
  tray.on('click',()=>showMainWindow());
}
export function updateTrayStatus(status: 'active'|'warning'|'expired'|'none', days: number): void {
  if(!tray)return; tray.setImage(icon(status));
  const labels: Record<string,string> = { active:`剩余 ${days} 天`, warning:`仅剩 ${days} 天`, expired:'已过期', none:'未激活' };
  tray.setToolTip(`智商藏不住 · ${labels[status]||labels.none}`);
  tray.setContextMenu(Menu.buildFromTemplate([
    {label:'打开主面板',click:()=>showMainWindow()},{type:'separator'},
    {label:(status==='active'?'✅':status==='warning'?'⚠️':status==='expired'?'❌':'⚪')+` License · ${labels[status]}`,enabled:false},
    {type:'separator'},{label:'检查更新',click:()=>checkForUpdates(true)},{type:'separator'},
    {label:'退出',click:()=>{store.set('settings.minimizeToTray',false);app.quit();}},
  ]));
}
