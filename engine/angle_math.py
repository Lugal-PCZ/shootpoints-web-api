import math


def calculate_azimuth(point_a: tuple, point_b: tuple) -> float:
    """Returns the azimuth in decimal degrees between two points (aN, aE) and (bN, bE)."""
    delta_n = point_b[0] - point_a[0]
    delta_e = point_b[1] - point_a[1]
    bearing = math.atan2(delta_e, delta_n) * (180/math.pi)
    if bearing < 0:
        azimuth = 360 + bearing
    else:
        azimuth = bearing
    # degrees, remainder = divmod(azimuth, 1)
    # minutes, remainder = divmod(remainder * 60, 1)
    # seconds = round(remainder * 60)
    # return int(degrees), int(minutes), int(seconds)
    return azimuth
