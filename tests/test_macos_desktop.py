import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'macos'))
desktop=importlib.import_module('desktop')

class MacDesktopTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.data=Path(temp.name);override=patch.object(desktop.mac,'DATA',self.data);override.start();self.addCleanup(override.stop)
        self.core=desktop.mac.load_core();self.cfg=desktop.mac.load_config(self.core)
        self.session=desktop.Session(self.core,self.cfg)

    def test_saving_profile_uses_data_config_not_app_bundle(self):
        rule={'channel':0,'note':32,'mode':'solid','color':5,'source_channel':0,'source_cc':48,'press':'passthrough','reset_value':0,'rate_min':1,'rate_max':3}
        self.session.save({'profile_name':'Portable profile','control_rules':[rule]})
        saved=json.loads((self.data/'config.json').read_text())
        self.assertEqual(saved['control_rules'],[rule]);self.assertEqual(saved['profile_name'],'Portable profile')
        self.assertTrue((self.data/'config.before-ui.json').exists())
        self.assertEqual(self.core.CFG_PATH,str(self.data/'config.json'))

    def test_invalid_profile_does_not_replace_config(self):
        original=(self.data/'config.json').read_bytes()
        with self.assertRaises((ValueError,KeyError)):self.session.save({'control_rules':[{'channel':0,'note':999,'mode':'solid'}]})
        self.assertEqual((self.data/'config.json').read_bytes(),original)
        with self.assertRaises(ValueError):self.session.save({'unknown_setting':True})

    def test_local_api_refuses_other_sessions_and_cross_origin_writes(self):
        server=desktop.make_server(self.session,'test-secret')
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            with urllib.request.urlopen(base+'/test-secret/surface.json') as reply:self.assertEqual(len(json.load(reply)),145)
            for url,origin in [('/wrong/config',base),('/test-secret/config','https://example.org')]:
                request=urllib.request.Request(base+url,data=b'{}',headers={'Origin':origin,'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
                self.assertEqual(error.exception.code,400)
                error.exception.close()
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(base+'/test-secret/../config.json')
            error.exception.close()
        finally:server.shutdown();server.server_close();worker.join(timeout=5)

    def test_diagnostics_remain_a_local_file(self):
        with patch.object(desktop.mac,'snapshot',return_value={'ports_ready':False,'error':'test error'}),patch.object(desktop.subprocess,'run'):
            # Force the normal fallback destination without touching the real Desktop.
            original=desktop.mac.report
            with patch.object(desktop.mac,'report',side_effect=lambda details:original(details,self.data/'exports')):
                result=self.session.action('diagnostics')
        self.assertTrue(Path(result['file']).exists());self.assertIn('Nothing was uploaded',result['message'])

if __name__=='__main__':unittest.main()
