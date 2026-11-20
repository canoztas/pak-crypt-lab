"""Unpack samples.zip (password: infected) and check every APK against SHA256SUMS.

Usage: python3 unpack_samples.py <folder with samples.zip and SHA256SUMS> <destination>
The archive is password-protected so that the samples cannot be opened or installed by accident.
"""
from pathlib import Path
import hashlib, sys, zipfile

source, destination = Path(sys.argv[1]), Path(sys.argv[2])
expected = {}
for line in (source / 'SHA256SUMS').read_text().splitlines():
    if line.strip():
        digest, name = line.split(None, 1)
        expected[name.lstrip('*').strip()] = digest.lower()
destination.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(source / 'samples.zip') as archive:
    names = sorted(archive.namelist())
    if names != sorted(expected):
        raise SystemExit('samples.zip does not hold exactly the files listed in SHA256SUMS')
    for name in names:
        if Path(name).name != name:
            raise SystemExit('Unexpected path inside samples.zip: ' + name)
        data = archive.read(name, pwd=b'infected')
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected[name]:
            raise SystemExit('SHA-256 mismatch for ' + name)
        (destination / name).write_bytes(data)
        print(name + ': ' + digest)
