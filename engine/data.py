import sqlite3
import os
import math

from . import station
from . import prism
from . import angle_math


dbconn = sqlite3.connect('ShootPoints.db')
cursor = dbconn.cursor()
try:
    cursor.execute('SELECT 1 FROM stations')
except:
    # The ShootPoints.db database is empty, so initialize it with the default schema.
    with open('blank_database.sql', 'r') as f:
        sql = f.read().split(';')
        for each in sql:
            cursor.execute(each)
        dbconn.commit()


def apply_offsets_to_measurement(raw_measurement: dict) -> dict:
    measurement = raw_measurement['measurement']
    # Apply the occupied point offsets
    occupied_point = station.get_occupied_point()['coordinates']
    measurement['calculated_n'] = measurement['delta_n'] + occupied_point['n']
    measurement['calculated_e'] = measurement['delta_e'] + occupied_point['e']
    measurement['calculated_z'] = measurement['delta_z'] + occupied_point['z']
    # Apply the instrument height offset
    instrument_height = station.get_instrument_height()['instrument_height']
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
    horizontal_distance = math.hypot(measurement['delta_n'], measurement['delta_e'])
    proportion = offset / horizontal_distance
    n_diff = measurement['delta_n'] * proportion
    e_diff = measurement['delta_e'] * proportion
    return n_diff, e_diff


def _calculate_tangent_offset(measurement: dict, offset: float) -> tuple:
    # TODO: Test these with real-world measurements
    distance_to_prism = math.hypot(measurement['delta_n'], measurement['delta_e'])
    distance_to_point = math.hypot(distance_to_prism, offset)
    offset_angle = math.degrees(math.acos((distance_to_prism**2 + distance_to_point**2 - offset**2) / (2 * distance_to_prism * distance_to_point)))
    azimuth_to_prism = angle_math.calculate_azimuth(
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


def save_to_database(sql: str, data: tuple) -> bool:
    try:
        cursor.execute(sql, data)
        dbconn.commit()
        success = True
    except:
        success = False
    return success


def read_from_database(sql: str) -> bool:
    try:
        cursor.execute(sql)
        result = {'success': True, 'results': cursor.fetchall()}
    except sqlite3.Error as err:
        result = {'success': False, 'error_message': str(err)}
    return result
