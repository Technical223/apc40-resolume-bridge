import importlib.util
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / 'bridge/visualizer'

class WorkspaceTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node validates portable workspace input')
    def test_workspace_rejects_corrupt_or_foreign_data(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const context={Blob,TextEncoder,TextDecoder,ArrayBuffer,DataView,Set,Promise};
vm.createContext(context);vm.runInContext(fs.readFileSync('bridge/visualizer/workspace.js','utf8'),context);
const api=context.APCWorkspace;
const header=()=>({version:1,records:[{key:'stage:video',type:'blob',size:4,mime:'video/mp4'}],local:[['apc40-appearance','{}']],session:[]});
assert.equal(api.validate(header(),4).version,1);
for(const change of [h=>h.records.push(h.records[0]),h=>h.records[0].key='../file',h=>h.records[0].size=-1,h=>h.records[0].size=NaN,h=>h.records[0].type='file',h=>h.local.push(['unrelated-secret','x']),h=>h.local.push(h.local[0]),h=>h.version=2]){const h=header();change(h);assert.throws(()=>api.validate(h,4));}
assert.throws(()=>api.validate(header(),5));
(async()=>{for(const file of [new Blob(['not a workspace']),new Blob(['APCWORKSPACE1\n',new Uint8Array([255,255,255,255])])])await assert.rejects(()=>api.readHeader(file));const json=new TextEncoder().encode(JSON.stringify(header())),length=new ArrayBuffer(4);new DataView(length).setUint32(0,json.length,true);const valid=new Blob(['APCWORKSPACE1\n',length,json,'data']);assert.equal((await api.readHeader(valid)).header.records[0].key,'stage:video');await assert.rejects(()=>api.readHeader(valid.slice(0,valid.size-1)));})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_windows_open_reuses_dashboard_without_starting_browser(self):
        spec=importlib.util.spec_from_file_location('workspace_launcher',VIEWER/'launcher.py')
        launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
        with patch.object(launcher.os,'name','nt'),patch.object(Path,'is_file',return_value=True),patch.object(launcher.subprocess,'Popen') as start,patch.object(launcher.webbrowser,'open') as browser,patch.object(launcher,'ensure_preview') as server:
            launcher.open_preview()
            self.assertEqual(start.call_args.args[0][-1],'--visualizer')
            browser.assert_not_called();server.assert_not_called()

if __name__=='__main__': unittest.main()
