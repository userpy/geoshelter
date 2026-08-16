from pathlib import Path
from typing import Protocol

from domain.models import Place


class PlacesClient(Protocol):
    async def fetch_page(
        self, category_id: int, page: int, bbox: str, count: int
    ) -> list[Place]: ...


class PlacesWriter(Protocol):
    def save(self, places: list[Place], output_file: Path) -> None: ...
