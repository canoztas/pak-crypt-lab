"""Start, reach and check the lab phone. Used by reset_phone.py and selftest.py; needs root."""
from pathlib import Path
import re, subprocess, time

ROOT = Path('/opt/pcc-lab')
ADB = '/opt/android-sdk/platform-tools/adb'
FRIDA = str(ROOT / 'venv/bin/frida')
SERIAL = 'emulator-5554'


def run(args, timeout=45, check=True):
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(str(args[:5]) + '\n' + str(r.stderr)[-1800:])
    return r


def adb(*args, **kw):
    return run([ADB, '-s', SERIAL, *args], **kw)


def boot():
    global SERIAL
    run([ADB, 'start-server'])
    for attempt in range(90):
        listing = run([ADB, 'devices']).stdout
        if 'emulator-5554\tdevice' in listing:
            SERIAL = 'emulator-5554'
        else:
            run([ADB, 'connect', '127.0.0.1:5555'], check=False)
            if '127.0.0.1:5555\tdevice' in run([ADB, 'devices']).stdout:
                SERIAL = '127.0.0.1:5555'
        r = adb('shell', 'getprop', 'sys.boot_completed', check=False)
        if r.returncode == 0 and r.stdout.strip() == '1':
            break
        if attempt % 6 == 0:
            print('Waiting for Android to boot', flush=True)
        time.sleep(4)
    else:
        raise RuntimeError('Android did not finish booting')
    if 'emulator-5554\tdevice' in run([ADB, 'devices']).stdout:
        run([ADB, 'disconnect', '127.0.0.1:5555'], check=False)
        SERIAL = 'emulator-5554'
    adb('root', check=False)
    time.sleep(2)
    adb('wait-for-device', timeout=40)
    assert adb('shell', 'id', '-u').stdout.strip() == '0'
    adb('shell', 'input', 'keyevent', '82', check=False)
    time.sleep(2)


def start_frida():
    adb('push', str(ROOT / 'tools/frida-server'), '/data/local/tmp/frida-server')
    adb('shell', 'chmod', '755', '/data/local/tmp/frida-server')
    adb('shell', 'sh', '-c', "'/data/local/tmp/frida-server </dev/null >/data/local/tmp/frida-server.log 2>&1 &'", check=False)
    time.sleep(2)
    adb('forward', 'tcp:27042', 'tcp:27042')
    import frida
    device = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
    return len(device.enumerate_processes())


def check_isolation():
    """Fail loudly unless both the emulator account and the Android guest are cut off."""
    # This probe runs as the account that owns the emulator's network sockets.
    probe = ("import socket,sys; s=socket.socket(); s.settimeout(3); "
             "r=s.connect_ex((sys.argv[1],int(sys.argv[2]))); print(r); sys.exit(0 if r else 1)")
    for name, host, port in [('the internet', '1.1.1.1', 443), ('link-local addresses', '169.254.169.254', 80)]:
        r = run(['runuser', '-u', 'androidemu', '--', 'python3', '-c', probe, host, str(port)], check=False)
        print('emulator account cannot reach %s: %s' % (name, 'PASS' if r.returncode == 0 else 'FAIL'), flush=True)
        if r.returncode != 0:
            raise RuntimeError('Network isolation check failed')

    def rejected_packets(host):
        listing = run(['iptables', '-n', '-v', '-x', '-L', 'PCC_EMULATOR']).stdout
        return sum(int(parts[0]) for line in listing.splitlines()
                   if len(parts := line.split()) > 8 and parts[2] == 'REJECT' and host in parts)

    # The guest may see a rejected host socket as a timeout, so the firewall counter must move too.
    for name, host in [('the internet', '1.1.1.1'), ('link-local addresses', '169.254.169.254')]:
        before = rejected_packets(host)
        r = adb('shell', f'toybox nc -w 2 {host} 80 < /dev/null', timeout=8, check=False)
        passed = r.returncode != 0 and rejected_packets(host) > before
        print('phone cannot reach %s: %s' % (name, 'PASS' if passed else 'FAIL'), flush=True)
        if not passed:
            raise RuntimeError('Guest network isolation is not established')


def tap_text(label):
    """Tap an on-screen button by its label."""
    for _ in range(5):
        adb('shell', 'uiautomator', 'dump', '/sdcard/ui.xml', check=False)
        dump = adb('shell', 'cat', '/sdcard/ui.xml', check=False).stdout
        for node in re.findall(r'<node[^>]*>', dump):
            if re.search(r'text="%s"' % re.escape(label), node, re.I):
                box = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
                if box:
                    x1, y1, x2, y2 = map(int, box.groups())
                    adb('shell', 'input', 'tap', str((x1 + x2) // 2), str((y1 + y2) // 2), check=False)
                    return True
        time.sleep(2)
    return False


def frida_run(target, script, seconds=9):
    """Run one hook file against ['-f', package] or ['-p', pid] and return what it printed."""
    args = [FRIDA, '-H', '127.0.0.1:27042', *target, '-l', str(script), '-q', '-t', str(seconds)]
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                       text=True, timeout=seconds + 40)
    return r.stdout


def reset():
    """A fresh Android 12 with root adb and frida-server, verified to have no network."""
    run(['systemctl', 'restart', 'pcc-android.service'], timeout=50)
    time.sleep(4)
    boot()
    start_frida()
    check_isolation()
