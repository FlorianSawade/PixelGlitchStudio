"""Package an onedir build without losing macOS symlinks or Unix permissions."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pixelglitch import __version__


def package(platform):
    name = f"PixelGlitchStudio-v{__version__}-{platform}"
    stage = ROOT / "build" / "packages" / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    app_name = "PixelGlitchStudio.app" if platform.startswith("macos-") else "PixelGlitchStudio"
    source = ROOT / "dist" / app_name
    executable = (source / "Contents/MacOS/PixelGlitchStudio" if app_name.endswith(".app")
                  else source / ("PixelGlitchStudio.exe" if platform.startswith("windows-")
                                 else "PixelGlitchStudio"))
    if not executable.is_file():
        raise FileNotFoundError(f"Build missing: {executable}")
    shutil.copytree(source, stage / app_name, symlinks=True)
    for filename in ("LICENSE", "README.md", "CHANGELOG.md", "BUILD.md", "requirements.txt",
                     "requirements-release.txt", "requirements-release-lock.txt"):
        shutil.copy2(ROOT / filename, stage / filename)
    shutil.copytree(ROOT / "docs", stage / "docs", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "build" / "dependencies.txt", stage / "dependencies.txt")
    shutil.copytree(ROOT / "build" / "release-licenses", stage / "THIRD_PARTY_LICENSES")
    third_party = (ROOT / "docs" / "THIRD_PARTY.md").read_text(encoding="utf-8")
    (stage / "THIRD_PARTY.md").write_text(
        third_party.replace("](../LICENSE)", "](LICENSE)").replace("](../BUILD.md)", "](BUILD.md)"),
        encoding="utf-8")
    (stage / "START.txt").write_text(
        "PixelGlitch Studio " + __version__ + "\n\n"
        "macOS: Open PixelGlitchStudio.app.\n"
        "Windows: Extract the entire archive, then open PixelGlitchStudio/PixelGlitchStudio.exe.\n"
        "Linux: Extract the archive, then run ./PixelGlitchStudio/PixelGlitchStudio.\n\n"
        "Unsigned application: see docs/INSTALLATION.md for startup instructions.\n"
        "Copyright (c) 2026 Florian Sawade. GPL-3.0-only; see LICENSE.\n"
        "Third-party components retain their own licenses.\n",
        encoding="utf-8",
    )
    output = ROOT / "dist" / "packages"
    output.mkdir(parents=True, exist_ok=True)
    if platform.startswith("macos-"):
        archive = output / f"{name}.zip"
        if archive.exists():
            archive.unlink()
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(stage), str(archive)], check=True)
    elif platform.startswith("windows-"):
        archive = Path(shutil.make_archive(str(output / name), "zip", stage.parent, name))
    else:
        archive = output / f"{name}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(stage, arcname=name)
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8")
    print(archive)
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=(
        "macos-arm64", "macos-x86_64", "windows-x86_64", "linux-x86_64"))
    package(parser.parse_args().platform)
