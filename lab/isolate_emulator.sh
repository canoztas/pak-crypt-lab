#!/usr/bin/env bash
set -Eeuo pipefail
emu_uid=$(id -u androidemu)
for binary in iptables ip6tables; do
  "$binary" -w -N PCC_EMULATOR 2>/dev/null || true
  "$binary" -w -F PCC_EMULATOR
  "$binary" -w -A PCC_EMULATOR -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  # No new connections, including host loopback and metadata. The controller
  # connects to the emulator's ADB listener; established replies are sufficient.
  if [ "$binary" = iptables ]; then
    "$binary" -w -A PCC_EMULATOR -d 1.1.1.1/32 -j REJECT
    "$binary" -w -A PCC_EMULATOR -d 169.254.169.254/32 -j REJECT
  fi
  "$binary" -w -A PCC_EMULATOR -j REJECT
  "$binary" -w -C OUTPUT -m owner --uid-owner "$emu_uid" -j PCC_EMULATOR 2>/dev/null || "$binary" -w -I OUTPUT 1 -m owner --uid-owner "$emu_uid" -j PCC_EMULATOR
done
