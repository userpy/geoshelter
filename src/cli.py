import asyncio
from pathlib import Path

from loguru import logger

from application.download_places import DownloadPlaces
from domain.models import DownloadSettings
from infrastructure.app_settings import DEFAULT_SETTINGS
from infrastructure.kml_writer import KmlPlacesWriter
from infrastructure.wikimapia_client import WikimapiaClient


def main() -> int:
    api_keys = tuple(
        key.strip()
        for key in str(DEFAULT_SETTINGS["api_keys"]).split(",")
        if key.strip()
    )
    if not api_keys:
        logger.error("WIKIMAPIA_API_KEY не задан в .env")
        return 1
    settings = DownloadSettings(
        api_keys=api_keys,
        categories=tuple(
            int(value.strip())
            for value in str(DEFAULT_SETTINGS["categories"]).split(",")
        ),
        top_point=_point(DEFAULT_SETTINGS["top_point"]),
        bottom_point=_point(DEFAULT_SETTINGS["bottom_point"]),
        square_count=int(DEFAULT_SETTINGS["square_count"]),
        row_count=int(DEFAULT_SETTINGS["row_count"]),
        vertical_direction=str(DEFAULT_SETTINGS["vertical_direction"]),
        direction=str(DEFAULT_SETTINGS["direction"]),
        max_pages=int(DEFAULT_SETTINGS["max_pages"]),
        results_per_page=int(DEFAULT_SETTINGS["results_per_page"]),
        request_delay=float(DEFAULT_SETTINGS["request_delay"]),
        include_detailed_description=bool(
            DEFAULT_SETTINGS["include_detailed_description"]
        ),
        output_dir=Path(str(DEFAULT_SETTINGS["output_dir"])),
    )
    result = asyncio.run(_download(settings, api_keys))
    logger.info(
        "Готово. Файлов: {}, объектов: {}",
        result.saved_files,
        result.saved_places,
    )
    return 0


async def _download(settings, api_keys):
    clients = tuple(
        WikimapiaClient(
            key,
            include_detailed_description=settings.include_detailed_description,
        )
        for key in api_keys
    )
    try:
        return await DownloadPlaces(clients, KmlPlacesWriter()).execute(
            settings, log=logger.info
        )
    finally:
        await asyncio.gather(*(client.close() for client in clients))


def _point(value: object) -> tuple[float, float]:
    latitude, longitude = str(value).split(",")
    return float(latitude), float(longitude)


if __name__ == "__main__":
    raise SystemExit(main())
