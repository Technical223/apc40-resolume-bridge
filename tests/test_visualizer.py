import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
VIEWER=ROOT/'bridge/visualizer'

class MappingTest(unittest.TestCase):
    def test_output_names_lumiverse_and_changed_counts(self):
        spec=importlib.util.spec_from_file_location('viewer_prepare',VIEWER/'prepare.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);module.HOME=home
            (home/'physical-layout.json').write_text(json.dumps({'fixtures':[],'camera':{}}))
            source=home/'output.xml';module.source_paths=lambda space=None:(source,source,'Test preset')
            for count in (0,1,3):
                slices=''.join('<DmxSlice uniqueId="'+str(i)+'"><Params><Param name="Name" value="Fixture '+str(i)+'"/></Params><InputRect><v x="0" y="0"/><v x="200" y="0"/><v x="200" y="100"/><v x="0" y="100"/></InputRect></DmxSlice>' for i in range(count))
                source.write_text('<XmlState><CurrentCompositionTextureSize width="200" height="100"/><screens><DmxScreen name="Old name" LumiverseId="7"><Params><Param name="Name" value="Renamed output"/></Params>'+slices+'</DmxScreen></screens></XmlState>')
                module.prepare()
                data=json.loads((home/'active-layout.js').read_text()[len('window.APC40Layout='):-1])
                self.assertEqual(len(data['outputFixtures']),count)
                if count:
                    item=data['outputFixtures'][0]
                    self.assertEqual((item['screen'],item['slice'],item['lumiverse']),('Renamed output','Fixture 0','7'))
                    self.assertEqual(item['uv'],[[0,1],[1,1],[1,0],[0,0]])

    def test_space_presets_use_their_own_model_layout_and_output(self):
        spec=importlib.util.spec_from_file_location('viewer_prepare_spaces',VIEWER/'prepare.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve();module.HOME=home
            def output(name,uid):
                (home/name).write_text('<XmlState><CurrentCompositionTextureSize width="100" height="100"/><screens><DmxScreen name="S"><DmxSlice uniqueId="'+uid+'"><InputRect><v x="0" y="0"/><v x="10" y="0"/><v x="10" y="100"/><v x="0" y="100"/></InputRect><ParamFixturePixels><ParamRange name="Width" value="1"/><ParamRange name="Height" value="4"/></ParamFixturePixels></DmxSlice></DmxScreen></screens></XmlState>')
            output('live.xml','1');(home/'stage').mkdir();output('stage/fixed.xml','2')
            fixture=lambda uid:{'fixtures':[{'kind':'metrovka','object':'Bar','sliceUid':uid,'pos':[[0,0,0],[0,1,0]]}],'camera':{}}
            (home/'a.json').write_text(json.dumps(fixture('1')));(home/'stage/b.json').write_text(json.dumps(fixture('2')))
            for name in ('a.glb','stage/b.glb'):(home/name).write_bytes(b'glb')
            module.arena_paths=lambda:(home/'live.xml',home/'live.xml','Live')
            (home/'spaces.json').write_text(json.dumps({'spaces':[
                {'id':'main','name':'Main','model':'a.glb','layout':'a.json'},
                {'id':'stage-2','name':'Stage 2','model':'stage/b.glb','layout':'stage/b.json','output':'stage/fixed.xml'},
                {'id':'boards','name':'Boards','model':'a.glb','layout':'a.json','mode':'projection'}]}))
            module.prepare()
            read=lambda name:json.loads((home/name).read_text()[len('window.APC40Layout='):-1])
            main,second=read('active-layout.js'),read('active-layout-stage-2.js')
            self.assertEqual((main['preset'],main['space']['model'],len(main['fixtures'][0]['uv'])),('Live','a.glb',4))
            self.assertEqual((second['preset'],second['space']['model'],second['fixtures'][0]['sliceUid']),('fixed','stage/b.glb','2'))
            self.assertEqual([s['id'] for s in second['spaces']],['main','stage-2','boards'])
            boards=read('active-layout-boards.js')
            self.assertEqual((boards['space']['mode'],boards['fixtures'],main['space']['mode']),('projection',[],'led'))
            self.assertTrue(boards['outputFixtures'])
            for bad in ({'id':'x','name':'X','model':'../a.glb','layout':'a.json'},{'id':'Bad id','name':'X','model':'a.glb','layout':'a.json'},
                        {'id':'x','name':'X','model':'a.glb','layout':'a.json','mode':'video'}):
                (home/'spaces.json').write_text(json.dumps({'spaces':[bad]}))
                with self.assertRaises(ValueError):module.prepare()

    def test_projection_only_in_projection_spaces(self):
        html=(VIEWER/'preview.html').read_text(encoding='utf-8')
        self.assertIn('projectionMode=wn.space?.mode==="projection"',html)
        self.assertIn('if(!projectionMode||!ki)return;',html)
        self.assertNotIn('projDiffusers',html)

    @unittest.skipUnless(shutil.which('node'),'Node is needed for selection geometry checks')
    def test_selection_and_pixel_geometry(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8');
const core=html.slice(html.indexOf('var fixtureSelection='),html.indexOf('var Ye=s=>'));
const state={wn:{preset:'test'},localStorage:{getItem(){return null}}};vm.createContext(state);vm.runInContext(core,state);
const item={sliceUid:'a',width:1,height:2,uv:[[0,1],[1,1],[1,0],[0,0]]};
assert(state.previewEnabled(item,0));state.fixtureSelection.disabled.a=true;assert(!state.previewEnabled(item,0));
state.fixtureSelection.disabled.a=false;state.fixtureSelection.pixels.a={0:true};assert(!state.previewEnabled(item,0));assert(state.previewEnabled(item,1));
assert(state.polygonContains(item.uv,.5,.5));assert(!state.polygonContains(item.uv,2,.5));
const thin={uv:[[0,1],[.001,1],[.001,0],[0,0]]};
assert(state.fixtureHitDistance(thin,.005,.5,1000,500)<7);
assert(state.fixtureHitDistance(thin,.02,.5,1000,500)>7);
assert.strictEqual(state.fixtureHitDistance(thin,.0005,.5,1000,500),0);
assert(state.fixtureIntersectsRect(thin,-.01,.2,.01,.4));
assert(!state.fixtureIntersectsRect(thin,.1,.2,.2,.4));
assert(state.fixtureIntersectsRect(item,.2,.2,.3,.3));
const diagonal={uv:[[0,0],[.01,0],[1,1],[.99,1]]};
assert(state.fixtureIntersectsRect(diagonal,.45,.45,.55,.55));
assert(!state.fixtureIntersectsRect(diagonal,.1,.8,.2,.9));


assert.strictEqual(state.fixturePixelUV(item,0)[1],.75);assert.strictEqual(state.fixturePixelUV(item,1)[1],.25);
assert(html.includes('previewEnabled(b,sourcePixel)||c.set(0,0,0)'));
assert(html.includes('drawMappingPixelOverlay();'));
console.log('Selection checks passed');
'''
        subprocess.run(['node','-e',script,str(VIEWER/'preview.html')],check=True,capture_output=True,text=True)


class PauseTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node checks pause snapshot lifecycle')
    def test_snapshot_stops_video_and_releases_texture_on_resume(self):
        script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(process.argv[1],'utf8'),code=html.slice(html.indexOf('var previewPaused=false'),html.indexOf('const pausePreviewButton='));
let time=4,paused=0,played=0,disposed=0;
const context={document:{createElement(){return {width:0,height:0,getContext(){return {fillRect(){},drawImage(){}}}};}},
 _0:'video',Cn:1920,Bn:1080,ui:{},At:{videoWidth:1920,videoHeight:1080,pause(){paused++;},play(){played++;return Promise.resolve();}},
 Xs:class{dispose(){disposed++;}},tt:'srgb',pi:{map:{value:'live'}},Yo:'video texture',Tr:'test texture',R4:{getElapsedTime(){return time;}},pausePreviewButton:{setAttribute(){}},di(message){throw Error(message);}};
vm.createContext(context);vm.runInContext(code,context);context.setPreviewPaused(true);
assert.equal(context.previewPaused,true);assert.equal(context.pausePreviewButton.textContent,'Resume');assert.equal(paused,1);
assert.equal(vm.runInContext('pausedFrame.width',context),1280);assert.equal(vm.runInContext('pausedFrame.height',context),720);
const frozen=context.pi.map.value;context.setPreviewPaused(true);assert.equal(context.pi.map.value,frozen);
time=9;context.setPreviewPaused(false);assert.equal(context.previewPaused,false);assert.equal(context.previewPauseOffset,5);assert.equal(context.pi.map.value,'video texture');assert.equal(played,1);assert.equal(disposed,1);assert.equal(context.pausePreviewButton.textContent,'Pause');assert.equal(vm.runInContext('pausedFrame.width',context),1);
context._0='test';context.setPreviewPaused(true);context.setPreviewPaused(false);assert.equal(context.pi.map.value,'test texture');assert.equal(played,1);
"""
        subprocess.run(['node','-e',script,str(VIEWER/'preview.html')],check=True,capture_output=True,text=True,timeout=20)

class WiringTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node checks physical wiring validation')
    def test_profile_order_and_invalid_connections(self):
        script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const scope={};vm.createContext(scope);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),scope);
const api=scope.APCWiring;
assert.equal(api.outputs.length,16);
assert.equal(api.outputs.slice(0,5).reduce((s,o)=>s+o.pieces,0),50);
assert.equal(api.outputs[5].pieces,5);assert.equal(api.outputs[5].nominalPixels,120);
assert.equal(api.outputs[11].pieces,4);assert.equal(api.outputs[11].meters,5);assert.equal(api.outputs[11].nominalPixels,1250);
const a={uid:'a',output:1,order:1,reverse:false},b={uid:'b',output:1,order:2,reverse:true};
const original={version:1,connections:[b,a]},fixtures=[{sliceUid:'a',pixels:59}];
const result=api.ordered(original,fixtures);
assert.equal(result[0].uid,'a');assert.equal(result[0].fixture.pixels,59);assert.equal(result[1].reverse,true);assert.equal(result[1].fixture,null);
assert.equal(original.connections[0].uid,'b');
for(const bad of [null,{}, {version:1,connections:[null]}, {version:1,connections:[a,a]},
 {version:1,connections:[a,{...b,order:1}]}, {version:1,connections:[{...a,output:17}]},
 {version:1,connections:[{...a,order:0}]}, {version:1,connections:[{...a,output:12,order:5}]},
 {version:1,connections:[{...a,reverse:'false'}]}, {version:1,connections:[{...a,uid:''}]}])assert.throws(()=>api.validate(bad));
assert.equal(api.validate({version:1,connections:[]}).connections.length,0);
const fixturesByGroup=api.outputs.flatMap(o=>Array.from({length:o.pieces},(_,i)=>({screenUid:'g'+o.id,screen:'OUTPUT '+o.id+' LED',sliceUid:'g'+o.id+'p'+i,pixels:o.id>=12?250:59,lumiverse:o.id===5?'8':'0'})));
let fixed=api.reconcile({version:1,connections:[]},fixturesByGroup);
assert.equal(fixed.connections.length,100);assert.equal(fixed.connections.find(c=>c.uid==='g5p0').output,5);
assert.equal(fixed.connections.find(c=>c.uid==='g6p0').output,6);assert.equal(fixed.connections.find(c=>c.uid==='g11p4').output,11);assert.equal(fixed.connections.find(c=>c.uid==='g16p3').output,16);
fixed.connections.find(c=>c.uid==='g1p0').reverse=true;
assert.equal(api.reconcile(fixed,fixturesByGroup).connections.find(c=>c.uid==='g1p0').reverse,true);
const unassigned=api.reconcile({...fixed,groups:[{key:'g1',output:0}]},fixturesByGroup);assert.equal(unassigned.connections.length,90);
assert.throws(()=>api.reconcile({...fixed,groups:[{key:'g2',output:1}]},fixturesByGroup));
assert.equal(api.groupsFor([{screenUid:'dmx',screen:'DMX 1',sliceUid:'d'}],fixed)[0].output,0);
assert.equal(fixturesByGroup.find(f=>f.sliceUid==='g12p0').pixels,250);

"""
        subprocess.run(['node','-e',script,str(VIEWER/'wiring.js')],check=True,capture_output=True,text=True,timeout=20)

if __name__=='__main__':unittest.main()
