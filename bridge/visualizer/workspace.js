/* Local, uncompressed workspace transfer. Original browser data is never removed. */
(function(scope){
const MAGIC='APCWORKSPACE1\n',MAX=512*1024*1024,STAGE='__apc-import__';
let cleanup=Promise.resolve();
const validKey=key=>typeof key==='string'&&/^[a-zA-Z0-9_-]{1,64}(?::(?:recovery-base|recovery-state|video))?$/.test(key);
function validate(header,total){
 if(!header||header.version!==1||!Array.isArray(header.records)||header.records.length>256)throw Error('Invalid workspace header');
 let size=0;const keys=new Set();
 for(const record of header.records){
  if(!validKey(record.key)||keys.has(record.key)||!['arraybuffer','blob','json'].includes(record.type)||!Number.isSafeInteger(record.size)||record.size<0||record.size>256*1024*1024||typeof record.mime!=='string'||record.mime.length>200)throw Error('Invalid workspace record');
  keys.add(record.key);size+=record.size;
 }
 for(const name of ['local','session']){
  if(!Array.isArray(header[name])||header[name].length>1000)throw Error('Invalid workspace settings');
  const names=new Set();for(const pair of header[name])if(!Array.isArray(pair)||pair.length!==2||typeof pair[0]!=='string'||!pair[0].startsWith('apc40-')||pair[0].length>500||names.has(pair[0])||typeof pair[1]!=='string'||pair[1].length>1024*1024)throw Error('Invalid workspace setting');else names.add(pair[0]);
 }
 if(size!==total||size>MAX)throw Error('Workspace length mismatch');return header;
}
const request=req=>new Promise((resolve,reject)=>{req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
const complete=tx=>new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=tx.onabort=()=>reject(tx.error||Error('Workspace transaction cancelled'));});
async function database(){const open=indexedDB.open('apc40-space-projects',1);open.onupgradeneeded=()=>open.result.createObjectStore('projects');return request(open);}
function settings(storage){return Object.keys(storage).filter(k=>k.startsWith('apc40-')).map(k=>[k,storage.getItem(k)]);}
async function exportFile(){
 const db=await database(),parts=[],records=[];
 try{
  const keys=await request(db.transaction('projects').objectStore('projects').getAllKeys());
  for(const key of keys){
   if(!validKey(key))continue;
   const value=await request(db.transaction('projects').objectStore('projects').get(key));
   let type,blob;
   if(value instanceof ArrayBuffer){type='arraybuffer';blob=new Blob([value]);}
   else if(value instanceof Blob){type='blob';blob=value;}
   else {type='json';blob=new Blob([JSON.stringify(value)]);}
   parts.push(blob);records.push({key,type,size:blob.size,mime:blob.type});
  }
 }finally{db.close();}
 const header={version:1,records,local:settings(localStorage),session:settings(sessionStorage)};
 validate(header,parts.reduce((sum,p)=>sum+p.size,0));
 const bytes=new TextEncoder().encode(JSON.stringify(header));if(bytes.length>1024*1024)throw Error('Workspace settings are too large');
 const length=new ArrayBuffer(4);new DataView(length).setUint32(0,bytes.length,true);
 return new Blob([MAGIC,length,bytes,...parts],{type:'application/octet-stream'});
}
async function readHeader(file){
 if(file.size>MAX+1024*1024+32)throw Error('Workspace is larger than 512 MiB');
 const prefix=await file.slice(0,MAGIC.length+4).arrayBuffer();
 if(prefix.byteLength!==MAGIC.length+4||new TextDecoder().decode(prefix.slice(0,MAGIC.length))!==MAGIC)throw Error('This is not an APC40 workspace');
 const length=new DataView(prefix).getUint32(MAGIC.length,true),offset=MAGIC.length+4+length;
 if(length>1024*1024||offset>file.size)throw Error('Invalid workspace header length');
 const header=JSON.parse(await file.slice(MAGIC.length+4,offset).text());validate(header,file.size-offset);return{header,offset};
}
async function importFile(file){
 await cleanup;
 const {header,offset:initial}=await readHeader(file),db=await database(),staged=[],undo=[];let offset=initial;
 const nonce=STAGE+crypto.randomUUID()+':';
 try{
  for(const record of header.records){
   const blob=file.slice(offset,offset+record.size,record.mime);offset+=record.size;
   const value=record.type==='blob'?blob:record.type==='arraybuffer'?await blob.arrayBuffer():JSON.parse(await blob.text());
   if(record.type==='arraybuffer'&&(!record.key.includes(':')||record.key.endsWith(':recovery-base'))&&(value.byteLength<12||new DataView(value).getUint32(0,true)!==0x46546c67||new DataView(value).getUint32(4,true)!==2||new DataView(value).getUint32(8,true)!==value.byteLength))throw Error('Invalid GLB project in workspace');
   const key=nonce+record.key,tx=db.transaction('projects','readwrite'),done=complete(tx);tx.objectStore('projects').put(value,key);await done;staged.push([key,record.key]);
  }
  // Keep canonical projects unchanged until every binary record is staged and settings fit.
  for(const [storage,entries] of [[localStorage,header.local],[sessionStorage,header.session]])for(const [key,value] of entries){undo.push([storage,key,storage.getItem(key)]);storage.setItem(key,value);}
  const tx=db.transaction('projects','readwrite'),done=complete(tx),store=tx.objectStore('projects');
  for(const [temporary,key] of staged){const req=store.get(temporary);req.onsuccess=()=>{if(req.result===undefined){tx.abort();return;}store.put(req.result,key);store.delete(temporary);};}
  await done;
 }catch(error){
  for(const [storage,key,value] of undo.reverse())try{value===null?storage.removeItem(key):storage.setItem(key,value);}catch{}
  const tx=db.transaction('projects','readwrite'),done=complete(tx);for(const [key] of staged)tx.objectStore('projects').delete(key);await done.catch(()=>{});throw error;
 }finally{db.close();}
}
async function clearStaging(){
 const db=await database();try{const keys=await request(db.transaction('projects').objectStore('projects').getAllKeys());const tx=db.transaction('projects','readwrite'),done=complete(tx);for(const key of keys)if(typeof key==='string'&&key.startsWith(STAGE))tx.objectStore('projects').delete(key);await done;}finally{db.close();}
}
scope.APCWorkspace={validate,exportFile,importFile,readHeader};
if(typeof document==='undefined')return;
let busy=false;
async function prepare(){if(busy)throw Error('Finish the workspace transfer before leaving.');await scope.apcPrepareToLeave?.();}
scope.chrome?.webview?.addEventListener('message',async event=>{
 if(event.data?.type!=='prepare-close'||typeof event.data.id!=='string')return;
 try{await prepare();scope.chrome.webview.postMessage({type:'prepared',id:event.data.id,ok:true});}
 catch(error){scope.chrome.webview.postMessage({type:'prepared',id:event.data.id,ok:false,error:error.message});}
});
function mount(){
 cleanup=clearStaging().catch(()=>{});
 const nav=document.querySelector('#visualizerNav,body>header');if(!nav)return;
 const button=document.createElement('button');button.textContent='Workspace';button.type='button';button.style.marginLeft='auto';nav.append(button);
 const dialog=document.createElement('dialog');dialog.style.cssText='max-width:520px;background:#1d232c;color:#eef3f9;border:1px solid #445568;border-radius:12px;padding:24px;font:14px/1.6 Segoe UI,system-ui';
 dialog.innerHTML='<h2 style="margin-top:0">Your local workspace</h2><p>Move browser projects into Bridge, or keep a portable backup. Includes saved scenes, recovery, mapping, appearance and cached video. Nothing is uploaded.</p><p><strong>Moving from Chrome?</strong> Export here in the old browser, then import the file inside Bridge. The original browser data stays intact.</p><button id="workspaceExport">Export workspace</button> <button id="workspaceImport">Import workspace</button> <button id="workspaceClose">Close</button><input id="workspaceFile" type="file" accept=".apcworkspace" hidden><p id="workspaceStatus" role="status"></p>';
 document.body.append(dialog);const find=id=>dialog.querySelector('#'+id),status=find('workspaceStatus');
 button.onclick=()=>dialog.showModal();find('workspaceClose').onclick=()=>{if(!busy)dialog.close();};dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
 const setBusy=value=>{busy=value;for(const id of ['workspaceExport','workspaceImport','workspaceClose'])find(id).disabled=value;};
 find('workspaceExport').onclick=async()=>{
  try{await prepare();setBusy(true);status.textContent='Preparing local workspaceâ€¦';const blob=await exportFile(),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='APC40-workspace.apcworkspace';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),60000);status.textContent='Workspace exported. Keep this file private; it can contain your models and video.';}
  catch(error){status.textContent='Export failed: '+error.message;}finally{setBusy(false);}
 };
 find('workspaceImport').onclick=()=>find('workspaceFile').click();
 find('workspaceFile').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  if(!confirm('Import this local workspace? Matching projects and settings will be replaced. Export your current workspace first if you need a backup.')){event.target.value='';return;}
  try{setBusy(true);status.textContent='Importing local workspaceâ€¦';await importFile(file);location.reload();}
  catch(error){status.textContent='Import failed: '+error.message;event.target.value='';}finally{setBusy(false);}
 };
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})(typeof window==='undefined'?globalThis:window);
