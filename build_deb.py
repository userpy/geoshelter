#!/usr/bin/env python3
"""Build an installable GeoShelter Debian package in ./build."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
BUILD_DIR = PROJECT_DIR / "build"
INSTALL_DIR = Path("opt/geoshelter")


def run(*command: str, cwd: Path = PROJECT_DIR) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def project_metadata() -> tuple[str, str, str]:
    with (PROJECT_DIR / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)["project"]
    author = project.get("authors", [{}])[0]
    maintainer = author.get("name", "GeoShelter developers")
    if email := author.get("email"):
        maintainer = f"{maintainer} <{email}>"
    return project["name"], project["version"], maintainer


def architecture() -> str:
    result = subprocess.run(
        ["dpkg", "--print-architecture"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def installed_size(package_root: Path) -> int:
    total = sum(
        path.stat().st_size
        for path in package_root.rglob("*")
        if path.is_file() and "DEBIAN" not in path.parts
    )
    return max(1, (total + 1023) // 1024)


def build_package(output_dir: Path) -> Path:
    uv = shutil.which("uv")
    dpkg_deb = shutil.which("dpkg-deb")
    if not uv:
        raise RuntimeError("Не найден uv. Установите uv и повторите сборку.")
    if not dpkg_deb:
        raise RuntimeError("Не найден dpkg-deb. Установите пакет dpkg-dev.")
    if not (PROJECT_DIR / "uv.lock").is_file():
        raise RuntimeError("Не найден uv.lock; выполните `uv lock`.")

    name, version, maintainer = project_metadata()
    arch = architecture()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{name}_{version}_{arch}.deb"

    with tempfile.TemporaryDirectory(prefix="geoshelter-deb-", dir=output_dir) as tmp:
        package_root = Path(tmp) / "root"
        app_dir = package_root / INSTALL_DIR
        requirements = Path(tmp) / "requirements.txt"
        app_dir.mkdir(parents=True)

        run(
            uv,
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--output-file",
            str(requirements),
        )
        run(
            uv,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(app_dir),
            "--requirements",
            str(requirements),
        )
        run(
            uv,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--target",
            str(app_dir),
            "--no-deps",
            str(PROJECT_DIR),
        )

        launcher = (
            "#!/bin/sh\n"
            "export PYTHONPATH=/opt/geoshelter\n"
            "exec python3 -c 'from main import main; raise SystemExit(main())' \"$@\"\n"
        )
        cli_launcher = (
            "#!/bin/sh\n"
            "export PYTHONPATH=/opt/geoshelter\n"
            "exec python3 -c 'from cli import main; raise SystemExit(main())' \"$@\"\n"
        )
        write_text(package_root / "usr/bin/geoshelter", launcher, 0o755)
        write_text(package_root / "usr/bin/geoshelter-cli", cli_launcher, 0o755)

        icon_source = PROJECT_DIR / "src/assets/app_icon.svg"
        icon_target = (
            package_root
            / "usr/share/icons/hicolor/scalable/apps/geoshelter.svg"
        )
        icon_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_source, icon_target)
        write_text(
            package_root / "usr/share/applications/geoshelter.desktop",
            """[Desktop Entry]
Type=Application
Name=GeoShelter
Comment=Загрузка объектов Wikimapia в KML
Exec=geoshelter
Icon=geoshelter
Terminal=false
Categories=Utility;Geography;
StartupNotify=true
""",
        )

        control = f"""Package: {name}
Version: {version}
Section: utils
Priority: optional
Architecture: {arch}
Depends: python3 (>= 3.12)
Installed-Size: {installed_size(package_root)}
Maintainer: {maintainer}
Description: Wikimapia places downloader and KML/KMZ utility
 GeoShelter downloads places from Wikimapia and saves them as KML files.
 It also combines KML files into a categorized KMZ archive.
"""
        write_text(package_root / "DEBIAN/control", control)
        os.chmod(package_root / "DEBIAN", 0o755)

        if output_file.exists():
            output_file.unlink()
        run(dpkg_deb, "--build", "--root-owner-group", str(package_root), str(output_file))

    print(f"\nГотово: {output_file}")
    return output_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Собрать GeoShelter в DEB-пакет"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BUILD_DIR,
        help="каталог результата (по умолчанию: ./build)",
    )
    args = parser.parse_args()
    try:
        build_package(args.output_dir.resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Ошибка сборки: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
