"""This module contains utilities to simplify calculations and conversions of surveying data."""

import math
import utm

from . import tripod
from . import prism


def _calculate_radial_offset(measurement: dict, offset: float) -> tuple:
    """This function calculates the northing and easting change due to toward/away radial prism offsets."""
    if not offset:
        return 0, 0
    horizontal_distance = math.hypot(measurement["delta_n"], measurement["delta_e"])
    proportion = offset / horizontal_distance
    n_diff = measurement["delta_n"] * proportion
    e_diff = measurement["delta_e"] * proportion
    return n_diff, e_diff


def _calculate_tangent_offset(measurement: dict, offset: float) -> tuple:
    """This function calculates the northing and easting change due to left/right prism offsets tangential the circle's radius at the prism."""
    if not offset:
        return 0, 0
    azimuth_to_prism = _calculate_azimuth(
        (0, 0), (measurement["delta_n"], measurement["delta_e"])
    )[0]
    distance_to_prism = math.hypot(measurement["delta_n"], measurement["delta_e"])
    distance_to_point = math.hypot(distance_to_prism, offset)
    offset_angle = math.degrees(
        math.acos(
            (distance_to_prism**2 + distance_to_point**2 - offset**2)
            / (2 * distance_to_prism * distance_to_point)
        )
    )
    if offset < 0:
        offset_angle *= -1
    azimuth_to_point = azimuth_to_prism + offset_angle
    # Correct azimuth when the offset moves it across due north
    if azimuth_to_point < 0:
        azimuth_to_point += 360
    elif azimuth_to_point > 360:
        azimuth_to_point -= 360
    n_diff = (
        distance_to_point
        * (math.sin(math.radians(90 - azimuth_to_point)) / math.sin(math.radians(90)))
        - measurement["delta_n"]
    )
    e_diff = (
        distance_to_point
        * (math.sin(math.radians(azimuth_to_point)) / math.sin(math.radians(90)))
        - measurement["delta_e"]
    )
    return n_diff, e_diff


def _calculate_wedge_offset(measurement: dict, offset: float) -> tuple:
    """This function calculates the northing and easting change due to cw/ccw wedge prism offsets on the circle's radius."""
    if not offset:
        return 0, 0
    azimuth_to_prism = _calculate_azimuth(
        (0, 0), (measurement["delta_n"], measurement["delta_e"])
    )[0]
    distance_to_prism = math.hypot(measurement["delta_n"], measurement["delta_e"])
    # Note: distance_to_point = distance_to_prism
    offset_angle = math.degrees(
        math.acos(
            ((2 * distance_to_prism**2) - offset**2) / (2 * distance_to_prism**2)
        )
    )
    if offset < 0:
        offset_angle *= -1
    azimuth_to_point = azimuth_to_prism + offset_angle
    if azimuth_to_point < 0:
        azimuth_to_point += 360
    elif azimuth_to_point > 360:
        azimuth_to_point -= 360
    n_diff = (
        distance_to_prism * math.cos(math.radians(azimuth_to_point))
    ) - measurement["delta_n"]
    e_diff = (
        distance_to_prism * math.sin(math.radians(azimuth_to_point))
    ) - measurement["delta_e"]
    return n_diff, e_diff


def _apply_atmospheric_correction(
    measurement: dict, pressure: int, temperature: int
) -> dict:
    """
    This function calculates and applies the atmospheric correction to the given measurement,
    air pressure in mmHg and air temperature in °C.
    Note: the total station should be set to 0ppm (760mmHg at 15°C).
    """
    p = pressure * 106.036
    t = temperature + 273.15
    Ka = (279.66 - (p / t)) * pow(10, -6)
    measurement["delta_n"] += measurement["delta_n"] * Ka
    measurement["delta_e"] += measurement["delta_e"] * Ka
    measurement["delta_z"] += measurement["delta_z"] * Ka
    measurement["delta_n"] = round(measurement["delta_n"], 3)
    measurement["delta_e"] = round(measurement["delta_e"], 3)
    measurement["delta_z"] = round(measurement["delta_z"], 3)
    return measurement


def _apply_offsets_to_measurement(measurement: dict) -> dict:
    """
    This function applies the occupied station coordinates, instrument height,
    and prism offsets to the measurement returned from the total station (which
    assumes that its coordinates are 0, 0, 0).
    """
    # Apply the occupied point offsets
    measurement["calculated_n"] = measurement["delta_n"] + tripod.occupied_point["n"]
    measurement["calculated_e"] = measurement["delta_e"] + tripod.occupied_point["e"]
    measurement["calculated_z"] = measurement["delta_z"] + tripod.occupied_point["z"]
    # Apply the instrument height offset
    measurement["calculated_z"] += tripod.instrument_height
    # Apply the prism vertical offset
    measurement["calculated_z"] += prism.offsets["vertical_distance"]
    # Apply the prism absolute offsets
    measurement["calculated_n"] += prism.offsets["latitude_distance"]
    measurement["calculated_e"] += prism.offsets["longitude_distance"]
    # Apply the prism relative offsets
    radial_n_diff, radial_e_diff = _calculate_radial_offset(
        measurement,
        prism.offsets["radial_distance"],
    )
    measurement["calculated_n"] += radial_n_diff
    measurement["calculated_e"] += radial_e_diff
    tangent_n_diff, tangent_e_diff = _calculate_tangent_offset(
        measurement,
        prism.offsets["tangent_distance"],
    )
    measurement["calculated_n"] += tangent_n_diff
    measurement["calculated_e"] += tangent_e_diff
    wedge_n_diff, wedge_e_diff = _calculate_wedge_offset(
        measurement,
        prism.offsets["wedge_distance"],
    )
    measurement["calculated_n"] += wedge_n_diff
    measurement["calculated_e"] += wedge_e_diff
    # Round the calculated values to the nearest millimeter
    measurement["calculated_n"] = round(measurement["calculated_n"], 3)
    measurement["calculated_e"] = round(measurement["calculated_e"], 3)
    measurement["calculated_z"] = round(measurement["calculated_z"], 3)
    return measurement


def _calculate_azimuth(point_a: tuple, point_b: tuple) -> tuple:
    """This function returns the azimuth in decimal degrees and D, M, S between two points (aN, aE) and (bN, bE)."""
    delta_n = point_b[0] - point_a[0]
    delta_e = point_b[1] - point_a[1]
    azimuth = math.degrees(math.atan2(delta_e, delta_n))
    if azimuth < 0.0:
        azimuth += 360.0
    degrees, remainder = divmod(azimuth, 1)
    minutes, remainder = divmod(remainder * 60, 1)
    seconds = round(remainder * 60)
    degrees, minutes, seconds = int(degrees), int(minutes), int(seconds)
    return (
        azimuth,
        degrees,
        minutes,
        seconds,
    )


def _calculate_coordinates_by_resection(
    P0: tuple,
    P1: tuple,
    r0: float,
    r1: float,
) -> tuple:
    """
    This function calculates the X and Y coordinates of an unknown point, given
    measurements to two points with known coordinates. From the point of view of the
    occupied point (P3), P0 is the known station to the left, and P1 is the one to the
    right. r0 and r1 are the measured distances to those two points, respectively.

    The math in this routine is from the “Intersection of Two Circles” example
    on the website http://paulbourke.net/geometry/circlesphere/
    """
    # The distance between P0 and P1
    d = math.hypot(P0[0] - P1[0], P0[1] - P1[1])
    # The length of the left segment of d where it intersects the perpendicular to the unknown point
    a = (r0**2 - r1**2 + d**2) / (2 * d)
    # The length of the leg from occupied_point, perpendicular to d
    # Note: this might throw an error if the three points are in a line
    h = math.sqrt(abs(r0**2 - a**2))
    # The XY coordinates of the point where the leg from point P3 intersects d
    P2 = (
        P0[0] + a * (P1[0] - P0[0]) / d,
        P0[1] + a * (P1[1] - P0[1]) / d,
    )
    # Finally, find the XY coordinates of P3
    P3 = (
        round(P2[0] + h * (P1[1] - P0[1]) / d, 3),
        round(P2[1] - h * (P1[0] - P0[0]) / d, 3),
    )
    return P3


def _convert_latlon_to_utm(latitude: float, longitude: float) -> tuple:
    """This function converts latitude/longitude coordinates to UTM."""
    easting, northing, zonenumber, zoneletter = utm.from_latlon(latitude, longitude)
    northing = round(northing, 3)
    easting = round(easting, 3)
    return (northing, easting, f"{zonenumber}{zoneletter}")


def _convert_utm_to_latlon(
    northing: float, easting: float, zonenumber: int, zoneletter: str
) -> tuple:
    """This function converts UTM coordinates to latitude/longitude."""
    latitude, longitude = utm.to_latlon(easting, northing, zonenumber, zoneletter)
    return (latitude, longitude)


def _calculate_backsight_variance(
    occupied_northing: float,
    occupied_easting: float,
    backsight_northing: float,
    backsight_easting: float,
    delta_n: float,
    delta_e: float,
) -> float:
    """
    This function calculates the variance between the expected
    backsight distance and the measured backsight distance.
    """
    expected_distance = math.hypot(
        occupied_northing - backsight_northing, occupied_easting - backsight_easting
    )
    measured_distance = math.hypot(delta_n, delta_e)
    return round(abs(expected_distance - measured_distance) * 100, 1)
