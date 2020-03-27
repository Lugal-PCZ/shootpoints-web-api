import math
from decimal import Decimal


def calculate_azimuth(point_a: tuple, point_b: tuple) -> str:
    delta_n = point_b[0] - point_a[0]
    delta_e = point_b[1] - point_a[1]
    angle = math.atan2(delta_e, delta_n) * (180/math.pi)
    if angle < 0:
        bearing = 360 + angle
    else:
        bearing = angle
    degrees, remainder = divmod(bearing, 1)
    minutes, remainder = divmod(remainder * 60, 1)
    seconds = round(remainder * 60)
    return int(degrees), int(minutes), int(seconds)


def calculate_slope_distance(measurement: dict) -> float:
    horizontal_distance = math.hypot(measurement['delta_n'], measurement['delta_e'])
    slope_distance = math.hypot(horizontal_distance, measurement['delta_z'])
    return float(Decimal(slope_distance).quantize(Decimal('1.000')))
