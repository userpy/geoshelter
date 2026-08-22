#!/usr/bin/env python3
"""Build the Windows GeoShelter GUI as a standalone executable."""

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
SRC_DIR = PROJECT_DIR / "src"
ASSETS_DIR = SRC_DIR / "assets"
ENTRY_POINT = SRC_DIR / "main.py"
BUILD_DIR = PROJECT_DIR / "build" / "windows"
EXECUTABLE_NAME = "GeoShelter"


def run(*command: str) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=PROJECT_DIR, check=True)


def project_version() -> str:
    with (PROJECT_DIR / "pyproject.toml").open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


def render_windows_icon(output_file: Path) -> None:
    """Render the SVG icon to PNG for PyInstaller's Pillow converter."""
    try:
        from PyQt6.QtCore import QRectF, Qt
        from PyQt6.QtGui import QImage, QPainter
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError as error:
        raise RuntimeError(
            "Не найден PyQt6. Запустите сборку командой `uv run python build_exe.py`."
        ) from error

    renderer = QSvgRenderer(str(ASSETS_DIR / "app_icon.svg"))
    if not renderer.isValid():
        raise RuntimeError("Не удалось прочитать src/assets/app_icon.svg.")

    size = 256
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    if not image.save(str(output_file), "PNG"):
        raise RuntimeError("Не удалось подготовить иконку Windows.")


def build_executable(output_dir: Path) -> Path:
    if os.name != "nt":
        raise RuntimeError(
            "Windows EXE необходимо собирать в Windows: PyInstaller "
            "не поддерживает кросс-компиляцию."
        )

    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("Не найден uv. Установите uv и повторите сборку.")
    if not (PROJECT_DIR / "uv.lock").is_file():
        raise RuntimeError("Не найден uv.lock; выполните `uv lock`.")
    if not ENTRY_POINT.is_file():
        raise RuntimeError(f"Не найдена точка запуска: {ENTRY_POINT}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{EXECUTABLE_NAME}.exe"

    with tempfile.TemporaryDirectory(prefix="geoshelter-exe-") as temp:
        temp_dir = Path(temp)
        icon_file = temp_dir / "app_icon.png"
        render_windows_icon(icon_file)

        run(
            uv,
            "run",
            "--frozen",
            "--group",
            "build",
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            EXECUTABLE_NAME,
            "--distpath",
            str(output_dir),
            "--workpath",
            str(temp_dir / "work"),
            "--specpath",
            str(temp_dir / "spec"),
            "--paths",
            str(SRC_DIR),
            "--add-data",
            f"{ASSETS_DIR}{os.pathsep}assets",
            "--icon",
            str(icon_file),
            str(ENTRY_POINT),
        )

    if not output_file.is_file():
        raise RuntimeError(f"PyInstaller не создал ожидаемый файл: {output_file}")

    print(f"\nГотово: {output_file} (GeoShelter {project_version()})")
    return output_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Собрать Windows-версию GeoShelter в один EXE-файл"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BUILD_DIR,
        help="каталог результата (по умолчанию: ./build/windows)",
    )
    args = parser.parse_args()
    try:
        build_executable(args.output_dir.resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Ошибка сборки: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
