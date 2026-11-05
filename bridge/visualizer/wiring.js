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
 return {version:1,connections,groups:groups.map(g=>({key:g.key,output:g.output}))};
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
 return validate({...data,connections});
}
scope.APCWiring={outputs,validate,ordered,groupKey,groupsFor,reconcile,install};
function install(api){
 const el=tag=>document.createElement(tag),key=()=> 'apc40-wiring:'+(new URLSearchParams(location.search).get('space')||'default')+':'+api.layout().preset;
 let data={version:1,connections:[]},loadedKey=null,enabled=false,chains=[],focusUid=null;
 const canvas=el('canvas'),ctx=canvas.getContext('2d');canvas.id='wiringOverlay';canvas.hidden=true;
 canvas.style.cssText='position:fixed;inset:0;pointer-events:none;z-index:3;width:100%;height:100%';document.body.append(canvas);
 const toggleLabel=el('label'),toggle=el('input');toggle.id='wiringView';toggle.type='checkbox';toggleLabel.append(toggle,' Wiring view');toggleLabel.style.cssText='margin-left:auto;white-space:nowrap';api.navigation.append(toggleLabel);
 toggle.onchange=()=>{enabled=toggle.checked;canvas.hidden=!enabled&&!focusUid;api.canvas.style.filter=enabled?'grayscale(1) brightness(.45)':'';api.setWiring(enabled);refresh();};
 const box=el('section');box.id='wiringSettings';box.style.cssText='padding:12px 16px;border-top:1px solid #303b4b';
 const title=el('strong'),hint=el('p'),status=el('p');title.textContent='Physical output group';status.id='wiringStatus';status.setAttribute('role','status');
 hint.textContent='The whole group owns one physical output. Use fixture checkboxes or bulk selection to choose pieces in use today. Order and direction stay editable per piece.';
 const controls=el('div');controls.style.cssText='display:flex;gap:12px;flex-wrap:wrap;align-items:center';
 const output=el('span'),order=el('select'),reverse=el('input');output.id='wiringOutputLabel';order.id='wiringOrder';reverse.id='wiringReverse';reverse.type='checkbox';
 for(const [text,input] of [['Physical output',output],['Piece in chain',order],['Reverse IN / OUT',reverse]]){const label=el('label');label.append(text,' ',input);controls.append(label);}
 box.append(title,hint,controls,status);api.mapper.append(box);
 function option(select,value,text){const o=el('option');o.value=value;o.textContent=text;select.append(o);}
 function load(){if(loadedKey===key())return;loadedKey=key();data={version:1,connections:[]};try{const saved=localStorage.getItem(loadedKey);if(saved)data=validate(JSON.parse(saved));data=reconcile(data,api.layout().outputFixtures||[]);}catch(error){api.message('Wiring could not load: '+error.message);}}
 function save(next){try{next=reconcile(next,api.layout().outputFixtures||[]);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();api.changed?.();}catch(error){api.message('Wiring was not saved: '+error.message);refresh();}}
 function selected(){return (api.layout().outputFixtures||[]).find(f=>f.sliceUid===api.selected());}
 function refresh(){
  load();data=reconcile(data,api.layout().outputFixtures||[]);chains=ordered(data,api.layout().outputFixtures||[]);
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
  return select;
 }
 function change(){
  const item=selected(),current=data.connections.find(c=>c.uid===item?.sliceUid);if(!current)return;
  const target=Number(order.value);
  save({...data,connections:data.connections.map(c=>c.uid===current.uid?{...c,order:target,reverse:reverse.checked}:c.output===current.output&&c.order===target?{...c,order:current.order}:c)});
 }
 order.onchange=reverse.onchange=change;api.mapper.addEventListener('click',event=>{if(!box.contains(event.target))refresh();});
 const tool=el('div'),flip=el('button');tool.id='fixtureDirectionTool';tool.hidden=true;tool.style.cssText='position:fixed;z-index:4;padding:6px;background:#101820ee;border:1px solid #ff9b38;border-radius:8px;display:none';
 flip.textContent='Reverse direction';flip.id='reverseFixture';tool.title='Double-click empty space or press Escape to dismiss';tool.append(flip);document.body.append(tool);
 function showTool(show){tool.hidden=!show;tool.style.display=show?'flex':'none';}
 function clearFocus(){focusUid=null;showTool(false);canvas.hidden=!enabled;ctx.clearRect(0,0,canvas.width,canvas.height);api.select?.(null);}
 document.addEventListener('keydown',event=>{if(event.key==='Escape')clearFocus();});
 flip.onclick=()=>{const current=data.connections.find(c=>c.uid===focusUid);if(current)save({...data,connections:data.connections.map(c=>c.uid===focusUid?{...c,reverse:!c.reverse}:c)});};
 api.canvas.addEventListener('dblclick',event=>{
  if(api.isMapping?.())return;let uid=null,best=14;
  for(const fixture of api.layout().fixtures||[]){if(!api.visible(fixture.sliceUid))continue;const points=api.positions(fixture.sliceUid)||[],stride=Math.max(1,Math.ceil(points.length/100));
   for(let i=0;i<points.length;i+=stride){const point=api.project(points[i]);if(!point)continue;const d=Math.hypot(event.clientX-point[0],event.clientY-point[1]);if(d<best){best=d;uid=fixture.sliceUid;}}
  }
  if(!uid){clearFocus();return;}focusUid=uid;api.select?.(uid);refresh();canvas.hidden=false;
 });
 function arrow(a,b,color,dashed=false,head=true){
  if(!a||!b)return;ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=dashed?1.5:3;ctx.setLineDash(dashed?[5,5]:[]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);if(!head||Math.hypot(b[0]-a[0],b[1]-a[1])<2)return;
  const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);ctx.beginPath();ctx.moveTo(...b);ctx.lineTo(b[0]-9*Math.cos(angle-.45),b[1]-9*Math.sin(angle-.45));ctx.lineTo(b[0]-9*Math.cos(angle+.45),b[1]-9*Math.sin(angle+.45));ctx.closePath();ctx.fill();
 }
 function label(text,p,color){if(!p)return;ctx.font='12px system-ui';const w=ctx.measureText(text).width;ctx.fillStyle='#101820e8';ctx.fillRect(p[0]+5,p[1]-17,w+10,19);ctx.fillStyle=color;ctx.fillText(text,p[0]+10,p[1]-3);}
 function draw(){
  if(!enabled&&!focusUid)return;api.setWiring(enabled);const width=innerWidth,height=innerHeight;if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}ctx.clearRect(0,0,width,height);
  let previous=null,drawn=0;
  showTool(false);
  for(const c of chains){
   if(!enabled&&c.uid!==focusUid)continue;
   const positions=api.positions(c.uid),color=c.uid===focusUid?'#ff9b38':'hsl('+((c.output-1)*137.5%360)+' 85% 70%)';
   if(!c.fixture||!positions||positions.length<2||!api.visible(c.uid)){previous=null;continue;}
   const points=[],stride=Math.max(1,Math.ceil((positions.length-1)/48));for(let n=0;n<positions.length;n+=stride)points.push(api.project(positions[n]));points.push(api.project(positions[positions.length-1]));if(c.reverse)points.reverse();
   const first=points[0],last=points[points.length-1];if(previous?.output===c.output&&previous.order+1===c.order)arrow(previous.end,first,color,true);
   for(let n=1;n<points.length;n++)arrow(points[n-1],points[n],color,false,n===Math.floor(points.length/2)||n===points.length-1);
   if(c.uid===focusUid){
    label('IN',first,'#51f29b');label('OUT',last,'#ff6475');
    if(first&&points[1])arrow(first,points[1],'#51f29b');if(last&&points[points.length-2])arrow(points[points.length-2],last,'#ff6475');
    const middle=points[Math.floor(points.length/2)];if(middle){showTool(true);tool.style.left=Math.max(10,Math.min(width-210,middle[0]+10))+'px';tool.style.top=Math.max(60,Math.min(height-50,middle[1]+10))+'px';flip.textContent='Reverse direction'+(c.reverse?' (reversed)':'');}
   }else{label('OUT '+c.output+' | '+c.order+' IN',first,color);label('OUT',last,color);}
   previous={output:c.output,order:c.order,end:last};drawn++;
  }
  if(enabled)label(drawn?'WIRING VIEW | configured pixel direction':'WIRING VIEW | assign physical outputs in Output mapping',[340,70],'#edf2f7');
 }
 refresh();return {draw,refresh,groupControl,pixelIndex:(uid,index,count)=>data.connections.find(c=>c.uid===uid)?.reverse?count-1-index:index,export:()=>{load();return validate(data);},import:value=>{const next=reconcile(value,api.layout().outputFixtures||[]);localStorage.setItem(key(),JSON.stringify(next));data=next;refresh();api.changed?.();}};
}
})(typeof window==='undefined'?globalThis:window);

