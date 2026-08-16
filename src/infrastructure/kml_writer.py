from pathlib import Path

import simplekml

from domain.models import Place


class KmlPlacesWriter:
    def save(self, places: list[Place], output_file: Path) -> None:
        kml = simplekml.Kml()
        for place in places:
            point = kml.newpoint(
                name=place.name,
                coords=[(place.longitude, place.latitude)],
            )
            point.description = place.description
        kml.save(str(output_file))

