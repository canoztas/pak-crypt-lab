from pathlib import Path
import hashlib,json,os,subprocess,time,urllib.request
os.umask(0o022)
ROOT=Path('/opt/pcc-lab');C=json.loads((ROOT/'config.json').read_text())
TOOLS=ROOT/'tools/ollama';BINARY=TOOLS/'bin/ollama'
if not BINARY.exists():
    subprocess.run(['apt-get','install','-y','-qq','zstd'],check=True)
    archive=ROOT/'state/ollama.tar.zst'
    subprocess.run(['curl','-fL','--retry','3','-o',str(archive),C['ollama_url']],check=True)
    h=hashlib.sha256()
    with archive.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    expected=C.get('ollama_digest')
    if expected:assert 'sha256:'+h.hexdigest()==expected
    TOOLS.mkdir(parents=True,exist_ok=True)
    subprocess.run(['tar','--zstd','-xf',str(archive),'-C',str(TOOLS)],check=True)
    (ROOT/'state/ollama-download.json').write_text(json.dumps({'version':C['ollama_version'],'url':C['ollama_url'],'sha256':h.hexdigest()},indent=2))
    archive.unlink()
TOOLS.chmod(0o755)
if subprocess.run(['id','localllm'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
    subprocess.run(['useradd','--system','--create-home','--home-dir','/var/lib/pcc-llm','--shell','/usr/sbin/nologin','localllm'],check=True)
(ROOT/'models').mkdir(exist_ok=True)
subprocess.run(['chown','-R','localllm:localllm',str(ROOT/'models'),'/var/lib/pcc-llm'],check=True)
Path('/etc/systemd/system/pcc-local-model.service').write_text('''[Unit]
Description=PCC local code review model
After=network-online.target
[Service]
User=localllm
Group=localllm
Environment=HOME=/var/lib/pcc-llm
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_MODELS=/opt/pcc-lab/models
Environment=OLLAMA_NO_CLOUD=1
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
ExecStart=/opt/pcc-lab/tools/ollama/bin/ollama serve
Restart=on-failure
[Install]
WantedBy=multi-user.target
''')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','reset-failed','pcc-local-model.service'],check=False)
subprocess.run(['systemctl','enable','--now','pcc-local-model.service'],check=True)
for _ in range(30):
    try:
        urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2).read();break
    except Exception:time.sleep(1)
else:raise RuntimeError('Local model service did not become ready')
request=urllib.request.Request('http://127.0.0.1:11434/api/pull',data=json.dumps({'model':C['model'],'stream':False}).encode(),headers={'Content-Type':'application/json'})
pulled=json.load(urllib.request.urlopen(request,timeout=900))
if 'error' in pulled:raise RuntimeError(pulled['error'])
tags=json.load(urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=10))
tag=next(x for x in tags['models'] if x['name']==C['model'])
if C.get('model_digest'):assert tag['digest']==C['model_digest'],'Model tag changed since the recorded build'
(ROOT/'state/local-model.json').write_text(json.dumps(tag,indent=2))
print('Local model ready:',C['model'],tag['digest'],flush=True)
