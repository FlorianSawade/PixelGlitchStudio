"""Fail when source/license pins and the hashed installation lock disagree."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def pins(path):
    return {name.lower().replace('_', '-'): version
            for name, version in re.findall(r'^([\w.-]+)==([^\s;\\]+)', path.read_text(), re.M)}


def main():
    direct = pins(ROOT / 'requirements-release.txt')
    locked = pins(ROOT / 'requirements-release-lock.txt')
    mismatches = {name: (version, locked.get(name)) for name, version in direct.items()
                  if locked.get(name) != version}
    if not direct or mismatches:
        raise SystemExit(f'Release pins differ from lock: {mismatches}')
    print(f'Release lock matches all {len(direct)} direct dependency pins')


if __name__ == '__main__':
    main()
