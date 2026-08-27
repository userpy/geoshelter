#!/usr/bin/env python3
"""Build a standalone PyInstaller ``--onedir`` Debian package.

Examples::

    python3 build_deb.py
    python3 build_deb.py --clean
    python3 build_deb.py --version 1.2.0 --maintainer "Name <mail@example.com>"
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


PROJECT_DIR = Path(__file__).resolve().parent
PYPROJECT = PROJECT_DIR / "pyproject.toml"
LINUX_BUILD_DIR = PROJECT_DIR / "build" / "linux"
WORK_DIR = LINUX_BUILD_DIR / ".work"

# GeoShelter displays SVG icons and runs on regular X11/Wayland desktops. These
# Qt plugins target embedded/framebuffer environments or unused image formats.
UNUSED_QT_PLUGIN_DIRS = ("egldeviceintegrations",)
UNUSED_QT_PLUGINS = (
    "platforms/libqeglfs.so",
    "platforms/libqlinuxfb.so",
    "platforms/libqminimal.so",
    "platforms/libqminimalegl.so",
    "platforms/libqvkkhrdisplay.so",
    "platforms/libqvnc.so",
    "imageformats/libqicns.so",
    "imageformats/libqpdf.so",
    "imageformats/libqtga.so",
    "imageformats/libqtiff.so",
    "imageformats/libqwbmp.so",
    "imageformats/libqwebp.so",
)
KEPT_QT_TRANSLATIONS = {
    "qt_en.qm",
    "qt_ru.qm",
    "qtbase_en.qm",
    "qtbase_ru.qm",
}
UNUSED_QT_LIBRARIES = (
    "libQt6EglFSDeviceIntegration.so.6",
    "libQt6Pdf.so.6",
)


@dataclass(frozen=True)
class Metadata:
    package: str
    display_name: str
    version: str
    entry_point: Path
    executable: str
    maintainer: str
    description: str
    icon: Path | None


def log(message: str) -> None:
    print(f"==> {message}", flush=True)


def run(
    command: list[str], *, cwd: Path = PROJECT_DIR, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )


def fail(message: str) -> NoReturn:
    raise RuntimeError(message)


def load_project() -> dict[str, object]:
    if not PYPROJECT.is_file():
        fail(f"Не найден {PYPROJECT.name} в {PROJECT_DIR}")
    with PYPROJECT.open("rb") as stream:
        data = tomllib.load(stream)
    project = data.get("project")
    if not isinstance(project, dict):
        fail("В pyproject.toml отсутствует таблица [project].")
    return project


def debian_package_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9+.-]+", "-", value.lower()).strip("-+.")
    if not name or not name[0].isalnum():
        fail(f"Нельзя преобразовать имя {value!r} в имя Debian-пакета.")
    return name


def debian_version(value: str) -> str:
    version = value.strip().replace("_", ".")
    version = re.sub(r"[^A-Za-z0-9.+:~\-]", "+", version)
    if not version or not version[0].isdigit():
        version = f"0+{version}"
    return version


def one_line(value: str) -> str:
    return " ".join(value.split())


def discover_metadata(args: argparse.Namespace) -> Metadata:
    project = load_project()
    raw_name = args.name or str(project.get("name") or "application")
    package = debian_package_name(raw_name)
    version = debian_version(args.version or str(project.get("version") or "0.0.0"))
    description = one_line(
        args.description or str(project.get("description") or raw_name)
    )

    maintainer = args.maintainer
    if not maintainer:
        authors = project.get("authors")
        author = authors[0] if isinstance(authors, list) and authors else {}
        if not isinstance(author, dict):
            author = {}
        maintainer = str(author.get("name") or f"{raw_name} developers")
        if author.get("email"):
            maintainer += f" <{author['email']}>"

    entry = (args.entry_point or PROJECT_DIR / "src" / "main.py").resolve()
    if not entry.is_file() or PROJECT_DIR not in entry.parents:
        fail(f"Точка входа не найдена внутри проекта: {entry}")

    icon = args.icon.resolve() if args.icon else PROJECT_DIR / "src/assets/app_icon.svg"
    if not icon.is_file():
        print(f"Предупреждение: иконка не найдена: {icon}", file=sys.stderr)
        icon = None

    return Metadata(
        package=package,
        display_name="GeoShelter" if raw_name.lower() == "geoshelter" else raw_name,
        version=version,
        entry_point=entry,
        executable=package,
        maintainer=one_line(maintainer),
        description=description,
        icon=icon,
    )


def check_tools() -> tuple[str, str, str]:
    if platform.system() != "Linux":
        fail("DEB-пакет необходимо собирать в Linux.")
    missing = [tool for tool in ("dpkg", "dpkg-deb") if not shutil.which(tool)]
    try:
        run([sys.executable, "-m", "PyInstaller", "--version"], capture=True)
    except (OSError, subprocess.CalledProcessError):
        missing.append("PyInstaller")
    if missing:
        fail(
            f"Не найдены инструменты: {', '.join(missing)}.\n"
            "Установка для Ubuntu/Kubuntu:\n"
            "  python3 -m pip install pyinstaller\n"
            "  sudo apt install dpkg-dev"
        )
    return shutil.which("dpkg") or "dpkg", shutil.which("dpkg-deb") or "dpkg-deb", shutil.which("ldd") or "ldd"


def safe_remove_work() -> None:
    expected = LINUX_BUILD_DIR.resolve() / ".work"
    resolved = WORK_DIR.resolve()
    if resolved != expected or resolved == PROJECT_DIR.resolve():
        fail(f"Отказ удалять небезопасный путь: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def write_text(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def installed_size(root: Path) -> int:
    # lstat avoids counting a symlink target for every link to a bundled Qt library.
    total = sum(
        p.lstat().st_size
        for p in root.rglob("*")
        if (p.is_file() or p.is_symlink()) and "DEBIAN" not in p.parts
    )
    return max(1, (total + 1023) // 1024)


def normalize_permissions(root: Path, executable: Path) -> None:
    root.chmod(0o755)
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            path.chmod(0o755 if path == executable or os.access(path, os.X_OK) else 0o644)


def create_package_tree(meta: Metadata, pyinstaller_dir: Path, package_root: Path) -> Path:
    app_dir = package_root / "opt" / meta.package
    # PyInstaller uses relative links for duplicate Qt libraries. Preserve them;
    # following the links inflates Installed-Size by tens of megabytes.
    shutil.copytree(pyinstaller_dir, app_dir, symlinks=True)
    binary = app_dir / meta.executable
    if not binary.is_file():
        fail(f"PyInstaller не создал главный бинарник: {binary}")

    write_text(
        package_root / "usr/bin" / meta.package,
        f'#!/bin/sh\nexec /opt/{meta.package}/{meta.executable} "$@"\n',
        0o755,
    )
    write_text(
        package_root / "usr/share/applications" / f"{meta.package}.desktop",
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={meta.display_name}\n"
        f"Comment={meta.description}\n"
        f"Exec={meta.package}\n"
        f"Icon={meta.package}\n"
        "Terminal=false\n"
        "Categories=Utility;Geography;\n"
        "StartupNotify=true\n",
    )
    if meta.icon:
        icon_dir = "scalable" if meta.icon.suffix.lower() == ".svg" else "256x256"
        target = package_root / "usr/share/icons/hicolor" / icon_dir / "apps" / f"{meta.package}{meta.icon.suffix.lower()}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(meta.icon, target)
    normalize_permissions(package_root, binary)
    return binary


def optimize_pyinstaller_tree(app_dir: Path) -> None:
    """Remove Qt assets which GeoShelter cannot use, retaining desktop support."""
    qt_dir = app_dir / "_internal" / "PyQt6" / "Qt6"
    plugins_dir = qt_dir / "plugins"
    removed_bytes = 0

    for relative in UNUSED_QT_PLUGIN_DIRS:
        target = plugins_dir / relative
        if target.is_dir():
            removed_bytes += sum(
                item.stat().st_size for item in target.rglob("*") if item.is_file()
            )
            shutil.rmtree(target)

    for relative in UNUSED_QT_PLUGINS:
        target = plugins_dir / relative
        if target.is_file():
            removed_bytes += target.stat().st_size
            target.unlink()

    translations = qt_dir / "translations"
    if translations.is_dir():
        for translation in translations.iterdir():
            if translation.is_file() and translation.name not in KEPT_QT_TRANSLATIONS:
                removed_bytes += translation.stat().st_size
                translation.unlink()

    # Their only consumers were the EGLFS and PDF image plugins removed above.
    qt_libraries = qt_dir / "lib"
    internal_dir = app_dir / "_internal"
    for library_name in UNUSED_QT_LIBRARIES:
        library = qt_libraries / library_name
        if library.is_file():
            removed_bytes += library.stat().st_size
            library.unlink()
        link = internal_dir / library_name
        if link.is_symlink():
            link.unlink()

    log(f"Удалено неиспользуемых Qt-ресурсов: {removed_bytes / 1024 / 1024:.1f} MiB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_package(output: Path, meta: Metadata, binary: Path, dpkg_deb: str, ldd: str) -> None:
    if not output.is_file() or output.stat().st_size == 0:
        fail(f"Готовый DEB не создан или пуст: {output}")
    info = run([dpkg_deb, "--info", str(output)], capture=True)
    contents = run([dpkg_deb, "--contents", str(output)], capture=True)
    print(info.stdout, end="")
    print(contents.stdout, end="")
    required = (f"./usr/bin/{meta.package}", f"./usr/share/applications/{meta.package}.desktop", f"./opt/{meta.package}/")
    for item in required:
        if item not in contents.stdout:
            fail(f"В DEB отсутствует {item}")
    if re.search(r"^ Depends:.*\bpython3\b", info.stdout, re.MULTILINE):
        fail("В Depends ошибочно указан python3.")
    if not os.access(binary, os.X_OK):
        fail(f"Главный бинарник не исполняемый: {binary}")
    ldd_result = run([ldd, str(binary)], capture=True)
    print(ldd_result.stdout, end="")
    if "not found" in ldd_result.stdout.lower():
        fail("ldd обнаружил ненайденные динамические библиотеки.")


def build(args: argparse.Namespace) -> Path:
    meta = discover_metadata(args)
    dpkg, dpkg_deb, ldd = check_tools()
    architecture = run([dpkg, "--print-architecture"], capture=True).stdout.strip()
    LINUX_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    safe_remove_work()
    WORK_DIR.mkdir(parents=True)
    dist_dir = WORK_DIR / "dist"
    package_root = WORK_DIR / "package-root"

    log(f"PyInstaller --onedir: {meta.entry_point.relative_to(PROJECT_DIR)}")
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--windowed", "--strip", "--name", meta.executable, "--distpath", str(dist_dir),
        "--workpath", str(WORK_DIR / "pyinstaller"), "--specpath", str(WORK_DIR / "spec"),
        "--paths", str(PROJECT_DIR / "src"),
    ]
    assets = PROJECT_DIR / "src" / "assets"
    if assets.is_dir():
        command.extend(["--add-data", f"{assets}{os.pathsep}assets"])
    command.append(str(meta.entry_point))
    run(command)

    log("Оптимизация Qt-ресурсов")
    optimize_pyinstaller_tree(dist_dir / meta.executable)
    log("Формирование корня Debian-пакета")
    binary = create_package_tree(meta, dist_dir / meta.executable, package_root)
    control = (
        f"Package: {meta.package}\nVersion: {meta.version}\nSection: utils\n"
        f"Priority: optional\nArchitecture: {architecture}\nMaintainer: {meta.maintainer}\n"
        f"Installed-Size: {installed_size(package_root)}\nDepends:\n"
        f"Description: {meta.description}\n"
        " Standalone desktop application for downloading Wikimapia places and creating KML/KMZ files.\n"
    )
    write_text(package_root / "DEBIAN/control", control)
    (package_root / "DEBIAN").chmod(0o755)

    output = LINUX_BUILD_DIR / f"{meta.package}_{meta.version}_{architecture}.deb"
    if output.exists():
        output.unlink()
    log("Сборка DEB")
    run([dpkg_deb, "--build", "--root-owner-group", str(package_root), str(output)])
    log("Проверка DEB, его состава и динамических библиотек")
    verify_package(output, meta, binary, dpkg_deb, ldd)

    digest = sha256(output)
    print(f"\nГотово: {output}")
    print(f"Размер: {output.stat().st_size} байт")
    print(f"Архитектура: {architecture}")
    print(f"Версия: {meta.version}")
    print(f"SHA-256: {digest}")
    print(f"Установка: sudo apt install ./{output.relative_to(PROJECT_DIR)}")
    print(f"Удаление: sudo apt remove {meta.package}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Собрать standalone Linux-приложение в DEB")
    parser.add_argument("--name")
    parser.add_argument("--version")
    parser.add_argument("--entry-point", type=Path)
    parser.add_argument("--maintainer")
    parser.add_argument("--description")
    parser.add_argument("--icon", type=Path)
    parser.add_argument("--clean", action="store_true", help="удалить только build/linux/.work перед сборкой")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.clean:
            safe_remove_work()
        build(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Ошибка сборки: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
