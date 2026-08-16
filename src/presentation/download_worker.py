import asyncio

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from application.download_places import DownloadPlaces
from application.errors import DownloadCancelled
from domain.models import DownloadSettings
from infrastructure.kml_writer import KmlPlacesWriter
from infrastructure.wikimapia_client import WikimapiaClient


class DownloadWorker(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    key_status = pyqtSignal(int, int, int, int, int)
    key_selected = pyqtSignal(int)
    area_started = pyqtSignal(int, int, int)
    area_completed = pyqtSignal(int, int, int)
    finished = pyqtSignal(int, int)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, settings: DownloadSettings):
        super().__init__()
        self.settings = settings
        self._stop_requested = False

    @pyqtSlot()
    def stop(self) -> None:
        self._stop_requested = True

    @pyqtSlot()
    def run(self) -> None:
        asyncio.run(self._run_async())

    async def _run_async(self) -> None:
        clients = tuple(
            WikimapiaClient(
                key,
                include_detailed_description=(
                    self.settings.include_detailed_description
                ),
            )
            for key in self.settings.api_keys
        )
        use_case = DownloadPlaces(clients, KmlPlacesWriter())
        try:
            result = await use_case.execute(
                self.settings,
                log=self.log.emit,
                progress=self.progress.emit,
                key_status=self.key_status.emit,
                key_selected=self.key_selected.emit,
                area_started=self.area_started.emit,
                area_completed=self.area_completed.emit,
                is_cancelled=lambda: self._stop_requested,
            )
        except DownloadCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.finished.emit(result.saved_files, result.saved_places)
        finally:
            await asyncio.gather(*(client.close() for client in clients))
