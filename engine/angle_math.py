"""This module contains utilities to simplify calculations and conversions of surveying data."""

import math
import utm

from . import tripod
from . import prism


def calculate_azimuth(point_a: tuple, point_b: tuple) -> float:
    """This function returns the azimuth in decimal degrees between two points (aN, aE) and (bN, bE)."""
    delta_n = point_b[0] - point_a[0]
    delta_e = point_b[1] - point_a[1]
    bearing = math.atan2(delta_e, delta_n) * (180/math.pi)
    if bearing < 0:
        azimuth = 360 + bearing
    else:
        azimuth = bearing
    return azimuth


def convert_latlon_to_utm(latitude: float, longitude: float) -> tuple:
    """This function converts latitude/longitude coordinates to UTM."""
    northing, easting, zonenumber, zoneletter = utm.from_latlon(latitude, longitude)
    northing = round(northing, 3)
    easting = round(easting, 3)
    return (northing, easting, f'{zonenumber}{zoneletter}')


def convert_utm_to_latlon(northing: float, easting: float, zonenumber: int, zoneletter: str) -> tuple:
    """This function converts UTM coordinates to latitude/longitude."""
    latitude, longitude = utm.to_latlon(northing, easting, zonenumber, zoneletter)
    return (latitude, longitude)


def apply_offsets_to_measurement(raw_measurement: dict) -> dict:
    """
    This function applies the occupied station coordinates, instrument height,
    and prism offsets to the measurement returned from the total station (which
    assumes that its coordinates are 0, 0, 0).
    """
    measurement = raw_measurement['measurement']
    # Apply the occupied point offsets
    occupied_point = tripod.get_occupied_point()['coordinates']
    measurement['calculated_n'] = measurement['delta_n'] + occupied_point['n']
    measurement['calculated_e'] = measurement['delta_e'] + occupied_point['e']
    measurement['calculated_z'] = measurement['delta_z'] + occupied_point['z']
    # Apply the instrument height offset
    instrument_height = tripod.get_instrument_height()['instrument_height']
    measurement['calculated_z'] += instrument_height
    # Apply the prism vertical offset
    prism_offsets = prism.get_prism_offset(True)['prism_offset']
    measurement['calculated_z'] += prism_offsets['vertical_distance']
    # Apply the prism absolute offsets
    measurement['calculated_n'] += prism_offsets['latitude_distance']
    measurement['calculated_e'] += prism_offsets['longitude_distance']
    # Apply the prism relative offsets
    radial_n_diff, radial_e_diff = _calculate_radial_offset(
        measurement,
        prism_offsets['radial_distance'],
    )
    measurement['calculated_n'] += radial_n_diff
    measurement['calculated_e'] += radial_e_diff
    # TODO: rethink the following, since it appears to stomp on previous offset calculations
    measurement['calculated_n'], measurement['calculated_e'] = _calculate_tangent_offset(
        measurement,
        prism_offsets['tangent_distance'],
    )
    # Round the calculated values to the nearest millimeter
    measurement['calculated_n'] = round(measurement['calculated_n'], 3)
    measurement['calculated_e'] = round(measurement['calculated_e'], 3)
    measurement['calculated_z'] = round(measurement['calculated_z'], 3)
    return {
        'success': raw_measurement['success'],
        'measurement': measurement,
    }


def _calculate_radial_offset(measurement: dict, offset: float) -> tuple:
    """This function calculates the northing and easting change due to toward/away radial prism offsets."""
    horizontal_distance = math.hypot(measurement['delta_n'], measurement['delta_e'])
    proportion = offset / horizontal_distance
    n_diff = measurement['delta_n'] * proportion
    e_diff = measurement['delta_e'] * proportion
    return n_diff, e_diff


def _calculate_tangent_offset(measurement: dict, offset: float) -> tuple:
    """This function calculates the northing and easting change due to left/right tangential prism offsets."""
    # TODO: Test these with real-world measurements
    distance_to_prism = math.hypot(measurement['delta_n'], measurement['delta_e'])
    distance_to_point = math.hypot(distance_to_prism, offset)
    offset_angle = math.degrees(math.acos((distance_to_prism**2 + distance_to_point**2 - offset**2) / (2 * distance_to_prism * distance_to_point)))
    azimuth_to_prism = calculate_azimuth(
        (0, 0),
        (measurement['delta_n'], measurement['delta_e']),
    )
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
    return point_n, point_e
