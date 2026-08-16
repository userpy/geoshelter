import asyncio

import httpx
from loguru import logger

from domain.models import Place


class WikimapiaClient:
    URL = "https://api.wikimapia.org/"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30,
        detail_request_delay: float = 3,
        include_detailed_description: bool = False,
    ):
        self.api_key = api_key
        self.detail_request_delay = detail_request_delay
        self.include_detailed_description = include_detailed_description
        self._client = httpx.AsyncClient(timeout=timeout)

    async def fetch_page(
        self, category_id: int, page: int, bbox: str, count: int
    ) -> list[Place]:
        params = {
            "key": self.api_key,
            "function": "box",
            "bbox": bbox,
            "category": category_id,
            "page": page,
            "count": count,
            "format": "json",
        }
        logger.info(
            "GET {} | key=***, bbox={}, category={}, page={}, count={}",
            self.URL,
            bbox,
            category_id,
            page,
            count,
        )
        response = await self._client.get(self.URL, params=params)
        response.raise_for_status()
        data = response.json()
        self.validate_response(data)
        raw_places = data.get("places", data.get("folder", []))
        if not self.include_detailed_description:
            return [
                place for item in raw_places if (place := self._to_place(item))
            ]
        detailed_places = []
        for item in raw_places:
            detailed_places.append(await self._fetch_details(item))
        return [
            place
            for item in detailed_places
            if (place := self._to_place(item))
        ]

    async def _fetch_details(self, summary: dict) -> dict:
        """Load fields omitted by ``box``, most importantly description."""
        place_id = summary.get("id")
        if place_id is None or summary.get("description"):
            return summary
        if self.detail_request_delay > 0:
            await asyncio.sleep(self.detail_request_delay)

        params = {
            "key": self.api_key,
            "function": "place.getbyid",
            "id": place_id,
            "data_blocks": "main,location",
            "format": "json",
        }
        logger.debug("GET {} | function=place.getbyid, id={}", self.URL, place_id)
        response = await self._client.get(self.URL, params=params)
        response.raise_for_status()
        details = response.json()
        self._raise_api_error(details)
        if not isinstance(details, dict):
            raise RuntimeError("Неожиданный формат карточки места Wikimapia")

        # Coordinates are reliably present in the box response, while a caller may
        # request only the main block from place.getbyid.  Keep summary values as a
        # fallback and let the detailed response override them.
        return {**summary, **details}

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def validate_response(data: object) -> None:
        if not isinstance(data, dict):
            raise RuntimeError("Неожиданный формат ответа Wikimapia")
        WikimapiaClient._raise_api_error(data)
        if "places" not in data and "folder" not in data:
            message = data.get("message") or "в ответе нет places и folder"
            raise RuntimeError(f"Некорректный ответ Wikimapia: {message}")

    @staticmethod
    def _raise_api_error(data: dict) -> None:
        error = data.get("error") or data.get("debug")
        if error:
            if isinstance(error, dict):
                message = error.get("message") or error.get("description") or error
                if error.get("code") is not None:
                    message = f"{message} (код {error['code']})"
            else:
                message = error
            raise RuntimeError(f"Ошибка Wikimapia API: {message}")

    @staticmethod
    def _to_place(raw: dict) -> Place | None:
        location = raw.get("location")
        if not location:
            return None
        longitude = location.get("lon")
        latitude = location.get("lat")
        if longitude is None or latitude is None:
            return None
        description = []
        if raw.get("description"):
            description.append(raw["description"])
        categories = ", ".join(
            item.get("title", "")
            for item in raw.get("categories", [])
            if item.get("title")
        )
        if categories:
            description.append(f"Категории: {categories}")
        return Place(
            name=raw.get("title") or raw.get("name") or "Без названия",
            longitude=longitude,
            latitude=latitude,
            description="\n".join(description),
        )


validate_api_response = WikimapiaClient.validate_response
