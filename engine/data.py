from . import station
from . import prism
from . import angle_math


def apply_offsets_to_measurement(raw_measurement: dict) -> dict:
    measurement = raw_measurement['measurement']
    # Apply the occupied point offsets
    occupied_point = station.get_occupied_point()['coordinates']
    measurement['n'] = measurement['delta_n'] + occupied_point['n']
    measurement['e'] = measurement['delta_e'] + occupied_point['e']
    measurement['z'] = measurement['delta_z'] + occupied_point['z']
    # Apply the instrument height offset
    instrument_height = station.get_instrument_height()['instrument_height']
    measurement['z'] += instrument_height
    # Apply the prism vertical offset
    prism_offsets = prism.get_prism_offset(False)['prism_offset']
    measurement['z'] += prism_offsets['vertical_distance']
    # Apply the prism absolute offsets
    measurement['n'] += prism_offsets['latitude_distance']
    measurement['e'] += prism_offsets['longitude_distance']
    # Apply the prism relative offsets
    radial_n_diff, radial_e_diff = angle_math.calculate_radial_offset(raw_measurement, prism_offsets['radial_distance'])
    measurement['n'] += radial_n_diff
    measurement['e'] += radial_e_diff
    tangent_n_diff, tangent_e_diff = angle_math.calculate_tangent_offset(raw_measurement, prism_offsets['tangent_distance'])
    measurement['n'] += tangent_n_diff
    measurement['e'] += tangent_e_diff
    # Round the calculated values to the nearest millimeter
    measurement['n'] = round(measurement['n'], 3)
    measurement['e'] = round(measurement['e'], 3)
    measurement['z'] = round(measurement['z'], 3)
    return {
        'success': raw_measurement['success'],
        'measurement': measurement,
    }
