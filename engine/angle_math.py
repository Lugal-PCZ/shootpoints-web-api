import math
import utm


def calculate_azimuth(point_a: tuple, point_b: tuple) -> float:
    """Returns the azimuth in decimal degrees between two points (aN, aE) and (bN, bE)."""
    delta_n = point_b[0] - point_a[0]
    delta_e = point_b[1] - point_a[1]
    bearing = math.atan2(delta_e, delta_n) * (180/math.pi)
    if bearing < 0:
        azimuth = 360 + bearing
    else:
        azimuth = bearing
    return azimuth


def convert_latlon_to_utm(latitude: float, longitude: float) -> tuple:
    northing, easting, zonenumber, zoneletter = utm.from_latlon(latitude, longitude)
    northing = round(northing, 3)
    easting = round(easting, 3)
    return (northing, easting, f'{zonenumber}{zoneletter}')


def convert_utm_to_latlon(northing: float, easting: float, zonenumber: int, zoneletter: str) -> tuple:
    latitude, longitude = utm.to_latlon(northing, easting, zonenumber, zoneletter)
    return (latitude, longitude)

