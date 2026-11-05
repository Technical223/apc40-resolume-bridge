"""Native WebKit dashboard host. Local-only API, no upload endpoint or telemetry."""
import importlib.util
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import site
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mac_bridge as mac

HERE=Path(__file__).resolve().parent

def stop_process(child):
    if child is None or child.poll() is not None:return
    if sys.platform=='darwin':os.killpg(child.pid,signal.SIGTERM)
    else:child.terminate()
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if sys.platform=='darwin':os.killpg(child.pid,signal.SIGKILL)
        else:child.kill()
        child.wait(timeout=5)

def validate_config(core,cfg):
    for key in ('apc_port_match','to_resolume_port','from_resolume_port'):
        if not isinstance(cfg.get(key),str) or not cfg[key].strip():raise ValueError('Enter the MIDI port names.')
    if cfg['to_resolume_port'].casefold()==cfg['from_resolume_port'].casefold():raise ValueError('Use two different IAC buses.')
    if not 0<float(cfg['hue_max'])<=1 or not .5<=float(cfg['blink_hz'])<=10:raise ValueError('Numeric setting outside supported range.')
    if not isinstance(cfg.get('profile_name',''),str) or len(cfg.get('profile_name',''))>100:raise ValueError('Invalid profile name.')
    core.validate_control_rules(cfg)
    controls=json.loads((HERE/'surface.json').read_text())
    targets={(c['channel'],c['number']):c for c in controls if c['kind']=='button'}
    sources={(c['channel'],c['number']) for c in controls if c['kind']!='button'}
    for rule in cfg.get('control_rules',[]):
        target=targets.get((rule['channel'],rule['note']))
        if target is None or (rule['mode']=='hue' and not target['rgb']):raise ValueError('Unsupported control or Hue target.')
        if rule['color'] not in (3,5,9,13,17,21,29,37,45,49,53,57):raise ValueError('Unsupported editor palette color.')
        if (rule['source_channel'],rule['source_cc']) not in sources:raise ValueError('Unknown controller source.')

class Session:
    def __init__(self,core,cfg):
        self.core,self.cfg=core,cfg;self.child=None;self.setup=None;self.cached={};self.checked=0;self.last_report=None
        self.action_lock=threading.Lock()
    def python(self):
        path=mac.DATA/'venv/bin/python3'
        return str(path if path.exists() else Path(sys.executable))
    def dependencies_ready(self):
        path=mac.DATA/('venv/lib/python%d.%d/site-packages'%sys.version_info[:2])
        if not (mac.DATA/'venv/bin/python3').exists() or not path.is_dir():return False
        if str(path) not in sys.path:site.addsitedir(str(path))
        return True
    def save(self,data):
        allowed={'apc_port_match','to_resolume_port','from_resolume_port','hue_max','blink_hz','sync_resolume_feedback','always_lit','speed_button_pulse','global_crossfade','control_rules','profile_name'}
        if not isinstance(data,dict) or set(data)-allowed:raise ValueError('Unsupported settings.')
        cfg=dict(self.cfg,**data);validate_config(self.core,cfg)
        path=mac.DATA/'config.json';temporary=mac.DATA/'config.ui.tmp'
        temporary.write_text(json.dumps(cfg,indent=2),encoding='utf-8')
        if path.exists():(mac.DATA/'config.before-ui.json').write_bytes(path.read_bytes())
        os.replace(temporary,path);self.cfg=cfg;self.checked=0
    def status(self,live=False):
        if time.monotonic()-self.checked>5:
            self.dependencies_ready()
            self.cached=mac.snapshot(self.core,self.cfg)
            self.checked=time.monotonic()
        data=dict(self.cached,running=self.child is not None and self.child.poll() is None,
                  preparing=self.setup is not None and self.setup.poll() is None,
                  dependencies_ready=self.dependencies_ready(),config=self.cfg,
                  privacy='Nothing is uploaded automatically. Review and share diagnostics manually.')
        if self.setup is not None and self.setup.poll() is not None:data['setup_exit_code']=self.setup.returncode
        if live:
            (mac.DATA/'controller-live-request.json').write_text(json.dumps({'expires':time.time()+5}))
            try:
                snapshot=json.loads((mac.DATA/'controller-live.json').read_text())
                if time.time()-snapshot.get('updated',0)<3:data['live']=snapshot
            except (OSError,ValueError):pass
        return data
    def action(self,name):
        with self.action_lock:
            if name=='stop':stop_process(self.child);self.child=None
            elif name in ('start','restart','test'):
                if self.setup is not None and self.setup.poll() is None:raise ValueError('Wait for dependency setup to finish.')
                if not self.dependencies_ready():raise ValueError('Choose Install / repair first.')
                stop_process(self.child)
                args=['--test','--seconds','180'] if name=='test' else ['--run']
                self.child=subprocess.Popen([self.python(),str(HERE/'mac_bridge.py'),*args],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                logging.info('Started bridge child PID %s',self.child.pid)
            elif name=='prepare':
                if self.child is not None and self.child.poll() is None:raise ValueError('Stop the bridge before preparing dependencies.')
                if self.setup is None or self.setup.poll() is not None:
                    self.setup=subprocess.Popen([sys.executable,str(HERE/'mac_bridge.py'),'--prepare'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                    logging.info('Started setup child PID %s',self.setup.pid)
            elif name=='audio-midi':subprocess.run(['/usr/bin/open','-a','Audio MIDI Setup'],check=True,timeout=10)
            elif name=='diagnostics':
                state=self.status()
                self.last_report=mac.report(dict(self.cached,desktop_version=mac.VERSION,bridge_running=state['running'],setup_exit_code=state.get('setup_exit_code')))
                subprocess.run(['/usr/bin/open','-R',str(self.last_report)],check=True,timeout=10)
                return {'message':'Diagnostics saved locally. Review the ZIP and attach it manually. Nothing was uploaded.','file':str(self.last_report)}
            elif name=='visualizer':self.open_visualizer()
            else:raise ValueError('Unknown action.')
        return {'message':'Done.'}
    def open_visualizer(self):
        source=HERE/'visualizer'
        if not source.exists():source=HERE.parent/'bridge/visualizer'
        target=mac.DATA/'visualizer';target.mkdir(exist_ok=True)
        import shutil
        for file in source.iterdir():
            if file.is_file() and file.name not in ('active-layout.js','viewer-session.json','physical-layout.json'):shutil.copy2(file,target/file.name)
        if (source/'editor-vendor').is_dir():shutil.copytree(source/'editor-vendor',target/'editor-vendor',dirs_exist_ok=True)
        if not (target/'physical-layout.json').exists():shutil.copy2(source/'physical-layout.json',target/'physical-layout.json')
        spec=importlib.util.spec_from_file_location('mac_preview_launcher',target/'launcher.py');launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
        launcher.open_preview()
    def close(self):
        stop_process(self.child);stop_process(self.setup)

def make_server(session,token):
    assets={'desktop.html':HERE/'desktop.html','surface.json':HERE/'surface.json','controller.jpg':HERE/'controller.jpg'}
    if not assets['controller.jpg'].exists():assets['controller.jpg']=HERE.parent/'bridge/ui/apc40-top.jpg'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,data,status=200,kind='application/json'):
            body=json.dumps(data).encode() if kind=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def route(self):
            prefix='/'+token+'/'
            if not self.path.startswith(prefix):raise ValueError('Invalid session')
            return self.path[len(prefix):].split('?',1)[0]
        def do_GET(self):
            try:
                route=self.route()
                if route=='status':self.reply(session.status(live='live=1' in self.path))
                elif route=='logs':
                    chunks=[]
                    for name in ('app.log','bridge.log','setup.log','bootstrap.log'):
                        path=mac.DATA/name
                        if path.exists():
                            with path.open('rb') as stream:stream.seek(max(0,path.stat().st_size-32000));chunks.append(name+'\n'+stream.read(32000).decode('utf-8',errors='replace'))
                    self.reply({'text':mac.redact('\n\n'.join(chunks))})
                elif route in assets:self.reply(assets[route].read_bytes(),kind='image/jpeg' if route.endswith('.jpg') else 'text/html; charset=utf-8' if route.endswith('.html') else 'application/json; charset=utf-8')
                else:self.reply({'error':'Not found'},404)
            except Exception as error:self.reply({'error':str(error)},400)
        def do_POST(self):
            try:
                route=self.route();origin=self.headers.get('Origin')
                if origin and origin!='http://127.0.0.1:'+str(self.server.server_port):raise ValueError('Invalid request origin')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<=length<=1024*1024:raise ValueError('Request is too large')
                data=json.loads(self.rfile.read(length) or b'{}')
                if route=='config':session.save(data);self.reply({'message':'Saved. Controller lighting updates live; restart for MIDI port changes.'})
                elif route=='export-profile':
                    validate_config(session.core,dict(session.cfg,control_rules=data.get('rules',[]),profile_name=data.get('name','')))
                    import uuid
                    folder=mac.DATA/'profiles';folder.mkdir(exist_ok=True);path=folder/('APC40-profile-'+uuid.uuid4().hex[:8]+'.json')
                    path.write_text(json.dumps({'format':'apc40-bridge-profile','version':1,'name':data.get('name',''),'control_rules':data.get('rules',[])},indent=2),encoding='utf-8')
                    subprocess.run(['/usr/bin/open','-R',str(path)],check=True,timeout=10)
                    self.reply({'message':'Profile exported to '+str(path)})
                elif route=='action':self.reply(session.action(data.get('action','')))
                else:self.reply({'error':'Not found'},404)
            except Exception as error:
                logging.exception('Dashboard action failed');self.reply({'error':str(error)},400)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    return server

def run(core,cfg):
    import fcntl
    with (mac.DATA/'dashboard.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:mac.dialog('APC40 Bridge is already open.');return
        session=Session(core,cfg);token=secrets.token_urlsafe(24);server=make_server(session,token)
        worker=threading.Thread(target=server.serve_forever,name='mac-dashboard-http',daemon=True);worker.start()
        native=HERE.parent/'MacOS/BridgeWindow'
        if not native.exists():native=HERE/'BridgeWindow'
        try:
            if not native.exists():raise RuntimeError('The native dashboard is missing. Download the compiled macOS test package; source ZIPs use --legacy-menu.')
            subprocess.run([str(native),'http://127.0.0.1:'+str(server.server_port)+'/'+token+'/desktop.html'],check=True)
        finally:session.close();server.shutdown();server.server_close();worker.join(timeout=5)
