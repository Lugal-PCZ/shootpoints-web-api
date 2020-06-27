"""
This module handles the vertical and horizontal prism offsets.

Offset direction is always FROM the point TO the prism, as viewed
from the occupied station.

  Vertical Offset:
    vertical_distance > 0 = Up
    vertical_distance < 0 = Down
    
  Absolute Offsets:
    latitude_distance > 0 = North
    latitude_distance < 0 = South
    longitude_distance > 0 = East
    longitude_distance < 0 = West

  Relative Offsets:
    radial_distance > 0 = Away
    radial_distance < 0 = Toward
    tangent_distance > 0 = Right
    tangent_distance < 0 = Left
"""

from . import _database


offsets = {
    'vertical_distance': 0.0,
    'latitude_distance': 0.0,
    'longitude_distance': 0.0,
    'radial_distance': 0.0,
    'tangent_distance': 0.0,
}

_directions = {
    'vertical': ['Up', 'Down'],
    'latitude': ['North', 'South'],
    'longitude': ['East', 'West'],
    'radial': ['Away', 'Toward'],
    'tangent': ['Right', 'Left']
}


def get_readable_offsets() -> dict:
    """This function returns the prism offsets in human-readable form."""
    readable_offsets = {}
    for key, val in offsets.items():
        if key == 'vertical_distance':
            if val > 0:
                readable_offsets['vertical_direction'] = _directions['vertical'][0]
            elif val < 0:
                readable_offsets['vertical_direction'] = _directions['vertical'][1]
                val = abs(val)
        elif key == 'latitude_distance':
            if val > 0:
                readable_offsets['latitude_direction'] = _directions['latitude'][0]
            elif val < 0:
                readable_offsets['latitude_direction'] = _directions['latitude'][1]
                val = abs(val)
        elif key == 'longitude_distance':
            if val > 0:
                readable_offsets['longitude_direction'] = _directions['longitude'][0]
            elif val < 0:
                readable_offsets['longitude_direction'] = _directions['longitude'][1]
                val = abs(val)
        elif key == 'radial_distance':
            if val > 0:
                readable_offsets['radial_direction'] = _directions['radial'][0]
            elif val < 0:
                readable_offsets['radial_direction'] = _directions['radial'][1]
                val = abs(val)
        elif key == 'tangent_distance':
            if val > 0:
                readable_offsets['tangent_direction'] = _directions['tangent'][0]
            elif val < 0:
                readable_offsets['tangent_direction'] = _directions['tangent'][1]
                val = abs(val)
    return readable_offsets


def _validate_prism_offset(offsettype: str, distance: str, direction: str, errors: list) -> None:
    """This function verifies the sanity of the given prism offset."""
    global offsets
    try:
        distance = float(distance)
        try:
            if direction.upper() == _directions[offsettype][0].upper():
                distance = abs(distance)
            elif direction.upper() == _directions[offsettype][1].upper():
                distance = -abs(distance)
            else:
                errors.append(f'The {offsettype.title()} Offset direction entered ({direction}) was invalid. It must be {_directions[offsettype][0]} or {_directions[offsettype][1]}.')
            offsets[f'{offsettype}_distance'] = distance
        except KeyError:
            errors.append(f'No direction was given for the {offsettype.title()} Offset.')
    except ValueError:
        errors.append(f'The {offsettype.title()} Offset distance entered ({distance}) is not numerical.')


def set_prism_offsets(**kwargs) -> dict:
    """This function sets the prism offsets and saves them to the database."""
    outcome = {'errors': [], 'result': ''}
    for key, val in kwargs.items():
        if key == 'vertical_distance':
            _validate_prism_offset('vertical', kwargs['vertical_distance'], kwargs['vertical_direction'], outcome['errors'])
        elif key == 'latitude_distance':
            _validate_prism_offset('latitude', kwargs['latitude_distance'], kwargs['latitude_direction'], outcome['errors'])
        elif key == 'longitude_distance':
            _validate_prism_offset('longitude', kwargs['longitude_distance'], kwargs['longitude_direction'], outcome['errors'])
        elif key == 'radial_distance':
            _validate_prism_offset('radial', kwargs['radial_distance'], kwargs['radial_direction'], outcome['errors'])
        elif key == 'tangent_distance':
            _validate_prism_offset('tangent', kwargs['tangent_distance'], kwargs['tangent_direction'], outcome['errors'])
    if not outcome['errors']:
        data = (
            offsets['vertical_distance'],
            offsets['latitude_distance'],
            offsets['longitude_distance'],
            offsets['radial_distance'],
            offsets['tangent_distance'],
        )
        sql = (
            'UPDATE prism '
            'SET '
                'vertical_distance = ?, '
                'latitude_distance = ?, '
                'longitude_distance = ?, '
                'radial_distance = ?, '
                'tangent_distance = ?'
        )
        _database.save_to_database(sql, data)
        outcome['result'] = f'Prism offsets are now {str(offsets)}.'
    outcome['success'] = not outcome['errors']
    return outcome
