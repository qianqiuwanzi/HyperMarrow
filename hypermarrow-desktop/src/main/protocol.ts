import { app } from 'electron';
import { showMainWindow } from './index';
export function registerProtocol(): void {
  if(!app.isDefaultProtocolClient('hypermarrow')) app.setAsDefaultProtocolClient('hypermarrow');
  app.on('open-url',(e,url)=>{e.preventDefault();handle(url);});
  const a=process.argv.find(x=>x.startsWith('hypermarrow://')); if(a) handle(a);
}
function handle(url:string):void{try{const p=new URL(url);const{BrowserWindow}=require('electron');const w=BrowserWindow.getAllWindows()[0];if(p.hostname==='payment'&&w)w.webContents.send('payment:callback',{outTradeNo:p.searchParams.get('out_trade_no'),status:p.searchParams.get('status')||'unknown'});}catch(e){}showMainWindow();}
