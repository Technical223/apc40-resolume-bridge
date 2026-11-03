"""Fetch the pinned publisher camera, then let Windows request registration permission."""
import ctypes
import hashlib
import os
import urllib.request
from pathlib import Path

HOME=Path(__file__).resolve().parent
URL="https://raw.githubusercontent.com/leadedge/SpoutCam/db86ea39f402b7fe4a12bbcd17526e2f7278ba00/binaries/SPOUTCAM/SpoutCam64/SpoutCam64.ax"
EXPECTED="a7d911c8e1977bae7da85421aea735f48f5fd7012d7ea4c1c91e14dc6a40787a"

def install():
    camera=HOME/"SpoutCam64.ax"
    if not camera.exists() or hashlib.sha256(camera.read_bytes()).hexdigest()!=EXPECTED:
        request=urllib.request.Request(URL,headers={"User-Agent":"APC40-Bridge"})
        with urllib.request.urlopen(request,timeout=30) as response:
            data=response.read(2*1024*1024+1)
        if len(data)>2*1024*1024 or hashlib.sha256(data).hexdigest()!=EXPECTED:
            raise ValueError("The publisher camera download did not pass verification.")
        temporary=camera.with_suffix(".download")
        temporary.write_bytes(data)
        os.replace(temporary,camera)
    result=ctypes.windll.shell32.ShellExecuteW(None,"runas",str(Path(os.environ["WINDIR"])/"System32/regsvr32.exe"),'"'+str(camera)+'"',str(HOME),1)
    if result<=32:raise OSError("Camera registration was cancelled or could not start.")

if __name__=="__main__":
    try:install()
    except Exception as error:ctypes.windll.user32.MessageBoxW(None,str(error),"SpoutCam setup",0x10)
