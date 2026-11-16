"""Download upstream sources and collect their license/copyright notices."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'build/release-sources'
LICENSES = ROOT / 'build/release-licenses'


def download(url, target, expected=None):
    if not target.exists():
        print('Downloading', target.name, flush=True)
        temp = target.with_suffix(target.suffix + '.part')
        with urllib.request.urlopen(url, timeout=60) as response, temp.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        temp.replace(target)
    with target.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if expected and digest != expected:
        raise ValueError(f'Checksum mismatch: {target.name}')
    return digest


def collect_notices(archive, destination):
    count = 0
    with tarfile.open(archive, 'r|*') as source:
        for member in source:
            path = PurePosixPath(member.name)
            filename = path.name.lower()
            if not member.isfile() or not (
                'licenses' in [p.lower() for p in path.parts]
                or re.match(r'^(licen[sc]e|copying|copyright|notice)([._-]|$)', filename)
            ):
                continue
            if '..' in path.parts or path.is_absolute() or member.size > 5_000_000:
                raise ValueError(f'Unsafe license path: {member.name}')
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as content, target.open('wb') as output:
                shutil.copyfileobj(content, output)
            count += 1
    if not count:
        raise ValueError(f'No notices found in {archive.name}')
    return count


def main():
    SOURCES.mkdir(parents=True, exist_ok=True)
    LICENSES.mkdir(parents=True, exist_ok=True)
    pins = dict(re.findall(r'^([\w-]+)==([\d.]+)',
                          (ROOT / 'requirements-release.txt').read_text(), re.M))
    qt = pins['PySide6']
    minor = '.'.join(qt.split('.')[:2])
    urls = [
        (f'https://download.qt.io/archive/qt/{minor}/{qt}/single/qt-everywhere-src-{qt}.tar.xz', 'Qt', None),
        (f'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{qt}-src/pyside-setup-everywhere-src-{qt}.tar.xz', 'PySide6-Shiboken6', None),
    ]
    # Include exact package sources as well as the complete Qt/PySide sources.
    for package in ('numpy', 'Pillow', 'pyobjc-core', 'pyobjc-framework-Cocoa', 'pyinstaller'):
        with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{pins[package]}/json', timeout=30) as response:
            info = json.load(response)
        source = next(item for item in info['urls'] if item['packagetype'] == 'sdist')
        urls.append((source['url'], package, source['digests']['sha256']))
    manifest = []
    for url, component, expected in urls:
        filename = url.rsplit('/', 1)[-1]
        target = SOURCES / filename
        digest = download(url, target, expected)
        count = collect_notices(target, LICENSES / component)
        manifest.append({'component': component, 'file': filename, 'url': url,
                         'sha256': digest, 'license_files': count})
        print(component, count, 'notice files', flush=True)
    text = json.dumps(manifest, indent=2) + '\n'
    (SOURCES / 'UPSTREAM-SOURCES.json').write_text(text, encoding='utf-8')
    (LICENSES / 'UPSTREAM-SOURCES.json').write_text(text, encoding='utf-8')
    (SOURCES / 'SHA256SUMS').write_text(
        ''.join(f"{m['sha256']}  {m['file']}\n" for m in manifest), encoding='utf-8')


if __name__ == '__main__':
    main()
