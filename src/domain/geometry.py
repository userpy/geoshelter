from domain.models import Point


def build_bbox(top_point: Point, bottom_point: Point) -> str:
    lat_top, lon_left = top_point
    lat_bottom, lon_right = bottom_point
    if lat_top <= lat_bottom:
        raise ValueError("Широта верхней точки должна быть больше широты нижней")
    if lon_right <= lon_left:
        raise ValueError("Долгота нижней точки должна быть больше долготы верхней")
    return f"{lon_left},{lat_bottom},{lon_right},{lat_top}"


def shift_square_right(
    top_point: Point, bottom_point: Point, square_index: int
) -> tuple[Point, Point]:
    shift = (bottom_point[1] - top_point[1]) * square_index
    return (
        (top_point[0], top_point[1] + shift),
        (bottom_point[0], bottom_point[1] + shift),
    )


def shift_square_down(
    top_point: Point, bottom_point: Point, row_index: int
) -> tuple[Point, Point]:
    shift = (top_point[0] - bottom_point[0]) * row_index
    return (
        (top_point[0] - shift, top_point[1]),
        (bottom_point[0] - shift, bottom_point[1]),
    )

