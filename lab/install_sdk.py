"""Install official SDK components and pin the other analysis tools."""
from pathlib import Path
import hashlib,io,json,lzma,os,shutil,subprocess,urllib.request,xml.etree.ElementTree as E,zipfile
ROOT=Path('/opt/pcc-lab');SDK=Path('/opt/android-sdk');SDK.mkdir(exist_ok=True)
def fetch(url):
    with urllib.request.urlopen(url,timeout=120) as r:return r.read()
def extract(blob,dest):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for n in z.namelist():
            if not (dest/n).resolve().is_relative_to(dest.resolve()):raise ValueError('Unsafe archive member')
        z.extractall(dest)
lock_path=ROOT/'state/tool-downloads.json'
locks=json.loads(lock_path.read_text()) if lock_path.exists() else []
if not (SDK/'cmdline-tools/latest/bin/sdkmanager').exists():
    repo=E.fromstring(fetch('https://dl.google.com/android/repository/repository2-3.xml'))
    package=next(p for p in repo if p.tag.rsplit('}',1)[-1]=='remotePackage' and p.attrib.get('path')=='cmdline-tools;latest')
    archive=next(a for a in package.findall('./archives/archive') if a.findtext('host-os')=='linux')
    complete=archive.find('complete');url='https://dl.google.com/android/repository/'+complete.findtext('url')
    blob=fetch(url)
    expected=complete.findtext('checksum');assert hashlib.sha1(blob).hexdigest()==expected
    temp=ROOT/'sdk-download';extract(blob,temp)
    (SDK/'cmdline-tools').mkdir(exist_ok=True)
    shutil.move(str(temp/'cmdline-tools'),str(SDK/'cmdline-tools/latest'))
    locks.append({'tool':'command-line tools','url':url,'sha256':hashlib.sha256(blob).hexdigest()})
for p in (SDK/'cmdline-tools/latest/bin').glob('*'):p.chmod(0o755)
env={**os.environ,'ANDROID_SDK_ROOT':str(SDK),'JAVA_HOME':'/usr/lib/jvm/java-21-openjdk-amd64'}
manager=str(SDK/'cmdline-tools/latest/bin/sdkmanager')
subprocess.run([manager,'--sdk_root='+str(SDK),'--licenses'],input='y\n'*100,text=True,env=env,check=True)
subprocess.run([manager,'--sdk_root='+str(SDK),'platform-tools','emulator','system-images;android-31;default;x86_64'],env=env,check=True)
for p in [SDK/'platform-tools/adb',SDK/'emulator/emulator']:p.chmod(0o755)
tools=ROOT/'tools';tools.mkdir(exist_ok=True)
if not (tools/'jadx/bin/jadx').exists():
    url='https://github.com/skylot/jadx/releases/download/v1.5.6/jadx-1.5.6.zip';blob=fetch(url);extract(blob,tools/'jadx')
    locks.append({'tool':'jadx','version':'1.5.6','url':url,'sha256':hashlib.sha256(blob).hexdigest()})
for p in (tools/'jadx/bin').glob('*'):p.chmod(0o755)
server=tools/'frida-server'
if not server.exists():
    url='https://github.com/frida/frida/releases/download/17.9.1/frida-server-17.9.1-android-x86_64.xz';blob=fetch(url);server.write_bytes(lzma.decompress(blob));server.chmod(0o755)
    locks.append({'tool':'frida-server','version':'17.9.1','url':url,'sha256':hashlib.sha256(blob).hexdigest()})
lock_path.write_text(json.dumps(locks,indent=2))
subprocess.run([str(ROOT/'venv/bin/pip'),'freeze'],stdout=(ROOT/'state/python-packages.txt').open('w'),check=True)
with (ROOT/'state/sdk-packages.txt').open('w') as f:subprocess.run([manager,'--sdk_root='+str(SDK),'--list_installed'],env=env,stdout=f,check=True)
subprocess.run(['chmod','-R','a+rX',str(SDK),str(tools)],check=True)
print('SDK and tools installed',flush=True)
