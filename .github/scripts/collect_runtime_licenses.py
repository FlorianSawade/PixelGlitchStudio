"""Add installed-wheel notices and the license of the bundled CPython version."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
output = ROOT / 'build/release-licenses'
output.mkdir(parents=True, exist_ok=True)
# A new interpreter/environment must not retain notices from an earlier build.
shutil.rmtree(output / 'installed-packages', ignore_errors=True)
for previous in output.glob('Python-*-LICENSE.txt'):
    previous.unlink()
for dist in distributions():
    for item in dist.files or []:
        name = item.name.lower()
        if name in ('license', 'license.txt', 'license.md', 'copying', 'copying.txt', 'notice', 'notice.txt') or '.dist-info/licenses/' in str(item):
            source = Path(dist.locate_file(item))
            if not source.is_file():
                continue
            target = output / 'installed-packages' / dist.metadata['Name'] / str(item)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
version = '.'.join(map(str, sys.version_info[:3]))
url = f'https://raw.githubusercontent.com/python/cpython/v{version}/LICENSE'
with urllib.request.urlopen(url, timeout=30) as response:
    license_text = response.read()
if b'PYTHON SOFTWARE FOUNDATION' not in license_text:
    raise ValueError('Unexpected Python license content')
(output / f'Python-{version}-LICENSE.txt').write_bytes(license_text)
