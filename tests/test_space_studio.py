import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
VIEWER=ROOT/'bridge/visualizer'
spec=importlib.util.spec_from_file_location('model_convert',VIEWER/'model_convert.py')
convert=importlib.util.module_from_spec(spec);spec.loader.exec_module(convert)

class ConversionTest(unittest.TestCase):
    def test_missing_converter_is_actionable_without_running_anything(self):
        with patch.object(convert,'blender_path',return_value=None),patch.object(convert.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'blender.org'):convert.convert_model(b'BLENDER', '.blend')
            run.assert_not_called()

    def test_unsupported_and_empty_files_do_not_start_converter(self):
        with patch.object(convert.subprocess,'run') as run:
            for data,ext in [(b'x','.exe'),(b'','.blend')]:
                with self.assertRaises(ValueError):convert.convert_model(data,ext,executable='unused')
            run.assert_not_called()

    def test_conversion_disables_scripts_and_removes_temporary_files(self):
        visited=[]
        def fake_run(command,**kwargs):
            self.assertIn('--disable-autoexec',command)
            self.assertIn('--factory-startup',command)
            self.assertEqual(kwargs['timeout'],180)
            folder=Path(command[-1]).parent;visited.append(folder)
            script=(folder/'convert.py').read_text()
            self.assertIn('use_scripts=False',script)
            self.assertIn('export_extras=True',script)
            Path(command[-1]).write_bytes(b'glTF'+bytes(20))
            return subprocess.CompletedProcess(command,0)
        with patch.object(convert.subprocess,'run',side_effect=fake_run):
            self.assertTrue(convert.convert_model(b'BLENDER','.blend',executable='fake-blender').startswith(b'glTF'))
        self.assertFalse(visited[0].exists())

    def test_timeout_returns_clear_message(self):
        with patch.object(convert.subprocess,'run',side_effect=subprocess.TimeoutExpired('blender',180)):
            with self.assertRaisesRegex(RuntimeError,'stopped'):convert.convert_model(b'BLENDER','.blend',executable='fake-blender')

class EditorTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node checks local panel settings')
    def test_panel_preferences_accept_only_known_finite_numeric_fields(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
let saved='{"editorWidth":540,"treeRatio":70,"viewerWidth":"700px","mapperHeight":-1,"mapperWidth":1e309,"active":false}';
const context={window:{},localStorage:{getItem(key){assert.equal(key,'apc40-panel-layout:v1');return saved;}}};
vm.createContext(context);vm.runInContext(fs.readFileSync('bridge/visualizer/editor-project.js','utf8'),context);
const read=()=>JSON.parse(JSON.stringify(context.readPanelLayout()));
assert.deepEqual(read(),{editorWidth:540,treeRatio:70});
for(const value of ['null','[]','"text"','not json','{"editorWidth":0}']){saved=value;assert.deepEqual(read(),{});}
context.localStorage.getItem=()=>{throw Error('Storage blocked');};assert.deepEqual(read(),{});
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks room front geometry')
    def test_front_cut_clones_geometry_and_keeps_sides(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import path from 'node:path';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const T=await import(pathToFileURL(path.resolve('bridge/visualizer/editor-vendor/three.module.js')));
const context={window:{}};vm.createContext(context);vm.runInContext(fs.readFileSync('bridge/visualizer/editor-project.js','utf8'),context);
const root=new T.Group(),geometry=new T.BoxGeometry(2,2,.2),material=new T.MeshStandardMaterial();material.name='stena';const wall=new T.Mesh(geometry,material);wall.position.z=4.7;root.add(wall);
const removed=context.window.apcOpenFront(root,{axis:'z',min:4.7},{Vector3:T.Vector3});
assert.equal(removed,2);assert.equal(geometry.index.count,36);assert.equal(wall.geometry.index.count,30);assert.notEqual(wall.geometry,geometry);
assert.throws(()=>context.window.apcOpenFront(root,{axis:'q',min:4.7},{Vector3:T.Vector3}));
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks explicit outliner fold state')
    def test_selected_object_does_not_expand_closed_collection(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const source=fs.readFileSync('bridge/visualizer/editor.js','utf8');
const code=source.slice(source.indexOf('const collectionStateKey ='),source.indexOf('$("treeSearch").oninput'));
class Element {constructor(){this.children=[];this.style={};this.value='';}append(...items){this.children.push(...items);}replaceChildren(){this.children=[];}setAttribute(){} }
const controls={tree:new Element(),treeSearch:{value:''},selectionScope:{value:'All'},showHidden:new Element()};
const node={isMesh:true,name:'Wall',userData:{apcEditor:{editorVisible:true,active:true}}};
let saved=JSON.stringify({Environment:false});
const context={URLSearchParams,location:{search:''},localStorage:{getItem(){return saved;},setItem(key,value){saved=value;}},document:{createElement(){return new Element();}},$:id=>controls[id],root:{traverse(fn){fn(node);}},selected:node,objectCategory(){return 'Environment';},objectLabel(){return 'Wall';},meta:n=>n.userData.apcEditor,effective:()=>true,select(){},remember(){},changed(){}};
vm.createContext(context);vm.runInContext(code,context);context.refresh=()=>context.renderTree();context.renderTree();
assert.equal(controls.tree.children[0].open,false);
controls.treeSearch.value='Wall';context.renderTree();assert.equal(controls.tree.children[0].open,false);
const summary=controls.tree.children[0].children[0];summary.children[0].onclick({preventDefault(){},stopPropagation(){}});
assert.equal(controls.tree.children[0].open,false);
summary.onclick({target:{closest(){return null;}},preventDefault(){}});
context.renderTree();assert.equal(controls.tree.children[0].open,true);assert.equal(JSON.parse(saved).Environment,true);
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks object collections')
    def test_object_collections_preserve_model_metadata(self):
        script=r"""
import fs from 'node:fs';import assert from 'node:assert/strict';
const source=fs.readFileSync('bridge/visualizer/editor-model.js');
const {objectCategory,objectLabel}=await import('data:text/javascript;base64,'+source.toString('base64'));
const wall={name:'Plane.002',material:{name:'stěna'},userData:{}};
assert.equal(objectCategory(wall),'Environment');assert.equal(objectLabel(wall),'Wall · Plane.002');assert.equal(wall.name,'Plane.002');assert.deepEqual(wall.userData,{});
assert.equal(objectCategory({name:'FINAL mlha v prostoru',material:{name:'Volume'}}),'Helpers');
assert.equal(objectCategory({name:'Neon tube'}),'LEDs');
assert.equal(objectCategory({name:'Unknown',userData:{apcEditor:{type:'strip'}}}),'LEDs');
assert.equal(objectCategory({name:'Plane',userData:{apcEditor:{type:'projection'}}}),'Surfaces');
assert.equal(objectCategory({name:'Difuzor jemne pletivo'}),'Surfaces');
assert.equal(objectLabel({name:'STROP',material:{name:'stena'}}),'Ceiling · STROP');
assert.equal(objectCategory({name:'Imported sculpture'}),'Objects');
const {editorStyle,EDITOR_COLORS}=await import('data:text/javascript;base64,'+source.toString('base64'));
assert.equal(editorStyle(wall).color,EDITOR_COLORS.Walls);
assert.equal(editorStyle({name:'Plane',material:{name:'podlaha'}}).kind,'Floor');
assert.equal(editorStyle({name:'STROP',material:{name:'stena'}}).kind,'Ceiling');
assert.equal(editorStyle({name:'Leva hlava'}).color,editorStyle({name:'Prava hlava'}).color);
assert.equal(editorStyle({name:'Stropni retez'}).kind,'Rigging');
assert.equal(editorStyle({name:'Neon tube'}).kind,'LEDs');
assert.notEqual(EDITOR_COLORS.Floor,EDITOR_COLORS.Walls);assert.notEqual(EDITOR_COLORS.Decor,EDITOR_COLORS.LEDs);
assert.equal(wall.name,'Plane.002');assert.deepEqual(wall.userData,{});

"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks local storage keys')
    def test_local_store_keeps_project_compatibility_and_space_isolation(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const values=new Map();
const indexedDB={open(){const open={};queueMicrotask(()=>{open.result={close(){},transaction(){const tx={objectStore(){return {get(key){return request(key,false);},put(value,key){return request(key,true,value);}};}};function request(key,write,value){const req={};queueMicrotask(()=>{if(write)values.set(key,value);req.result=write?key:values.get(key);req.onsuccess();tx.oncomplete();});return req;}return tx;}};open.onsuccess();});return open;}};
const context={window:{},indexedDB,URLSearchParams,location:{search:'?space=led'}};vm.createContext(context);vm.runInContext(fs.readFileSync('bridge/visualizer/editor-project.js','utf8'),context);
await context.window.apcProjectStore('legacy-project');assert.equal(values.get('led'),'legacy-project');
await context.window.apcLocalStore('recovery-state',{version:1});assert.equal((await context.window.apcLocalStore('recovery-state')).version,1);
context.location.search='?space=projection';assert.equal(await context.window.apcProjectStore(),undefined);assert.equal(await context.window.apcLocalStore('recovery-state'),undefined);
context.location.search='?space=led';assert.equal(await context.window.apcProjectStore(),'legacy-project');
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks recovery hierarchy')
    def test_scene_recovery_keeps_ids_hierarchy_and_transforms(self):
        script=r"""
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const src=fs.readFileSync('bridge/visualizer/editor-model.js');const {sceneState,restoreSceneState,duplicateRow}=await import('data:text/javascript;base64,'+src.toString('base64'));
const T=await import(pathToFileURL(process.cwd()+'/bridge/visualizer/editor-vendor/three.module.js'));
const root=new T.Group(),group=new T.Group(),mesh=new T.Mesh(new T.BoxGeometry());root.add(group);group.add(mesh);root.traverse(n=>{n.userData.apcEditorId=n.uuid;n.userData.apcEditor={type:'room',pixels:1,rows:1};});
mesh.position.set(1,2,3);const state=sceneState(root);const baseline=root.clone(true);mesh.position.x=99;
restoreSceneState(root,state);assert.equal(mesh.position.x,1);assert.equal(mesh.parent,group);
const wrapper=new T.Group();wrapper.add(baseline);restoreSceneState(wrapper,state);assert.equal(wrapper.children.length,1);assert.equal(wrapper.children[0].children[0].position.z,3);
const bad=JSON.parse(JSON.stringify(state));bad.objects[0].parent=bad.objects[1].id;
assert.throws(()=>restoreSceneState(root,bad));assert.equal(mesh.parent,group);
const copies=duplicateRow(mesh,'x',3,1,T);const ids=[mesh,...copies].map(n=>n.userData.apcEditorId);assert.equal(new Set(ids).size,3);
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks physical dimensions and array spacing')
    def test_dimensions_and_row_under_transformed_parent(self):
        script=r"""
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const helpers=fs.readFileSync('bridge/visualizer/editor-model.js');const {dimensions,resizeDimension,duplicateRow}=await import('data:text/javascript;base64,'+helpers.toString('base64'));
const T=await import(pathToFileURL(process.cwd()+'/bridge/visualizer/editor-vendor/three.module.js'));
const parent=new T.Group();parent.scale.set(2,.5,3);parent.rotation.y=.7;
const mesh=new T.Mesh(new T.PlaneGeometry(2,1));mesh.rotation.z=.4;parent.add(mesh);
resizeDimension(mesh,'x',4,T);assert.ok(Math.abs(dimensions(mesh,T).x-4)<1e-6);
resizeDimension(mesh,'y',2,T);assert.ok(Math.abs(dimensions(mesh,T).y-2)<1e-6);
assert.throws(()=>resizeDimension(mesh,'z',1,T));assert.throws(()=>resizeDimension(mesh,'x',NaN,T));
const origin=mesh.getWorldPosition(new T.Vector3()),copies=duplicateRow(mesh,'x',4,1.25,T);
assert.equal(copies.length,3);copies.forEach((copy,i)=>{assert.ok(Math.abs(copy.getWorldPosition(new T.Vector3()).distanceTo(origin)-1.25*(i+1))<1e-6);assert.equal(copy.geometry,mesh.geometry);});
assert.throws(()=>duplicateRow(mesh,'x',500,1,T));assert.throws(()=>duplicateRow(mesh,'x',2,-1,T));
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_all_static_editor_controls_exist(self):
        html=(VIEWER/'editor.html').read_text(encoding='utf-8')
        js=(VIEWER/'editor.js').read_text(encoding='utf-8')
        ids=set(re.findall(r'id="([\w-]+)"',html))
        refs=set(re.findall(r"\$\([\"']([\w-]+)[\"']\)",js))
        self.assertFalse(refs-ids,refs-ids)

    def test_vendor_imports_are_local_and_complete(self):
        for path in (VIEWER/'editor-vendor').glob('*.js'):
            for relative in re.findall(r"^}?[ \t]*from [\'\"]([^\'\"]+)|^import .* from [\'\"]([^\'\"]+)",path.read_text(),re.M):
                name=next(x for x in relative if x)
                self.assertTrue(name.startswith('./'),(path,name))
                self.assertTrue((path.parent/name).is_file(),(path,name))

    @unittest.skipUnless(shutil.which('node'),'Node checks direct OBJ and GLB roundtrip')
    def test_obj_to_glb_preserves_project_metadata_and_hidden_objects(self):
        script = r"""
import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const base=process.cwd().replaceAll('\\','/')+'/bridge/visualizer/editor-vendor/';
const {OBJLoader}=await import(pathToFileURL(base+'OBJLoader.js'));
const {GLTFLoader}=await import(pathToFileURL(base+'GLTFLoader.js'));
const {GLTFExporter}=await import(pathToFileURL(base+'GLTFExporter.js'));
globalThis.FileReader=class{readAsArrayBuffer(blob){blob.arrayBuffer().then(data=>{this.result=data;this.onloadend?.();});}};
globalThis.ProgressEvent=class{constructor(type,props){Object.assign(this,props);}};
const object=new OBJLoader().parse('v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n');
object.children[0].visible=false;
object.children[0].userData.apcEditor={type:'panel',active:true,editorVisible:false,pixels:8,rows:4};
const glb=await new GLTFExporter().parseAsync(object,{binary:true,onlyVisible:false});
const result=await new GLTFLoader().parseAsync(glb,'');let mesh;result.scene.traverse(n=>{if(n.isMesh)mesh=n;});
assert.ok(mesh);assert.equal(mesh.userData.apcEditor.type,'panel');assert.equal(mesh.userData.apcEditor.editorVisible,false);assert.equal(mesh.userData.apcEditor.active,true);
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks timing and pivot transforms')
    def test_frame_phase_and_centered_pivot_preserve_world_geometry(self):
        script=r"""
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const src=fs.readFileSync('bridge/visualizer/editor-model.js');const {advanceFrame,centerPivot}=await import('data:text/javascript;base64,'+src.toString('base64'));
for(const hz of [60,120,144]){let last=0,count=0;for(let i=1;i<=hz*4;i++){const next=advanceFrame(i*1000/hz,last);if(next!==null){last=next;count++;}}assert.equal(count,120);}
const T=await import(pathToFileURL(process.cwd()+'/bridge/visualizer/editor-vendor/three.module.js'));
const root=new T.Group();root.position.set(3,4,5);root.rotation.y=.6;root.scale.set(2,.8,1.5);
const mesh=new T.Mesh(new T.BoxGeometry(2,1,3).translate(4,1,0));mesh.position.set(1,2,3);mesh.rotation.z=.4;root.add(mesh);root.updateMatrixWorld(true);
function points(){root.updateMatrixWorld(true);const p=mesh.geometry.getAttribute('position');return Array.from({length:p.count},(_,i)=>new T.Vector3().fromBufferAttribute(p,i).applyMatrix4(mesh.matrixWorld));}
const before=points(),center=new T.Box3().setFromObject(mesh).getCenter(new T.Vector3());const pivot=centerPivot(mesh,T);
assert.ok(pivot.getWorldPosition(new T.Vector3()).distanceTo(center)<1e-6);
points().forEach((p,i)=>assert.ok(p.distanceTo(before[i])<1e-6));
assert.equal(centerPivot(pivot,T),pivot);points().forEach((p,i)=>assert.ok(p.distanceTo(before[i])<1e-6));
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks local video cleanup')
    def test_local_video_releases_urls_and_returns_to_black(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const src=fs.readFileSync('bridge/visualizer/editor.js','utf8');let revoked=0,cleared=0,fail=false;
const context={URL:{createObjectURL:()=> 'blob:local',revokeObjectURL:()=>revoked++},video:{pause(){},load(){},removeAttribute(){},play(){return fail?Promise.reject(Error('codec')):Promise.resolve();}},videoFileUrl:null,media:null,restoring:true,storeView(){},testPattern:false,sourceUniform:{value:null},videoTexture:{},blackTexture:{},black:{width:256,height:256},blackContext:{fillRect(){cleared++;}},renderNeeded:false,message(){}};
vm.createContext(context);vm.runInContext(src.slice(src.indexOf('async function openVideoFile('),src.indexOf('async function startMedia(')),context);
await vm.runInContext('openVideoFile({})',context);assert.equal(context.sourceUniform.value,context.videoTexture);
vm.runInContext('stopMedia()',context);assert.equal(revoked,1);assert.equal(context.sourceUniform.value,context.blackTexture);assert.ok(cleared>0);
fail=true;await vm.runInContext('openVideoFile({})',context);assert.equal(revoked,2);assert.equal(context.videoFileUrl,null);
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node checks editor math and GLB project extras')
    def test_editor_validation_and_project_preview(self):
        script=r"""
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';
const text=fs.readFileSync('bridge/visualizer/editor-model.js','utf8');
const {validateObject,effective,sampleUV,COMPOSITION}=await import('data:text/javascript;base64,'+Buffer.from(text).toString('base64'));
assert.throws(()=>validateObject({type:'panel',pixels:4096,rows:2}));
assert.throws(()=>validateObject({type:'panel',pixels:NaN,rows:1}));
validateObject({type:'strip',pixels:60,rows:1});
const parent={userData:{apcEditor:{editorVisible:false,active:true}}};
const node={parent,userData:{apcEditor:{type:'panel',active:true,editorVisible:true,pixels:8,rows:4,source:'composition'}}};
assert.equal(effective(node,'editorVisible'),false);assert.equal(effective(node,'active'),true);
assert.deepEqual(sampleUV(COMPOSITION,0,0,1,1),[.5,.5]);
let material;const context={window:{},console};vm.createContext(context);
vm.runInContext(fs.readFileSync('bridge/visualizer/editor-project.js','utf8'),context);
node.isMesh=true;node.material={old:true};
const root={traverse:callback=>callback(node)};
class Material{constructor(options){Object.assign(this,options);material=this;}}
class Vector2{constructor(x,y){this.x=x;this.y=y;}}
context.window.applyAPCEditorProject(root,{Material,Vector2,map:{value:'input'},crop:{},fixtures:[]});
assert.equal(node.visible,true);assert.equal(material.uniforms.columns.value,8);
assert.equal(material.uniforms.map.value,'input');
parent.userData.apcEditor.active=false;
context.window.applyAPCEditorProject(root,{Material,Vector2,map:{value:'input'},crop:{},fixtures:[]});
assert.equal(node.visible,false);
parent.userData.apcEditor.active=true;node.userData.apcPreviewExcluded=true;context.window.applyAPCEditorProject(root,{Material,Vector2,map:{value:'input'},crop:{},fixtures:[]});assert.equal(node.visible,false);
console.log('Editor validation, UV sampling and preview inclusion passed');
"""
        result=subprocess.run(['node','--input-type=module','-e',script],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
