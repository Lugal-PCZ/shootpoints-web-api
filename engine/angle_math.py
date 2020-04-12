import math

from . import station


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


def calculate_radial_offset(raw_measurement: dict, offset: float) -> tuple:
    measurement = raw_measurement['measurement']
    horizontal_distance = math.hypot(measurement['delta_n'], measurement['delta_e'])
    proportion = offset/horizontal_distance
    n_diff = round(measurement['delta_n']*proportion), 3)
    e_diff = round(measurement['delta_e']*proportion), 3)
    return n_diff, e_diff


def calculate_tangent_offset(raw_measurement: dict, offset: float) -> tuple:
    measurement = raw_measurement['measurement']
    # TODO: Test these with real-world measurements
    distance_to_prism = math.hypot(measurement['delta_n'], measurement['delta_e'])
    distance_to_point = math.hypot(distance_to_prism, offset)
    offset_angle = math.degrees(math.acos((distance_to_prism**2 + distance_to_point**2 - offset**2) / (2 * distance_to_prism * distance_to_point)))
    azimuth_to_prism = calculate_azimuth((0, 0), (measurement['delta_n'], measurement['delta_e']))
    if offset < 0:
        azimuth_to_point = azimuth_to_prism - offset_angle
    else:
        azimuth_to_point = azimuth_to_prism + offset_angle
    # Correct azimuth when the offset moves it across due north
    if azimuth_to_point < 0:
        azimuth_to_point += 360
    elif azimuth_to_point > 360:
        azimuth_to_point -= 360
    point_n = distance_to_point * math.cos(math.radians(azimuth_to_point))
    point_e = distance_to_point * math.sin(math.radians(azimuth_to_point))
    # Return the differences between the prism and the actual point, to match the pattern of other functions.
    n_diff = measurement['delta_n'] - point_n
    e_diff = measurement['delta_e'] - point_e
    n_diff = round(n_diff, 3)
    e_diff = round(e_diff, 3)
    return n_diff, e_diff
    