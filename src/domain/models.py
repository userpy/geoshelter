from dataclasses import dataclass
from pathlib import Path
from typing import Literal


Point = tuple[float, float]
HorizontalDirection = Literal["left", "right"]
VerticalDirection = Literal["up", "down"]
MAX_AREAS = 8


@dataclass(frozen=True)
class DownloadSettings:
    api_keys: tuple[str, ...]
    categories: tuple[int, ...]
    top_point: Point
    bottom_point: Point
    square_count: int
    row_count: int
    vertical_direction: VerticalDirection
    direction: HorizontalDirection
    max_pages: int
    results_per_page: int
    request_delay: float
    output_dir: Path
    include_detailed_description: bool = False
    selected_api_key_index: int = 0

    def __post_init__(self) -> None:
        if not self.api_keys:
            raise ValueError("Укажите хотя бы один API-ключ Wikimapia")
        if not 0 <= self.selected_api_key_index < len(self.api_keys):
            raise ValueError("Выбранный API-ключ не найден")
        if self.square_count < 1 or self.row_count < 1:
            raise ValueError(
                "Число областей должно быть не меньше 1"
            )
        if self.square_count * self.row_count > MAX_AREAS:
            raise ValueError(
                f"Можно выбрать не более {MAX_AREAS} областей"
            )

    @property
    def total_jobs(self) -> int:
        return len(self.categories) * self.square_count * self.row_count


@dataclass(frozen=True)
class Place:
    name: str
    longitude: float
    latitude: float
    description: str = ""


@dataclass(frozen=True)
class DownloadResult:
    saved_files: int
    saved_places: int
