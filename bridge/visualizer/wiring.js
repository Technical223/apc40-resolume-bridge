/* A Lumiverse is not a physical controller socket: cable order is explicit. */
(function(scope){
const outputs=Array.from({length:16},(_,i)=>({id:i+1,name:i<5?'1 m strips':i<11?'2 m strips':'5 m neons',pieces:i<5?10:i<11?5:4,meters:i<5?1:i<11?2:5,nominalPixels:i<5?60:i<11?120:1250}));
function validate(data){
 if(!data||data.version!==1||!Array.isArray(data.connections)||data.connections.length>10000)throw Error('Invalid wiring profile');
 const ids=new Set(),slots=new Set();
 const connections=data.connections.map(c=>{
  const profile=outputs.find(o=>o.id===c?.output);
  if(!c||typeof c.uid!=='string'||!c.uid||c.uid.length>200||!profile||!Number.isInteger(c.order)||c.order<1||c.order>profile.pieces||typeof c.reverse!=='boolean'||ids.has(c.uid)||slots.has(c.output+':'+c.order))throw Error('Invalid or duplicate wiring connection');
  ids.add(c.uid);slots.add(c.output+':'+c.order);return {uid:c.uid,output:c.output,order:c.order,reverse:c.reverse};
 });return {version:1,connections};
}
function ordered(data,fixtures){const byId=new Map(fixtures.map(f=>[f.sliceUid,f]));return validate(data).connections.sort((a,b)=>a.output-b.output||a.order-b.order).map(c=>({...c,fixture:byId.get(c.uid)||null}));}
scope.APCWiring={outputs,validate,ordered,install};
function install(api){
 const el=tag=>document.createElement(tag),key=()=> 'apc40-wiring:'+(new URLSearchParams(location.search).get('space')||'default')+':'+api.layout().preset;
 let data={version:1,connections:[]},loadedKey=null,enabled=false,chains=[];
 const canvas=el('canvas'),ctx=canvas.getContext('2d');canvas.id='wiringOverlay';canvas.hidden=true;
 canvas.style.cssText='position:fixed;inset:0;pointer-events:none;z-index:3;width:100%;height:100%';document.body.append(canvas);
 const toggleLabel=el('label'),toggle=el('input');toggle.id='wiringView';toggle.type='checkbox';toggleLabel.append(toggle,' Wiring view');toggleLabel.style.cssText='margin-left:auto;white-space:nowrap';api.navigation.append(toggleLabel);
 toggle.onchange=()=>{enabled=toggle.checked;canvas.hidden=!enabled;api.canvas.style.filter=enabled?'grayscale(1) brightness(.45)':'';api.setWiring(enabled);refresh();};
 const box=el('section');box.id='wiringSettings';box.style.cssText='padding:12px 16px;border-top:1px solid #303b4b';
 const title=el('strong'),hint=el('p'),status=el('p');title.textContent='Physical wiring Â· selected fixture';status.id='wiringStatus';status.setAttribute('role','status');
 hint.textContent='Select a fixture, then choose its physical socket and position. Lumiverse IDs do not define cable order. Changes save locally; no DMX is sent.';
 const controls=el('div');controls.style.cssText='display:flex;gap:12px;flex-wrap:wrap;align-items:center';
 const output=el('select'),order=el('select'),reverse=el('input'),remove=el('button');output.id='wiringOutput';order.id='wiringOrder';reverse.id='wiringReverse';reverse.type='checkbox';
 for(const [text,input] of [['Physical output',output],['Piece in chain',order],['Reverse IN / OUT',reverse]]){const label=el('label');label.append(text,' ',input);controls.append(label);}
 remove.textContent='Unassign';controls.append(remove);const dmx=el('p');dmx.textContent='DMX is separate: 4 outputs × 512 channels. These assignments never change DMX addressing.';box.append(title,hint,controls,status,dmx);api.mapper.append(box);
 function option(select,value,text){const o=el('option');o.value=value;o.textContent=text;select.append(o);}
 option(output,'','Unassigned');outputs.forEach(o=>option(output,o.id,'OUT '+o.id+' Â· '+o.pieces+' Ă— '+o.meters+' m Â· '+o.name));
 function load(){if(loadedKey===key())return;loadedKey=key();data={version:1,connections:[]};try{const saved=localStorage.getItem(loadedKey);if(saved)data=validate(JSON.parse(saved));}catch(error){api.message('Wiring could not load: '+error.message);}}
 function save(next){try{next=validate(next);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();}catch(error){api.message('Wiring was not saved: '+error.message);refresh();}}
 function selected(){return (api.layout().outputFixtures||[]).find(f=>f.sliceUid===api.selected());}
 function refresh(){
  load();chains=ordered(data,api.layout().outputFixtures||[]);const item=selected(),c=data.connections.find(c=>c.uid===item?.sliceUid),profile=outputs.find(o=>o.id===c?.output);
  output.disabled=order.disabled=reverse.disabled=remove.disabled=!item;output.value=c?.output||'';reverse.checked=c?.reverse||false;order.replaceChildren();
  if(profile)for(let n=1;n<=profile.pieces;n++)option(order,n,n);order.value=c?.order||'';order.disabled=reverse.disabled=!c;
  const modeled=data.connections.filter(c=>api.positions(c.uid)?.length>1).length;
  status.textContent=(item?(item.slice||item.sliceUid)+' Â· '+item.pixels+' actual pixels':'Select a fixture')+' Â· '+data.connections.length+' assigned / '+modeled+' with 3D positions'+(c?' Â· OUT '+c.output+' / piece '+c.order+' Â· nominal '+profile.nominalPixels+' px':'');
 }
 output.onchange=()=>{
  const item=selected();if(!item)return;const next=data.connections.filter(c=>c.uid!==item.sliceUid),id=Number(output.value);
  if(id){const profile=outputs.find(o=>o.id===id),used=new Set(next.filter(c=>c.output===id).map(c=>c.order)),free=Array.from({length:profile.pieces},(_,i)=>i+1).find(n=>!used.has(n));
   if(!free){api.message('This output has no free piece slots.');refresh();return;}next.push({uid:item.sliceUid,output:id,order:free,reverse:false});}
  save({version:1,connections:next});
 };
 function change(){
  const item=selected(),current=data.connections.find(c=>c.uid===item?.sliceUid);if(!current)return;
  const target=Number(order.value);
  save({version:1,connections:data.connections.map(c=>c.uid===current.uid?{...c,order:target,reverse:reverse.checked}:c.output===current.output&&c.order===target?{...c,order:current.order}:c)});
 }
 order.onchange=reverse.onchange=change;remove.onclick=()=>{output.value='';output.onchange();};api.mapper.addEventListener('click',event=>{if(!box.contains(event.target))refresh();});
 function arrow(a,b,color,dashed=false,head=true){
  if(!a||!b)return;ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=dashed?1.5:3;ctx.setLineDash(dashed?[5,5]:[]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);if(!head||Math.hypot(b[0]-a[0],b[1]-a[1])<2)return;
  const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);ctx.beginPath();ctx.moveTo(...b);ctx.lineTo(b[0]-9*Math.cos(angle-.45),b[1]-9*Math.sin(angle-.45));ctx.lineTo(b[0]-9*Math.cos(angle+.45),b[1]-9*Math.sin(angle+.45));ctx.closePath();ctx.fill();
 }
 function label(text,p,color){if(!p)return;ctx.font='12px system-ui';const w=ctx.measureText(text).width;ctx.fillStyle='#101820e8';ctx.fillRect(p[0]+5,p[1]-17,w+10,19);ctx.fillStyle=color;ctx.fillText(text,p[0]+10,p[1]-3);}
 function draw(){
  if(!enabled)return;api.setWiring(true);const width=innerWidth,height=innerHeight;if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}ctx.clearRect(0,0,width,height);
  let previous=null,drawn=0;
  for(const c of chains){
   const positions=api.positions(c.uid),color='hsl('+((c.output-1)*137.5%360)+' 85% 70%)';
   if(!c.fixture||!positions||positions.length<2||!api.visible(c.uid)){previous=null;continue;}
   const points=[],stride=Math.max(1,Math.ceil((positions.length-1)/48));for(let n=0;n<positions.length;n+=stride)points.push(api.project(positions[n]));points.push(api.project(positions[positions.length-1]));if(c.reverse)points.reverse();
   const first=points[0],last=points[points.length-1];if(previous?.output===c.output&&previous.order+1===c.order)arrow(previous.end,first,color,true);
   for(let n=1;n<points.length;n++)arrow(points[n-1],points[n],color,false,n===Math.floor(points.length/2)||n===points.length-1);
   label('OUT '+c.output+' Â· '+c.order+' IN',first,color);label('OUT',last,color);previous={output:c.output,order:c.order,end:last};drawn++;
  }
  label(drawn?'WIRING VIEW Â· configured pixel direction':'WIRING VIEW Â· assign physical outputs in Output mapping',[340,70],'#edf2f7');
 }
 refresh();return {draw,refresh,export:()=>{load();return validate(data);},import:value=>{const next=validate(value);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();}};
}
})(typeof window==='undefined'?globalThis:window);

