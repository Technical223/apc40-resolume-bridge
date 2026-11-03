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
            source=home/'output.xml';module.source_paths=lambda:(source,source,'Test preset')
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
assert.strictEqual(state.fixturePixelUV(item,0)[1],.75);assert.strictEqual(state.fixturePixelUV(item,1)[1],.25);
assert(html.includes('previewEnabled(b,d)||c.set(0,0,0)'));
assert(html.includes('drawMappingPixelOverlay();'));
console.log('Selection checks passed');
'''
        subprocess.run(['node','-e',script,str(VIEWER/'preview.html')],check=True,capture_output=True,text=True)

if __name__=='__main__':unittest.main()
