#!/usr/bin/env bash
# Pak-Crypt mobile malware lab: local installer.
#
#   sudo ./install.sh                 the lab
#   sudo ./install.sh --with-model    the lab plus the small local model used in Lab 3 step 4
#
# Needs Ubuntu 22.04 or 24.04 on x86_64 with hardware virtualisation (KVM).
# It installs an Android 12 emulator that has no route to any network, adb, Frida,
# jadx and the three samples. Safe to run again: finished steps are skipped.
set -Eeuo pipefail

SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=/opt/pcc-lab
SDK=/opt/android-sdk
WITH_MODEL=no

usage() {
  sed -n '2,9p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}
for arg in "$@"; do
  case "$arg" in
    --with-model) WITH_MODEL=yes ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { printf '\nStopped: %s\n' "$1" >&2; exit 1; }
step() { printf '\n== %s\n' "$1"; }
trap 'printf "\nThe installer stopped at line %s. Fix the cause and run it again; finished steps are skipped.\n" "$LINENO" >&2' ERR

step "Checking the machine"
[ "$(id -u)" = 0 ] || fail "run it with sudo:  sudo ./install.sh"
LAB_USER=${SUDO_USER:-}
if [ -z "$LAB_USER" ] || [ "$LAB_USER" = root ]; then
  fail "run it with sudo from your own account, not from a root shell. The lab is set up for the account that calls sudo."
fi
LAB_HOME=$(getent passwd "$LAB_USER" | cut -d: -f6)
[ -d "$LAB_HOME" ] || fail "no home directory for $LAB_USER"
[ "$(uname -m)" = x86_64 ] || fail "this lab needs an x86_64 machine; the Android image and frida-server are x86_64."
grep -Eqw 'vmx|svm' /proc/cpuinfo || fail "the CPU does not expose VT-x or AMD-V. On a virtual machine, turn on nested virtualisation; on a PC, enable virtualisation in the firmware setup."
if [ -r /etc/os-release ]; then
  . /etc/os-release
  case "${ID:-}:${VERSION_ID:-}" in
    ubuntu:22.04|ubuntu:24.04) ;;
    *) printf 'Note: tested on Ubuntu 22.04 and 24.04; this is %s %s. Continuing.\n' "${ID:-unknown}" "${VERSION_ID:-}" ;;
  esac
fi
free_gb=$(df -BG --output=avail /opt 2>/dev/null | tail -1 | tr -dc '0-9')
[ "${free_gb:-0}" -ge 15 ] || fail "about 15 GB of free space is needed under /opt; found ${free_gb:-0} GB."
ram_gb=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
[ "$ram_gb" -ge 7 ] || printf 'Note: %s GB of memory. The phone is given 4 GB; 8 GB or more is comfortable.\n' "$ram_gb"
for sample in service_framework brokewell authenticator_downloader; do
  grep -q " \*\{0,1\}$sample.apk\$" "$SRC/samples/SHA256SUMS" || fail "samples/SHA256SUMS does not list $sample.apk"
done
printf 'Account: %s   Memory: %s GB   Free under /opt: %s GB\n' "$LAB_USER" "$ram_gb" "$free_gb"

step "Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq openjdk-21-jre unzip curl python3-venv qemu-kvm iptables xz-utils \
  libgl1 libpulse0 libnss3 libx11-6 libxcomposite1 libxcursor1 libxi6 libxdamage1 libxrandr2 \
  libxtst6 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0
apt-get install -y -qq libasound2t64 2>/dev/null || apt-get install -y -qq libasound2
if apt-cache show scrcpy >/dev/null 2>&1; then
  apt-get install -y -qq scrcpy
else
  printf 'Note: this release has no scrcpy package. Everything works from the terminal; to see the\nphone screen, install scrcpy from https://github.com/Genymobile/scrcpy and run it.\n'
fi
test -c /dev/kvm || fail "/dev/kvm is missing. Virtualisation is off in the firmware, or this is a virtual machine without nested virtualisation."

step "Copying the lab to $ROOT"
install -d -m 755 "$ROOT" "$ROOT/state" "$ROOT/evidence" "$ROOT/tools" "$ROOT/demo"
install -m 644 "$SRC"/lab/*.py "$ROOT/"
install -m 755 "$SRC/lab/isolate_emulator.sh" "$ROOT/isolate_emulator.sh"
install -m 644 "$SRC/lab/requirements.txt" "$SRC/lab/config.json" "$ROOT/"
cp -r "$SRC"/lab/demo/. "$ROOT/demo/"
chmod -R a+rX "$ROOT/demo"
chmod 755 "$ROOT/reset_phone.py"
# The command files were written on a machine whose account was called analyst.
sed -i "s#/home/analyst#$LAB_HOME#g" "$ROOT"/demo/commands/*.txt

step "Unpacking the samples"
install -d -m 755 "$ROOT/demo/samples"
python3 "$SRC/lab/unpack_samples.py" "$SRC/samples" "$ROOT/demo/samples"

step "Creating the lab accounts"
# The emulator runs as its own account so that one firewall rule can cut all of its traffic.
id androidemu >/dev/null 2>&1 || useradd -m -s /bin/bash androidemu
usermod -aG kvm androidemu
usermod -aG kvm "$LAB_USER"
chmod 755 /home/androidemu
for home in /root /home/androidemu "$LAB_HOME"; do printf '%s\n' '--no-metrics' > "$home/.androidrc"; done
chown androidemu:androidemu /home/androidemu/.androidrc
chown "$LAB_USER": "$LAB_HOME/.androidrc"

step "Installing Python tools (Frida, YARA)"
test -x "$ROOT/venv/bin/python" || python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install --quiet --upgrade pip
"$ROOT/venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"

step "Installing the Android SDK, the Android 12 image, jadx and frida-server (several minutes)"
python3 "$ROOT/install_sdk.py"

step "Starting the adb service"
cat > /etc/systemd/system/pcc-adb.service <<'EOF'
[Unit]
Description=Pak-Crypt lab ADB server
Before=pcc-android.service
[Service]
Type=simple
Environment=HOME=/root
ExecStart=/opt/android-sdk/platform-tools/adb -L tcp:5037 server nodaemon
Restart=always
RestartSec=1
[Install]
WantedBy=multi-user.target
EOF
systemctl stop pcc-android.service 2>/dev/null || true
"$SDK/platform-tools/adb" kill-server 2>/dev/null || true
systemctl daemon-reload
systemctl reset-failed pcc-adb.service 2>/dev/null || true
systemctl enable --now pcc-adb.service
cat > /etc/profile.d/pcc-lab.sh <<'EOF'
export ANDROID_SDK_ROOT=/opt/android-sdk
export PATH=/opt/pcc-lab/venv/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator:/opt/android-sdk/cmdline-tools/latest/bin:/opt/pcc-lab/tools/jadx/bin:$PATH
EOF

step "Creating the phone"
export ANDROID_SDK_ROOT=$SDK
if ! test -f /home/androidemu/.android/avd/pcc_aosp.ini; then
  printf 'no\n' | runuser -u androidemu -- env ANDROID_SDK_ROOT=$SDK "$SDK/cmdline-tools/latest/bin/avdmanager" create avd \
    --name pcc_aosp --package 'system-images;android-31;default;x86_64' --device pixel_2
fi
python3 - <<'PY'
from pathlib import Path
p = Path('/home/androidemu/.android/avd/pcc_aosp.avd/config.ini')
updates = {'hw.ramSize': '4096', 'hw.cpu.ncore': '4', 'hw.gpu.enabled': 'yes', 'hw.gpu.mode': 'swiftshader_indirect',
           'disk.dataPartition.size': '6G', 'showDeviceFrame': 'no'}
lines = [line for line in p.read_text().splitlines() if line.split('=', 1)[0].strip() not in updates]
p.write_text('\n'.join(lines + [k + '=' + v for k, v in updates.items()]) + '\n')
PY
chown -R androidemu:androidemu /home/androidemu/.android

step "Closing the phone's network"
install -m 755 "$ROOT/isolate_emulator.sh" /usr/local/sbin/pcc-isolate-emulator
cat > /etc/systemd/system/pcc-emulator-isolation.service <<'EOF'
[Unit]
Description=Reject all traffic started by the Pak-Crypt lab emulator
Before=pcc-android.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/pcc-isolate-emulator
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/pcc-android.service <<'EOF'
[Unit]
Description=Pak-Crypt lab Android emulator (no network)
Requires=pcc-emulator-isolation.service pcc-adb.service
After=pcc-emulator-isolation.service pcc-adb.service
[Service]
User=androidemu
Group=androidemu
SupplementaryGroups=kvm
Environment=ANDROID_SDK_ROOT=/opt/android-sdk
Environment=ANDROID_AVD_HOME=/home/androidemu/.android/avd
ExecStart=/opt/android-sdk/emulator/emulator -avd pcc_aosp -no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect -accel on -port 5554 -wipe-data
Restart=no
TimeoutStopSec=30
KillMode=control-group
EOF
systemctl daemon-reload
systemctl enable pcc-emulator-isolation.service
systemctl restart pcc-emulator-isolation.service

step "Setting up $LAB_USER's desktop"
DESK="$LAB_HOME/Desktop"
install -d -m 755 -o "$LAB_USER" -g "$(id -gn "$LAB_USER")" "$DESK"
cat > "$ROOT/android_screen.sh" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
export PATH=/opt/android-sdk/platform-tools:$PATH
serial=$(adb devices | awk '$2=="device" {print $1; exit}')
test -n "$serial" || { echo "The phone is not running. Run: python3 ~/Desktop/reset_phone.py"; exit 1; }
exec scrcpy --serial "$serial" --window-title='Android Phone'
EOF
chmod 755 "$ROOT/android_screen.sh"
for item in service_framework brokewell authenticator_downloader; do
  install -m 644 -o "$LAB_USER" -g "$(id -gn "$LAB_USER")" "$ROOT/demo/samples/$item.apk" "$DESK/$item.apk"
done
ln -sfn "$ROOT/reset_phone.py" "$DESK/reset_phone.py"
launcher() { # file, name, command, icon
  printf '[Desktop Entry]\nType=Application\nName=%s\nExec=%s\nIcon=%s\nTerminal=false\n' "$2" "$3" "$4" > "$DESK/$1"
  chown "$LAB_USER": "$DESK/$1"; chmod 755 "$DESK/$1"
}
launcher PCC-Android.desktop "Android Phone" "$ROOT/android_screen.sh" phone
launcher PCC-Jadx.desktop "jadx" "$ROOT/tools/jadx/bin/jadx-gui" applications-development
chown -h "$LAB_USER": "$DESK/reset_phone.py"
# Resetting the phone and reading the firewall chain are the two things the labs do as root.
printf '%s ALL=(root) NOPASSWD: %s/venv/bin/python %s/reset_phone.py, /usr/sbin/iptables -S PCC_EMULATOR, /usr/sbin/ip6tables -S PCC_EMULATOR\n' \
  "$LAB_USER" "$ROOT" "$ROOT" > /etc/sudoers.d/pcc-lab
chmod 440 /etc/sudoers.d/pcc-lab
visudo -cf /etc/sudoers.d/pcc-lab >/dev/null
install -d -m 775 -o "$LAB_USER" -g "$(id -gn "$LAB_USER")" "$ROOT/evidence"

if [ "$WITH_MODEL" = yes ]; then
  step "Installing the local model for Lab 3 step 4 (about 1 GB)"
  python3 "$ROOT/setup_model.py"
fi

step "Starting the phone and checking that it cannot reach any network (1-2 minutes)"
"$ROOT/venv/bin/python" "$ROOT/reset_phone.py"
printf '%s\n' 'pak-crypt-lab-local-1' > "$ROOT/state/setup-version.txt"

cat <<EOF

Ready.

Open a NEW terminal (so that adb, frida and jadx-gui are on your PATH), then:

    cd /opt/pcc-lab/demo
    adb devices
    frida-ps -H 127.0.0.1:27042 -a

The three samples and reset_phone.py are on your desktop. The commands of each lab are in
/opt/pcc-lab/demo/commands (check.txt, lab1.txt, lab2.txt, lab3.txt). To see the phone, open "Android Phone" on the desktop or run
/opt/pcc-lab/android_screen.sh. After a reboot the phone is off; start it with:

    python3 ~/Desktop/reset_phone.py

To check the whole lab end to end:  sudo /opt/pcc-lab/venv/bin/python /opt/pcc-lab/selftest.py
To remove everything:               sudo ./uninstall.sh
EOF
