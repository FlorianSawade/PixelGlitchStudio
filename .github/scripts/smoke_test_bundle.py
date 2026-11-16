"""Run the actual frozen executable and require its startup/render/export report."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pixelglitch import __version__

executable = (ROOT / 'dist/PixelGlitchStudio.app/Contents/MacOS/PixelGlitchStudio' if sys.platform == 'darwin'
              else ROOT / 'dist/PixelGlitchStudio' / ('PixelGlitchStudio.exe' if sys.platform == 'win32' else 'PixelGlitchStudio'))
with tempfile.TemporaryDirectory(prefix='pixelglitch-bundle-check-') as temp:
    report = Path(temp) / 'result.json'
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PIXELGLITCH_SMOKE_RESULT': str(report)}
    subprocess.run([str(executable), '--smoke-test'], env=env, check=True, timeout=60)
    result = json.loads(report.read_text(encoding='utf-8'))
    if result != {'version': __version__, 'startup': True, 'render': True, 'export': True}:
        raise RuntimeError(f'Unexpected smoke-test result: {result}')
    print('Packaged app: startup, render and export OK')
