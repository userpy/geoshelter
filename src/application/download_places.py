import asyncio
import math
from collections.abc import Callable

from application.errors import DownloadCancelled
from application.ports import PlacesClient, PlacesWriter
from application.rate_limiter import RequestRateLimiter
from domain.geometry import build_bbox, shift_square_down, shift_square_right
from domain.models import DownloadResult, DownloadSettings


class DownloadPlaces:
    def __init__(self, clients: tuple[PlacesClient, ...], writer: PlacesWriter):
        if not clients:
            raise ValueError("Нужен хотя бы один API-ключ")
        self.clients = clients
        self.writer = writer

    async def execute(
        self,
        settings: DownloadSettings,
        log: Callable[[str], None] = lambda _message: None,
        progress: Callable[[int, int], None] = lambda _value, _total: None,
        area_completed: Callable[[int, int, int], None] = (
            lambda _row, _column, _places: None
        ),
        area_started: Callable[[int, int, int], None] = (
            lambda _row, _column, _category_id: None
        ),
        key_status: Callable[[int, int, int, int, int], None] = (
            lambda _index, _count, _limit, _seconds, _errors: None
        ),
        is_cancelled: Callable[[], bool] = lambda: False,
        key_selected: Callable[[int], None] = lambda _index: None,
    ) -> DownloadResult:
        saved_files = 0
        saved_places = 0
        completed_jobs = 0
        rate_limiters = [
            RequestRateLimiter(limit=100, window_seconds=300)
            for _client in self.clients
        ]
        key_errors = [0 for _client in self.clients]
        self._next_client_index = settings.selected_api_key_index
        self._client_selection_lock = asyncio.Lock()
        concurrency = asyncio.Semaphore(len(self.clients))

        for category_id in settings.categories:
            log(f"Категория {category_id}")
            results: list[tuple[int, int]] = []

            async def process(row_index: int, square_index: int) -> None:
                nonlocal completed_jobs
                async with concurrency:
                    self._ensure_not_cancelled(is_cancelled)
                    area_started(row_index, square_index, category_id)
                    result = await self._process_area(
                        settings,
                        category_id,
                        row_index,
                        square_index,
                        rate_limiters,
                        key_errors,
                        key_status,
                        key_selected,
                        is_cancelled,
                        log,
                    )
                    results.append(result)
                    places_count = result[1]
                    completed_jobs += 1
                    area_completed(row_index, square_index, places_count)
                    progress(completed_jobs, settings.total_jobs)

            tasks = [
                asyncio.create_task(process(row_index, square_index))
                for row_index in range(settings.row_count)
                for square_index in range(settings.square_count)
            ]
            try:
                await asyncio.gather(*tasks)
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

            saved_files += sum(files for files, _places in results)
            saved_places += sum(places for _files, places in results)

        return DownloadResult(saved_files, saved_places)

    async def _process_area(
        self,
        settings: DownloadSettings,
        category_id: int,
        row_index: int,
        square_index: int,
        rate_limiters: list[RequestRateLimiter],
        key_errors: list[int],
        key_status: Callable[[int, int, int, int, int], None],
        key_selected: Callable[[int], None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> tuple[int, int]:
        vertical_index = (
            row_index if settings.vertical_direction == "down" else -row_index
        )
        row_top, row_bottom = shift_square_down(
            settings.top_point, settings.bottom_point, vertical_index
        )
        horizontal_index = (
            square_index if settings.direction == "right" else -square_index
        )
        shifted_top, shifted_bottom = shift_square_right(
            row_top, row_bottom, horizontal_index
        )
        bbox = build_bbox(shifted_top, shifted_bottom)
        area_label = (
            f"строка {row_index + 1}/{settings.row_count}, "
            f"столбец {square_index + 1}/{settings.square_count}"
        )
        log(f"  Область: {area_label}: {bbox}")
        places = []
        for page in range(1, settings.max_pages + 1):
            self._ensure_not_cancelled(is_cancelled)
            log(f"    {area_label}: страница {page}/{settings.max_pages}")
            page_places = await self._fetch_page(
                category_id,
                page,
                bbox,
                settings.results_per_page,
                rate_limiters,
                key_errors,
                key_status,
                key_selected,
                is_cancelled,
                log,
            )
            if not page_places:
                log(f"    {area_label}: объектов нет")
                break
            places.extend(page_places)
            if page < settings.max_pages:
                await self._delay(settings.request_delay, is_cancelled)

        if not places:
            log(f"  {area_label}: пустой KML не создан.")
            return 0, 0

        output_file = settings.output_dir / (
            f"wikimapia_{category_id}_row_{row_index + 1}_"
            f"square_{square_index + 1}_{shifted_top}_{shifted_bottom}.kml"
        )
        self.writer.save(places, output_file)
        log(f"  KML создан: {output_file} (объектов: {len(places)})")
        return 1, len(places)

    async def _fetch_page(
        self,
        category_id: int,
        page: int,
        bbox: str,
        count: int,
        limiters: list[RequestRateLimiter],
        key_errors: list[int],
        key_status: Callable[[int, int, int, int, int], None],
        key_selected: Callable[[int], None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> list:
        failed_indexes: set[int] = set()
        last_error: Exception | None = None
        while len(failed_indexes) < len(self.clients):
            client_index = await self._acquire_client(
                limiters,
                key_errors,
                failed_indexes,
                key_status,
                key_selected,
                is_cancelled,
                log,
            )
            try:
                places = await self.clients[client_index].fetch_page(
                    category_id, page, bbox, count
                )
            except Exception as error:
                last_error = error
                failed_indexes.add(client_index)
                key_errors[client_index] += 1
                limiter = limiters[client_index]
                key_status(
                    client_index,
                    limiter.count,
                    limiter.limit,
                    math.ceil(limiter.retry_after),
                    key_errors[client_index],
                )
                log(
                    f"    API-ключ №{client_index + 1}: ошибка. "
                    "Переключаюсь на следующий."
                )
                continue
            return places

        raise RuntimeError(
            f"Запрос не выполнен ни одним API-ключом: {last_error}"
        ) from last_error

    async def _acquire_client(
        self,
        limiters: list[RequestRateLimiter],
        key_errors: list[int],
        excluded_indexes: set[int],
        key_status: Callable[[int, int, int, int, int], None],
        key_selected: Callable[[int], None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> int:
        waiting_reported = False
        while True:
            self._ensure_not_cancelled(is_cancelled)
            async with self._client_selection_lock:
                for offset in range(len(limiters)):
                    index = (
                        self._next_client_index + offset
                    ) % len(limiters)
                    if index in excluded_indexes:
                        continue
                    limiter = limiters[index]
                    if limiter.try_acquire():
                        self._next_client_index = (index + 1) % len(limiters)
                        key_status(
                            index,
                            limiter.count,
                            limiter.limit,
                            math.ceil(limiter.retry_after),
                            key_errors[index],
                        )
                        key_selected(index)
                        return index

            available_indexes = [
                index
                for index in range(len(limiters))
                if index not in excluded_indexes
            ]
            waits = [limiters[index].retry_after for index in available_indexes]
            for index, limiter in enumerate(limiters):
                if index in excluded_indexes:
                    continue
                key_status(
                    index,
                    limiter.count,
                    limiter.limit,
                    math.ceil(limiter.retry_after),
                    key_errors[index],
                )
            if not waiting_reported:
                log(
                    "    Лимиты всех API-ключей исчерпаны. "
                    f"Ожидание: {min(waits):.0f} с."
                )
                waiting_reported = True
            await asyncio.sleep(min(0.25, max(0.05, min(waits))))

    @staticmethod
    def _ensure_not_cancelled(is_cancelled: Callable[[], bool]) -> None:
        if is_cancelled():
            raise DownloadCancelled

    async def _delay(
        self, seconds: float, is_cancelled: Callable[[], bool]
    ) -> None:
        loop = asyncio.get_running_loop()
        end_time = loop.time() + seconds
        while loop.time() < end_time:
            self._ensure_not_cancelled(is_cancelled)
            await asyncio.sleep(min(0.1, max(0, end_time - loop.time())))
