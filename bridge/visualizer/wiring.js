/* Physical groups come from explicit OUTPUT labels, never from Lumiverse IDs. */
(function(scope){
const outputs=Array.from({length:16},(_,i)=>({id:i+1,name:i<5?'1 m strips':i<11?'2 m strips':'5 m neons',pieces:i<5?10:i<11?5:4,meters:i<5?1:i<11?2:5,nominalPixels:i<5?60:i<11?120:1250}));
function validate(data){
 if(!data||data.version!==1||!Array.isArray(data.connections)||data.connections.length>10000)throw Error('Invalid wiring profile');
 const ids=new Set(),slots=new Set();
 const connections=data.connections.map(c=>{
  const profile=outputs.find(o=>o.id===c?.output);
  if(!c||typeof c.uid!=='string'||!c.uid||c.uid.length>200||!profile||!Number.isInteger(c.order)||c.order<1||c.order>profile.pieces||typeof c.reverse!=='boolean'||ids.has(c.uid)||slots.has(c.output+':'+c.order))throw Error('Invalid or duplicate wiring connection');
  ids.add(c.uid);slots.add(c.output+':'+c.order);return {uid:c.uid,output:c.output,order:c.order,reverse:c.reverse};
 });const groups=data.groups||[];
 if(!Array.isArray(groups)||groups.length>1000)throw Error('Invalid output groups');
 const keys=new Set();
 for(const g of groups){if(!g||typeof g.key!=='string'||!g.key||g.key.length>300||keys.has(g.key)||!Number.isInteger(g.output)||g.output<0||g.output>16)throw Error('Invalid output group');keys.add(g.key);}
 const result={version:1,connections,groups:groups.map(g=>({key:g.key,output:g.output}))};if(data.links!==undefined)result.links=validateLinks(connections,data.links);return result;
}
function validateLinks(connections,links){
 if(!Array.isArray(links)||links.length>10000)throw Error('Invalid cable links');
 const nodes=new Map(connections.map(c=>[c.uid,c])),outgoing=new Map(),incoming=new Set();
 const result=links.map(edge=>{
  const a=nodes.get(edge?.from),b=nodes.get(edge?.to);
  if(!a||!b||a.uid===b.uid||a.output!==b.output||b.order===1||outgoing.has(a.uid)||incoming.has(b.uid))throw Error('Connection needs a free input in the same output group');
  outgoing.set(a.uid,b.uid);incoming.add(b.uid);return{from:a.uid,to:b.uid};
 });
 for(const start of outgoing.keys()){const seen=new Set();let id=start;while(outgoing.has(id)){if(seen.has(id))throw Error('Cable loops are not allowed');seen.add(id);id=outgoing.get(id);}}
 return result;
}
function cableLinks(data){
 if(data.links!==undefined)return validateLinks(data.connections,data.links);
 const sorted=data.connections.slice().sort((a,b)=>a.output-b.output||a.order-b.order),links=[];
 for(let i=1;i<sorted.length;i++)if(sorted[i].output===sorted[i-1].output&&sorted[i].order===sorted[i-1].order+1)links.push({from:sorted[i-1].uid,to:sorted[i].uid});
 return links;
}
function linkedNodes(data){
 const edges=new Map(cableLinks(data).map(e=>[e.from,e.to])),linked=new Set();
 for(const root of data.connections.filter(c=>c.order===1)){let id=root.uid;while(id&&!linked.has(id)){linked.add(id);id=edges.get(id);}}
 return linked;
}
function ordered(data,fixtures){const byId=new Map(fixtures.map(f=>[f.sliceUid,f]));return validate(data).connections.sort((a,b)=>a.output-b.output||a.order-b.order).map(c=>({...c,fixture:byId.get(c.uid)||null}));}
function groupKey(f){return String(f.screenUid||f.screen||'Unknown output');}
function groupsFor(fixtures,data){
 const grouped=new Map();
 for(const f of fixtures){const key=groupKey(f);if(!grouped.has(key))grouped.set(key,{key,name:f.screen,fixtures:[]});grouped.get(key).fixtures.push(f);}
 return [...grouped.values()].map(g=>{const explicit=data.groups?.find(x=>x.key===g.key),match=/^OUTPUT\s+(\d+)\b/i.exec(g.name||''),id=match?Number(match[1]):0;return {...g,output:explicit?explicit.output:(outputs.some(o=>o.id===id)?id:0)};});
}
function reconcile(value,fixtures){
 const data=validate(value),connections=[],usedOutputs=new Set();
 for(const group of groupsFor(fixtures,data)){
  const profile=outputs.find(o=>o.id===group.output);if(!profile)continue;
  if(usedOutputs.has(profile.id))throw Error('Two groups cannot use the same physical output');usedOutputs.add(profile.id);
  const members=group.fixtures.slice(0,profile.pieces),reserved=new Set();
  for(const item of members){const old=data.connections.find(c=>c.uid===item.sliceUid&&c.output===profile.id);if(old&&!reserved.has(old.order)){reserved.add(old.order);connections.push({...old});}}
  for(const item of members){if(connections.some(c=>c.uid===item.sliceUid))continue;const order=Array.from({length:profile.pieces},(_,i)=>i+1).find(n=>!reserved.has(n));reserved.add(order);connections.push({uid:item.sliceUid,output:profile.id,order,reverse:data.connections.find(c=>c.uid===item.sliceUid)?.reverse||false});}
 }
 const ids=new Map(connections.map(c=>[c.uid,c]));const result={...data,connections};if(data.links!==undefined)result.links=data.links.filter(e=>ids.has(e.from)&&ids.has(e.to)&&ids.get(e.from).output===ids.get(e.to).output&&ids.get(e.to).order!==1);return validate(result);
}
scope.APCWiring={outputs,validate,ordered,groupKey,groupsFor,reconcile,validateLinks,cableLinks,linkedNodes,install};
function install(api){
 const el=tag=>document.createElement(tag),key=()=> 'apc40-wiring:'+(new URLSearchParams(location.search).get('space')||'default')+':'+api.layout().preset;
 let data={version:1,connections:[]},loadedKey=null,enabled=false,chains=[],focusUid=null,edges=[],linked=new Set(),graphOutput=null,graphDrag=null,graphNodes=[];
 const canvas=el('canvas'),ctx=canvas.getContext('2d');canvas.id='wiringOverlay';canvas.hidden=true;
 canvas.style.cssText='position:fixed;inset:0;pointer-events:none;z-index:3;width:100%;height:100%;display:none';document.body.append(canvas);
 const controlsPanel=el('div'),toggle=el('button'),branchChoice=el('select'),graphStatus=el('small');
 controlsPanel.id='wiringControls';controlsPanel.style.cssText='position:fixed;z-index:12;display:flex;flex-wrap:wrap;align-items:center;gap:6px;max-width:310px';
 toggle.id='wiringView';toggle.type='button';toggle.textContent='Wiring view';toggle.setAttribute('aria-pressed','false');
 const controlStyle='font:600 12px/1.4 "Segoe UI Variable Text","Segoe UI",system-ui,sans-serif;padding:8px 12px;background:#18232f;color:#dce6ef;border:1px solid #485b70;border-radius:7px;';toggle.style.cssText=branchChoice.style.cssText=controlStyle;
 branchChoice.id='wiringBranch';branchChoice.setAttribute('aria-label','Wiring output branch');branchChoice.hidden=true;graphStatus.style.cssText='display:none;flex-basis:100%;color:#afbfcc;font:11px/1.4 system-ui;background:#101820dc;padding:5px 8px;border-radius:5px';controlsPanel.append(toggle,branchChoice,graphStatus);document.body.append(controlsPanel);
 function placeControl(){const pause=document.getElementById('pausePreview');if(!pause)return;const r=pause.getBoundingClientRect();controlsPanel.style.left=r.left+'px';controlsPanel.style.top=(r.bottom+7)+'px';}
 toggle.onclick=()=>{if(enabled){closeGraph();clearFocus();}else openGraph(null);};
 branchChoice.onchange=()=>{graphOutput=branchChoice.value?Number(branchChoice.value):null;focusUid=null;showTool(false);};
 const box=el('section');box.id='wiringSettings';box.style.cssText='padding:12px 16px;border-top:1px solid #303b4b';
 const title=el('strong'),hint=el('p'),status=el('p');title.textContent='Physical output group';status.id='wiringStatus';status.setAttribute('role','status');
 hint.textContent='The whole group owns one physical output. Use fixture checkboxes or bulk selection to choose pieces in use today. Order and direction stay editable per piece.';
 const controls=el('div');controls.style.cssText='display:flex;gap:12px;flex-wrap:wrap;align-items:center';
 const output=el('span'),order=el('select'),reverse=el('input');output.id='wiringOutputLabel';order.id='wiringOrder';reverse.id='wiringReverse';reverse.type='checkbox';
 for(const [text,input] of [['Physical output',output],['Piece in chain',order],['Reverse IN / OUT',reverse]]){const label=el('label');label.append(text,' ',input);controls.append(label);}
 box.append(title,hint,controls,status);api.mapper.append(box);
 function option(select,value,text){const o=el('option');o.value=value;o.textContent=text;select.append(o);}
 function load(){if(loadedKey===key())return;loadedKey=key();data={version:1,connections:[]};try{const saved=localStorage.getItem(loadedKey);if(saved)data=validate(JSON.parse(saved));data=reconcile(data,api.layout().outputFixtures||[]);}catch(error){api.message('Wiring could not load: '+error.message);}}
 function save(next){try{next=reconcile(next,api.layout().outputFixtures||[]);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();api.changed?.();return true;}catch(error){api.message('Wiring was not saved: '+error.message);refresh();return false;}}
 function selected(){return (api.layout().outputFixtures||[]).find(f=>f.sliceUid===api.selected());}
 function refresh(){
  load();data=reconcile(data,api.layout().outputFixtures||[]);chains=ordered(data,api.layout().outputFixtures||[]);edges=cableLinks(data);linked=linkedNodes(data);
  const item=selected(),c=data.connections.find(c=>c.uid===item?.sliceUid),group=item?groupsFor(api.layout().outputFixtures||[],data).find(g=>g.key===groupKey(item)):null;
  const profile=outputs.find(o=>o.id===group?.output);output.textContent=group?.output?'OUT '+group.output:/^DMX\b/i.test(group?.name||'')?group.name+' (separate DMX)':'Not assigned at group level';reverse.checked=c?.reverse||false;order.replaceChildren();
  if(profile)for(let n=1;n<=profile.pieces;n++)option(order,n,n);order.value=c?.order||'';order.disabled=reverse.disabled=!c;
  const count=group?.fixtures.filter(f=>api.visible(f.sliceUid)).length||0;
  status.textContent=(item?(item.slice||item.sliceUid)+' | '+item.pixels+' actual pixels':'Select a fixture')+(group?' | '+count+' / '+group.fixtures.length+' pieces in use':'')+(c?' | piece '+c.order:'');
 }
 function groupControl(items){
  load();const group=groupsFor(items,data)[0];if(/^DMX\b/i.test(group.name||'')){const info=el('small');info.textContent='Separate DMX output - 512 channels';return info;}const select=el('select');select.className='physicalGroup';select.setAttribute('aria-label','Physical output for '+group.name);
  option(select,0,'Unassigned group');outputs.forEach(o=>option(select,o.id,'OUT '+o.id+' | '+o.pieces+' x '+o.meters+' m'));
  select.value=group.output;select.onclick=e=>e.stopPropagation();select.onchange=()=>save({...data,groups:[...data.groups.filter(g=>g.key!==group.key),{key:group.key,output:Number(select.value)}]});
  const wrapper=el('div'),edit=el('button');edit.textContent='Edit chain';edit.disabled=!group.output;edit.onclick=()=>openGraph(group.output);wrapper.style.cssText='display:flex;gap:6px';wrapper.append(select,edit);return wrapper;
 }
 function change(){
  const item=selected(),current=data.connections.find(c=>c.uid===item?.sliceUid);if(!current)return;
  const target=Number(order.value);
  save({...data,connections:data.connections.map(c=>c.uid===current.uid?{...c,order:target,reverse:reverse.checked}:c.output===current.output&&c.order===target?{...c,order:current.order}:c)});
 }
 order.onchange=reverse.onchange=change;api.mapper.addEventListener('click',event=>{if(!box.contains(event.target))refresh();});
 const tool=el('div'),flip=el('button');tool.id='fixtureDirectionTool';tool.hidden=true;tool.style.cssText='position:fixed;z-index:4;padding:6px;background:#101820ee;border:1px solid #ff9b38;border-radius:8px;display:none';
 const editChain=el('button');editChain.textContent='Edit chain';editChain.onclick=()=>{const c=data.connections.find(c=>c.uid===focusUid);if(c)openGraph(c.output);};tool.append(editChain);flip.textContent='Reverse direction';flip.id='reverseFixture';tool.title='Double-click empty space or press Escape to dismiss';tool.append(flip);document.body.append(tool);
 function setOverlay(show){canvas.hidden=!show;canvas.style.display=show?'block':'none';}
 function showTool(show){tool.hidden=!show;tool.style.display=show?'flex':'none';}
 function clearFocus(){focusUid=null;showTool(false);setOverlay(enabled);ctx.clearRect(0,0,canvas.width,canvas.height);api.select?.(null);}
 document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(graphDrag){save({...data,links:graphDrag.previous});graphDrag=null;}else clearFocus();}});
 flip.onclick=()=>{const current=data.connections.find(c=>c.uid===focusUid);if(current)save({...data,connections:data.connections.map(c=>c.uid===focusUid?{...c,reverse:!c.reverse}:c)});};
 api.canvas.addEventListener('dblclick',event=>{
  if(api.isMapping?.())return;let uid=null,best=14;
  for(const fixture of api.layout().fixtures||[]){if(!api.visible(fixture.sliceUid))continue;const points=api.positions(fixture.sliceUid)||[],stride=Math.max(1,Math.ceil(points.length/100));
   for(let i=0;i<points.length;i+=stride){const point=api.project(points[i]);if(!point)continue;const d=Math.hypot(event.clientX-point[0],event.clientY-point[1]);if(d<best){best=d;uid=fixture.sliceUid;}}
  }
  if(!uid){clearFocus();return;}focusUid=uid;if(enabled){graphOutput=data.connections.find(c=>c.uid===uid)?.output??null;branchChoice.value=graphOutput||'';}api.select?.(uid);refresh();setOverlay(true);
 });

 function openGraph(output){
  api.leaveMapping?.();if(output===null&&focusUid)output=data.connections.find(c=>c.uid===focusUid)?.output??null;enabled=true;graphOutput=output;graphDrag=null;toggle.setAttribute('aria-pressed','true');toggle.style.borderColor='#72c5af';
  branchChoice.hidden=false;branchChoice.replaceChildren();option(branchChoice,'','All outputs');
  for(const id of [...new Set(data.connections.map(c=>c.output))].sort((a,b)=>a-b))option(branchChoice,id,'OUT '+id);
  branchChoice.value=output||'';graphStatus.style.display='block';graphStatus.textContent='Drag OUT to IN. Grab connected IN to unplug. Esc cancels.';setOverlay(true);
 }
 function closeGraph(){
  if(graphDrag){save({...data,links:graphDrag.previous});graphDrag=null;}
  enabled=false;graphOutput=null;toggle.setAttribute('aria-pressed','false');toggle.style.borderColor='#485b70';branchChoice.hidden=true;graphStatus.style.display='none';setOverlay(false);api.canvas.style.cursor='';
 }
 function hitPort(x,y,inputOnly=false){let hit=null,best=inputOnly?25:10;
  for(const n of graphNodes)for(const input of inputOnly?[true]:[true,false]){const p=input?n.input:n.outputPort;if(!p)continue;const d=Math.hypot(x-p[0],y-p[1]);if(d<best){best=d;hit={node:n,input,point:p};}}return hit;
 }
 function candidate(from,to){const next=edges.filter(e=>e.from!==from&&e.to!==to);next.push({from,to});try{validateLinks(data.connections,next);return{valid:true,links:next};}catch(error){return{valid:false,message:error.message};}}
 api.canvas.addEventListener('pointerdown',event=>{
  if(!enabled||api.isMapping?.()||event.button!==0)return;const hit=hitPort(event.clientX,event.clientY);if(!hit)return;
  event.preventDefault();event.stopImmediatePropagation();
  const previous=edges.map(e=>({...e})),old=hit.input?edges.find(e=>e.to===hit.node.uid):edges.find(e=>e.from===hit.node.uid),from=hit.input?old?.from:hit.node.uid;
  if(!from){graphStatus.textContent=hit.node.order===1?'The first input belongs to the physical output.':'Start a cable from an OUT port.';return;}
  if(!graphNodes.some(n=>n.uid===from&&n.outputPort)){graphStatus.textContent='The previous piece has no known 3D position.';return;}
  if(old&&!save({...data,links:edges.filter(e=>e!==old)}))return;
  graphOutput=hit.node.output;branchChoice.value=graphOutput;focusUid=hit.node.uid;api.select?.(hit.node.uid);graphDrag={from,x:event.clientX,y:event.clientY,target:null,valid:false,previous};api.canvas.setPointerCapture(event.pointerId);showTool(false);
 },true);
 api.canvas.addEventListener('pointermove',event=>{
  if(!enabled)return;
  if(!graphDrag){api.canvas.style.cursor=hitPort(event.clientX,event.clientY)?'pointer':'';return;}
  event.preventDefault();event.stopImmediatePropagation();Object.assign(graphDrag,{x:event.clientX,y:event.clientY,target:null,valid:false});
  const hit=hitPort(event.clientX,event.clientY,true);
  if(hit&&hit.node.output===graphOutput){graphDrag.target=hit.node.uid;const result=candidate(graphDrag.from,hit.node.uid);graphDrag.valid=result.valid;graphDrag.links=result.links;graphStatus.textContent=result.valid?'Release to connect.':result.message;}
  else graphStatus.textContent='Release in empty space to leave the cable unplugged.';
 },true);
 api.canvas.addEventListener('pointerup',event=>{
  if(!graphDrag)return;event.preventDefault();event.stopImmediatePropagation();const drag=graphDrag;graphDrag=null;if(drag.target&&drag.valid)save({...data,links:drag.links});
  graphStatus.textContent=drag.target&&drag.valid?'Connected. Saved locally.':'Cable unplugged. Saved locally.';if(api.canvas.hasPointerCapture(event.pointerId))api.canvas.releasePointerCapture(event.pointerId);
 },true);
 api.canvas.addEventListener('pointercancel',()=>{if(graphDrag)save({...data,links:graphDrag.previous});graphDrag=null;});
 function portPosition(a,b){if(!a)return null;const dx=(b?.[0]??a[0]+1)-a[0],dy=(b?.[1]??a[1])-a[1],length=Math.hypot(dx,dy)||1;return[a[0]+dy/length*5,a[1]-dx/length*5];}
 function cable(a,b,color,dashed=false){if(!a||!b)return;const bend=Math.max(25,Math.min(100,Math.abs(b[0]-a[0])*.4));ctx.strokeStyle=color;ctx.lineWidth=1.8;ctx.setLineDash(dashed?[5,4]:[]);ctx.beginPath();ctx.moveTo(...a);ctx.bezierCurveTo(a[0]+bend,a[1],b[0]-bend,b[1],...b);ctx.stroke();ctx.setLineDash([]);}
 function arrow(a,b,color,dashed=false,head=true){
  if(!a||!b)return;ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=dashed?1.5:3;ctx.setLineDash(dashed?[5,5]:[]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);if(!head||Math.hypot(b[0]-a[0],b[1]-a[1])<2)return;
  const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);ctx.beginPath();ctx.moveTo(...b);ctx.lineTo(b[0]-9*Math.cos(angle-.45),b[1]-9*Math.sin(angle-.45));ctx.lineTo(b[0]-9*Math.cos(angle+.45),b[1]-9*Math.sin(angle+.45));ctx.closePath();ctx.fill();
 }
 function label(text,p,color){if(!p)return;ctx.font='12px system-ui';const w=ctx.measureText(text).width;ctx.fillStyle='#101820e8';ctx.fillRect(p[0]+5,p[1]-17,w+10,19);ctx.fillStyle=color;ctx.fillText(text,p[0]+10,p[1]-3);}
 function draw(){
  const mapping=api.isMapping?.();controlsPanel.hidden=!!mapping;controlsPanel.style.display=mapping?'none':'flex';
  if(mapping){if(enabled)closeGraph();focusUid=null;setOverlay(false);showTool(false);api.canvas.style.filter='';api.setWiring(false);return;}
  setOverlay(enabled||!!focusUid);api.canvas.style.filter='';api.setWiring(false);
  if(!enabled&&!focusUid)return;
  const width=innerWidth,height=innerHeight;if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}ctx.clearRect(0,0,width,height);showTool(false);graphNodes=[];
  for(const c of chains){
   if(enabled&&graphOutput!==null&&c.output!==graphOutput)continue;if(!enabled&&c.uid!==focusUid)continue;
   const positions=api.positions(c.uid);if(!c.fixture||!positions||positions.length<2||!api.visible(c.uid))continue;
   const points=[],stride=Math.max(1,Math.ceil((positions.length-1)/48));for(let n=0;n<positions.length;n+=stride)points.push(api.project(positions[n]));if((positions.length-1)%stride!==0)points.push(api.project(positions[positions.length-1]));if(c.reverse)points.reverse();
   const first=points[0],last=points.at(-1),input=portPosition(first,points[1]),outputPort=portPosition(last,points.at(-2));graphNodes.push({...c,input,outputPort});
   if(c.uid===focusUid&&!graphDrag){for(let n=1;n<points.length;n++)arrow(points[n-1],points[n],'#ff9b38',false,n===points.length-1);label('IN',first,'#51f29b');label('OUT',last,'#ff6475');const middle=points[Math.floor(points.length/2)];if(middle){showTool(true);tool.style.left=Math.max(10,Math.min(width-290,middle[0]+10))+'px';tool.style.top=Math.max(65,Math.min(height-50,middle[1]+10))+'px';flip.textContent='Reverse direction'+(c.reverse?' (reversed)':'');}}
  }
  if(enabled){
   const nodes=new Map(graphNodes.map(n=>[n.uid,n]));for(const e of edges){const a=nodes.get(e.from),b=nodes.get(e.to);if(a&&b)cable(a.outputPort,b.input,linked.has(e.from)?'#72cdb2':'#7a8797');}
   for(const n of graphNodes)for(const [input,p] of [[true,n.input],[false,n.outputPort]]){if(!p)continue;ctx.fillStyle=input?(linked.has(n.uid)?'#71d6b3':'#8b97a6'):'#df8e89';if(graphDrag?.target===n.uid&&input)ctx.fillStyle=graphDrag.valid?'#81f5bc':'#ff686f';ctx.strokeStyle='#101820';ctx.lineWidth=1;ctx.fillRect(p[0]-4,p[1]-4,8,8);ctx.strokeRect(p[0]-4,p[1]-4,8,8);}
   if(graphDrag){const from=nodes.get(graphDrag.from),target=nodes.get(graphDrag.target);if(from)cable(from.outputPort,target?.input||[graphDrag.x,graphDrag.y],graphDrag.target?(graphDrag.valid?'#81f5bc':'#ff686f'):'#d4ba83',true);}
  }
 }
 refresh();return {draw,refresh,groupControl,placeControl,hasSignal:uid=>!data.connections.some(c=>c.uid===uid)||linked.has(uid),pixelIndex:(uid,index,count)=>data.connections.find(c=>c.uid===uid)?.reverse?count-1-index:index,export:()=>{load();return validate(data);},import:value=>{const next=reconcile(value,api.layout().outputFixtures||[]);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();api.changed?.();}};
}
})(typeof window==='undefined'?globalThis:window);

