import os
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtCore import QSettings

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = (
    SRC_DIR.parent if (SRC_DIR.parent / "pyproject.toml").is_file() else Path.cwd()
)
ASSETS_DIR = SRC_DIR / "assets"
ICON_FILE = ASSETS_DIR / "app_icon.svg"
WIKIMAPIA_MARK_FILE = ASSETS_DIR / "wikimapia_mark.svg"
load_dotenv(PROJECT_DIR / ".env")

ORGANIZATION_NAME = "GeoShelter"
APPLICATION_NAME = "GeoShelter"


def create_user_settings() -> QSettings:
    """Return per-user settings in the platform's native storage."""
    return QSettings(
        QSettings.Format.NativeFormat,
        QSettings.Scope.UserScope,
        ORGANIZATION_NAME,
        APPLICATION_NAME,
    )


DEFAULT_SETTINGS = {
    "api_keys": os.getenv("WIKIMAPIA_API_KEY", ""),
    "categories": "44690, 2390",
    "top_point": "55.838340, 49.206620",
    "bottom_point": "55.795710, 49.305150",
    "square_count": 1,
    "row_count": 1,
    "vertical_direction": "down",
    "direction": "right",
    "max_pages": 10,
    "results_per_page": 100,
    "request_delay": 10.0,
    "include_detailed_description": False,
    "output_dir": "",
}
