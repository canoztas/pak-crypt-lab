#!/usr/bin/env bash
# Remove the Pak-Crypt lab: services, the emulator account, the firewall chain and the files.
#   sudo ./uninstall.sh
set -Euo pipefail
[ "$(id -u)" = 0 ] || { echo "Run it with sudo: sudo ./uninstall.sh"; exit 1; }
LAB_USER=${SUDO_USER:-}
systemctl disable --now pcc-android.service pcc-adb.service pcc-local-model.service pcc-emulator-isolation.service 2>/dev/null
rm -f /etc/systemd/system/pcc-android.service /etc/systemd/system/pcc-adb.service \
      /etc/systemd/system/pcc-local-model.service /etc/systemd/system/pcc-emulator-isolation.service
systemctl daemon-reload
for binary in iptables ip6tables; do
  if id androidemu >/dev/null 2>&1; then
    "$binary" -w -D OUTPUT -m owner --uid-owner "$(id -u androidemu)" -j PCC_EMULATOR 2>/dev/null
  fi
  "$binary" -w -F PCC_EMULATOR 2>/dev/null
  "$binary" -w -X PCC_EMULATOR 2>/dev/null
done
pkill -u androidemu 2>/dev/null
userdel -r androidemu 2>/dev/null
userdel -r localllm 2>/dev/null
rm -rf /opt/pcc-lab /opt/android-sdk /var/lib/pcc-llm
rm -f /usr/local/sbin/pcc-isolate-emulator /etc/sudoers.d/pcc-lab /etc/profile.d/pcc-lab.sh
if [ -n "$LAB_USER" ] && [ "$LAB_USER" != root ]; then
  DESK="$(getent passwd "$LAB_USER" | cut -d: -f6)/Desktop"
  rm -f "$DESK/service_framework.apk" "$DESK/brokewell.apk" "$DESK/authenticator_downloader.apk" \
        "$DESK/reset_phone.py" "$DESK/PCC-Android.desktop" "$DESK/PCC-Jadx.desktop" \
        "$DESK/service_framework.dex" "$DESK/other.dex" "$DESK/downloader.dex"
fi
echo "The lab is removed. System packages installed for it (Java, qemu-kvm, scrcpy) were left in place."
