import copy
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
KML_TAG = f"{{{KML_NAMESPACE}}}"
FEATURE_NAMES = {
    "Document",
    "Folder",
    "Placemark",
    "NetworkLink",
    "GroundOverlay",
    "PhotoOverlay",
    "ScreenOverlay",
}

ET.register_namespace("", KML_NAMESPACE)
ET.register_namespace("gx", "http://www.google.com/kml/ext/2.2")


def category_from_filename(path: Path) -> str:
    match = re.search(r"wikimapia_(\d+)(?:_|\b)", path.stem, re.IGNORECASE)
    return match.group(1) if match else path.stem


def merge_kml_by_category(
    sources: list[tuple[Path, str]], output_file: Path
) -> tuple[int, int]:
    """Merge KML features into category folders and package them as a KMZ."""
    if not sources:
        raise ValueError("Добавьте хотя бы один KML-файл")
    if output_file.suffix.lower() != ".kmz":
        output_file = output_file.with_suffix(".kmz")

    grouped: dict[str, list[Path]] = defaultdict(list)
    for path, category in sources:
        path = Path(path)
        category = category.strip()
        if not category:
            raise ValueError(f"Не указана категория для {path.name}")
        if path.suffix.lower() != ".kml" or not path.is_file():
            raise ValueError(f"KML-файл не найден: {path}")
        grouped[category].append(path)

    root = ET.Element(f"{KML_TAG}kml")
    document = ET.SubElement(root, f"{KML_TAG}Document")
    ET.SubElement(document, f"{KML_TAG}name").text = output_file.stem
    feature_count = 0

    for category, paths in grouped.items():
        folder = ET.SubElement(document, f"{KML_TAG}Folder")
        ET.SubElement(folder, f"{KML_TAG}name").text = category
        for path in paths:
            try:
                source_root = ET.parse(path).getroot()
            except ET.ParseError as error:
                raise ValueError(f"Некорректный KML {path.name}: {error}") from error

            containers = (
                list(source_root)
                if _local_name(source_root.tag) == "kml"
                else [source_root]
            )
            for container in containers:
                children = (
                    list(container)
                    if _local_name(container.tag) in {"Document", "Folder"}
                    else [container]
                )
                for child in children:
                    if _local_name(child.tag) in FEATURE_NAMES - {"Document"}:
                        folder.append(copy.deepcopy(child))
                        feature_count += 1

    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", xml)
    return len(grouped), feature_count


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
