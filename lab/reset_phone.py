#!/opt/pcc-lab/venv/bin/python
"""Reset the lab phone: fresh Android 12, root adb, frida-server and the network isolation check.

Run  python3 ~/Desktop/reset_phone.py  in a terminal. Takes one to two minutes.
"""
from pathlib import Path
import os, subprocess, sys

ROOT = Path('/opt/pcc-lab')

if os.geteuid() != 0:
    code = subprocess.call(['sudo', str(ROOT / 'venv/bin/python'), str(ROOT / 'reset_phone.py')])
    if code == 0 and os.environ.get('DISPLAY') and (ROOT / 'android_screen.sh').exists():
        subprocess.Popen([str(ROOT / 'android_screen.sh')], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    sys.exit(code)

sys.path.insert(0, str(ROOT))
import phone

print('Resetting the phone: fresh Android 12, root adb, frida-server, network isolation check (1-2 min).', flush=True)
phone.reset()
installed = phone.adb('shell', 'pm', 'list', 'packages', '-3', check=False).stdout.strip()
if installed:
    print('Warning: third-party packages remain:\n' + installed)
    sys.exit(1)
print('Phone is clean: no third-party apps, Frida is listening on 127.0.0.1:27042.')
