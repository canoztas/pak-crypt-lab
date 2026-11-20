"""Run the core of each lab once and say whether this machine reproduces it. Needs root.

    sudo /opt/pcc-lab/venv/bin/python /opt/pcc-lab/selftest.py

It installs each sample on the isolated phone, checks the one finding the lab is built on,
and leaves a clean phone behind. Takes about eight minutes.
"""
from pathlib import Path
import os, sys, time, zipfile

ROOT = Path('/opt/pcc-lab')
if os.geteuid() != 0:
    raise SystemExit('Run it with sudo: sudo /opt/pcc-lab/venv/bin/python /opt/pcc-lab/selftest.py')
sys.path.insert(0, str(ROOT))
import phone

SAMPLES = ROOT / 'demo/samples'
HOOKS = ROOT / 'demo/hooks'
results = []


def check(name, passed, detail=''):
    results.append(bool(passed))
    print(('PASS  ' if passed else 'FAIL  ') + name + ('  ' + detail if detail else ''), flush=True)


def install(name):
    phone.reset()
    r = phone.adb('install', '-r', str(SAMPLES / (name + '.apk')), check=False, timeout=120)
    check(name + ': installs on the phone', r.returncode == 0,
          (r.stdout + r.stderr).strip()[-80:] if r.returncode else '')
    return r.returncode == 0


def launch(package):
    phone.adb('shell', 'monkey', '-p', package, '-c', 'android.intent.category.LAUNCHER', '1', check=False)


print('Lab 1: Google Service Framework', flush=True)
if install('service_framework'):
    package = 'com.example.reverseshell2'
    launch(package)
    time.sleep(4)
    check('the permission review screen appears and is accepted', phone.tap_text('CONTINUE'))
    time.sleep(6)
    pid = phone.adb('shell', 'pidof', package, check=False).stdout.strip()
    check('the app is running', pid)
    entry = phone.adb('shell', 'cmd', 'package', 'resolve-activity', '--brief', '-c',
                      'android.intent.category.LAUNCHER', package, check=False).stdout
    check('it has hidden its launcher icon', 'No activity found' in entry)
    output = phone.frida_run(['-p', pid.split()[0]], HOOKS / 'observe_c2.js') if pid else ''
    check('Frida sees it reach for 3.67.78.149:2002', '3.67.78.149:2002' in output)

print('\nLab 2: Brokewell', flush=True)
with zipfile.ZipFile(SAMPLES / 'brokewell.apk') as archive:
    carried = [item for item in archive.namelist() if item.endswith('.apk')]
check('the courier carries a second APK', carried == ['res/SB.apk'], ', '.join(carried))
if install('brokewell'):
    package = 'xyIBgcE.FKnaCEV.XDKUPweO'
    launch(package)
    time.sleep(5)
    check('the courier is running', phone.adb('shell', 'pidof', package, check=False).stdout.strip())
    check('it shows its update lure', phone.tap_text('CONTINUE'))

print('\nLab 3: Authenticator downloader', flush=True)
if install('authenticator_downloader'):
    output = phone.frida_run(['-f', 'com.privacy.account.safetyapp'], HOOKS / 'read_constants.js')
    check('Frida reads the hidden strings', 'version.json' in output and 'version.apk' in output)
    check('the domain is printed defanged', 'privacyandroidapp[.]club' in output)

print('\nLeaving a clean phone', flush=True)
phone.reset()
left = phone.adb('shell', 'pm', 'list', 'packages', '-3', check=False).stdout.strip()
check('no sample is left installed', not left, left)

print('\n%d of %d checks passed.' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
