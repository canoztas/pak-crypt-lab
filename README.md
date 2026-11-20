# Pak-Crypt mobile malware lab

Three hands-on Android malware analysis labs, with the machine they run on.
Made by WISE Lab, Hacettepe University, for the Pak-Crypt workshop
*Mobile Malware Analysis: Static and Dynamic*.

One script turns an Ubuntu machine into the lab: an Android 12 phone that cannot reach
any network, adb, Frida, jadx and three real samples. Each lab then asks the same
question in a different shape: what does this app do when it runs?

| Lab | Sample | What you find |
|---|---|---|
| 1 | Google Service Framework, an AndroRAT build posing as a system component | The server address in the code, the same address at run time, a YARA rule that matches it |
| 2 | Brokewell, a courier app | A second APK carried inside, installed with the user's consent, and what that second app asks for |
| 3 | Authenticator downloader, a fake 2FA app | Strings that are assembled letter by letter in the code, read whole from the running process |

## Read this first

**The samples are real malware.** They are here for teaching and research.

- Run them only on the lab phone this repository builds. Never install them on a real device.
- The archive `samples/samples.zip` is password-protected so that nothing opens or installs by
  accident. The password is `infected`, the usual convention for malware samples.
- The phone has no route out. The emulator runs under its own account, and a firewall rule
  rejects every connection that account starts. The installer and every phone reset prove
  this before they report success; if the check fails, they stop.
- You are responsible for using this lawfully where you are.

## What you need

- Ubuntu 22.04 or 24.04, x86_64. Tested end to end on Ubuntu 24.04.
- Hardware virtualisation (VT-x or AMD-V). On a virtual machine, turn on nested virtualisation.
- 8 GB of memory or more, 15 GB of free disk, and a desktop session if you want to see the phone.
- An internet connection during installation. The lab itself needs none.

## Install

```
git clone https://github.com/canoztas/pak-crypt-lab.git
cd pak-crypt-lab
sudo ./install.sh
```

It takes ten to fifteen minutes, most of it downloading the Android SDK and system image.
Add `--with-model` if you want the optional step in Lab 3 that asks a small local model to
summarise a class (about 1 GB more).

When it says `Ready`, open a **new** terminal and check the lab:

```
cd /opt/pcc-lab/demo
adb devices
frida-ps -H 127.0.0.1:27042 -a
```

The first command lists the phone, the second lists the apps running on it.

To run the core of all three labs unattended and see whether your machine reproduces them:

```
sudo /opt/pcc-lab/venv/bin/python /opt/pcc-lab/selftest.py
```

## Doing the labs

Every command of every lab is on your machine, in order, with a comment line above each step:

```
/opt/pcc-lab/demo/commands/check.txt
/opt/pcc-lab/demo/commands/lab1.txt
/opt/pcc-lab/demo/commands/lab2.txt
/opt/pcc-lab/demo/commands/lab3.txt
```

Open one, paste the commands into a terminal one step at a time, and reset the phone between
labs. Each lab follows the same four moves: put the APK on the phone, read the code in jadx,
watch it run with Frida, write down what you found.

Things you will use:

- **The phone.** Open *Android Phone* on the desktop, or run `/opt/pcc-lab/android_screen.sh`.
  Drop an APK on the window to install it, or use `adb install ~/Desktop/<file>.apk`.
- **The samples.** `service_framework.apk`, `brokewell.apk` and `authenticator_downloader.apk`
  are on your desktop.
- **jadx.** `jadx-gui ~/Desktop/<file>.apk &`
- **The Frida scripts.** `/opt/pcc-lab/demo/hooks/`. They only observe: they print what the
  app does and send nothing to it.
- **Reset.** `python3 ~/Desktop/reset_phone.py` gives you a factory-fresh phone in a minute or
  two. Do it between labs. After a reboot of your machine the phone is off; the same command
  starts it.

## What is in the box

```
install.sh, uninstall.sh   set the lab up, take it away
samples/                   samples.zip (password: infected) and SHA256SUMS
lab/                       the scripts install.sh puts under /opt/pcc-lab
lab/demo/hooks/            Frida scripts used in the labs
lab/demo/rules/            the YARA rules the labs arrive at
lab/demo/commands/         every command of every lab, in order
```

## The samples

| File | Package | SHA-256 |
|---|---|---|
| service_framework.apk | com.example.reverseshell2 | `347f1b018f643de0b9c946c94bd490a7426503869a0828b0a70b4d318fa097d6` |
| brokewell.apk | xyIBgcE.FKnaCEV.XDKUPweO | `48b2095d9f746bb60ddf126365a9bb9ebaeae36f21dc1b5fa2213eafbdc9f18b` |
| authenticator_downloader.apk | com.privacy.account.safetyapp | `00a733c78f1b4d4f54cf06a0ea8cc33604512d6032ef4ef9114c89c700bfafcf` |

The first two come from MalwareBazaar (abuse.ch); the third is from the public
sk3ptre/AndroidMalware_2022 collection. The installer checks each file against
`samples/SHA256SUMS` before it is used. The labs were verified on AOSP Android 12 (API 31,
x86_64); `service_framework.apk` targets API 22 and will not install on Android 14 or later.

## How the phone is kept offline

- The emulator runs as a dedicated account, `androidemu`, started by a systemd service.
- `lab/isolate_emulator.sh` adds an iptables chain, `PCC_EMULATOR`, that rejects every new
  connection made by that account, IPv4 and IPv6. Replies to adb, which connects *to* the
  emulator, are the only traffic allowed.
- Every reset tries to reach the internet twice, once as that account and once from inside
  Android, and requires the firewall's reject counter to move. No pass, no phone.

You can read the chain yourself: `sudo iptables -S PCC_EMULATOR`.

## Remove it

```
sudo ./uninstall.sh
```

This stops the services and removes `/opt/pcc-lab`, `/opt/android-sdk`, the emulator
account, the firewall chain and the files it put on your desktop.

## Credits

WISE Lab, Hacettepe University. Samples via MalwareBazaar and sk3ptre/AndroidMalware_2022. Built on the Android emulator,
[Frida](https://frida.re), [jadx](https://github.com/skylot/jadx) and
[YARA](https://virustotal.github.io/yara/).
